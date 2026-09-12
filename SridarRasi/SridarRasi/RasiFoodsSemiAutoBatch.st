FUNCTION_BLOCK Semi_Auto_Batching_V15
VAR_INPUT
    Start_Button : BOOL;                                 // Optional start pin (legacy). Also ORed with GVL.Start_Button (%MX2.0 HMI) and Start_PB
    Start_PB : BOOL;                                     // Physical Start pushbutton DI (one-shot pulse)
    Auto_Mode_DI : BOOL;                                 // Auto Mode DI: TRUE = start/resume allowed; FALSE = HMI/PB start ignored
    E_Stop_Active : BOOL;                                // Emergency Stop circuit status (NC contact: TRUE = Healthy/Run permitted, FALSE = E-Stop tripped)
    Reset : BOOL;                                        // System reset pulse (clears active steps, outputs, alarms, and error flags)
    Fault_Reset : BOOL;                                  // Rising-edge fault acknowledge: clears Error_Code if live fault cleared
    Semi_Auto_Bin_Material_Mapping : ARRAY[1..10] OF INT;// Array mapping physical Silos 1..10 to Recipe Material IDs (1..20, 0 = Silo skipped)
    Semi_Auto_Coarse_To_Fine_Speed : ARRAY[1..10] OF REAL;// Weight offset threshold (kg) before target to transition from Coarse to Fine feeding
    Semi_Auto_Bin_Tolerance : ARRAY[1..10] OF REAL;      // Allowable weight tolerance window (±kg) around target weight for each silo
    Inter_Bin_Delay : TIME := T#2S;                      // Pause after Bin*=FALSE: tailings fall on SAME bin ID; then next mat (Semi e.g. T#2S)
    Excess_Allowed : BOOL := FALSE;                      // Overfill handling policy: TRUE = proceed if target is exceeded, FALSE = raise alarm and halt
    load_cell_value : REAL;                              // Live gross weight input reading from the Semi-Auto scale load cell (kg)
    Target_Batch_Cycles : INT := 1;                      // Target number of batch cycle repetitions configured from HMI (defaults to 1)
    Next_Cycle_Start : BOOL;                             // NextBatchStart: after a completed cycle (Target>1), press when this FB scale < Empty_Weight_Limit
    Empty_Weight_Limit : REAL := 0.5;                    // Both scales must be LT this (kg) before dosing, Next_Cycle_Start, or Tare pulse
    Line_Fault : BOOL;                                   // Wire from FB_Samyak_Multi.arrLine_Fault[n] (Semi scale). TRUE = hold process
END_VAR
VAR_OUTPUT
    Semi_Auto_Bin : ARRAY[1..10] OF BOOL;                // Coarse feeding valve / gate actuation command outputs for Silos 1..10
    semi_auto_bin_cutoff : ARRAY[1..10] OF BOOL;         // Fine feeding valve / vibrator cutoff actuation command outputs for Silos 1..10
    semi_auto_bin_motor : ARRAY[1..10] OF BOOL;          // Feeder / screw conveyor motor run commands for Silos 1..10
    Actual_Weights : ARRAY[1..10] OF REAL;               // Net material weight (kg) successfully dosed for each silo in the current cycle
    Semi_Auto_Sum_ActWeight : REAL;                      // Sum of Actual_Weights[1..10] / GVL.Semi_Auto_Weights %MD350; hold until Reset, accepted Next_Cycle_Start, or new job Start; HMI GVL.Semi_Auto_Total_Actual_Weight %MD184
    Semi_Auto_Target_Weight : ARRAY[1..10] OF REAL;      // Per-bin target kg (bin index 1..10) — ST mirrors GVL.Semi_Auto_Target_Weights (plant %MD410)
    Sequence_Complete : BOOL;                            // Handshake flag: TRUE when all mapped Semi-Auto silos have completed dosing and settling
    Active_Material_ID : INT;                            // Recipe Material ID currently being dosed (1..20, 0 when idle/complete)
    Active_Bin_ID : INT;                                 // Physical Silo index currently being dosed (1..10, 0 when idle/complete)
    Active_Target_Weight : REAL;                         // Target weight setpoint (kg) of the ingredient currently being dosed
    Active_Live_Weight : REAL;                           // Live net/tared weight (kg) accumulated into the scale for the active silo
    Current_Step : INT;                                  // Real-time sequence step:
                                                         //   0   = Idle / Waiting for Start
                                                         //   1..10 = Dosing Silos 1..10 (feeding coarse/fine)
                                                         //   31  = Settling delay in progress
                                                         //   32  = Sequence complete
    Cycle_Manager_State : INT;                           // Master supervisory cycle manager state:
                                                         //   0   = System Idle / Stopped
                                                         //   1   = Running active batch cycle
                                                         //   4   = All target batch cycles completed successfully
                                                         //   5   = Paused between cycles (Cycle Hold active)
    Excess_Alarm : BOOL;                                 // TRUE when Live > Target+Tolerance and Excess_Allowed=FALSE (remove excess from tank)
    Error_Code : INT;                                    // Fault diagnostic code (mirrors GVL.Error_Code)
    Semi_Auto_Current_Batch_Cycle : INT;                 // Active batch cycle number currently processing (1..Target_Batch_Cycles)
    Semi_Auto_Completed_Batch_Cycles : INT;              // Total number of batch cycle loops completed successfully
    Semi_Auto_All_Cycles_Complete : BOOL;                // Master flag: TRUE when all Target_Batch_Cycles have finished
    Status_Message : STRING(80);                         // Real-time human-readable process status and diagnostic text message
    Tare_Semi_Auto_Batch : BOOL;                         // One-scan pulse to Samyak ONLY when BOTH scales LT Empty_Weight_Limit (never after batch with product on scale)
    Waiting_Next_Batch : BOOL;                           // TRUE in state 5 while Current < Target (HMI hide/lamp); FALSE when next cycle runs; never TRUE on last cycle
    Next_Cycle_Ready : BOOL;                             // TRUE when hopper is confirmed empty (load_cell <= Empty_Weight_Limit) and ready for next cycle
END_VAR
VAR
    bin_last_weight : REAL;
    actual_bin : REAL;
    target_weight : REAL;
    cutoff_trigger_weight : REAL;
    min_tol_weight : REAL;
    max_tol_weight : REAL;
    Paused_By_Hold : BOOL;
    Effective_Delay : TIME;                              // Final settle Step 31
    Inter_Bin_Settling : BOOL;
    Inter_Bin_Settle_Arm : INT;
    Inter_Bin_Timer : TON;
    Settle_Hold_Step : INT;
    Settle_Hold_Mat : INT;
    Settle_Hold_Target : REAL;
    Inter_Bin_Next_Step : INT;
    Mat_Idx : INT;
    j_Mat : INT;
    i : INT;
    j : INT;
    Completion_Timer : TON;
    Empty_Debounce_Timer : TON;                          // 1s filter for empty scale verification in State 5
    Next_Cycle_Last : BOOL;
    Next_Cycle_Rising : BOOL;
    Between_Cycle_Hold : BOOL;
    Tare_Pulse_Req : BOOL;
    eff_empty_limit : REAL;
    Start_Cmd : BOOL;
    Start_Cmd_Last : BOOL;
    Start_Pulse : BOOL;
    Reset_Last : BOOL;
    Reset_Pulse : BOOL;
    Fault_Reset_Last : BOOL;
    Fault_Reset_Pulse : BOOL;
    First_Scan_Done : BOOL;
    Scale_Empty_OK : BOOL;
    Semi_Has_Active_Bins : BOOL;
    Auto_Has_Active_Bins : BOOL;
    Duplicate_Found : BOOL;
    Duplicate_Vs_Auto : BOOL;
    Invalid_Material_Range : BOOL;
    Weight_Limit_Error : BOOL;
    Semi_Mapping_All_Zero : BOOL;
    Internal_FB_Start : BOOL;
    Last_Dosing_Step : INT;
END_VAR

// -----------------------------------------------------------------------------
// 0. TIMINGS & THRESHOLDS
// -----------------------------------------------------------------------------
Effective_Delay := Inter_Bin_Delay;
IF Effective_Delay = T#0S THEN
    Effective_Delay := T#2S;
END_IF;

eff_empty_limit := Empty_Weight_Limit;
IF eff_empty_limit <= 0.0 THEN
    eff_empty_limit := GVL.Empty_Weight_Limit;
END_IF;
IF eff_empty_limit <= 0.0 THEN
    eff_empty_limit := 0.5;
END_IF;

Scale_Empty_OK := (load_cell_value < eff_empty_limit) AND (GVL.load_cell_semi_auto < eff_empty_limit)
    AND (GVL.load_cell_auto < eff_empty_limit);

// Edge Detections
Start_Cmd := (Start_Button OR GVL.Start_Button OR Start_PB) AND Auto_Mode_DI;
Start_Pulse := Start_Cmd AND NOT Start_Cmd_Last;
Start_Cmd_Last := Start_Cmd;

Next_Cycle_Rising := (Next_Cycle_Start OR GVL.Next_Cycle_Start) AND NOT Next_Cycle_Last;
Next_Cycle_Last := (Next_Cycle_Start OR GVL.Next_Cycle_Start);

Reset_Pulse := (Reset OR GVL.Reset) AND NOT Reset_Last;
Reset_Last := (Reset OR GVL.Reset);

Fault_Reset_Pulse := Fault_Reset AND NOT Fault_Reset_Last;
Fault_Reset_Last := Fault_Reset;

// -----------------------------------------------------------------------------
// 1. FIRST SCAN POWER-RESUME & RETAIN SYNC
// -----------------------------------------------------------------------------
IF NOT First_Scan_Done THEN
    First_Scan_Done := TRUE;
    
    // Restore Mapping Retain if GVL uninitialized
    FOR i := 1 TO 10 DO
        IF (GVL.Semi_Auto_Bin_Material_Mapping[i] = 0) AND (PersistentVars.Ret_Semi_Bin_Material_Mapping[i] > 0) THEN
            GVL.Semi_Auto_Bin_Material_Mapping[i] := PersistentVars.Ret_Semi_Bin_Material_Mapping[i];
        END_IF;
    END_FOR;

    // Power Resume Logic: restore exact state without corrupting actual weights with live load cell
    IF PersistentVars.Ret_Semi_Process_Was_Active AND (PersistentVars.Ret_Semi_Cycle_Manager_State = 1) 
       AND (PersistentVars.Ret_Semi_Resume_Step >= 1) AND (PersistentVars.Ret_Semi_Resume_Step <= 10) THEN
        
        Current_Step := PersistentVars.Ret_Semi_Resume_Step;
        Last_Dosing_Step := Current_Step;
        Cycle_Manager_State := 1;
        Internal_FB_Start := TRUE;
        Between_Cycle_Hold := FALSE;
        GVL.Run := TRUE;
        GVL.Current_Batch_Cycle := PersistentVars.Ret_Semi_Current_Batch_Cycle;
        GVL.Completed_Batch_Cycles := PersistentVars.Ret_Semi_Completed_Batch_Cycles;
        IF PersistentVars.Ret_Semi_Target_Batch_Cycles > 0 THEN
            GVL.Target_Batch_Cycles := PersistentVars.Ret_Semi_Target_Batch_Cycles;
        END_IF;

        // Restore EXACT dosed weights from retain
        Semi_Auto_Sum_ActWeight := 0.0;
        FOR i := 1 TO 10 DO
            Actual_Weights[i] := PersistentVars.Ret_Semi_Actual_Weights[i];
            GVL.Semi_Auto_Weights[i] := Actual_Weights[i];
            Semi_Auto_Sum_ActWeight := Semi_Auto_Sum_ActWeight + Actual_Weights[i];
        END_FOR;
        GVL.Semi_Auto_Total_Actual_Weight := Semi_Auto_Sum_ActWeight;

        // Restore tare baseline and active weights (LOCKED - no live load cell overwrite on boot)
        bin_last_weight := PersistentVars.Ret_Semi_bin_last_weight;
        Active_Live_Weight := PersistentVars.Ret_Semi_Active_Live_Weight;
        GVL.Semi_Auto_Active_Live_Weight := Active_Live_Weight;
        Active_Material_ID := PersistentVars.Ret_Semi_Active_Material_ID;
        Active_Bin_ID := PersistentVars.Ret_Semi_Active_Bin_ID;
        Active_Target_Weight := PersistentVars.Ret_Semi_Active_Target_Weight;
        GVL.Semi_Auto_Active_Mat := Active_Material_ID;
        GVL.Semi_Auto_Active_Bin := Active_Bin_ID;
        GVL.Semi_Auto_Active_Target_Weight := Active_Target_Weight;

        // Hold feeders OFF until safety checks pass; strictly inhibit tare pulse
        Paused_By_Hold := TRUE;
        Tare_Pulse_Req := FALSE;
        Tare_Semi_Auto_Batch := FALSE;
        Status_Message := CONCAT('Semi-Auto [POWER RESUME]: Resumed Step ', INT_TO_STRING(Current_Step));

    ELSIF (PersistentVars.Ret_Semi_Cycle_Manager_State = 5) THEN
        Cycle_Manager_State := 5;
        Between_Cycle_Hold := TRUE;
        Current_Step := 32;
        Sequence_Complete := TRUE;
        GVL.Semi_Auto_Sequence_Complete := TRUE;
        GVL.Run := TRUE;
        GVL.Current_Batch_Cycle := PersistentVars.Ret_Semi_Current_Batch_Cycle;
        GVL.Completed_Batch_Cycles := PersistentVars.Ret_Semi_Completed_Batch_Cycles;
        IF PersistentVars.Ret_Semi_Target_Batch_Cycles > 0 THEN
            GVL.Target_Batch_Cycles := PersistentVars.Ret_Semi_Target_Batch_Cycles;
        END_IF;
        FOR i := 1 TO 10 DO
            Actual_Weights[i] := PersistentVars.Ret_Semi_Actual_Weights[i];
            GVL.Semi_Auto_Weights[i] := Actual_Weights[i];
        END_FOR;
        Tare_Pulse_Req := FALSE;
        Tare_Semi_Auto_Batch := FALSE;
        Status_Message := 'Semi-Auto [POWER RESUME]: Waiting empty scale & Next_Cycle_Start';

    ELSE
        // Clean Idle
        Current_Step := 0;
        Cycle_Manager_State := 0;
        Internal_FB_Start := FALSE;
        Between_Cycle_Hold := FALSE;
        Sequence_Complete := FALSE;
        Tare_Pulse_Req := FALSE;
        Tare_Semi_Auto_Batch := FALSE;
        Next_Cycle_Ready := FALSE;
        Status_Message := 'Semi-Auto [Idle]: Ready - Waiting for Start';
    END_IF;
END_IF;

// Maintain continuous retain snapshot of HMI mappings
FOR i := 1 TO 10 DO
    PersistentVars.Ret_Semi_Bin_Material_Mapping[i] := GVL.Semi_Auto_Bin_Material_Mapping[i];
END_FOR;

// -----------------------------------------------------------------------------
// 2. CONFIGURATION CHECKS & ERROR DIAGNOSTICS
// -----------------------------------------------------------------------------
Duplicate_Found := FALSE;
Duplicate_Vs_Auto := FALSE;
Semi_Mapping_All_Zero := TRUE;
Invalid_Material_Range := FALSE;
Weight_Limit_Error := FALSE;
Semi_Has_Active_Bins := FALSE;
Auto_Has_Active_Bins := FALSE;

GVL.Semi_Auto_Total_Target_Weight := 0.0;
GVL.Semi_Auto_Material_Count := 0;

FOR i := 1 TO 10 DO
    Mat_Idx := Semi_Auto_Bin_Material_Mapping[i];
    IF (Mat_Idx < 1) OR (Mat_Idx > 20) THEN
        Mat_Idx := GVL.Semi_Auto_Bin_Material_Mapping[i];
    END_IF;
    
    IF Mat_Idx <> 0 THEN
        Semi_Mapping_All_Zero := FALSE;
    END_IF;
    IF (Mat_Idx < 0) OR (Mat_Idx > 20) THEN
        Invalid_Material_Range := TRUE;
    END_IF;
    
    IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) THEN
        // Duplicate check within Semi-Auto
        FOR j := 1 TO 10 DO
            IF j <> i THEN
                j_Mat := Semi_Auto_Bin_Material_Mapping[j];
                IF (j_Mat < 1) OR (j_Mat > 20) THEN
                    j_Mat := GVL.Semi_Auto_Bin_Material_Mapping[j];
                END_IF;
                IF (j_Mat = Mat_Idx) THEN
                    Duplicate_Found := TRUE;
                END_IF;
            END_IF;
        END_FOR;
        // Duplicate check vs Auto
        FOR j := 1 TO 6 DO
            j_Mat := GVL.Auto_Bin_Material_Mapping[j];
            IF (j_Mat = Mat_Idx) THEN
                Duplicate_Vs_Auto := TRUE;
            END_IF;
        END_FOR;
        
        target_weight := GVL.Recipe_Weights[Mat_Idx];
        IF target_weight > 0.0 THEN
            GVL.Semi_Auto_Total_Target_Weight := GVL.Semi_Auto_Total_Target_Weight + target_weight;
            GVL.Semi_Auto_Material_Count := GVL.Semi_Auto_Material_Count + 1;
            Semi_Has_Active_Bins := TRUE;
            IF target_weight < (Semi_Auto_Coarse_To_Fine_Speed[i] + Semi_Auto_Bin_Tolerance[i]) THEN
                Weight_Limit_Error := TRUE;
            END_IF;
        END_IF;
    END_IF;
END_FOR;

// Auto Active Bins Check
FOR i := 1 TO 6 DO
    Mat_Idx := GVL.Auto_Bin_Material_Mapping[i];
    IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) THEN
        IF GVL.Recipe_Weights[Mat_Idx] > 0.0 THEN
            Auto_Has_Active_Bins := TRUE;
        END_IF;
    END_IF;
END_FOR;

// Error Evaluation
IF load_cell_value > 500.0 THEN
    Error_Code := 21;
    GVL.Error_Code := 21;
    Status_Message := 'Semi_Error_Code 21: Scale Overload (> 500 kg)!';
ELSIF Line_Fault THEN
    Error_Code := 5;
    GVL.Error_Code := 5;
    Status_Message := 'Semi_Error_Code 5: Semi Scale Line_Fault Communication Error!';
ELSIF Duplicate_Found THEN
    Error_Code := 9;
    GVL.Error_Code := 9;
    Status_Message := 'Semi_Error_Code 9: Duplicate Material ID within Semi bins!';
ELSIF Invalid_Material_Range THEN
    Error_Code := 2;
    GVL.Error_Code := 2;
    Status_Message := 'Semi_Error_Code 2: Material Index out of range (must be 1..20)!';
ELSIF Weight_Limit_Error THEN
    Error_Code := 3;
    GVL.Error_Code := 3;
    Status_Message := 'Semi_Error_Code 3: Recipe weight < Coarse_To_Fine_Speed + Tolerance!';
ELSIF Duplicate_Vs_Auto THEN
    Error_Code := 7;
    GVL.Error_Code := 7;
    Status_Message := 'Semi_Error_Code 7: Material ID duplicated on Auto and Semi-Auto!';
ELSIF (Error_Code <> 4) THEN
    Error_Code := 0;
END_IF;

// -----------------------------------------------------------------------------
// 3. MASTER RESET & FAULT RESET
// -----------------------------------------------------------------------------
IF Reset_Pulse THEN
    FOR i := 1 TO 10 DO
        Semi_Auto_Bin[i] := FALSE;
        semi_auto_bin_cutoff[i] := FALSE;
        semi_auto_bin_motor[i] := FALSE;
        Actual_Weights[i] := 0.0;
        Semi_Auto_Target_Weight[i] := 0.0;
        GVL.Semi_Auto_Bin[i] := FALSE;
        GVL.semi_auto_bin_cutoff[i] := FALSE;
        GVL.semi_auto_bin_motor[i] := FALSE;
        GVL.Semi_Auto_Weights[i] := 0.0;
        GVL.Semi_Auto_Target_Weights[i] := 0.0;
        PersistentVars.Ret_Semi_Actual_Weights[i] := 0.0;
        PersistentVars.Ret_Semi_Bin_Target_Weights[i] := 0.0;
    END_FOR;
    Semi_Auto_Sum_ActWeight := 0.0;
    GVL.Semi_Auto_Total_Actual_Weight := 0.0;
    Sequence_Complete := FALSE;
    GVL.Semi_Auto_Sequence_Complete := FALSE;
    Active_Material_ID := 0;
    Active_Bin_ID := 0;
    Active_Target_Weight := 0.0;
    Active_Live_Weight := 0.0;
    GVL.Semi_Auto_Active_Target_Weight := 0.0;
    GVL.Semi_Auto_Active_Live_Weight := 0.0;
    GVL.Semi_Auto_Active_Mat := 0;
    GVL.Semi_Auto_Active_Bin := 0;
    Excess_Alarm := FALSE;
    Error_Code := 0;
    Semi_Auto_Completed_Batch_Cycles := 0;
    Semi_Auto_Current_Batch_Cycle := 0;
    Semi_Auto_All_Cycles_Complete := FALSE;
    Current_Step := 0;
    Cycle_Manager_State := 0;
    Internal_FB_Start := FALSE;
    Tare_Pulse_Req := FALSE;
    Tare_Semi_Auto_Batch := FALSE;
    Waiting_Next_Batch := FALSE;
    Between_Cycle_Hold := FALSE;
    Paused_By_Hold := FALSE;
    Next_Cycle_Ready := FALSE;
    PersistentVars.Ret_Semi_Process_Was_Active := FALSE;
    PersistentVars.Ret_Semi_Cycle_Manager_State := 0;
    PersistentVars.Ret_Semi_Current_Step := 0;
    PersistentVars.Ret_Semi_Resume_Step := 0;
    PersistentVars.Ret_Semi_bin_last_weight := 0.0;
    bin_last_weight := 0.0;
    Status_Message := 'Semi-Auto [Reset]: Fresh cycle ready. Press Start.';
    RETURN;
END_IF;

IF Fault_Reset_Pulse THEN
    IF (Error_Code = 4) AND Scale_Empty_OK THEN
        Error_Code := 0;
    ELSIF (Error_Code = 21) AND (load_cell_value <= 500.0) THEN
        Error_Code := 0;
        Paused_By_Hold := FALSE;
    ELSIF (Error_Code = 5) AND (NOT Line_Fault) THEN
        Error_Code := 0;
        Paused_By_Hold := FALSE;
    END_IF;
END_IF;

// Process HOLD on Safety / Fault conditions
IF NOT E_Stop_Active OR NOT Auto_Mode_DI OR (Error_Code > 0) THEN
    Paused_By_Hold := TRUE;
    FOR i := 1 TO 10 DO
        Semi_Auto_Bin[i] := FALSE;
        semi_auto_bin_cutoff[i] := FALSE;
        semi_auto_bin_motor[i] := FALSE;
        GVL.Semi_Auto_Bin[i] := FALSE;
        GVL.semi_auto_bin_cutoff[i] := FALSE;
        GVL.semi_auto_bin_motor[i] := FALSE;
    END_FOR;
ELSE
    Paused_By_Hold := FALSE;
END_IF;

// -----------------------------------------------------------------------------
// 4. MASTER CYCLE MANAGER STATE MACHINE
// -----------------------------------------------------------------------------
CASE Cycle_Manager_State OF
    0: // IDLE
        Internal_FB_Start := FALSE;
        Sequence_Complete := FALSE;
        GVL.Semi_Auto_Sequence_Complete := FALSE;
        Current_Step := 0;
        GVL.Semi_Auto_Current_Step := 0;
        Next_Cycle_Ready := FALSE;

        IF Start_Pulse THEN
            IF NOT E_Stop_Active THEN
                Status_Message := 'Semi-Auto [State 0]: Cannot Start - E-Stop Open!';
            ELSIF Error_Code > 0 AND Error_Code <> 4 THEN
                Status_Message := CONCAT('Semi-Auto [State 0]: Cannot Start - Error_Code ', INT_TO_STRING(Error_Code));
            ELSIF NOT Scale_Empty_OK THEN
                Error_Code := 4;
                Status_Message := CONCAT('Semi-Auto [State 0]: Error 4 - Empty scale < ', CONCAT(REAL_TO_STRING(eff_empty_limit), ' kg before Start'));
            ELSE
                Error_Code := 0;
                Semi_Auto_Completed_Batch_Cycles := 0;
                Semi_Auto_Current_Batch_Cycle := 1;
                Semi_Auto_All_Cycles_Complete := FALSE;
                Internal_FB_Start := TRUE;
                Cycle_Manager_State := 1;
                Current_Step := 0;
                bin_last_weight := 0.0;
                PersistentVars.Ret_Semi_bin_last_weight := 0.0;
                FOR i := 1 TO 10 DO
                    Actual_Weights[i] := 0.0;
                    PersistentVars.Ret_Semi_Actual_Weights[i] := 0.0;
                END_FOR;
                Tare_Pulse_Req := TRUE;
            END_IF;
        END_IF;

    1: // RUNNING ACTIVE BATCH CYCLE
        Internal_FB_Start := TRUE;
        Next_Cycle_Ready := FALSE;

        // Check Cycle Completion Handshake
        IF Sequence_Complete AND GVL.Auto_Sequence_Complete AND (Semi_Has_Active_Bins OR Auto_Has_Active_Bins) THEN
            Semi_Auto_Completed_Batch_Cycles := GVL.Current_Batch_Cycle;
            
            IF (GVL.Current_Batch_Cycle < GVL.Target_Batch_Cycles) AND (GVL.Error_Code = 0) THEN
                Internal_FB_Start := FALSE;
                Cycle_Manager_State := 5; // Transition to Between-Cycle Hold
                Between_Cycle_Hold := TRUE;
                Status_Message := 'Semi-Auto [Cycle Done]: Discharging - waiting for empty scale';
            ELSE
                Cycle_Manager_State := 4; // All Target Cycles Completed
                Between_Cycle_Hold := FALSE;
            END_IF;
        END_IF;

    5: // PAUSED BETWEEN CYCLES (DISCHARGE & NEXT CYCLE READY HANDSHAKE)
        Internal_FB_Start := FALSE;
        
        // Debounce live load cell check for scale empty
        IF (load_cell_value <= eff_empty_limit) AND (GVL.load_cell_semi_auto <= eff_empty_limit) AND (GVL.load_cell_auto <= eff_empty_limit) THEN
            Empty_Debounce_Timer(IN := TRUE, PT := T#1S);
            IF Empty_Debounce_Timer.Q THEN
                Next_Cycle_Ready := TRUE;
                Status_Message := 'Semi-Auto [State 5]: Scale Empty - Ready for Next Cycle Start';
            END_IF;
        ELSE
            Empty_Debounce_Timer(IN := FALSE);
            Next_Cycle_Ready := FALSE;
            Status_Message := CONCAT('Semi-Auto [State 5]: Discharging batch (Scale > ', CONCAT(REAL_TO_STRING(eff_empty_limit), ' kg)...'));
        END_IF;

        // Next Cycle Trigger
        IF Next_Cycle_Rising THEN
            IF Error_Code > 0 THEN
                Status_Message := CONCAT('Semi-Auto [State 5]: Blocked by Error_Code ', INT_TO_STRING(Error_Code));
            ELSIF Next_Cycle_Ready AND (GVL.Current_Batch_Cycle < GVL.Target_Batch_Cycles) THEN
                Next_Cycle_Ready := FALSE;
                Semi_Auto_Current_Batch_Cycle := GVL.Current_Batch_Cycle;
                
                Sequence_Complete := FALSE;
                GVL.Semi_Auto_Sequence_Complete := FALSE;
                Between_Cycle_Hold := FALSE;
                Cycle_Manager_State := 1;
                Current_Step := 0;
                Internal_FB_Start := TRUE;
                
                bin_last_weight := 0.0;
                PersistentVars.Ret_Semi_bin_last_weight := 0.0;
                FOR i := 1 TO 10 DO
                    Actual_Weights[i] := 0.0;
                    PersistentVars.Ret_Semi_Actual_Weights[i] := 0.0;
                    Semi_Auto_Bin[i] := FALSE;
                    semi_auto_bin_cutoff[i] := FALSE;
                    semi_auto_bin_motor[i] := FALSE;
                END_FOR;
                
                Tare_Pulse_Req := TRUE;
                Status_Message := CONCAT('Semi-Auto [State 5]: Cycle ', CONCAT(INT_TO_STRING(GVL.Current_Batch_Cycle), ' Started'));
            ELSE
                Status_Message := CONCAT('Semi-Auto [State 5]: Empty scale < ', CONCAT(REAL_TO_STRING(eff_empty_limit), ' kg before pressing Next Cycle!'));
            END_IF;
        END_IF;

    4: // ALL CYCLES COMPLETE
        Internal_FB_Start := FALSE;
        Between_Cycle_Hold := FALSE;
        Semi_Auto_All_Cycles_Complete := TRUE;
        Sequence_Complete := TRUE;
        GVL.Semi_Auto_Sequence_Complete := TRUE;
        Next_Cycle_Ready := FALSE;
        Status_Message := CONCAT('Semi-Auto [Finished]: All ', CONCAT(INT_TO_STRING(GVL.Target_Batch_Cycles), ' Batch Cycles Complete'));

        IF Start_Pulse THEN
            IF Scale_Empty_OK THEN
                Current_Step := 0;
                Cycle_Manager_State := 0;
                Semi_Auto_All_Cycles_Complete := FALSE;
            ELSE
                Error_Code := 4;
                Status_Message := 'Semi-Auto [Finished]: Empty hopper before starting new job!';
            END_IF;
        END_IF;
END_CASE;

// -----------------------------------------------------------------------------
// 5. DOSING SEQUENCE (STEPS 1..10, SETTLE 31, COMPLETE 32)
// -----------------------------------------------------------------------------
IF (Current_Step = 0) AND Internal_FB_Start AND (Cycle_Manager_State = 1) THEN
    IF NOT Semi_Has_Active_Bins THEN
        Current_Step := 32;
        Sequence_Complete := TRUE;
        GVL.Semi_Auto_Sequence_Complete := TRUE;
    ELSE
        Current_Step := 1;
        bin_last_weight := load_cell_value;
        PersistentVars.Ret_Semi_bin_last_weight := bin_last_weight;
        Last_Dosing_Step := 1;
        Sequence_Complete := FALSE;
        GVL.Semi_Auto_Sequence_Complete := FALSE;
    END_IF;
END_IF;

CASE Current_Step OF
    0:
        Active_Material_ID := 0;
        Active_Bin_ID := 0;
        Active_Target_Weight := 0.0;
        Active_Live_Weight := 0.0;
        FOR i := 1 TO 10 DO
            Semi_Auto_Bin[i] := FALSE;
            semi_auto_bin_cutoff[i] := FALSE;
            semi_auto_bin_motor[i] := FALSE;
        END_FOR;

    1..10:
        // Skip unmapped / zero-target bins
        WHILE (Current_Step >= 1) AND (Current_Step <= 10) DO
            Mat_Idx := Semi_Auto_Bin_Material_Mapping[Current_Step];
            IF (Mat_Idx < 1) OR (Mat_Idx > 20) THEN
                Mat_Idx := GVL.Semi_Auto_Bin_Material_Mapping[Current_Step];
            END_IF;
            target_weight := 0.0;
            IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) THEN
                target_weight := GVL.Recipe_Weights[Mat_Idx];
            END_IF;

            IF (Mat_Idx < 1) OR (Mat_Idx > 20) OR (target_weight <= 0.0) THEN
                Semi_Auto_Bin[Current_Step] := FALSE;
                semi_auto_bin_cutoff[Current_Step] := FALSE;
                semi_auto_bin_motor[Current_Step] := FALSE;
                Actual_Weights[Current_Step] := 0.0;
                IF Current_Step = 10 THEN
                    Current_Step := 31;
                    EXIT;
                ELSE
                    Current_Step := Current_Step + 1;
                END_IF;
            ELSE
                EXIT;
            END_IF;
        END_WHILE;

        IF Inter_Bin_Settling THEN
            FOR i := 1 TO 10 DO
                Semi_Auto_Bin[i] := FALSE;
                semi_auto_bin_cutoff[i] := FALSE;
                semi_auto_bin_motor[i] := FALSE;
            END_FOR;
            Active_Material_ID := Settle_Hold_Mat;
            Active_Bin_ID := Settle_Hold_Step;
            Active_Target_Weight := Settle_Hold_Target;
            
            IF Inter_Bin_Settle_Arm = 0 THEN
                Inter_Bin_Timer(IN := FALSE);
                Inter_Bin_Settle_Arm := 1;
            ELSE
                Inter_Bin_Timer(IN := TRUE, PT := Inter_Bin_Delay);
                IF Inter_Bin_Timer.Q THEN
                    Inter_Bin_Timer(IN := FALSE);
                    bin_last_weight := load_cell_value;
                    PersistentVars.Ret_Semi_bin_last_weight := bin_last_weight;
                    Current_Step := Inter_Bin_Next_Step;
                    Last_Dosing_Step := Current_Step;
                    Inter_Bin_Settling := FALSE;
                    Inter_Bin_Settle_Arm := 0;
                END_IF;
            END_IF;

        ELSIF (Current_Step >= 1) AND (Current_Step <= 10) THEN
            Mat_Idx := Semi_Auto_Bin_Material_Mapping[Current_Step];
            IF (Mat_Idx < 1) OR (Mat_Idx > 20) THEN
                Mat_Idx := GVL.Semi_Auto_Bin_Material_Mapping[Current_Step];
            END_IF;
            target_weight := GVL.Recipe_Weights[Mat_Idx];
            
            IF Current_Step <> Last_Dosing_Step THEN
                bin_last_weight := load_cell_value;
                PersistentVars.Ret_Semi_bin_last_weight := bin_last_weight;
                Last_Dosing_Step := Current_Step;
            END_IF;

            cutoff_trigger_weight := target_weight - Semi_Auto_Coarse_To_Fine_Speed[Current_Step];
            min_tol_weight := target_weight - Semi_Auto_Bin_Tolerance[Current_Step];
            max_tol_weight := target_weight + Semi_Auto_Bin_Tolerance[Current_Step];

            actual_bin := load_cell_value - bin_last_weight;
            IF actual_bin < 0.0 THEN
                actual_bin := 0.0;
            END_IF;

            Active_Material_ID := Mat_Idx;
            Active_Bin_ID := Current_Step;
            Active_Target_Weight := target_weight;

            IF (NOT Paused_By_Hold) AND GVL.Run AND (Error_Code = 0) THEN
                Actual_Weights[Current_Step] := actual_bin;
                Active_Live_Weight := actual_bin;
                
                // Dosing Outputs
                IF actual_bin < cutoff_trigger_weight THEN
                    Semi_Auto_Bin[Current_Step] := TRUE;
                    semi_auto_bin_cutoff[Current_Step] := FALSE;
                    semi_auto_bin_motor[Current_Step] := TRUE;
                    Excess_Alarm := FALSE;
                    Status_Message := CONCAT('Semi-Auto [Step ', CONCAT(INT_TO_STRING(Current_Step), ']: Coarse Feeding'));
                ELSIF actual_bin < min_tol_weight THEN
                    Semi_Auto_Bin[Current_Step] := FALSE;
                    semi_auto_bin_cutoff[Current_Step] := TRUE;
                    semi_auto_bin_motor[Current_Step] := TRUE;
                    Excess_Alarm := FALSE;
                    Status_Message := CONCAT('Semi-Auto [Step ', CONCAT(INT_TO_STRING(Current_Step), ']: Fine Feeding'));
                ELSIF actual_bin > max_tol_weight THEN
                    Semi_Auto_Bin[Current_Step] := FALSE;
                    semi_auto_bin_cutoff[Current_Step] := FALSE;
                    semi_auto_bin_motor[Current_Step] := FALSE;
                    IF Excess_Allowed THEN
                        Excess_Alarm := FALSE;
                        Status_Message := CONCAT('Semi-Auto [Step ', CONCAT(INT_TO_STRING(Current_Step), ']: Target Reached (Excess Allowed)'));
                        Settle_Hold_Step := Current_Step;
                        Settle_Hold_Mat := Mat_Idx;
                        Settle_Hold_Target := target_weight;
                        IF Current_Step >= 10 THEN
                            Current_Step := 31;
                        ELSE
                            Inter_Bin_Next_Step := Current_Step + 1;
                            Inter_Bin_Settling := TRUE;
                            Inter_Bin_Settle_Arm := 0;
                        END_IF;
                    ELSE
                        Excess_Alarm := TRUE;
                        Status_Message := CONCAT('Semi-Auto [Step ', CONCAT(INT_TO_STRING(Current_Step), ']: Excess Weight Alarm!'));
                    END_IF;
                ELSE
                    Semi_Auto_Bin[Current_Step] := FALSE;
                    semi_auto_bin_cutoff[Current_Step] := FALSE;
                    semi_auto_bin_motor[Current_Step] := FALSE;
                    Excess_Alarm := FALSE;
                    Status_Message := CONCAT('Semi-Auto [Step ', CONCAT(INT_TO_STRING(Current_Step), ']: Target Reached - Advancing'));
                    Settle_Hold_Step := Current_Step;
                    Settle_Hold_Mat := Mat_Idx;
                    Settle_Hold_Target := target_weight;
                    IF Current_Step >= 10 THEN
                        Current_Step := 31;
                    ELSE
                        Inter_Bin_Next_Step := Current_Step + 1;
                        Inter_Bin_Settling := TRUE;
                        Inter_Bin_Settle_Arm := 0;
                    END_IF;
                END_IF;
            END_IF;
        END_IF;

    31: // FINAL SETTLING DELAY
        Active_Material_ID := 0;
        Active_Bin_ID := 0;
        Active_Target_Weight := 0.0;
        Active_Live_Weight := 0.0;
        FOR i := 1 TO 10 DO
            Semi_Auto_Bin[i] := FALSE;
            semi_auto_bin_cutoff[i] := FALSE;
            semi_auto_bin_motor[i] := FALSE;
        END_FOR;
        Status_Message := 'Semi-Auto [Step 31]: Settling Delay in progress...';
        Completion_Timer(IN := TRUE, PT := Effective_Delay);
        IF Completion_Timer.Q THEN
            Completion_Timer(IN := FALSE);
            Current_Step := 32;
        END_IF;

    32: // SEQUENCE COMPLETE
        Active_Material_ID := 0;
        Active_Bin_ID := 0;
        Active_Target_Weight := 0.0;
        Active_Live_Weight := 0.0;
        FOR i := 1 TO 10 DO
            Semi_Auto_Bin[i] := FALSE;
            semi_auto_bin_cutoff[i] := FALSE;
            semi_auto_bin_motor[i] := FALSE;
        END_FOR;
        Sequence_Complete := TRUE;
        GVL.Semi_Auto_Sequence_Complete := TRUE;
        IF NOT GVL.Auto_Sequence_Complete THEN
            Status_Message := 'Semi-Auto [Step 32]: Waiting for Auto partner...';
        ELSE
            Status_Message := 'Semi-Auto [Step 32]: Both Sequences Complete';
        END_IF;
END_CASE;

// -----------------------------------------------------------------------------
// 6. OUTPUT SYNCHRONIZATION & PERSISTENT SNAPSHOT
// -----------------------------------------------------------------------------
FOR i := 1 TO 10 DO
    GVL.Semi_Auto_Bin[i] := Semi_Auto_Bin[i];
    GVL.semi_auto_bin_cutoff[i] := semi_auto_bin_cutoff[i];
    GVL.semi_auto_bin_motor[i] := semi_auto_bin_motor[i];
    GVL.Semi_Auto_Weights[i] := Actual_Weights[i];
END_FOR;

Semi_Auto_Sum_ActWeight := 0.0;
FOR i := 1 TO 10 DO
    Semi_Auto_Sum_ActWeight := Semi_Auto_Sum_ActWeight + Actual_Weights[i];
END_FOR;
GVL.Semi_Auto_Total_Actual_Weight := Semi_Auto_Sum_ActWeight;

GVL.Semi_Auto_Active_Mat := Active_Material_ID;
GVL.Semi_Auto_Active_Bin := Active_Bin_ID;
GVL.Semi_Auto_Active_Target_Weight := Active_Target_Weight;
GVL.Semi_Auto_Active_Live_Weight := Active_Live_Weight;
GVL.Semi_Auto_Current_Step := Current_Step;

// Target setpoints mirror to GVL
FOR i := 1 TO 10 DO
    Mat_Idx := Semi_Auto_Bin_Material_Mapping[i];
    IF (Mat_Idx < 1) OR (Mat_Idx > 20) THEN
        Mat_Idx := GVL.Semi_Auto_Bin_Material_Mapping[i];
    END_IF;
    target_weight := 0.0;
    IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) THEN
        target_weight := GVL.Recipe_Weights[Mat_Idx];
    END_IF;
    Semi_Auto_Target_Weight[i] := target_weight;
    GVL.Semi_Auto_Target_Weights[i] := target_weight;
END_FOR;

// Persistent Retain Snapshot
IF Cycle_Manager_State = 4 THEN
    PersistentVars.Ret_Semi_Process_Was_Active := FALSE;
    PersistentVars.Ret_Semi_Cycle_Manager_State := 0;
    PersistentVars.Ret_Semi_Current_Step := 0;
    PersistentVars.Ret_Semi_Resume_Step := 0;
    PersistentVars.Ret_Semi_Active_Live_Weight := 0.0;
    PersistentVars.Ret_Semi_bin_last_weight := 0.0;
    FOR i := 1 TO 10 DO
        PersistentVars.Ret_Semi_Actual_Weights[i] := 0.0;
    END_FOR;
ELSIF Cycle_Manager_State = 1 OR Cycle_Manager_State = 5 THEN
    PersistentVars.Ret_Semi_Process_Was_Active := TRUE;
    PersistentVars.Ret_Semi_Cycle_Manager_State := Cycle_Manager_State;
    PersistentVars.Ret_Semi_Current_Step := Current_Step;
    IF (Current_Step >= 1) AND (Current_Step <= 10) THEN
        PersistentVars.Ret_Semi_Resume_Step := Current_Step;
    END_IF;
    PersistentVars.Ret_Semi_Current_Batch_Cycle := GVL.Current_Batch_Cycle;
    PersistentVars.Ret_Semi_Completed_Batch_Cycles := GVL.Completed_Batch_Cycles;
    PersistentVars.Ret_Semi_Target_Batch_Cycles := GVL.Target_Batch_Cycles;
    PersistentVars.Ret_Semi_Active_Material_ID := Active_Material_ID;
    PersistentVars.Ret_Semi_Active_Bin_ID := Active_Bin_ID;
    PersistentVars.Ret_Semi_Active_Target_Weight := Active_Target_Weight;
    PersistentVars.Ret_Semi_Active_Live_Weight := Active_Live_Weight;
    PersistentVars.Ret_Semi_bin_last_weight := bin_last_weight;
    FOR i := 1 TO 10 DO
        PersistentVars.Ret_Semi_Actual_Weights[i] := Actual_Weights[i];
    END_FOR;
END_IF;

// -----------------------------------------------------------------------------
// 7. TARE PULSE EMISSION (STRICT INTERLOCK)
// -----------------------------------------------------------------------------
IF Tare_Pulse_Req THEN
    IF Scale_Empty_OK AND (Cycle_Manager_State = 1) AND (Current_Step <= 1) THEN
        Tare_Semi_Auto_Batch := TRUE;
    ELSE
        Tare_Semi_Auto_Batch := FALSE;
    END_IF;
    Tare_Pulse_Req := FALSE;
ELSE
    Tare_Semi_Auto_Batch := FALSE;
END_IF;

Waiting_Next_Batch := (Cycle_Manager_State = 5) AND (GVL.Target_Batch_Cycles > 1) AND (GVL.Current_Batch_Cycle < GVL.Target_Batch_Cycles);
Semi_Auto_Current_Batch_Cycle := GVL.Current_Batch_Cycle;
Semi_Auto_Completed_Batch_Cycles := GVL.Completed_Batch_Cycles;
Semi_Auto_All_Cycles_Complete := GVL.All_Cycles_Complete;
END_FUNCTION_BLOCK
