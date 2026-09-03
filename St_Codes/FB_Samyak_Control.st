(* ==========================================
   POU: FB_Samyak_Control
   ========================================== *)

=== DECLARATION ===
FUNCTION_BLOCK FB_Samyak_Control
VAR_INPUT
    Com_Slot      : BYTE := 1;     (* PLC COM port *)
    Slave_Dev_ID  : BYTE := 1;     (* Samyak slave ID *)
    iDivisor      : REAL := 10.0;  (* Scale factor: Weight_Scaled = Raw / iDivisor *)
    xTare_In      : BOOL;           (* Logic tare pulse *)
    xManual_Tare  : BOOL;           (* HMI/manual tare pulse *)
END_VAR

VAR_OUTPUT
    xStatus_Done   : BOOL;
    xStatus_Busy   : BOOL;
    xStatus_Error  : BOOL;
    iTotalErrCount : INT := 0;
    xLine_Fault    : BOOL;
    Weight_Raw     : DINT;
    Weight_Scaled  : REAL;
    wError_Code    : WORD; (* Check PLC & SAMYAK BaudRate, DevId, Parity; also check PLC serial port LED blink status and RS485 connection if error repeats *)
END_VAR

VAR
    fbRead         : ModRtuMast;
    fbTare         : ModRtuMast;
    iStep          : INT := 0;
    Samyak_Buffer  : ARRAY[0..17] OF WORD;
    wTareCommand   : WORD := 1;

    rtTareTrig     : R_TRIG;
    rtErrTrig      : R_TRIG;
    tStuckWatchdog : TON;
    tRecoveryTimer : TON;

    xTareReq       : BOOL := FALSE; (* Internal tare request latch *)
END_VAR


=== IMPLEMENTATION ===

(* --- 1) Error Tracking + Auto Recovery --- *)
tStuckWatchdog(IN := (fbRead.Busy OR fbTare.Busy), PT := T#2000MS);

rtErrTrig(CLK := (fbRead.Error OR fbTare.Error));
IF rtErrTrig.Q THEN
    iTotalErrCount := iTotalErrCount + 1;
END_IF

IF fbRead.Done OR fbTare.Done THEN
    iTotalErrCount := 0;
    xLine_Fault := FALSE;
END_IF

IF iTotalErrCount >= 10 THEN
    xLine_Fault := TRUE;
END_IF

tRecoveryTimer(IN := xLine_Fault, PT := T#5S);
IF tRecoveryTimer.Q THEN
    iTotalErrCount := 0;
    xLine_Fault := FALSE;
END_IF

IF tStuckWatchdog.Q THEN
    iStep := 99;
END_IF

(* Capture tare request from either input pulse *)
rtTareTrig(CLK := xTare_In OR xManual_Tare);
IF rtTareTrig.Q THEN
    xTareReq := TRUE;
END_IF

(* --- 2) Modbus State Machine --- *)
CASE iStep OF

    0:  (* Continuous Read *)
        fbTare(Execute := FALSE);

        fbRead(
            Execute := NOT (fbRead.Done OR fbRead.Error OR fbRead.Busy)
                       AND NOT xTareReq
                       AND NOT xLine_Fault,
            COM     := Com_Slot,
            Serv    := Slave_Dev_ID,
            FCT     := 3,
            Addr    := 0,
            Nb      := 2,
            Data    := ADR(Samyak_Buffer[0]),
            Timeout := 400,
            Done    => xStatus_Done,
            Busy    => xStatus_Busy,
            Error   => xStatus_Error,
            ErrorID => wError_Code
        );

        IF xStatus_Done THEN
            Weight_Raw := TO_DINT(SHL(TO_DWORD(Samyak_Buffer[1]), 16) OR TO_DWORD(Samyak_Buffer[0]));
            Weight_Scaled := TO_REAL(Weight_Raw) / iDivisor;
        END_IF

        IF xTareReq THEN
            iStep := 1;
        END_IF

    1:  (* Port Release *)
        fbRead(Execute := FALSE);
        IF NOT fbRead.Busy THEN
            iStep := 2;
        END_IF

    2:  (* Execute Tare *)
        fbTare(
            Execute := TRUE,
            COM     := Com_Slot,
            Serv    := Slave_Dev_ID,
            FCT     := 6,
            Addr    := 16,
            Nb      := 1,
            Data    := ADR(wTareCommand),
            Timeout := 1000,
            Done    => xStatus_Done,
            Busy    => xStatus_Busy,
            Error   => xStatus_Error,
            ErrorID => wError_Code
        );

        IF fbTare.Done OR fbTare.Error THEN
            xTareReq := FALSE;
            iStep := 3;
        END_IF

    3:  (* Return to Read *)
        fbTare(Execute := FALSE);
        IF NOT fbTare.Busy THEN
            iStep := 0;
        END_IF

    99: (* Emergency Recovery *)
        fbRead(Execute := FALSE);
        fbTare(Execute := FALSE);

        IF NOT (fbRead.Busy OR fbTare.Busy) THEN
            iTotalErrCount := 0;
            iStep := 0;
        END_IF

END_CASE

