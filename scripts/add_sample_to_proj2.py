import sys
import os

project_path = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\rasi_feed_batching_2\Rasi_feeds_batching2.project"
log_path = r"C:\Users\kabish\.gemini\antigravity-ide\brain\6bb09710-7f3e-4443-b187-ad04e16ca8dc\scratch\add_sample_log.txt"

decl_code = """FUNCTION_BLOCK sample_read_two_weights
VAR_INPUT
    Enable : BOOL := TRUE;                     (* Enable continuous cyclic polling *)
    Com_Slot : BYTE := 1;                      (* PLC COM port number (e.g. COM1 = 1) *)
    Slave_Auto_ID : BYTE := 1;                 (* Modbus Slave ID for Auto Scale Indicator *)
    Slave_Semi_ID : BYTE := 2;                 (* Modbus Slave ID for Semi-Auto Scale Indicator *)
    iDivisor_Auto : REAL := 10.0;              (* Scale factor: Weight = Raw / Divisor *)
    iDivisor_Semi : REAL := 10.0;              (* Scale factor: Weight = Raw / Divisor *)
    Reg_Address : WORD := 0;                   (* Starting register address for weight *)
    Reg_Quantity : WORD := 2;                  (* Number of registers (2 words = 32-bit) *)
    Timeout_MS : UINT := 400;                  (* Response timeout in milliseconds *)
    Gap_Time : TIME := T#15MS;                 (* Inter-request line settling delay *)
END_VAR
VAR_OUTPUT
    Weight_Auto : REAL;                        (* Scaled live weight for Auto scale -> GVL.load_cell_auto *)
    Weight_Semi : REAL;                        (* Scaled live weight for Semi-Auto scale -> GVL.load_cell_semi_auto *)
    Weight_Raw_Auto : DINT;                    (* Raw 32-bit value from Auto indicator *)
    Weight_Raw_Semi : DINT;                    (* Raw 32-bit value from Semi-Auto indicator *)
    Auto_Scale_Online : BOOL;                  (* Health flag for Auto scale *)
    Semi_Scale_Online : BOOL;                  (* Health flag for Semi-Auto scale *)
    Current_Slave_Polled : BYTE;               (* Currently active polled slave address *)
    Current_Slot_Index : INT;                  (* 1 = Auto Indicator, 2 = Semi-Auto Indicator *)
    Poll_Cycles : UDINT;                       (* Total completed round-robin cycles *)
    Total_Error_Count : UDINT;                 (* Cumulative communication error count *)
    Status_Message : STRING(80);               (* Diagnostic status message *)
END_VAR
VAR
    fbModbus : ModRtuMast;                     (* Single ModRtuMast instance for the entire bus *)
    iStep : INT := 0;                          (* State machine: 0=Init, 1=Dispatch, 2=Wait, 3=Parse, 4=Gap *)
    iSlot : INT := 1;                          (* 1 = Auto, 2 = Semi-Auto *)
    
    Buffer_Auto : ARRAY[0..3] OF WORD;         (* Receive buffer for Auto indicator *)
    Buffer_Semi : ARRAY[0..3] OF WORD;         (* Receive buffer for Semi-Auto indicator *)
    
    tWatchdog : TON;                           (* Watchdog timer for bus protection *)
    tGapDelay : TON;                           (* Inter-request gap delay timer *)
    
    xDone : BOOL;
    xBusy : BOOL;
    xError : BOOL;
    wErrorCode : ERROR_ID;
END_VAR
"""

impl_code = """(* ============================================================================
   Method 3: Continuous Hardware Modbus Master Polling Table
   Replaces BLINK block with a single ModRtuMast round-robin state machine.
   ============================================================================ *)

IF NOT Enable THEN
    fbModbus(Execute := FALSE);
    iStep := 0;
    iSlot := 1;
    Status_Message := 'Polling Disabled';
    tGapDelay(IN := FALSE);
    tWatchdog(IN := FALSE);
    RETURN;
END_IF;

(* 1. Driver Watchdog Protection *)
tWatchdog(IN := fbModbus.Busy, PT := T#2000MS);
IF tWatchdog.Q THEN
    iStep := 99; (* Force emergency recovery *)
END_IF;

(* 2. Round-Robin Master Polling Table State Machine *)
CASE iStep OF
    0: (* Initialize Polling Table *)
        iSlot := 1;
        Current_Slot_Index := iSlot;
        Current_Slave_Polled := Slave_Auto_ID;
        fbModbus(Execute := FALSE);
        Status_Message := 'Modbus Master Polling Initialized';
        iStep := 1;

    1: (* Dispatch Query for Current Slot *)
        Current_Slot_Index := iSlot;
        IF iSlot = 1 THEN
            Current_Slave_Polled := Slave_Auto_ID;
            fbModbus(
                Execute := TRUE,
                COM     := Com_Slot,
                Serv    := Slave_Auto_ID,
                FCT     := 3, (* Read Holding Registers *)
                Addr    := Reg_Address,
                Nb      := Reg_Quantity,
                Data    := ADR(Buffer_Auto[0]),
                Timeout := Timeout_MS,
                Done    => xDone,
                Busy    => xBusy,
                Error   => xError,
                ErrorID => wErrorCode
            );
            Status_Message := CONCAT('Polling Auto Scale (Node ', CONCAT(BYTE_TO_STRING(Slave_Auto_ID), ')...'));
        ELSE
            Current_Slave_Polled := Slave_Semi_ID;
            fbModbus(
                Execute := TRUE,
                COM     := Com_Slot,
                Serv    := Slave_Semi_ID,
                FCT     := 3,
                Addr    := Reg_Address,
                Nb      := Reg_Quantity,
                Data    := ADR(Buffer_Semi[0]),
                Timeout := Timeout_MS,
                Done    => xDone,
                Busy    => xBusy,
                Error   => xError,
                ErrorID => wErrorCode
            );
            Status_Message := CONCAT('Polling Semi-Auto Scale (Node ', CONCAT(BYTE_TO_STRING(Slave_Semi_ID), ')...'));
        END_IF;
        iStep := 2;

    2: (* Await Driver Response *)
        IF fbModbus.Done THEN
            fbModbus(Execute := FALSE);
            iStep := 3; (* Advance to Parse Data *)
        ELSIF fbModbus.Error THEN
            fbModbus(Execute := FALSE);
            Total_Error_Count := Total_Error_Count + 1;
            IF iSlot = 1 THEN
                Auto_Scale_Online := FALSE;
                Status_Message := CONCAT('Auto Scale Comm Error ID: ', INT_TO_STRING(ERROR_ID_TO_INT(wErrorCode)));
            ELSE
                Semi_Scale_Online := FALSE;
                Status_Message := CONCAT('Semi-Auto Scale Comm Error ID: ', INT_TO_STRING(ERROR_ID_TO_INT(wErrorCode)));
            END_IF;
            iStep := 4; (* Advance to Gap delay *)
        END_IF;

    3: (* Parse Received Modbus Data into Scaled Weight *)
        IF iSlot = 1 THEN
            Weight_Raw_Auto := TO_DINT(SHL(TO_DWORD(Buffer_Auto[1]), 16) OR TO_DWORD(Buffer_Auto[0]));
            IF iDivisor_Auto <> 0.0 THEN
                Weight_Auto := TO_REAL(Weight_Raw_Auto) / iDivisor_Auto;
            ELSE
                Weight_Auto := TO_REAL(Weight_Raw_Auto);
            END_IF;
            GVL.load_cell_auto := Weight_Auto;
            Auto_Scale_Online := TRUE;
        ELSE
            Weight_Raw_Semi := TO_DINT(SHL(TO_DWORD(Buffer_Semi[1]), 16) OR TO_DWORD(Buffer_Semi[0]));
            IF iDivisor_Semi <> 0.0 THEN
                Weight_Semi := TO_REAL(Weight_Raw_Semi) / iDivisor_Semi;
            ELSE
                Weight_Semi := TO_REAL(Weight_Raw_Semi);
            END_IF;
            GVL.load_cell_semi_auto := Weight_Semi;
            Semi_Scale_Online := TRUE;
            Poll_Cycles := Poll_Cycles + 1;
        END_IF;
        iStep := 4;

    4: (* Inter-Frame Line Gap Delay (Lets RS485 Settle) *)
        tGapDelay(IN := TRUE, PT := Gap_Time);
        IF tGapDelay.Q THEN
            tGapDelay(IN := FALSE);
            (* Alternate Table Slot: 1 -> 2 -> 1 -> 2 ... *)
            IF iSlot = 1 THEN
                iSlot := 2;
            ELSE
                iSlot := 1;
            END_IF;
            iStep := 1; (* Dispatch next query *)
        END_IF;

    99: (* Emergency Recovery *)
        fbModbus(Execute := FALSE);
        tGapDelay(IN := FALSE);
        IF NOT fbModbus.Busy THEN
            iStep := 0;
        END_IF;
END_CASE;
"""

with open(log_path, "w") as f:
    try:
        proj = projects.open(project_path)
        app = proj.find("Application", True)[0]
        
        # Check if sample_read_two_weights already exists
        p = proj.find("sample_read_two_weights", True)
        if len(p) == 0:
            pou = app.create_pou("sample_read_two_weights", PouType.FunctionBlock)
            f.write("Created POU sample_read_two_weights\n")
        else:
            pou = p[0]
            f.write("Found existing POU sample_read_two_weights\n")
            
        pou.textual_declaration.replace(decl_code)
        pou.textual_implementation.replace(impl_code)
        f.write("Replaced declaration and implementation.\n")
        
        f.write("Building application...\n")
        msgs = app.build()
        err_count = 0
        for m in msgs:
            f.write(str(m.Severity) + ": " + str(m.Text) + "\n")
            if str(m.Severity) == "Error":
                err_count += 1
        f.write("Build finished with " + str(err_count) + " errors.\n")
        
        proj.save()
        proj.close()
        f.write("Project saved successfully.\n")
    except Exception as e:
        f.write("Error: " + str(e) + "\n")
