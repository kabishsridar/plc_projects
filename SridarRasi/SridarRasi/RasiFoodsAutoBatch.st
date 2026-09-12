FUNCTION_BLOCK Auto_Batching_V15
VAR_INPUT
    Start_Button : BOOL;                            // Optional start pin (legacy). Also ORed with GVL.Start_Button (%MX2.0 HMI) and Start_PB
    Start_PB : BOOL;                                // Physical Start pushbutton DI (one-shot pulse)
    Auto_Mode_DI : BOOL;                            // Auto Mode DI: TRUE = process start allowed; FALSE = HMI/PB start ignored
    E_Stop_Active : BOOL;                           // Emergency Stop circuit status (NC contact: TRUE = Healthy/Run permitted, FALSE = E-Stop tripped)
    Reset : BOOL;                                   // Production abort: clears steps, weights, cycles, CMS. Does not replace Fault_Reset for Auto_Error_Code
    Fault_Reset : BOOL;                             // Rising-edge: Auto_Error_Code:=0 and Error:=FALSE only if live fault is gone (mapping, Line_Fault, overload, empty-scale). Does not abort batch
    Auto_Bin_Material_Mapping : ARRAY[1..6] OF INT; // Array mapping physical Silos 1..6 to Recipe Material IDs (1..20, 0 = Silo skipped)
    Auto_Coarse_To_Fine_Speed : ARRAY[1..6] OF REAL;// Weight offset threshold (kg) before target to transition from Coarse to Fine feeding
    Auto_Bin_Tolerance : ARRAY[1..6] OF REAL;       // Allowable weight tolerance window (±kg) around target weight for each silo
    Inter_Bin_Delay : TIME := T#5S;                 // Pause after Bin*=FALSE: tailings on SAME bin ID; then next mat (Auto e.g. T#5S)
    Excess_Allowed : BOOL := FALSE;                 // Overfill handling policy: TRUE = proceed if target is exceeded, FALSE = raise alarm and halt
    load_cell_value : REAL;                         // Live gross weight input reading from the Auto scale load cell (kg)
    Target_Batch_Cycles : INT := 1;                 // Target number of batch cycle repetitions configured from HMI (defaults to 1)
    Next_Cycle_Start : BOOL;                        // NextBatchStart: after a completed cycle (Target>1), press when this FB scale < Empty_Weight_Limit
    Empty_Weight_Limit : REAL := 0.5;               // Both scales must be LT this (kg) before Start/Start_PB, Next_Cycle_Start, or Tare pulse
    Line_Fault : BOOL;                              // Auto scale arrLine_Fault. TRUE => Auto_Error_Code=5 + HOLD
    Partner_Line_Fault : BOOL;                      // Partner Semi load-cell comms fail (arrLine_Fault). TRUE => Auto_Error_Code=8
    Partner_Semi_Auto_Bin_Material_Mapping : ARRAY[1..10] OF INT; // Semi silo Mat IDs 1..10 (wire GVL.Semi_Auto_Bin_Material_Mapping). Any ID also used on Auto => Auto_Error_Code=7
END_VAR
VAR_OUTPUT
    Auto_Bin : ARRAY[1..6] OF BOOL;                 // Coarse feeding valve / gate actuation command outputs for Silos 1..6
    auto_bin_cutoff : ARRAY[1..6] OF BOOL;          // Fine feeding valve / vibrator cutoff actuation command outputs for Silos 1..6
    auto_bin_motor : ARRAY[1..6] OF BOOL;           // Feeder / screw conveyor motor run commands for Silos 1..6
    Actual_Weights : ARRAY[1..6] OF REAL;           // Net material weight (kg) successfully dosed for each silo in the current cycle
    Auto_Sum_Act_Weight : REAL;                     // Sum of Actual_Weights[1..6] / GVL.Auto_Weights %MD300; hold until Reset, accepted Next_Cycle_Start, or new job Start; HMI GVL.Auto_Total_Actual_Weight %MD180
    Auto_Total_Target_Set : ARRAY[1..6] OF REAL;    // Per-bin target kg (bin index 1..6) — ST mirrors GVL.Auto_Target_Weights (plant %MD400)
    Sequence_Complete : BOOL;                       // Handshake flag: TRUE when all mapped Auto silos have completed dosing and settling
    Active_Material_ID : INT;                       // Recipe Material ID currently being dosed (1..20, 0 when idle/complete)
    Active_Bin_ID : INT;                            // Physical Silo index currently being dosed (1..6, 0 when idle/complete)
    Active_Target_Weight : REAL;                    // Target weight setpoint (kg) of the ingredient currently being dosed
    Active_Live_Weight : REAL;                      // Live net/tared weight (kg) accumulated into the scale for the active silo
    Current_Step : INT;                             // Real-time sequence step:
                                                    //   0  = Idle / Waiting for Start
                                                    //   1..6 = Dosing Silos 1..6 (feeding coarse/fine)
                                                    //   7  = Settling delay in progress
                                                    //   8  = Sequence complete
    Cycle_Manager_State : INT;                      // Master supervisory cycle manager state:
                                                    //   0  = System Idle / Stopped
                                                    //   1  = Running active batch cycle
                                                    //   4  = All target batch cycles completed successfully
                                                    //   5  = Paused between cycles (Cycle Hold active)
    Excess_Alarm : BOOL;                            // Overfill alarm: TRUE when dosed weight exceeds target + tolerance (with Excess_Allowed=FALSE)
    Auto_Error_Code : INT; (* 0=OK 1=Dup Auto 2=range 3=Recipe 4=empty 5=Line_Fault 6=all0 7=vs Semi ID 8=Partner_Line_Fault 9=Dup Semi map 21=ovld *)
    Error : BOOL;                                   // TRUE when Auto_Error_Code > 0 (any Auto fault); FALSE when Auto_Error_Code = 0
    Auto_Current_Batch_Cycle : INT;                 // Active batch cycle number currently processing (1..Target_Batch_Cycles)
    Auto_Completed_Batch_Cycles : INT;              // Total number of batch cycle loops completed successfully
    Auto_All_Cycles_Complete : BOOL;                // Master flag: TRUE when all Target_Batch_Cycles have finished
    Status_Message : STRING(80);                    // Real-time human-readable process status and diagnostic text message
    Tare_Auto_Batch : BOOL;                         // One-scan pulse to Samyak ONLY when BOTH scales LT Empty_Weight_Limit (never after batch with product on scale)
    Waiting_Next_Batch : BOOL;                      // TRUE in state 5 while Current < Target (HMI hide/lamp); FALSE when next cycle runs; never TRUE on last cycle
    Next_Cycle_Ready : BOOL;                        // TRUE when hopper is confirmed empty (load_cell <= Empty_Weight_Limit) and ready for next cycle
END_VAR
VAR
    bin_last_weight : REAL;
    actual_bin : REAL;
    target_weight : REAL;
    cutoff_trigger_weight : REAL;
    min_tol_weight : REAL;
    max_tol_weight : REAL;
    Paused_By_Hold : BOOL;                          // TRUE = process HOLD (E-Stop open or Auto_Mode_DI OFF or after power restore)
    Effective_Delay : TIME;                         // Final settle Step 7 (Inter_Bin_Delay -> T#2S default if pin=0)
    Inter_Bin_Settling : BOOL;                      // TRUE: waiting Inter_Bin_Delay before feeding next bin
    Inter_Bin_Settle_Arm : INT;                     // 0=arm Inter_Bin_Timer, 1=counting
    Inter_Bin_Timer : TON;
    Settle_Hold_Step : INT;                         // Completed bin step held on HMI during inter-bin settle
    Settle_Hold_Mat : INT;                          // Material ID of completed bin during settle hold
    Settle_Hold_Target : REAL;                      // Target kg of completed bin during settle hold
    Inter_Bin_Next_Step : INT;                      // Next active bin step — applied when inter-bin timer completes
    Mat_Idx : INT;
    j_Mat : INT;
    i : INT;
    j : INT;
    Transition_Timer : TON;
    Completion_Timer : TON;
    Empty_Debounce_Timer : TON;                     // 1s filter for empty scale verification in State 5
    
    (* Master Cycle Manager & Supervisory states *)
    Internal_FB_Start : BOOL;
    Duplicate_Found : BOOL;                         // TRUE = same Material ID on two Auto bins
    Duplicate_Vs_Partner : BOOL;                    // TRUE = Auto ID also on Partner_Semi_Auto_Bin_Material_Mapping
    Duplicate_Partner_Internal : BOOL;              // TRUE = same Material ID on two Partner Semi bins
    Auto_Mapping_All_Zero : BOOL;                   // TRUE = Auto_Bin_Material_Mapping[1..6] all 0
    Partner_Mapping_All_Zero : BOOL;                // TRUE = Partner_Semi_Auto_Bin_Material_Mapping[1..10] all 0
    Invalid_Material_Range : BOOL;
    Weight_Limit_Error : BOOL;
    eff_empty_limit : REAL;
    Scale_Empty_OK : BOOL;                          // TRUE when this FB load AND partner Semi scale are LT Empty_Weight_Limit
    Next_Cycle_Last : BOOL;
    Next_Cycle_Rising : BOOL;
    Tare_Pulse_Req : BOOL;                          // Internal request to emit Tare_Auto_Batch for one scan
    Start_Cmd : BOOL;                               // (Start_Button OR GVL.Start_Button OR Start_PB) AND Auto_Mode_DI
    Start_Cmd_Last : BOOL;                          // Edge memory for Start_Cmd
    Start_Pulse : BOOL;                             // Rising edge of Start_Cmd
    First_Scan_Done : BOOL;                         // FALSE after PLC power-up (non-retain)
    Auto_Has_Active_Bins : BOOL;                    // TRUE when any Auto bin 1..6 has target weight > 0
    Semi_Has_Active_Bins : BOOL;                    // Partner Semi: any bin 1..10 with target > 0
    Reset_Last : BOOL;                              // Edge memory for Reset
    Reset_Pulse : BOOL;                             // Rising edge Reset
    Fault_Reset_Last : BOOL;                        // Edge memory for Fault_Reset
    Fault_Reset_Pulse : BOOL;                       // Rising edge Fault_Reset
    Fresh_After_Reset : BOOL;                       // TRUE after Reset
    Between_Cycle_Hold : BOOL;                      // TRUE while waiting for empty scale + Next_Cycle_Start (CMS 5)
    Last_Dosing_Step : INT;                         // Last dosing step 1..6
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

Scale_Empty_OK := (load_cell_value < eff_empty_limit) AND (GVL.load_cell_auto < eff_empty_limit)
    AND (GVL.load_cell_semi_auto < eff_empty_limit);

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
    
    // Restore HMI Recipe & Mapping retain if GVL uninitialized
    FOR i := 1 TO 20 DO
        IF (GVL.Recipe_Weights[i] <= 0.001) AND (PersistentVars.Ret_Recipe_Weights[i] > 0.001) THEN
            GVL.Recipe_Weights[i] := PersistentVars.Ret_Recipe_Weights[i];
        END_IF;
    END_FOR;
    FOR i := 1 TO 6 DO
        IF (GVL.Auto_Bin_Material_Mapping[i] = 0) AND (PersistentVars.Ret_Bin_Material_Mapping[i] > 0) THEN
            GVL.Auto_Bin_Material_Mapping[i] := PersistentVars.Ret_Bin_Material_Mapping[i];
        END_IF;
    END_FOR;
    FOR i := 1 TO 10 DO
        IF (GVL.Semi_Auto_Bin_Material_Mapping[i] = 0) AND (PersistentVars.Ret_Semi_Bin_Material_Mapping[i] > 0) THEN
            GVL.Semi_Auto_Bin_Material_Mapping[i] := PersistentVars.Ret_Semi_Bin_Material_Mapping[i];
        END_IF;
    END_FOR;

    // Power Resume Logic: restore exact state without corrupting actual weights with live load cell
    IF PersistentVars.Ret_Process_Was_Active AND (PersistentVars.Ret_Cycle_Manager_State = 1) 
       AND (PersistentVars.Ret_Resume_Step >= 1) AND (PersistentVars.Ret_Resume_Step <= 6) THEN
        
        Current_Step := PersistentVars.Ret_Resume_Step;
        Last_Dosing_Step := Current_Step;
        Cycle_Manager_State := 1;
        Internal_FB_Start := TRUE;
        Between_Cycle_Hold := FALSE;
        GVL.Run := TRUE;
        GVL.Current_Batch_Cycle := PersistentVars.Ret_Current_Batch_Cycle;
        GVL.Completed_Batch_Cycles := PersistentVars.Ret_Completed_Batch_Cycles;
        IF PersistentVars.Ret_Target_Batch_Cycles > 0 THEN
            GVL.Target_Batch_Cycles := PersistentVars.Ret_Target_Batch_Cycles;
        END_IF;

        // Restore EXACT dosed weights from retain
        Auto_Sum_Act_Weight := 0.0;
        FOR i := 1 TO 6 DO
            Actual_Weights[i] := PersistentVars.Ret_Actual_Weights[i];
            GVL.Auto_Weights[i] := Actual_Weights[i];
            Auto_Sum_Act_Weight := Auto_Sum_Act_Weight + Actual_Weights[i];
        END_FOR;
        GVL.Auto_Total_Actual_Weight := Auto_Sum_Act_Weight;

        // Restore tare baseline and active weights (LOCKED - no live load cell overwrite on boot)
        bin_last_weight := PersistentVars.Ret_bin_last_weight;
        PersistentVars.bin_last_weight := bin_last_weight;
        Active_Live_Weight := PersistentVars.Ret_Active_Live_Weight;
        GVL.Auto_Active_Live_Weight := Active_Live_Weight;
        Active_Material_ID := PersistentVars.Ret_Active_Material_ID;
        Active_Bin_ID := PersistentVars.Ret_Active_Bin_ID;
        Active_Target_Weight := PersistentVars.Ret_Active_Target_Weight;
        GVL.Auto_Active_Mat := Active_Material_ID;
        GVL.Auto_Active_Bin := Active_Bin_ID;
        GVL.Auto_Active_Target_Weight := Active_Target_Weight;

        // Hold feeders OFF until safety checks pass; strictly inhibit tare pulse
        Paused_By_Hold := TRUE;
        Tare_Pulse_Req := FALSE;
        Tare_Auto_Batch := FALSE;
        Status_Message := CONCAT('Auto [POWER RESUME]: Resumed Step ', INT_TO_STRING(Current_Step));

    ELSIF (PersistentVars.Ret_Cycle_Manager_State = 5) THEN
        Cycle_Manager_State := 5;
        Between_Cycle_Hold := TRUE;
        Current_Step := 8;
        Sequence_Complete := TRUE;
        GVL.Auto_Sequence_Complete := TRUE;
        GVL.Run := TRUE;
        GVL.Current_Batch_Cycle := PersistentVars.Ret_Current_Batch_Cycle;
        GVL.Completed_Batch_Cycles := PersistentVars.Ret_Completed_Batch_Cycles;
        IF PersistentVars.Ret_Target_Batch_Cycles > 0 THEN
            GVL.Target_Batch_Cycles := PersistentVars.Ret_Target_Batch_Cycles;
        END_IF;
        FOR i := 1 TO 6 DO
            Actual_Weights[i] := PersistentVars.Ret_Actual_Weights[i];
            GVL.Auto_Weights[i] := Actual_Weights[i];
        END_FOR;
        Tare_Pulse_Req := FALSE;
        Tare_Auto_Batch := FALSE;
        Status_Message := 'Auto [POWER RESUME]: Waiting empty scale & Next_Cycle_Start';

    ELSE
        // Clean Idle
        Current_Step := 0;
        Cycle_Manager_State := 0;
        Internal_FB_Start := FALSE;
        Between_Cycle_Hold := FALSE;
        Sequence_Complete := FALSE;
        Tare_Pulse_Req := FALSE;
        Tare_Auto_Batch := FALSE;
        Next_Cycle_Ready := FALSE;
        Status_Message := 'Auto [Idle]: Ready - Waiting for Start';
    END_IF;
END_IF;

// Maintain continuous retain snapshot of HMI mappings
FOR i := 1 TO 20 DO
    PersistentVars.Ret_Recipe_Weights[i] := GVL.Recipe_Weights[i];
END_FOR;
FOR i := 1 TO 6 DO
    PersistentVars.Ret_Bin_Material_Mapping[i] := GVL.Auto_Bin_Material_Mapping[i];
END_FOR;
FOR i := 1 TO 10 DO
    PersistentVars.Ret_Semi_Bin_Material_Mapping[i] := GVL.Semi_Auto_Bin_Material_Mapping[i];
END_FOR;

// -----------------------------------------------------------------------------
// 2. CONFIGURATION CHECKS & ERROR DIAGNOSTICS
// -----------------------------------------------------------------------------
Duplicate_Found := FALSE;
Duplicate_Vs_Partner := FALSE;
Duplicate_Partner_Internal := FALSE;
Auto_Mapping_All_Zero := TRUE;
Partner_Mapping_All_Zero := TRUE;
Invalid_Material_Range := FALSE;
Weight_Limit_Error := FALSE;
Auto_Has_Active_Bins := FALSE;
Semi_Has_Active_Bins := FALSE;

GVL.Auto_Total_Target_Weight := 0.0;
GVL.Auto_Material_Count := 0;

FOR i := 1 TO 6 DO
    Mat_Idx := Auto_Bin_Material_Mapping[i];
    IF (Mat_Idx < 1) OR (Mat_Idx > 20) THEN
        Mat_Idx := GVL.Auto_Bin_Material_Mapping[i];
    END_IF;
    
    IF Mat_Idx <> 0 THEN
        Auto_Mapping_All_Zero := FALSE;
    END_IF;
    IF (Mat_Idx < 0) OR (Mat_Idx > 20) THEN
        Invalid_Material_Range := TRUE;
    END_IF;
    
    IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) THEN
        // Duplicate check within Auto
        FOR j := 1 TO 6 DO
            IF j <> i THEN
                j_Mat := Auto_Bin_Material_Mapping[j];
                IF (j_Mat < 1) OR (j_Mat > 20) THEN
                    j_Mat := GVL.Auto_Bin_Material_Mapping[j];
                END_IF;
                IF (j_Mat = Mat_Idx) THEN
                    Duplicate_Found := TRUE;
                END_IF;
            END_IF;
        END_FOR;
        // Duplicate check vs Partner Semi
        FOR j := 1 TO 10 DO
            j_Mat := Partner_Semi_Auto_Bin_Material_Mapping[j];
            IF (j_Mat < 1) OR (j_Mat > 20) THEN
                j_Mat := GVL.Semi_Auto_Bin_Material_Mapping[j];
            END_IF;
            IF (j_Mat = Mat_Idx) THEN
                Duplicate_Vs_Partner := TRUE;
            END_IF;
        END_FOR;
        
        target_weight := GVL.Recipe_Weights[Mat_Idx];
        IF target_weight > 0.0 THEN
            GVL.Auto_Total_Target_Weight := GVL.Auto_Total_Target_Weight + target_weight;
            GVL.Auto_Material_Count := GVL.Auto_Material_Count + 1;
            Auto_Has_Active_Bins := TRUE;
            IF target_weight < (Auto_Coarse_To_Fine_Speed[i] + Auto_Bin_Tolerance[i]) THEN
                Weight_Limit_Error := TRUE;
            END_IF;
        END_IF;
    END_IF;
END_FOR;

// Partner Semi Active & Duplicate Check
FOR i := 1 TO 10 DO
    Mat_Idx := Partner_Semi_Auto_Bin_Material_Mapping[i];
    IF (Mat_Idx < 1) OR (Mat_Idx > 20) THEN
        Mat_Idx := GVL.Semi_Auto_Bin_Material_Mapping[i];
    END_IF;
    IF Mat_Idx <> 0 THEN
        Partner_Mapping_All_Zero := FALSE;
    END_IF;
    IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) THEN
        FOR j := 1 TO 10 DO
            IF j <> i THEN
                j_Mat := Partner_Semi_Auto_Bin_Material_Mapping[j];
                IF (j_Mat < 1) OR (j_Mat > 20) THEN
                    j_Mat := GVL.Semi_Auto_Bin_Material_Mapping[j];
                END_IF;
                IF (j_Mat = Mat_Idx) THEN
                    Duplicate_Partner_Internal := TRUE;
                END_IF;
            END_IF;
        END_FOR;
        IF GVL.Recipe_Weights[Mat_Idx] > 0.0 THEN
            Semi_Has_Active_Bins := TRUE;
        END_IF;
    END_IF;
END_FOR;

// Error Code Priority Evaluation
IF load_cell_value > 500.0 THEN
    Auto_Error_Code := 21;
    GVL.Error_Code := 21;
    Status_Message := 'Auto_Error_Code 21: Scale Overload (> 500 kg)!';
ELSIF Line_Fault THEN
    Auto_Error_Code := 5;
    GVL.Error_Code := 5;
    Status_Message := 'Auto_Error_Code 5: Auto Scale Line_Fault Communication Error!';
ELSIF Partner_Line_Fault THEN
    Auto_Error_Code := 8;
    GVL.Error_Code := 8;
    Status_Message := 'Auto_Error_Code 8: Partner Semi Scale Communication Error!';
ELSIF Auto_Mapping_All_Zero OR Partner_Mapping_All_Zero THEN
    Auto_Error_Code := 6;
    GVL.Error_Code := 6;
    Status_Message := 'Auto_Error_Code 6: Material Mapping is all 0!';
ELSIF Duplicate_Found THEN
    Auto_Error_Code := 1;
    GVL.Error_Code := 1;
    Status_Message := 'Auto_Error_Code 1: Duplicate Material ID within Auto bins!';
ELSIF Invalid_Material_Range THEN
    Auto_Error_Code := 2;
    GVL.Error_Code := 2;
    Status_Message := 'Auto_Error_Code 2: Material Index out of range (must be 1..20)!';
ELSIF Weight_Limit_Error THEN
    Auto_Error_Code := 3;
    GVL.Error_Code := 3;
    Status_Message := 'Auto_Error_Code 3: Recipe weight < Coarse_To_Fine_Speed + Tolerance!';
ELSIF Duplicate_Vs_Partner THEN
    Auto_Error_Code := 7;
    GVL.Error_Code := 7;
    Status_Message := 'Auto_Error_Code 7: Material ID duplicated on Auto and Partner Semi!';
ELSIF Duplicate_Partner_Internal THEN
    Auto_Error_Code := 9;
    GVL.Error_Code := 9;
    Status_Message := 'Auto_Error_Code 9: Duplicate Material ID inside Partner Semi mapping!';
ELSIF (Auto_Error_Code <> 4) THEN
    Auto_Error_Code := 0;
    IF GVL.Error_Code <> 4 THEN
        GVL.Error_Code := 0;
    END_IF;
END_IF;

Error := (Auto_Error_Code > 0);

// -----------------------------------------------------------------------------
// 3. MASTER RESET & FAULT RESET
// -----------------------------------------------------------------------------
IF Reset_Pulse THEN
    FOR i := 1 TO 6 DO
        Auto_Bin[i] := FALSE;
        auto_bin_cutoff[i] := FALSE;
        auto_bin_motor[i] := FALSE;
        Actual_Weights[i] := 0.0;
        Auto_Total_Target_Set[i] := 0.0;
        GVL.Auto_Bin[i] := FALSE;
        GVL.auto_bin_cutoff[i] := FALSE;
        GVL.auto_bin_motor[i] := FALSE;
        GVL.Auto_Weights[i] := 0.0;
        GVL.Auto_Target_Weights[i] := 0.0;
        PersistentVars.Ret_Actual_Weights[i] := 0.0;
        PersistentVars.Ret_Bin_Target_Weights[i] := 0.0;
    END_FOR;
    Auto_Sum_Act_Weight := 0.0;
    GVL.Auto_Total_Actual_Weight := 0.0;
    Sequence_Complete := FALSE;
    GVL.Auto_Sequence_Complete := FALSE;
    Active_Material_ID := 0;
    Active_Bin_ID := 0;
    Active_Target_Weight := 0.0;
    Active_Live_Weight := 0.0;
    GVL.Auto_Active_Target_Weight := 0.0;
    GVL.Auto_Active_Live_Weight := 0.0;
    GVL.Auto_Active_Mat := 0;
    GVL.Auto_Active_Bin := 0;
    Excess_Alarm := FALSE;
    Auto_Error_Code := 0;
    GVL.Error_Code := 0;
    Error := FALSE;
    GVL.Current_Batch_Cycle := 0;
    GVL.Completed_Batch_Cycles := 0;
    GVL.All_Cycles_Complete := FALSE;
    Auto_Completed_Batch_Cycles := 0;
    Auto_Current_Batch_Cycle := 0;
    Auto_All_Cycles_Complete := FALSE;
    GVL.Target_Batch_Cycles := 0;
    GVL.Start_Button := FALSE;
    GVL.Run := FALSE;
    GVL.Next_Cycle_Start := FALSE;
    Next_Cycle_Ready := FALSE;
    GVL.Next_Cycle_Ready := FALSE;
    Current_Step := 0;
    Cycle_Manager_State := 0;
    Internal_FB_Start := FALSE;
    Tare_Pulse_Req := FALSE;
    Tare_Auto_Batch := FALSE;
    Waiting_Next_Batch := FALSE;
    Between_Cycle_Hold := FALSE;
    Paused_By_Hold := FALSE;
    Fresh_After_Reset := TRUE;
    PersistentVars.Ret_Process_Was_Active := FALSE;
    PersistentVars.Ret_Cycle_Manager_State := 0;
    PersistentVars.Ret_Current_Step := 0;
    PersistentVars.Ret_Resume_Step := 0;
    PersistentVars.Ret_bin_last_weight := 0.0;
    PersistentVars.bin_last_weight := 0.0;
    bin_last_weight := 0.0;
    Status_Message := 'Auto [Reset]: Fresh cycle ready. Press Start.';
    RETURN;
END_IF;

IF Fault_Reset_Pulse THEN
    IF (Auto_Error_Code = 4) AND Scale_Empty_OK THEN
        Auto_Error_Code := 0;
        GVL.Error_Code := 0;
    ELSIF (Auto_Error_Code = 21) AND (load_cell_value <= 500.0) THEN
        Auto_Error_Code := 0;
        GVL.Error_Code := 0;
        Paused_By_Hold := FALSE;
    ELSIF (Auto_Error_Code = 5) AND (NOT Line_Fault) THEN
        Auto_Error_Code := 0;
        GVL.Error_Code := 0;
        Paused_By_Hold := FALSE;
    ELSIF (Auto_Error_Code = 8) AND (NOT Partner_Line_Fault) THEN
        Auto_Error_Code := 0;
        GVL.Error_Code := 0;
        Paused_By_Hold := FALSE;
    END_IF;
    Error := (Auto_Error_Code > 0);
END_IF;

// Process HOLD on Safety / Fault conditions
IF NOT E_Stop_Active OR NOT Auto_Mode_DI OR (Auto_Error_Code > 0) THEN
    Paused_By_Hold := TRUE;
    FOR i := 1 TO 6 DO
        Auto_Bin[i] := FALSE;
        auto_bin_cutoff[i] := FALSE;
        auto_bin_motor[i] := FALSE;
        GVL.Auto_Bin[i] := FALSE;
        GVL.auto_bin_cutoff[i] := FALSE;
        GVL.auto_bin_motor[i] := FALSE;
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
        IF NOT PersistentVars.Ret_Process_Was_Active THEN
            GVL.Run := FALSE;
        END_IF;
        GVL.Next_Cycle_Start := FALSE;
        Next_Cycle_Ready := FALSE;
        GVL.Next_Cycle_Ready := FALSE;
        Sequence_Complete := FALSE;
        GVL.Auto_Sequence_Complete := FALSE;
        Current_Step := 0;
        GVL.Auto_Current_Step := 0;

        IF Start_Pulse THEN
            IF Target_Batch_Cycles > 0 THEN
                GVL.Target_Batch_Cycles := Target_Batch_Cycles;
            ELSIF GVL.Target_Batch_Cycles <= 0 THEN
                GVL.Target_Batch_Cycles := 1;
            END_IF;

            IF NOT E_Stop_Active THEN
                Status_Message := 'Auto [State 0]: Cannot Start - E-Stop Open!';
            ELSIF Auto_Error_Code > 0 AND Auto_Error_Code <> 4 THEN
                Status_Message := CONCAT('Auto [State 0]: Cannot Start - Auto_Error_Code ', INT_TO_STRING(Auto_Error_Code));
            ELSIF NOT Scale_Empty_OK THEN
                Auto_Error_Code := 4;
                GVL.Error_Code := 4;
                Status_Message := CONCAT('Auto [State 0]: Error 4 - Empty scale < ', CONCAT(REAL_TO_STRING(eff_empty_limit), ' kg before Start'));
            ELSE
                Auto_Error_Code := 0;
                GVL.Error_Code := 0;
                GVL.Current_Batch_Cycle := 1;
                GVL.Completed_Batch_Cycles := 0;
                GVL.All_Cycles_Complete := FALSE;
                Auto_Completed_Batch_Cycles := 0;
                Auto_Current_Batch_Cycle := 1;
                Auto_All_Cycles_Complete := FALSE;
                GVL.Run := TRUE;
                Internal_FB_Start := TRUE;
                Cycle_Manager_State := 1;
                Current_Step := 0;
                bin_last_weight := 0.0;
                PersistentVars.bin_last_weight := 0.0;
                PersistentVars.Ret_bin_last_weight := 0.0;
                FOR i := 1 TO 6 DO
                    Actual_Weights[i] := 0.0;
                    PersistentVars.Ret_Actual_Weights[i] := 0.0;
                END_FOR;
                Tare_Pulse_Req := TRUE; // Clean tare on fresh start
                GVL.Start_Button := FALSE;
            END_IF;
        END_IF;

    1: // RUNNING ACTIVE BATCH CYCLE
        Internal_FB_Start := TRUE;
        GVL.Run := TRUE;
        GVL.Next_Cycle_Start := FALSE;
        Next_Cycle_Ready := FALSE;
        GVL.Next_Cycle_Ready := FALSE;

        // Check Cycle Completion Handshake (Both Auto and Semi complete)
        IF Sequence_Complete AND GVL.Semi_Auto_Sequence_Complete AND (Auto_Has_Active_Bins OR Semi_Has_Active_Bins) THEN
            GVL.Completed_Batch_Cycles := GVL.Current_Batch_Cycle;
            Auto_Completed_Batch_Cycles := GVL.Current_Batch_Cycle;
            
            IF (GVL.Current_Batch_Cycle < GVL.Target_Batch_Cycles) AND (GVL.Error_Code = 0) THEN
                Internal_FB_Start := FALSE;
                Cycle_Manager_State := 5; // Transition to Between-Cycle Hold
                Between_Cycle_Hold := TRUE;
                Status_Message := 'Auto [Cycle Done]: Discharging - waiting for empty scale';
            ELSE
                Cycle_Manager_State := 4; // All Target Cycles Completed
                Between_Cycle_Hold := FALSE;
                GVL.Start_Button := FALSE;
            END_IF;
        END_IF;

    5: // PAUSED BETWEEN CYCLES (DISCHARGE & NEXT CYCLE READY HANDSHAKE)
        Internal_FB_Start := FALSE;
        GVL.Run := TRUE;
        
        // Debounce live load cell check for scale empty
        IF (load_cell_value <= eff_empty_limit) AND (GVL.load_cell_auto <= eff_empty_limit) AND (GVL.load_cell_semi_auto <= eff_empty_limit) THEN
            Empty_Debounce_Timer(IN := TRUE, PT := T#1S);
            IF Empty_Debounce_Timer.Q THEN
                Next_Cycle_Ready := TRUE;
                GVL.Next_Cycle_Ready := TRUE;
                Status_Message := 'Auto [State 5]: Scale Empty - Ready for Next Cycle Start';
            END_IF;
        ELSE
            Empty_Debounce_Timer(IN := FALSE);
            Next_Cycle_Ready := FALSE;
            GVL.Next_Cycle_Ready := FALSE;
            Status_Message := CONCAT('Auto [State 5]: Discharging batch (Scale > ', CONCAT(REAL_TO_STRING(eff_empty_limit), ' kg)...'));
        END_IF;

        // Next Cycle Trigger
        IF Next_Cycle_Rising THEN
            IF Auto_Error_Code > 0 THEN
                Status_Message := CONCAT('Auto [State 5]: Blocked by Auto_Error_Code ', INT_TO_STRING(Auto_Error_Code));
            ELSIF Next_Cycle_Ready AND (GVL.Current_Batch_Cycle < GVL.Target_Batch_Cycles) THEN
                // Reset Ready & Command
                Next_Cycle_Ready := FALSE;
                GVL.Next_Cycle_Ready := FALSE;
                GVL.Next_Cycle_Start := FALSE;
                Next_Cycle_Last := FALSE;
                
                // Increment batch cycle
                GVL.Current_Batch_Cycle := GVL.Current_Batch_Cycle + 1;
                Auto_Current_Batch_Cycle := GVL.Current_Batch_Cycle;
                
                // Prepare fresh cycle
                Sequence_Complete := FALSE;
                GVL.Auto_Sequence_Complete := FALSE;
                GVL.Semi_Auto_Sequence_Complete := FALSE;
                Between_Cycle_Hold := FALSE;
                Cycle_Manager_State := 1;
                Current_Step := 0;
                Internal_FB_Start := TRUE;
                
                bin_last_weight := 0.0;
                PersistentVars.bin_last_weight := 0.0;
                PersistentVars.Ret_bin_last_weight := 0.0;
                FOR i := 1 TO 6 DO
                    Actual_Weights[i] := 0.0;
                    PersistentVars.Ret_Actual_Weights[i] := 0.0;
                    Auto_Bin[i] := FALSE;
                    auto_bin_cutoff[i] := FALSE;
                    auto_bin_motor[i] := FALSE;
                END_FOR;
                
                // Fire tare pulse strictly on verified empty scale
                Tare_Pulse_Req := TRUE;
                Status_Message := CONCAT('Auto [State 5]: Cycle ', CONCAT(INT_TO_STRING(GVL.Current_Batch_Cycle), ' Started'));
            ELSE
                Status_Message := CONCAT('Auto [State 5]: Empty scale < ', CONCAT(REAL_TO_STRING(eff_empty_limit), ' kg before pressing Next Cycle!'));
            END_IF;
        END_IF;

    4: // ALL CYCLES COMPLETE
        Internal_FB_Start := FALSE;
        Between_Cycle_Hold := FALSE;
        GVL.Run := FALSE;
        GVL.Start_Button := FALSE;
        Auto_All_Cycles_Complete := TRUE;
        GVL.All_Cycles_Complete := TRUE;
        Sequence_Complete := TRUE;
        GVL.Auto_Sequence_Complete := TRUE;
        Next_Cycle_Ready := FALSE;
        GVL.Next_Cycle_Ready := FALSE;
        Status_Message := CONCAT('Auto [Finished]: All ', CONCAT(INT_TO_STRING(GVL.Target_Batch_Cycles), ' Batch Cycles Complete'));

        IF Start_Pulse THEN
            IF Scale_Empty_OK THEN
                Current_Step := 0;
                Cycle_Manager_State := 0;
                Auto_All_Cycles_Complete := FALSE;
                GVL.All_Cycles_Complete := FALSE;
            ELSE
                Auto_Error_Code := 4;
                GVL.Error_Code := 4;
                Status_Message := 'Auto [Finished]: Empty hopper before starting new job!';
            END_IF;
        END_IF;
END_CASE;

// -----------------------------------------------------------------------------
// 5. DOSING SEQUENCE (STEPS 1..6, SETTLE 7, COMPLETE 8)
// -----------------------------------------------------------------------------
IF (Current_Step = 0) AND Internal_FB_Start AND (Cycle_Manager_State = 1) THEN
    IF NOT Auto_Has_Active_Bins THEN
        Current_Step := 8;
        Sequence_Complete := TRUE;
        GVL.Auto_Sequence_Complete := TRUE;
    ELSE
        Current_Step := 1;
        bin_last_weight := load_cell_value;
        PersistentVars.Ret_bin_last_weight := bin_last_weight;
        PersistentVars.bin_last_weight := bin_last_weight;
        Last_Dosing_Step := 1;
        Sequence_Complete := FALSE;
        GVL.Auto_Sequence_Complete := FALSE;
    END_IF;
END_IF;

CASE Current_Step OF
    0:
        Active_Material_ID := 0;
        Active_Bin_ID := 0;
        Active_Target_Weight := 0.0;
        Active_Live_Weight := 0.0;
        FOR i := 1 TO 6 DO
            Auto_Bin[i] := FALSE;
            auto_bin_cutoff[i] := FALSE;
            auto_bin_motor[i] := FALSE;
        END_FOR;

    1..6:
        // Skip unmapped / zero-target bins
        WHILE (Current_Step >= 1) AND (Current_Step <= 6) DO
            Mat_Idx := Auto_Bin_Material_Mapping[Current_Step];
            IF (Mat_Idx < 1) OR (Mat_Idx > 20) THEN
                Mat_Idx := GVL.Auto_Bin_Material_Mapping[Current_Step];
            END_IF;
            target_weight := 0.0;
            IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) THEN
                target_weight := GVL.Recipe_Weights[Mat_Idx];
            END_IF;

            IF (Mat_Idx < 1) OR (Mat_Idx > 20) OR (target_weight <= 0.0) THEN
                Auto_Bin[Current_Step] := FALSE;
                auto_bin_cutoff[Current_Step] := FALSE;
                auto_bin_motor[Current_Step] := FALSE;
                Actual_Weights[Current_Step] := 0.0;
                IF Current_Step = 6 THEN
                    Current_Step := 7;
                    EXIT;
                ELSE
                    Current_Step := Current_Step + 1;
                END_IF;
            ELSE
                EXIT;
            END_IF;
        END_WHILE;

        IF Inter_Bin_Settling THEN
            FOR i := 1 TO 6 DO
                Auto_Bin[i] := FALSE;
                auto_bin_cutoff[i] := FALSE;
                auto_bin_motor[i] := FALSE;
            END_FOR;
            Active_Material_ID := Settle_Hold_Mat;
            Active_Bin_ID := Settle_Hold_Step;
            Active_Target_Weight := Settle_Hold_Target;
            
            // Debounce Inter-bin timer
            IF Inter_Bin_Settle_Arm = 0 THEN
                Inter_Bin_Timer(IN := FALSE);
                Inter_Bin_Settle_Arm := 1;
            ELSE
                Inter_Bin_Timer(IN := TRUE, PT := Inter_Bin_Delay);
                IF Inter_Bin_Timer.Q THEN
                    Inter_Bin_Timer(IN := FALSE);
                    bin_last_weight := load_cell_value;
                    PersistentVars.Ret_bin_last_weight := bin_last_weight;
                    PersistentVars.bin_last_weight := bin_last_weight;
                    Current_Step := Inter_Bin_Next_Step;
                    Last_Dosing_Step := Current_Step;
                    Inter_Bin_Settling := FALSE;
                    Inter_Bin_Settle_Arm := 0;
                END_IF;
            END_IF;

        ELSIF (Current_Step >= 1) AND (Current_Step <= 6) THEN
            Mat_Idx := Auto_Bin_Material_Mapping[Current_Step];
            IF (Mat_Idx < 1) OR (Mat_Idx > 20) THEN
                Mat_Idx := GVL.Auto_Bin_Material_Mapping[Current_Step];
            END_IF;
            target_weight := GVL.Recipe_Weights[Mat_Idx];
            
            IF Current_Step <> Last_Dosing_Step THEN
                bin_last_weight := load_cell_value;
                PersistentVars.Ret_bin_last_weight := bin_last_weight;
                PersistentVars.bin_last_weight := bin_last_weight;
                Last_Dosing_Step := Current_Step;
            END_IF;

            cutoff_trigger_weight := target_weight - Auto_Coarse_To_Fine_Speed[Current_Step];
            min_tol_weight := target_weight - Auto_Bin_Tolerance[Current_Step];
            max_tol_weight := target_weight + Auto_Bin_Tolerance[Current_Step];

            actual_bin := load_cell_value - bin_last_weight;
            IF actual_bin < 0.0 THEN
                actual_bin := 0.0;
            END_IF;

            Active_Material_ID := Mat_Idx;
            Active_Bin_ID := Current_Step;
            Active_Target_Weight := target_weight;

            // Update live weight only when not frozen in hold
            IF (NOT Paused_By_Hold) AND GVL.Run AND (Auto_Error_Code = 0) THEN
                Actual_Weights[Current_Step] := actual_bin;
                Active_Live_Weight := actual_bin;
                
                // Dosing Output Control
                IF actual_bin < cutoff_trigger_weight THEN
                    Auto_Bin[Current_Step] := TRUE;
                    auto_bin_cutoff[Current_Step] := FALSE;
                    auto_bin_motor[Current_Step] := TRUE;
                    Excess_Alarm := FALSE;
                    Status_Message := CONCAT('Auto [Step ', CONCAT(INT_TO_STRING(Current_Step), ']: Coarse Feeding'));
                ELSIF actual_bin < min_tol_weight THEN
                    Auto_Bin[Current_Step] := FALSE;
                    auto_bin_cutoff[Current_Step] := TRUE;
                    auto_bin_motor[Current_Step] := TRUE;
                    Excess_Alarm := FALSE;
                    Status_Message := CONCAT('Auto [Step ', CONCAT(INT_TO_STRING(Current_Step), ']: Fine Feeding'));
                ELSIF actual_bin > max_tol_weight THEN
                    Auto_Bin[Current_Step] := FALSE;
                    auto_bin_cutoff[Current_Step] := FALSE;
                    auto_bin_motor[Current_Step] := FALSE;
                    IF Excess_Allowed THEN
                        Excess_Alarm := FALSE;
                        Status_Message := CONCAT('Auto [Step ', CONCAT(INT_TO_STRING(Current_Step), ']: Target Reached (Excess Allowed)'));
                        // Advance to next
                        Settle_Hold_Step := Current_Step;
                        Settle_Hold_Mat := Mat_Idx;
                        Settle_Hold_Target := target_weight;
                        IF Current_Step >= 6 THEN
                            Current_Step := 7;
                        ELSE
                            Inter_Bin_Next_Step := Current_Step + 1;
                            Inter_Bin_Settling := TRUE;
                            Inter_Bin_Settle_Arm := 0;
                        END_IF;
                    ELSE
                        Excess_Alarm := TRUE;
                        Status_Message := CONCAT('Auto [Step ', CONCAT(INT_TO_STRING(Current_Step), ']: Excess Weight Alarm!'));
                    END_IF;
                ELSE
                    // Target Reached within Tolerance
                    Auto_Bin[Current_Step] := FALSE;
                    auto_bin_cutoff[Current_Step] := FALSE;
                    auto_bin_motor[Current_Step] := FALSE;
                    Excess_Alarm := FALSE;
                    Status_Message := CONCAT('Auto [Step ', CONCAT(INT_TO_STRING(Current_Step), ']: Target Reached - Advancing'));
                    Settle_Hold_Step := Current_Step;
                    Settle_Hold_Mat := Mat_Idx;
                    Settle_Hold_Target := target_weight;
                    IF Current_Step >= 6 THEN
                        Current_Step := 7;
                    ELSE
                        Inter_Bin_Next_Step := Current_Step + 1;
                        Inter_Bin_Settling := TRUE;
                        Inter_Bin_Settle_Arm := 0;
                    END_IF;
                END_IF;
            END_IF;
        END_IF;

    7: // FINAL SETTLING DELAY
        Active_Material_ID := 0;
        Active_Bin_ID := 0;
        Active_Target_Weight := 0.0;
        Active_Live_Weight := 0.0;
        FOR i := 1 TO 6 DO
            Auto_Bin[i] := FALSE;
            auto_bin_cutoff[i] := FALSE;
            auto_bin_motor[i] := FALSE;
        END_FOR;
        Status_Message := 'Auto [Step 7]: Settling Delay in progress...';
        Completion_Timer(IN := TRUE, PT := Effective_Delay);
        IF Completion_Timer.Q THEN
            Completion_Timer(IN := FALSE);
            Current_Step := 8;
        END_IF;

    8: // SEQUENCE COMPLETE
        Active_Material_ID := 0;
        Active_Bin_ID := 0;
        Active_Target_Weight := 0.0;
        Active_Live_Weight := 0.0;
        FOR i := 1 TO 6 DO
            Auto_Bin[i] := FALSE;
            auto_bin_cutoff[i] := FALSE;
            auto_bin_motor[i] := FALSE;
        END_FOR;
        Sequence_Complete := TRUE;
        GVL.Auto_Sequence_Complete := TRUE;
        IF NOT GVL.Semi_Auto_Sequence_Complete THEN
            Status_Message := 'Auto [Step 8]: Waiting for Semi-Auto partner...';
        ELSE
            Status_Message := 'Auto [Step 8]: Both Sequences Complete';
        END_IF;
END_CASE;

// -----------------------------------------------------------------------------
// 6. OUTPUT SYNCHRONIZATION & PERSISTENT SNAPSHOT
// -----------------------------------------------------------------------------
FOR i := 1 TO 6 DO
    GVL.Auto_Bin[i] := Auto_Bin[i];
    GVL.auto_bin_cutoff[i] := auto_bin_cutoff[i];
    GVL.auto_bin_motor[i] := auto_bin_motor[i];
    GVL.Auto_Weights[i] := Actual_Weights[i];
END_FOR;

Auto_Sum_Act_Weight := 0.0;
FOR i := 1 TO 6 DO
    Auto_Sum_Act_Weight := Auto_Sum_Act_Weight + Actual_Weights[i];
END_FOR;
GVL.Auto_Total_Actual_Weight := Auto_Sum_Act_Weight;

GVL.Auto_Active_Mat := Active_Material_ID;
GVL.Auto_Active_Bin := Active_Bin_ID;
GVL.Auto_Active_Target_Weight := Active_Target_Weight;
GVL.Auto_Active_Live_Weight := Active_Live_Weight;
GVL.Auto_Current_Step := Current_Step;

// Target setpoints mirror to GVL
FOR i := 1 TO 6 DO
    Mat_Idx := Auto_Bin_Material_Mapping[i];
    IF (Mat_Idx < 1) OR (Mat_Idx > 20) THEN
        Mat_Idx := GVL.Auto_Bin_Material_Mapping[i];
    END_IF;
    target_weight := 0.0;
    IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) THEN
        target_weight := GVL.Recipe_Weights[Mat_Idx];
    END_IF;
    Auto_Total_Target_Set[i] := target_weight;
    GVL.Auto_Target_Weights[i] := target_weight;
END_FOR;

// Persistent Retain Snapshot
IF Cycle_Manager_State = 4 THEN
    PersistentVars.Ret_Process_Was_Active := FALSE;
    PersistentVars.Ret_Cycle_Manager_State := 0;
    PersistentVars.Ret_Current_Step := 0;
    PersistentVars.Ret_Resume_Step := 0;
    PersistentVars.Ret_Active_Live_Weight := 0.0;
    PersistentVars.Ret_bin_last_weight := 0.0;
    FOR i := 1 TO 6 DO
        PersistentVars.Ret_Actual_Weights[i] := 0.0;
    END_FOR;
ELSIF Cycle_Manager_State = 1 OR Cycle_Manager_State = 5 THEN
    PersistentVars.Ret_Process_Was_Active := TRUE;
    PersistentVars.Ret_Cycle_Manager_State := Cycle_Manager_State;
    PersistentVars.Ret_Current_Step := Current_Step;
    IF (Current_Step >= 1) AND (Current_Step <= 6) THEN
        PersistentVars.Ret_Resume_Step := Current_Step;
    END_IF;
    PersistentVars.Ret_Current_Batch_Cycle := GVL.Current_Batch_Cycle;
    PersistentVars.Ret_Completed_Batch_Cycles := GVL.Completed_Batch_Cycles;
    PersistentVars.Ret_Target_Batch_Cycles := GVL.Target_Batch_Cycles;
    PersistentVars.Ret_Active_Material_ID := Active_Material_ID;
    PersistentVars.Ret_Active_Bin_ID := Active_Bin_ID;
    PersistentVars.Ret_Active_Target_Weight := Active_Target_Weight;
    PersistentVars.Ret_Active_Live_Weight := Active_Live_Weight;
    PersistentVars.Ret_bin_last_weight := bin_last_weight;
    FOR i := 1 TO 6 DO
        PersistentVars.Ret_Actual_Weights[i] := Actual_Weights[i];
    END_FOR;
END_IF;

// -----------------------------------------------------------------------------
// 7. TARE PULSE EMISSION (STRICT INTERLOCK)
// -----------------------------------------------------------------------------
// Tare can ONLY occur when explicitly requested on fresh start / next cycle AND scale < Empty_Weight_Limit
IF Tare_Pulse_Req THEN
    IF Scale_Empty_OK AND (Cycle_Manager_State = 1) AND (Current_Step <= 1) THEN
        Tare_Auto_Batch := TRUE;
    ELSE
        Tare_Auto_Batch := FALSE;
    END_IF;
    Tare_Pulse_Req := FALSE;
ELSE
    Tare_Auto_Batch := FALSE;
END_IF;

Waiting_Next_Batch := (Cycle_Manager_State = 5) AND (GVL.Target_Batch_Cycles > 1) AND (GVL.Current_Batch_Cycle < GVL.Target_Batch_Cycles);
GVL.Waiting_Next_batch_HMI_HIDE := Waiting_Next_Batch;
Auto_Current_Batch_Cycle := GVL.Current_Batch_Cycle;
Auto_Completed_Batch_Cycles := GVL.Completed_Batch_Cycles;
Auto_All_Cycles_Complete := GVL.All_Cycles_Complete;
END_FUNCTION_BLOCK
