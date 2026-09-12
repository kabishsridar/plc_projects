(* ==========================================
   POU: FB_Samyak_Multi
   ========================================== *)

=== DECLARATION ===
//SAMYAK 4016 Multi Slave Unit Customised Block
//Note: This FB_Samyak_Multi name is impotrtant when you create new POU.

FUNCTION_BLOCK FB_Samyak_Multi
VAR_INPUT
    Com_Slot      : BYTE := 1;    (* Port Number *)
    iSlaveCount   : INT := 1;     (* How many slaves active: 1 to 4 *)
    arrSlaveIDs   : ARRAY[1..4] OF BYTE := [1, 2, 3, 4]; (* Unit IDs *)
    arrDivisor    : ARRAY[1..4] OF REAL := [10.0, 10.0, 10.0, 10.0]; (* Scaling per Unit *)
    arrTare_In    : ARRAY[1..4] OF BOOL; (* Individual Tare triggers *)
END_VAR

VAR_OUTPUT
    arrWeight_Scaled : ARRAY[1..4] OF REAL; (* Scaled result per unit *)
    arrLine_Fault    : ARRAY[1..4] OF BOOL; (* Fault status per unit *)
    arrErrCount      : ARRAY[1..4] OF INT;  (* Error count per unit *)
    iCurrent_ID      : BYTE;                (* Current ID being polled *)
    xStatus_Busy     : BOOL;                (* Overall Bus Busy *)
END_VAR

VAR
    (* Internal ModRtuMast Instances *)
    fbRead         : ModRtuMast;
    fbTare         : ModRtuMast;
    
    (* Polling Control *)
    iStep          : INT := 0;
    iIdx           : INT := 1;    (* Current Loop Index *)
    Samyak_Buffer  : ARRAY[0..17] OF WORD;
    wTareCommand   : WORD := 1;
    
    (* Unique Timer/Trigger Instances *)
    rtTareTrig     : R_TRIG;
    rtErrTrig      : R_TRIG;
    tWatchdog      : TON;
    tRecovery      : TON;
END_VAR


=== IMPLEMENTATION ===


(* --- 1. INDIVIDUAL UNIT MONITORING --- *)
iCurrent_ID := arrSlaveIDs[iIdx]; 

(* Watchdog for Bus Hangs *)
tWatchdog(IN := (fbRead.Busy OR fbTare.Busy), PT := T#2000MS);
xStatus_Busy := fbRead.Busy OR fbTare.Busy;

(* Error Tracking for Current Index *)
rtErrTrig(CLK := (fbRead.Error OR fbTare.Error));
IF rtErrTrig.Q THEN
    arrErrCount[iIdx] := arrErrCount[iIdx] + 1;
END_IF

(* Reset on Success *)
IF fbRead.Done OR fbTare.Done THEN
    arrErrCount[iIdx] := 0;
    arrLine_Fault[iIdx] := FALSE;
END_IF

(* Line Fault Activation (10 errors) *)
IF arrErrCount[iIdx] >= 10 THEN
    arrLine_Fault[iIdx] := TRUE;
END_IF

(* Auto-Recovery pulse (5s) *)
tRecovery(IN := arrLine_Fault[iIdx], PT := T#5S);
IF tRecovery.Q THEN
    arrErrCount[iIdx] := 0;
    arrLine_Fault[iIdx] := FALSE;
END_IF

IF tWatchdog.Q THEN iStep := 99; END_IF

(* Check Tare for active slave *)
rtTareTrig(CLK := arrTare_In[iIdx]);

(* --- 2. SEQUENTIAL STATE MACHINE --- *)
CASE iStep OF
    
    0: (* READ CURRENT SLAVE *)
        fbTare(Execute := FALSE);
        fbRead(
            Execute := NOT (fbRead.Done OR fbRead.Error OR fbRead.Busy) 
                       AND NOT rtTareTrig.Q AND NOT arrLine_Fault[iIdx],
            COM     := Com_Slot,
            Serv    := arrSlaveIDs[iIdx],
            FCT     := 3, Addr := 0, Nb := 2, 
            Data    := ADR(Samyak_Buffer[0]), Timeout := 400
        );

        IF fbRead.Done THEN
            (* Scale weight using the array-based divisor for this specific index *)
            arrWeight_Scaled[iIdx] := TO_REAL(TO_DINT(SHL(TO_DWORD(Samyak_Buffer[1]), 16) OR TO_DWORD(Samyak_Buffer[0]))) / arrDivisor[iIdx];
            iStep := 10; (* Switch to next slave *)
        END_IF
        
        IF fbRead.Error THEN iStep := 10; END_IF (* Move on if error *)
        IF rtTareTrig.Q THEN iStep := 1; END_IF  (* Priority: Tare current unit *)

    1: (* PORT RELEASE *)
        fbRead(Execute := FALSE);
        IF NOT fbRead.Busy THEN iStep := 2; END_IF

    2: (* WRITE TARE FOR CURRENT SLAVE *)
        fbTare(
            Execute := TRUE,
            COM := Com_Slot, Serv := arrSlaveIDs[iIdx], 
            FCT := 6, Addr := 16, Nb := 1,
            Data := ADR(wTareCommand), Timeout := 1000
        );

        IF fbTare.Done OR fbTare.Error THEN
            arrTare_In[iIdx] := FALSE; (* Reset manual trigger *)
            iStep := 3;
        END_IF

    3: (* CLEANUP *)
        fbTare(Execute := FALSE);
        IF NOT fbTare.Busy THEN iStep := 10; END_IF

    10: (* INDEX ROTATION *)
        iIdx := iIdx + 1;
        IF iIdx > iSlaveCount THEN
            iIdx := 1; (* Back to first slave *)
        END_IF
        iStep := 0;

    99: (* EMERGENCY RESET *)
        fbRead(Execute := FALSE); fbTare(Execute := FALSE);
        IF NOT (fbRead.Busy OR fbTare.Busy) THEN iStep := 0; END_IF
        
END_CASE
