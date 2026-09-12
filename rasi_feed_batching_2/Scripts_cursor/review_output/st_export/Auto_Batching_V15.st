FUNCTION_BLOCK Auto_Batching_V15
VAR_INPUT
    Start_Button : BOOL;                            // Optional start pin (legacy). Also ORed with GVL.Start_Button (%MX2.0 HMI) and Start_PB
    Start_PB : BOOL;                                // Physical Start pushbutton DI (one-shot pulse)
    Auto_Mode_DI : BOOL;                            // Auto Mode DI: TRUE = process start allowed; FALSE = HMI/PB start ignored
    E_Stop_Active : BOOL;                           // Emergency Stop circuit status (NC contact: TRUE = Healthy/Run permitted, FALSE = E-Stop tripped)
    Reset : BOOL;                                   // System reset pulse (clears active steps, outputs, alarms, and error flags)
    Auto_Bin_Material_Mapping : ARRAY[1..6] OF INT; // Array mapping physical Silos 1..6 to Recipe Material IDs (1..20, 0 = Silo skipped)
    Auto_Coarse_To_Fine_Speed : ARRAY[1..6] OF REAL;// Weight offset threshold (kg) before target to transition from Coarse to Fine feeding
    Auto_Bin_Tolerance : ARRAY[1..6] OF REAL;       // Allowable weight tolerance window (±kg) around target weight for each silo
    Inter_Bin_Delay : TIME;                         // Pause after Bin*=FALSE: tailings on SAME bin ID; then next mat (Auto e.g. T#5S)
    Excess_Allowed : BOOL;                          // Overfill handling policy: TRUE = proceed if target is exceeded, FALSE = raise alarm and halt
    load_cell_value : REAL;                         // Live gross weight input reading from the Auto scale load cell (kg)
    Target_Batch_Cycles : INT;                      // Target number of batch cycle repetitions configured from HMI (defaults to 1)
    Next_Cycle_Start : BOOL;                        // NextBatchStart: after a completed cycle (Target>1), press when this FB scale < Empty_Weight_Limit
    Empty_Weight_Limit : REAL;                      // Both scales must be LT this (kg) before Start/Start_PB, Next_Cycle_Start, or Tare pulse
    Line_Fault : BOOL;                              // Wire from FB_Samyak_Multi.arrLine_Fault[n] (Auto scale). TRUE = hold process (Over Dump Avoid)
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
    Error_Code : INT;                               // Fault diagnostic code:
                                                    //   0  = No Error / System Healthy
                                                    //   1  = Duplicate Material ID mapped across Auto and Semi-Auto
                                                    //   2  = Material index out of range (must be 1..20)
                                                    //   3  = Recipe weight is less than (Coarse_To_Fine_Speed + Tolerance)
                                                    //   4  = Initial scale tare error (scale not empty before start)
                                                    //   5  = Communication Fault (Line_Fault from FB_Samyak_Multi; scale Modbus/line fault; Over Dump Avoid HOLD)
                                                    //   21 = Scale overload protection triggered (> 500 kg)
    Auto_Current_Batch_Cycle : INT;                     // Active batch cycle number currently processing (1..Target_Batch_Cycles)
    Auto_Completed_Batch_Cycles : INT;                  // Total number of batch cycle loops completed successfully
    Auto_All_Cycles_Complete : BOOL;                    // Master flag: TRUE when all Target_Batch_Cycles have finished
    Status_Message : STRING(80);                    // Real-time human-readable process status and diagnostic text message
    Tare_Auto_Batch : BOOL;                         // One-scan pulse to Samyak ONLY when BOTH scales LT Empty_Weight_Limit (never after batch with product on scale)
    Waiting_Next_Batch : BOOL;                      // TRUE in state 5 while Current < Target (HMI hide/lamp); FALSE when next cycle runs; never TRUE on last cycle
END_VAR
VAR
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
    Settle_Hold_Step : INT;                         // Completed bin step held on HMI during inter-bin settle (Excess_Allowed=FALSE)
    Settle_Hold_Mat : INT;                          // Material ID of completed bin during settle hold
    Settle_Hold_Target : REAL;                      // Target kg of completed bin during settle hold
    Inter_Bin_Next_Step : INT;                      // Next active bin step — applied when inter-bin timer completes
    Mat_Idx : INT;
    i : INT;
    j : INT;
    Transition_Timer : TON;
    Completion_Timer : TON;
    Simulation_Mode : BOOL;
    Sim_Rate : REAL;
    Sim_Timer : TON;
    Start_Sim_Weight : REAL;
    Discharge_Active : BOOL;
    
    (* Master Cycle Manager & Supervisory states *)
    Internal_FB_Start : BOOL;
    Duplicate_Found : BOOL;
    Invalid_Material_Range : BOOL;
    Weight_Limit_Error : BOOL;
    eff_empty_limit : REAL;
    Scale_Empty_OK : BOOL;                          // TRUE when this FB load AND partner Semi scale are LT Empty_Weight_Limit
    Next_Cycle_Last : BOOL;
    Next_Cycle_Rising : BOOL;
    Paused_By_LineFault : BOOL;                     // Latched while Line_Fault is TRUE (outputs forced OFF)
    Tare_Pulse_Req : BOOL;                          // Internal request to emit Tare_Auto_Batch for one scan
    Start_Cmd : BOOL;                               // (Start_Button OR GVL.Start_Button OR Start_PB) AND Auto_Mode_DI
    Start_Cmd_Last : BOOL;                          // Edge memory for Start_Cmd
    Start_Pulse : BOOL;                             // Rising edge of Start_Cmd (one-shot process start only; HOLD auto-resumes)
    First_Scan_Done : BOOL;                         // FALSE after PLC power-up (non-retain)
    Pending_Resume_Job : BOOL;                      // TRUE when Ret weights show unfinished bins after power
    Auto_Has_Active_Bins : BOOL;                    // TRUE when any Auto bin 1..6 has target weight > 0
    Semi_Has_Active_Bins : BOOL;                    // Partner Semi: any bin 1..10 with target > 0 (from GVL mapping)
    Reset_Last : BOOL;                              // Edge memory for Reset / GVL.Reset
    Reset_Pulse : BOOL;                             // Rising edge Reset (held Reset must not freeze FB)
    Fresh_After_Reset : BOOL;                       // TRUE after Reset: allow one Start even if scale not empty (Error 4 bypass once)
    Between_Cycle_Hold : BOOL;                      // TRUE while waiting for empty scale + Next_Cycle_Start (CMS 5); same role as Semi FB
    Last_Dosing_Step : INT;                         // Last dosing step 1..6 (snap bin_last on new bin → ALW=0)
END_VAR



(* Uses Application.PersistentVars (VAR_GLOBAL PERSISTENT) - no FB VAR RETAIN *)
(* Auto Batching FB V15: Start = (HMI%MX2.0 OR Start_PB OR pin) AND Auto_Mode_DI, rising-edge pulse *)

(* Inter_Bin_Delay: VAR_INPUT from batching14 only (no GVL) — between bins; Step 7 uses Effective_Delay *)
Effective_Delay := Inter_Bin_Delay;
IF Effective_Delay = T#0S THEN
    Effective_Delay := T#2S;
END_IF;

(* Empty-scale interlock (pin -> GVL.Empty_Weight_Limit -> 5 kg default) *)
eff_empty_limit := Empty_Weight_Limit;
IF eff_empty_limit <= 0.0 THEN
    eff_empty_limit := GVL.Empty_Weight_Limit;
END_IF;
IF eff_empty_limit <= 0.0 THEN
    eff_empty_limit := 5.0;
END_IF;
(* Tare + Next_Cycle_Start only when BOTH Auto and Semi live weights are below limit *)
(* Both FB pin AND GVL mirror per scale — avoids stale zero input passing when tank still has batch *)
Scale_Empty_OK := (load_cell_value < eff_empty_limit) AND (GVL.load_cell_auto < eff_empty_limit)
    AND (GVL.load_cell_semi_auto < eff_empty_limit);

(* Process Start: HMI Start (%MX2.0) unchanged; Start_PB pulse; gated by Auto_Mode_DI inside FB *)
Start_Cmd := (Start_Button OR GVL.Start_Button OR Start_PB) AND Auto_Mode_DI;
Start_Pulse := Start_Cmd AND NOT Start_Cmd_Last;
Start_Cmd_Last := Start_Cmd;

(* Detect rising edge on Next_Cycle_Start / NextBatchStart (pin OR GVL.%MX2.4) *)
Next_Cycle_Rising := (Next_Cycle_Start OR GVL.Next_Cycle_Start) AND NOT Next_Cycle_Last;
Next_Cycle_Last := (Next_Cycle_Start OR GVL.Next_Cycle_Start);

(* Reset must be rising-edge - held HMI Reset switch would block Start forever *)
Reset_Pulse := (Reset OR GVL.Reset) AND NOT Reset_Last;
Reset_Last := (Reset OR GVL.Reset);

(* GVL Recipe/Mapping <-> Application retain (PersistentVars, no AT address) *)
(* RESTORE: first scan after power ONLY — every-scan restore blocked HMI edits to %MD100/%MW60 *)
IF NOT First_Scan_Done THEN
    FOR i := 1 TO 20 DO
        IF (GVL.Recipe_Weights[i] <= 0.01) AND (PersistentVars.Ret_Recipe_Weights[i] > 0.01) THEN
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
END_IF;
(* SNAPSHOT: HMI owns GVL %MD100/%MW50/%MW60 — mirror full array to retain every scan *)
FOR i := 1 TO 20 DO
    PersistentVars.Ret_Recipe_Weights[i] := GVL.Recipe_Weights[i];
END_FOR;
FOR i := 1 TO 6 DO
    PersistentVars.Ret_Bin_Material_Mapping[i] := GVL.Auto_Bin_Material_Mapping[i];
END_FOR;
FOR i := 1 TO 10 DO
    PersistentVars.Ret_Semi_Bin_Material_Mapping[i] := GVL.Semi_Auto_Bin_Material_Mapping[i];
END_FOR;

(* 1. RECIPE TOTALS & SUPERVISORY CONFIGURATION CHECKS *)
Duplicate_Found := FALSE;
Invalid_Material_Range := FALSE;
Weight_Limit_Error := FALSE;

GVL.Auto_Total_Target_Weight := 0.0;
GVL.Auto_Material_Count := 0;
FOR i := 1 TO 6 DO
    IF Auto_Bin_Material_Mapping[i] < 0 OR Auto_Bin_Material_Mapping[i] > 20 THEN
        Invalid_Material_Range := TRUE;
    END_IF;
    IF Auto_Bin_Material_Mapping[i] <> 0 AND Auto_Bin_Material_Mapping[i] <= 20 THEN
        FOR j := 1 TO 10 DO
            IF Auto_Bin_Material_Mapping[i] = GVL.Semi_Auto_Bin_Material_Mapping[j] THEN
                Duplicate_Found := TRUE;
            END_IF;
        END_FOR;
    END_IF;
    IF Auto_Bin_Material_Mapping[i] > 0 AND Auto_Bin_Material_Mapping[i] <= 20 THEN
        IF GVL.Recipe_Weights[Auto_Bin_Material_Mapping[i]] > 0.0 THEN
            GVL.Auto_Total_Target_Weight := GVL.Auto_Total_Target_Weight + GVL.Recipe_Weights[Auto_Bin_Material_Mapping[i]];
            GVL.Auto_Material_Count := GVL.Auto_Material_Count + 1;
            IF GVL.Recipe_Weights[Auto_Bin_Material_Mapping[i]] < (Auto_Coarse_To_Fine_Speed[i] + Auto_Bin_Tolerance[i]) THEN
                Weight_Limit_Error := TRUE;
            END_IF;
        END_IF;
    END_IF;
END_FOR;

(* Any Auto bin with valid Mat_ID (1..20) AND target > 0 — FALSE when all Mat_ID=0 / Target=0 (Semi-only) *)
Auto_Has_Active_Bins := FALSE;
FOR i := 1 TO 6 DO
    Mat_Idx := Auto_Bin_Material_Mapping[i];
    IF (Mat_Idx < 1) OR (Mat_Idx > 20) THEN
        Mat_Idx := PersistentVars.Ret_Bin_Material_Mapping[i];
    END_IF;
    target_weight := 0.0;
    IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) THEN
        target_weight := GVL.Recipe_Weights[Mat_Idx];
    END_IF;
    (* Retain target after power even if %M recipe/mapping lost *)
    IF (target_weight <= 0.0) AND (PersistentVars.Ret_Bin_Target_Weights[i] > 0.0) THEN
        target_weight := PersistentVars.Ret_Bin_Target_Weights[i];
    END_IF;
    (* Active bin: valid material AND dose target > 0 *)
    IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) AND (target_weight > 0.0) THEN
        Auto_Has_Active_Bins := TRUE;
        EXIT;
    ELSIF (PersistentVars.Ret_Bin_Target_Weights[i] > 0.0) AND (target_weight > 0.0) THEN
        (* Power resume: pending retain target without live mapping *)
        Auto_Has_Active_Bins := TRUE;
        EXIT;
    END_IF;
END_FOR;

(* Partner Semi bins — for handshake guard (instant SeqComplete must not fake CMS5) *)
Semi_Has_Active_Bins := FALSE;
FOR i := 1 TO 10 DO
    Mat_Idx := GVL.Semi_Auto_Bin_Material_Mapping[i];
    IF (Mat_Idx < 1) OR (Mat_Idx > 20) THEN
        Mat_Idx := PersistentVars.Ret_Semi_Bin_Material_Mapping[i];
    END_IF;
    target_weight := 0.0;
    IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) THEN
        target_weight := GVL.Recipe_Weights[Mat_Idx];
    END_IF;
    IF (target_weight <= 0.0) AND (PersistentVars.Ret_Semi_Bin_Target_Weights[i] > 0.0) THEN
        target_weight := PersistentVars.Ret_Semi_Bin_Target_Weights[i];
    END_IF;
    IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) AND (target_weight > 0.0) THEN
        Semi_Has_Active_Bins := TRUE;
        EXIT;
    ELSIF (PersistentVars.Ret_Semi_Bin_Target_Weights[i] > 0.0) AND (target_weight > 0.0) THEN
        Semi_Has_Active_Bins := TRUE;
        EXIT;
    END_IF;
END_FOR;

IF Duplicate_Found THEN
    GVL.Error_Code := 1;
    Error_Code := 1;
    Status_Message := 'Error 1: Duplicate Material ID mapped in Auto and Semi-Auto!';
ELSIF Invalid_Material_Range THEN
    GVL.Error_Code := 2;
    Error_Code := 2;
    Status_Message := 'Error 2: Material Index configuration out of range (1..20)!';
ELSIF Weight_Limit_Error THEN
    GVL.Error_Code := 3;
    Error_Code := 3;
    Status_Message := 'Error 3: Recipe weight is less than Coarse_To_Fine_Speed + Tolerance!';
ELSE
    IF GVL.Error_Code <= 3 THEN
        GVL.Error_Code := 0;
        Error_Code := 0;
    END_IF;
END_IF;

(* 2. HARD RESET INTERLOCK *)
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
    END_FOR;
    Auto_Sum_Act_Weight := 0.0;
    GVL.Auto_Total_Actual_Weight := 0.0;
    
    (* Fresh cycle Reset: keep HMI Recipe Mode setpoints (do NOT clear Recipe_Weights / mappings) *)
    GVL.Auto_Total_Target_Weight := 0.0;
    GVL.Semi_Auto_Total_Target_Weight := 0.0;
    GVL.Auto_Material_Count := 0;
    GVL.Semi_Auto_Material_Count := 0;
    
    Sequence_Complete := FALSE;
    GVL.Auto_Sequence_Complete := FALSE;
    GVL.Semi_Auto_Sequence_Complete := FALSE;
    Active_Material_ID := 0;
    Active_Bin_ID := 0;
    Active_Target_Weight := 0.0;
    Active_Live_Weight := 0.0;
    GVL.Auto_Active_Target_Weight := 0.0;
    GVL.Auto_Active_Live_Weight := 0.0;
    Excess_Alarm := FALSE;
    Error_Code := 0;
    GVL.Error_Code := 0;
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
    Next_Cycle_Last := FALSE;
    Next_Cycle_Rising := FALSE;
    GVL.Auto_Active_Mat := 0;
    GVL.Auto_Active_Bin := 0;
    GVL.Auto_Excess_Alarm := FALSE;
    Current_Step := 0;
    Cycle_Manager_State := 0;
    Internal_FB_Start := FALSE;
    Paused_By_LineFault := FALSE;
    Tare_Pulse_Req := FALSE;
    Tare_Auto_Batch := FALSE;
    Waiting_Next_Batch := FALSE;
    Between_Cycle_Hold := FALSE;
    Start_Cmd := FALSE;
    Start_Cmd_Last := FALSE;
    Start_Pulse := FALSE;
    Paused_By_Hold := FALSE;
    First_Scan_Done := TRUE;
    Fresh_After_Reset := TRUE;
    PersistentVars.Ret_Process_Was_Active := FALSE;
    PersistentVars.Ret_GVL_Run := FALSE;
    PersistentVars.Ret_Cycle_Manager_State := 0;
    PersistentVars.Ret_Current_Step := 0;
    PersistentVars.Ret_Internal_FB_Start := FALSE;
    PersistentVars.Ret_Target_Batch_Cycles := 0;
    PersistentVars.Ret_Active_Material_ID := 0;
    PersistentVars.Ret_Active_Bin_ID := 0;
    PersistentVars.Ret_Active_Target_Weight := 0.0;
    PersistentVars.Ret_Active_Live_Weight := 0.0;
    PersistentVars.Ret_Resume_Step := 0;
    FOR i := 1 TO 6 DO
        PersistentVars.Ret_Actual_Weights[i] := 0.0;
        PersistentVars.Ret_Bin_Target_Weights[i] := 0.0;
        (* Ret_Bin_Material_Mapping + Ret_Recipe_Weights kept for HMI recipe after Reset *)
    END_FOR;
    GVL.Auto_Current_Step := 0;
    PersistentVars.bin_last_weight := 0.0;
    Start_Sim_Weight := 0.0;
    Transition_Timer(IN := FALSE);
    Completion_Timer(IN := FALSE);
    Inter_Bin_Timer(IN := FALSE);
    Inter_Bin_Settling := FALSE;
    Inter_Bin_Settle_Arm := 0;
    Settle_Hold_Step := 0;
    Settle_Hold_Mat := 0;
    Settle_Hold_Target := 0.0;
    Inter_Bin_Next_Step := 0;
    Last_Dosing_Step := 0;
    Sim_Timer(IN := FALSE);
    Status_Message := 'Auto [Reset]: Fresh cycle ready. Set Target + empty/confirm scale, then Start.';
    (* Do NOT clear GVL.Reset here — Auto runs before Semi in batching14; Semi clears after both FBs *)
    RETURN;
END_IF;

(* 2b. POWER-RESTORE - never trust CMS5/Step8 if pending bins (GVL Recipe/Mapping %M lost after power) *)
IF NOT First_Scan_Done THEN
    First_Scan_Done := TRUE;
    (* Power-down scans clear Process_Was_Active while Ret weights/batch counts survive — rebuild *)
    Pending_Resume_Job := FALSE;
    IF NOT PersistentVars.Ret_Process_Was_Active THEN
        FOR i := 1 TO 6 DO
            IF PersistentVars.Ret_Bin_Target_Weights[i] > 0.0 THEN
                IF PersistentVars.Ret_Actual_Weights[i] < (PersistentVars.Ret_Bin_Target_Weights[i] - 0.05) THEN
                    Pending_Resume_Job := TRUE;
                    PersistentVars.Ret_Process_Was_Active := TRUE;
                    PersistentVars.Ret_Current_Step := i;
                    PersistentVars.Ret_Cycle_Manager_State := 1;
                    PersistentVars.Ret_Internal_FB_Start := TRUE;
                    PersistentVars.Ret_Resume_Step := i;
                    Mat_Idx := PersistentVars.Ret_Bin_Material_Mapping[i];
                    IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) THEN
                        PersistentVars.Ret_Active_Material_ID := Mat_Idx;
                    END_IF;
                    PersistentVars.Ret_Active_Bin_ID := i;
                    PersistentVars.Ret_Active_Target_Weight := PersistentVars.Ret_Bin_Target_Weights[i];
                    PersistentVars.bin_last_weight := 0.0;
                    IF i > 1 THEN
                        FOR j := 1 TO (i - 1) DO
                            PersistentVars.bin_last_weight := PersistentVars.bin_last_weight + PersistentVars.Ret_Actual_Weights[j];
                        END_FOR;
                    END_IF;
                    PersistentVars.Ret_bin_last_weight := PersistentVars.bin_last_weight;
                    EXIT;
                END_IF;
            END_IF;
        END_FOR;
        IF (NOT Pending_Resume_Job) AND (PersistentVars.Ret_Target_Batch_Cycles > 0)
            AND (PersistentVars.Ret_Completed_Batch_Cycles < PersistentVars.Ret_Target_Batch_Cycles)
            AND (PersistentVars.Ret_Cycle_Manager_State = 5) THEN
            Pending_Resume_Job := TRUE;
            PersistentVars.Ret_Process_Was_Active := TRUE;
        END_IF;
    END_IF;
    (* Prefer last dosing step 1..6 only   never resume at Step 7/8 settling/complete *)
    IF PersistentVars.Ret_Process_Was_Active AND (PersistentVars.Ret_Resume_Step >= 1) AND (PersistentVars.Ret_Resume_Step <= 6) THEN
        PersistentVars.Ret_Current_Step := PersistentVars.Ret_Resume_Step;
        PersistentVars.Ret_Cycle_Manager_State := 1;
        PersistentVars.Ret_Internal_FB_Start := TRUE;
        IF PersistentVars.Ret_Current_Batch_Cycle < 1 THEN
            PersistentVars.Ret_Current_Batch_Cycle := 1;
        END_IF;
    END_IF;
    (* Step 7/8 or CMS5 with unfinished bins -> first pending material step *)
    IF PersistentVars.Ret_Process_Was_Active AND (
        (PersistentVars.Ret_Current_Step >= 7) OR (PersistentVars.Ret_Cycle_Manager_State = 5)
    ) THEN
        FOR i := 1 TO 6 DO
            Mat_Idx := Auto_Bin_Material_Mapping[i];
            IF (Mat_Idx < 1) OR (Mat_Idx > 20) THEN
                Mat_Idx := PersistentVars.Ret_Bin_Material_Mapping[i];
            END_IF;
            IF ((Mat_Idx >= 1) AND (Mat_Idx <= 20)) OR (PersistentVars.Ret_Bin_Target_Weights[i] > 0.0) THEN
                IF PersistentVars.Ret_Bin_Target_Weights[i] > 0.0 THEN
                    IF PersistentVars.Ret_Actual_Weights[i] < (PersistentVars.Ret_Bin_Target_Weights[i] * 0.5) THEN
                        PersistentVars.Ret_Current_Step := i;
                        PersistentVars.Ret_Cycle_Manager_State := 1;
                        PersistentVars.Ret_Internal_FB_Start := TRUE;
                        PersistentVars.Ret_Resume_Step := i;
                        IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) THEN
                            PersistentVars.Ret_Active_Material_ID := Mat_Idx;
                        END_IF;
                        PersistentVars.Ret_Active_Bin_ID := i;
                        PersistentVars.Ret_Active_Target_Weight := PersistentVars.Ret_Bin_Target_Weights[i];
                        PersistentVars.bin_last_weight := 0.0;
                        IF i > 1 THEN
                            FOR j := 1 TO (i - 1) DO
                                PersistentVars.bin_last_weight := PersistentVars.bin_last_weight + PersistentVars.Ret_Actual_Weights[j];
                            END_FOR;
                        END_IF;
                        PersistentVars.Ret_bin_last_weight := PersistentVars.bin_last_weight;
                        EXIT;
                    END_IF;
                ELSIF PersistentVars.Ret_Actual_Weights[i] <= 0.001 THEN
                    PersistentVars.Ret_Current_Step := i;
                    PersistentVars.Ret_Cycle_Manager_State := 1;
                    PersistentVars.Ret_Internal_FB_Start := TRUE;
                    PersistentVars.Ret_Resume_Step := i;
                    IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) THEN
                        PersistentVars.Ret_Active_Material_ID := Mat_Idx;
                    END_IF;
                    PersistentVars.Ret_Active_Bin_ID := i;
                    IF PersistentVars.Ret_Bin_Target_Weights[i] > 0.0 THEN
                        PersistentVars.Ret_Active_Target_Weight := PersistentVars.Ret_Bin_Target_Weights[i];
                    END_IF;
                    PersistentVars.bin_last_weight := 0.0;
                    IF i > 1 THEN
                        FOR j := 1 TO (i - 1) DO
                            PersistentVars.bin_last_weight := PersistentVars.bin_last_weight + PersistentVars.Ret_Actual_Weights[j];
                        END_FOR;
                    END_IF;
                    PersistentVars.Ret_bin_last_weight := PersistentVars.bin_last_weight;
                    EXIT;
                END_IF;
            END_IF;
        END_FOR;
    END_IF;
    (* Semi-only: never restore to step 7 settle — go straight to step 8 complete *)
    IF PersistentVars.Ret_Process_Was_Active AND (NOT Auto_Has_Active_Bins) AND (PersistentVars.Ret_Current_Step >= 7) THEN
        PersistentVars.Ret_Current_Step := 8;
        PersistentVars.Ret_Resume_Step := 0;
        PersistentVars.Ret_Cycle_Manager_State := 1;
        PersistentVars.Ret_Internal_FB_Start := TRUE;
    END_IF;
    IF PersistentVars.Ret_Process_Was_Active AND (PersistentVars.Ret_Cycle_Manager_State <> 4) AND (
        ((PersistentVars.Ret_Current_Step >= 1) AND (PersistentVars.Ret_Current_Step <= 6))
        OR ((PersistentVars.Ret_Current_Step = 8) AND (NOT Auto_Has_Active_Bins))
        OR ((PersistentVars.Ret_Cycle_Manager_State = 5) AND (PersistentVars.Ret_Completed_Batch_Cycles < PersistentVars.Ret_Target_Batch_Cycles) AND (PersistentVars.Ret_Resume_Step = 0))
    ) THEN
        Current_Step := PersistentVars.Ret_Current_Step;
        Cycle_Manager_State := PersistentVars.Ret_Cycle_Manager_State;
        IF Cycle_Manager_State = 0 THEN
            Cycle_Manager_State := 1;
        END_IF;
        IF Cycle_Manager_State = 5 THEN
            Internal_FB_Start := FALSE;
            Between_Cycle_Hold := TRUE;
        ELSE
            Internal_FB_Start := TRUE;
            Between_Cycle_Hold := FALSE;
        END_IF;
        PersistentVars.bin_last_weight := PersistentVars.Ret_bin_last_weight;
        GVL.Run := TRUE;
        GVL.Current_Batch_Cycle := PersistentVars.Ret_Current_Batch_Cycle;
        GVL.Completed_Batch_Cycles := PersistentVars.Ret_Completed_Batch_Cycles;
        IF PersistentVars.Ret_Target_Batch_Cycles > 0 THEN
            GVL.Target_Batch_Cycles := PersistentVars.Ret_Target_Batch_Cycles;
        END_IF;
        FOR i := 1 TO 6 DO
            Actual_Weights[i] := PersistentVars.Ret_Actual_Weights[i];
            GVL.Auto_Weights[i] := PersistentVars.Ret_Actual_Weights[i];
        END_FOR;
        Auto_Sum_Act_Weight := 0.0;
        FOR i := 1 TO 6 DO
            Auto_Sum_Act_Weight := Auto_Sum_Act_Weight + Actual_Weights[i];
        END_FOR;
        GVL.Auto_Total_Actual_Weight := Auto_Sum_Act_Weight;
        IF (Current_Step >= 1) AND (Current_Step <= 6) THEN
            Mat_Idx := Auto_Bin_Material_Mapping[Current_Step];
            IF (Mat_Idx < 1) OR (Mat_Idx > 20) THEN
                Mat_Idx := PersistentVars.Ret_Bin_Material_Mapping[Current_Step];
            END_IF;
            Active_Bin_ID := Current_Step;
            IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) THEN
                Active_Material_ID := Mat_Idx;
            ELSE
                Active_Material_ID := PersistentVars.Ret_Active_Material_ID;
            END_IF;
            IF PersistentVars.Ret_Bin_Target_Weights[Current_Step] > 0.0 THEN
                Active_Target_Weight := PersistentVars.Ret_Bin_Target_Weights[Current_Step];
            ELSIF PersistentVars.Ret_Active_Target_Weight > 0.0 THEN
                Active_Target_Weight := PersistentVars.Ret_Active_Target_Weight;
            ELSIF (Mat_Idx >= 1) AND (Mat_Idx <= 20) AND (GVL.Recipe_Weights[Mat_Idx] > 0.0) THEN
                Active_Target_Weight := GVL.Recipe_Weights[Mat_Idx];
            ELSE
                Active_Target_Weight := 0.0;
            END_IF;
        ELSE
            Active_Material_ID := PersistentVars.Ret_Active_Material_ID;
            Active_Bin_ID := PersistentVars.Ret_Active_Bin_ID;
            Active_Target_Weight := PersistentVars.Ret_Active_Target_Weight;
        END_IF;
        GVL.Auto_Active_Mat := Active_Material_ID;
        GVL.Auto_Active_Bin := Active_Bin_ID;
        GVL.Auto_Active_Target_Weight := Active_Target_Weight;
        PersistentVars.Ret_Active_Material_ID := Active_Material_ID;
        PersistentVars.Ret_Active_Bin_ID := Active_Bin_ID;
        PersistentVars.Ret_Active_Target_Weight := Active_Target_Weight;
        actual_bin := load_cell_value - PersistentVars.bin_last_weight;
        IF actual_bin < 0.0 THEN
            actual_bin := 0.0;
        END_IF;
        IF (load_cell_value = 0.0) AND (PersistentVars.Ret_Active_Live_Weight > 0.0) THEN
            Active_Live_Weight := PersistentVars.Ret_Active_Live_Weight;
        ELSE
            Active_Live_Weight := actual_bin;
        END_IF;
        GVL.Auto_Active_Live_Weight := Active_Live_Weight;
        PersistentVars.Ret_Active_Live_Weight := Active_Live_Weight;
        Auto_Current_Batch_Cycle := GVL.Current_Batch_Cycle;
        Auto_Completed_Batch_Cycles := GVL.Completed_Batch_Cycles;
        GVL.All_Cycles_Complete := FALSE;
        Auto_All_Cycles_Complete := FALSE;
        IF (Current_Step = 8) AND (NOT Auto_Has_Active_Bins) THEN
            Sequence_Complete := TRUE;
            GVL.Auto_Sequence_Complete := TRUE;
            Status_Message := 'Auto [POWER]: Semi-only — Auto complete (no bins)';
        ELSIF Cycle_Manager_State = 5 THEN
            Sequence_Complete := TRUE;
            GVL.Auto_Sequence_Complete := TRUE;
            Status_Message := 'Auto [POWER]: Waiting next - DUMP/empty scale then Next_Cycle_Start';
        ELSE
            Sequence_Complete := FALSE;
            GVL.Auto_Sequence_Complete := FALSE;
            GVL.Semi_Auto_Sequence_Complete := FALSE;
            Status_Message := CONCAT('Auto [POWER]: Pending Mat dump Step ', CONCAT(INT_TO_STRING(Current_Step), ' - HOLD then continue'));
        END_IF;
        (* Auto-continue if E-Stop healthy and Auto Mode ON   no Start press needed *)
        IF E_Stop_Active AND Auto_Mode_DI THEN
            Paused_By_Hold := FALSE;
        ELSE
            Paused_By_Hold := TRUE;
        END_IF;
    ELSE
        Pending_Resume_Job := FALSE;
        j := 0;
        FOR i := 1 TO 6 DO
            IF PersistentVars.Ret_Bin_Target_Weights[i] > 0.0 THEN
                IF PersistentVars.Ret_Actual_Weights[i] < (PersistentVars.Ret_Bin_Target_Weights[i] - 0.05) THEN
                    Pending_Resume_Job := TRUE;
                    j := i;
                    EXIT;
                END_IF;
            END_IF;
        END_FOR;
        IF Pending_Resume_Job OR PersistentVars.Ret_Process_Was_Active OR (PersistentVars.Ret_Current_Step <> 0) OR (PersistentVars.Ret_Cycle_Manager_State <> 0) THEN
            (* Fallback restore when flags were cleared but Ret weights/batch counts remain *)
            Current_Step := PersistentVars.Ret_Current_Step;
            IF (Current_Step < 1) OR (Current_Step > 7) THEN
                Current_Step := PersistentVars.Ret_Resume_Step;
            END_IF;
            IF ((Current_Step < 1) OR (Current_Step > 6)) AND (j > 0) THEN
                Current_Step := j;
            END_IF;
            Cycle_Manager_State := PersistentVars.Ret_Cycle_Manager_State;
            IF Cycle_Manager_State = 0 THEN
                Cycle_Manager_State := 1;
            END_IF;
            IF Cycle_Manager_State = 5 THEN
                Internal_FB_Start := FALSE;
            ELSE
                Internal_FB_Start := TRUE;
            END_IF;
            PersistentVars.bin_last_weight := PersistentVars.Ret_bin_last_weight;
            GVL.Current_Batch_Cycle := PersistentVars.Ret_Current_Batch_Cycle;
            GVL.Completed_Batch_Cycles := PersistentVars.Ret_Completed_Batch_Cycles;
            IF PersistentVars.Ret_Target_Batch_Cycles > 0 THEN
                GVL.Target_Batch_Cycles := PersistentVars.Ret_Target_Batch_Cycles;
            END_IF;
            FOR i := 1 TO 6 DO
                Actual_Weights[i] := PersistentVars.Ret_Actual_Weights[i];
                GVL.Auto_Weights[i] := PersistentVars.Ret_Actual_Weights[i];
            END_FOR;
            Auto_Sum_Act_Weight := 0.0;
            FOR i := 1 TO 6 DO
                Auto_Sum_Act_Weight := Auto_Sum_Act_Weight + Actual_Weights[i];
            END_FOR;
            GVL.Auto_Total_Actual_Weight := Auto_Sum_Act_Weight;
            IF (Current_Step >= 1) AND (Current_Step <= 6) THEN
                Active_Bin_ID := Current_Step;
                Mat_Idx := Auto_Bin_Material_Mapping[Current_Step];
                IF (Mat_Idx < 1) OR (Mat_Idx > 20) THEN
                    Mat_Idx := PersistentVars.Ret_Bin_Material_Mapping[Current_Step];
                END_IF;
                IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) THEN
                    Active_Material_ID := Mat_Idx;
                ELSE
                    Active_Material_ID := PersistentVars.Ret_Active_Material_ID;
                END_IF;
                IF PersistentVars.Ret_Bin_Target_Weights[Current_Step] > 0.0 THEN
                    Active_Target_Weight := PersistentVars.Ret_Bin_Target_Weights[Current_Step];
                ELSE
                    Active_Target_Weight := PersistentVars.Ret_Active_Target_Weight;
                END_IF;
            ELSE
                Active_Material_ID := PersistentVars.Ret_Active_Material_ID;
                Active_Bin_ID := PersistentVars.Ret_Active_Bin_ID;
                Active_Target_Weight := PersistentVars.Ret_Active_Target_Weight;
            END_IF;
            GVL.Auto_Active_Mat := Active_Material_ID;
            GVL.Auto_Active_Bin := Active_Bin_ID;
            GVL.Auto_Active_Target_Weight := Active_Target_Weight;
            actual_bin := load_cell_value - PersistentVars.bin_last_weight;
            IF actual_bin < 0.0 THEN
                actual_bin := 0.0;
            END_IF;
            IF (load_cell_value = 0.0) AND (PersistentVars.Ret_Active_Live_Weight > 0.0) THEN
                Active_Live_Weight := PersistentVars.Ret_Active_Live_Weight;
            ELSE
                Active_Live_Weight := actual_bin;
            END_IF;
            GVL.Auto_Active_Live_Weight := Active_Live_Weight;
            PersistentVars.Ret_Process_Was_Active := TRUE;
            Auto_Current_Batch_Cycle := GVL.Current_Batch_Cycle;
            Auto_Completed_Batch_Cycles := GVL.Completed_Batch_Cycles;
            GVL.All_Cycles_Complete := FALSE;
            Auto_All_Cycles_Complete := FALSE;
            IF (Current_Step = 8) AND (NOT Auto_Has_Active_Bins) THEN
                Sequence_Complete := TRUE;
                GVL.Auto_Sequence_Complete := TRUE;
                Status_Message := 'Auto [POWER-FIX]: Semi-only — Auto complete (no bins)';
            ELSIF Cycle_Manager_State = 5 THEN
                Sequence_Complete := TRUE;
                GVL.Auto_Sequence_Complete := TRUE;
            ELSE
                Sequence_Complete := FALSE;
                GVL.Auto_Sequence_Complete := FALSE;
            END_IF;
            IF E_Stop_Active AND Auto_Mode_DI THEN
                GVL.Run := TRUE;
                Paused_By_Hold := FALSE;
            ELSE
                Paused_By_Hold := TRUE;
            END_IF;
            IF (Current_Step <> 8) OR Auto_Has_Active_Bins THEN
                Status_Message := CONCAT('Auto [POWER-FIX]: Resumed Step ', INT_TO_STRING(Current_Step));
            END_IF;
        ELSE
            Current_Step := 0;
            Cycle_Manager_State := 0;
            Internal_FB_Start := FALSE;
            Sequence_Complete := FALSE;
            GVL.Auto_Sequence_Complete := FALSE;
            GVL.All_Cycles_Complete := FALSE;
            Auto_All_Cycles_Complete := FALSE;
            Active_Material_ID := 0;
            Active_Bin_ID := 0;
            Active_Target_Weight := 0.0;
            Active_Live_Weight := 0.0;
            Status_Message := 'Auto [POWER]: No mid-job retain - Idle. Press Start.';
            PersistentVars.Ret_Process_Was_Active := FALSE;
            PersistentVars.Ret_Current_Step := 0;
            PersistentVars.Ret_Cycle_Manager_State := 0;
            PersistentVars.Ret_Internal_FB_Start := FALSE;
            PersistentVars.Ret_GVL_Run := FALSE;
            PersistentVars.Ret_Active_Live_Weight := 0.0;
            PersistentVars.Ret_Resume_Step := 0;
        END_IF;
    END_IF;
END_IF;

(* 2c. SAFETY NET - false Step7/8/CMS5 only: active bin with Mat+Target>0 still under-dosed *)
(* Do NOT run at Step8/SeqComplete — was re-opening bin3 (AMID/ABID blink) after batch done *)
IF First_Scan_Done AND GVL.Run AND Auto_Has_Active_Bins AND (NOT Sequence_Complete)
    AND (Current_Step <> 8)
    AND ((Cycle_Manager_State = 5) OR (Current_Step >= 7)) THEN
    FOR i := 1 TO 6 DO
        Mat_Idx := Auto_Bin_Material_Mapping[i];
        IF (Mat_Idx < 1) OR (Mat_Idx > 20) THEN
            Mat_Idx := PersistentVars.Ret_Bin_Material_Mapping[i];
        END_IF;
        target_weight := 0.0;
        IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) THEN
            target_weight := GVL.Recipe_Weights[Mat_Idx];
        END_IF;
        IF (target_weight <= 0.0) AND (PersistentVars.Ret_Bin_Target_Weights[i] > 0.0) THEN
            target_weight := PersistentVars.Ret_Bin_Target_Weights[i];
        END_IF;
        IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) AND (target_weight > 0.0) THEN
            IF Actual_Weights[i] < (target_weight - 0.05) THEN
                Current_Step := i;
                Cycle_Manager_State := 1;
                Internal_FB_Start := TRUE;
                Sequence_Complete := FALSE;
                GVL.Auto_Sequence_Complete := FALSE;
                GVL.Semi_Auto_Sequence_Complete := FALSE;
                Waiting_Next_Batch := FALSE;
                Completion_Timer(IN := FALSE);
                PersistentVars.Ret_Resume_Step := i;
                PersistentVars.Ret_Current_Step := i;
                PersistentVars.Ret_Cycle_Manager_State := 1;
                PersistentVars.bin_last_weight := 0.0;
                IF i > 1 THEN
                    FOR j := 1 TO (i - 1) DO
                        PersistentVars.bin_last_weight := PersistentVars.bin_last_weight + Actual_Weights[j];
                    END_FOR;
                END_IF;
                PersistentVars.Ret_bin_last_weight := PersistentVars.bin_last_weight;
                Active_Bin_ID := i;
                Active_Material_ID := Mat_Idx;
                Active_Target_Weight := target_weight;
                GVL.Auto_Active_Mat := Active_Material_ID;
                GVL.Auto_Active_Bin := Active_Bin_ID;
                GVL.Auto_Active_Target_Weight := Active_Target_Weight;
                Paused_By_Hold := FALSE;
                Status_Message := CONCAT('Auto [RESUME-FIX]: Pending Mat Step ', INT_TO_STRING(i));
                EXIT;
            END_IF;
        END_IF;
    END_FOR;
END_IF;


(* 3. PROCESS HOLD - E-Stop open OR Auto_Mode_DI OFF (keep step/cycle; feeds OFF; auto-resume when both OK) *)
IF (Cycle_Manager_State <> 0) OR GVL.Run OR Internal_FB_Start OR (Current_Step <> 0) THEN
    IF NOT E_Stop_Active OR NOT Auto_Mode_DI THEN
        Paused_By_Hold := TRUE;
    END_IF;
END_IF;

IF Paused_By_Hold THEN
    FOR i := 1 TO 6 DO
        Auto_Bin[i] := FALSE;
        auto_bin_cutoff[i] := FALSE;
        auto_bin_motor[i] := FALSE;
    END_FOR;
    (* Keep Active Target/Live visible on HMI while held / after power resume (dosing steps 1..6 only) *)
    IF (Current_Step >= 1) AND (Current_Step <= 6) THEN
        Mat_Idx := Auto_Bin_Material_Mapping[Current_Step];
        IF (Mat_Idx < 1) OR (Mat_Idx > 20) THEN
            Mat_Idx := PersistentVars.Ret_Bin_Material_Mapping[Current_Step];
        END_IF;
        IF Mat_Idx >= 1 AND Mat_Idx <= 20 THEN
            Active_Material_ID := Mat_Idx;
            Active_Bin_ID := Current_Step;
            Active_Target_Weight := GVL.Recipe_Weights[Mat_Idx];
            IF (Active_Target_Weight <= 0.0) AND (PersistentVars.Ret_Bin_Target_Weights[Current_Step] > 0.0) THEN
                Active_Target_Weight := PersistentVars.Ret_Bin_Target_Weights[Current_Step];
            END_IF;
            GVL.Auto_Active_Mat := Mat_Idx;
            GVL.Auto_Active_Bin := Current_Step;
            GVL.Auto_Active_Target_Weight := Active_Target_Weight;
            actual_bin := load_cell_value - PersistentVars.bin_last_weight;
            IF actual_bin < 0.0 THEN
                actual_bin := 0.0;
            END_IF;
            IF (load_cell_value = 0.0) AND (PersistentVars.Ret_Active_Live_Weight > 0.0) AND (actual_bin <= 0.0) THEN
                Active_Live_Weight := PersistentVars.Ret_Active_Live_Weight;
            ELSE
                Active_Live_Weight := actual_bin;
                IF actual_bin > 0.0 THEN
                    PersistentVars.Ret_Active_Live_Weight := actual_bin;
                END_IF;
            END_IF;
            Actual_Weights[Current_Step] := Active_Live_Weight;
            GVL.Auto_Active_Live_Weight := Active_Live_Weight;
        END_IF;
    END_IF;
    IF Inter_Bin_Settling AND (Settle_Hold_Step >= 1) THEN
        actual_bin := load_cell_value - PersistentVars.bin_last_weight;
        IF actual_bin < 0.0 THEN
            actual_bin := 0.0;
        END_IF;
        Actual_Weights[Settle_Hold_Step] := actual_bin;
        Active_Live_Weight := actual_bin;
        GVL.Auto_Active_Live_Weight := actual_bin;
    END_IF;
    IF NOT E_Stop_Active THEN
        Status_Message := CONCAT('Auto [HOLD]: E-Stop at Step ', INT_TO_STRING(Current_Step));
    ELSIF NOT Auto_Mode_DI THEN
        Status_Message := CONCAT('Auto [HOLD]: Auto Mode OFF at Step ', INT_TO_STRING(Current_Step));
    ELSE
        Paused_By_Hold := FALSE;
        Status_Message := CONCAT('Auto [RESUME]: Continuing Step ', INT_TO_STRING(Current_Step));
    END_IF;
    IF Paused_By_Hold THEN
        Sim_Timer(IN := FALSE);
        Transition_Timer(IN := FALSE);
        Completion_Timer(IN := FALSE);
        Inter_Bin_Timer(IN := FALSE);
        Inter_Bin_Settle_Arm := 0;
        GVL.Auto_Current_Step := Current_Step;
        Auto_Sum_Act_Weight := 0.0;
        FOR i := 1 TO 6 DO
            GVL.Auto_Weights[i] := Actual_Weights[i];
            Auto_Sum_Act_Weight := Auto_Sum_Act_Weight + Actual_Weights[i];
            Mat_Idx := Auto_Bin_Material_Mapping[i];
            IF (Mat_Idx < 1) OR (Mat_Idx > 20) THEN
                Mat_Idx := PersistentVars.Ret_Bin_Material_Mapping[i];
            END_IF;
            target_weight := 0.0;
            IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) THEN
                target_weight := GVL.Recipe_Weights[Mat_Idx];
            END_IF;
            IF (target_weight <= 0.0) AND (PersistentVars.Ret_Bin_Target_Weights[i] > 0.0) THEN
                target_weight := PersistentVars.Ret_Bin_Target_Weights[i];
            END_IF;
            Auto_Total_Target_Set[i] := target_weight;
            GVL.Auto_Target_Weights[i] := target_weight;
        END_FOR;
        GVL.Auto_Total_Actual_Weight := Auto_Sum_Act_Weight;
        RETURN;
    END_IF;
END_IF;

(* 3b. LINE FAULT HOLD - Over Dump Avoid (wire Line_Fault from FB_Samyak_Multi.arrLine_Fault[n]) *)
(* While scale comms/line is faulted, freeze sequence and force feed outputs OFF. Auto-resume when fault clears. *)
Tare_Auto_Batch := FALSE;
IF Line_Fault THEN
    Paused_By_LineFault := TRUE;
END_IF;

IF Paused_By_LineFault THEN
    FOR i := 1 TO 6 DO
        Auto_Bin[i] := FALSE;
        auto_bin_cutoff[i] := FALSE;
        auto_bin_motor[i] := FALSE;
    END_FOR;
    Tare_Auto_Batch := FALSE;
    IF Line_Fault THEN
        Error_Code := 5; (* Communication Fault *)
        GVL.Error_Code := 5;
        Status_Message := CONCAT('Auto [HOLD]: Error 5 Communication Fault (Line_Fault) at Step ', INT_TO_STRING(Current_Step));
    ELSE
        Paused_By_LineFault := FALSE;
        IF Error_Code = 5 THEN
            Error_Code := 0;
        END_IF;
        IF GVL.Error_Code = 5 THEN
            GVL.Error_Code := 0;
        END_IF;
        Status_Message := CONCAT('Auto [RESUME]: Communication Fault cleared - continuing Step ', INT_TO_STRING(Current_Step));
    END_IF;
    IF (Current_Step >= 1) AND (Current_Step <= 6) THEN
        actual_bin := load_cell_value - PersistentVars.bin_last_weight;
        IF actual_bin < 0.0 THEN
            actual_bin := 0.0;
        END_IF;
        Actual_Weights[Current_Step] := actual_bin;
        Active_Live_Weight := actual_bin;
        GVL.Auto_Active_Live_Weight := actual_bin;
    END_IF;
    IF Inter_Bin_Settling AND (Settle_Hold_Step >= 1) THEN
        actual_bin := load_cell_value - PersistentVars.bin_last_weight;
        IF actual_bin < 0.0 THEN
            actual_bin := 0.0;
        END_IF;
        Actual_Weights[Settle_Hold_Step] := actual_bin;
        Active_Live_Weight := actual_bin;
        GVL.Auto_Active_Live_Weight := actual_bin;
    END_IF;
    Sim_Timer(IN := FALSE);
    Transition_Timer(IN := FALSE);
    Completion_Timer(IN := FALSE);
    GVL.Auto_Current_Step := Current_Step;
    Auto_Sum_Act_Weight := 0.0;
    FOR i := 1 TO 6 DO
        GVL.Auto_Weights[i] := Actual_Weights[i];
        Auto_Sum_Act_Weight := Auto_Sum_Act_Weight + Actual_Weights[i];
        Mat_Idx := Auto_Bin_Material_Mapping[i];
        IF (Mat_Idx < 1) OR (Mat_Idx > 20) THEN
            Mat_Idx := PersistentVars.Ret_Bin_Material_Mapping[i];
        END_IF;
        target_weight := 0.0;
        IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) THEN
            target_weight := GVL.Recipe_Weights[Mat_Idx];
        END_IF;
        IF (target_weight <= 0.0) AND (PersistentVars.Ret_Bin_Target_Weights[i] > 0.0) THEN
            target_weight := PersistentVars.Ret_Bin_Target_Weights[i];
        END_IF;
        Auto_Total_Target_Set[i] := target_weight;
        GVL.Auto_Target_Weights[i] := target_weight;
    END_FOR;
    GVL.Auto_Total_Actual_Weight := Auto_Sum_Act_Weight;
(* Snapshot: Ret_Resume_Step while dosing; never store CMS5 if pending bins remain *)
(* Auto snapshot: only clear retain when all cycles finished (CMS4). Never clear on Run=FALSE power loss. *)
IF Cycle_Manager_State = 4 THEN
    PersistentVars.Ret_Process_Was_Active := FALSE;
    PersistentVars.Ret_GVL_Run := FALSE;
    PersistentVars.Ret_Cycle_Manager_State := 0;
    PersistentVars.Ret_Current_Step := 0;
    PersistentVars.Ret_Internal_FB_Start := FALSE;
    PersistentVars.Ret_Active_Material_ID := 0;
    PersistentVars.Ret_Active_Bin_ID := 0;
    PersistentVars.Ret_Active_Target_Weight := 0.0;
    PersistentVars.Ret_Active_Live_Weight := 0.0;
    PersistentVars.Ret_Resume_Step := 0;
ELSIF (Internal_FB_Start OR GVL.Run OR (Cycle_Manager_State = 1) OR (Cycle_Manager_State = 5)) AND (Cycle_Manager_State <> 4) THEN
    j := 0;
    FOR i := 1 TO 6 DO
        Mat_Idx := Auto_Bin_Material_Mapping[i];
        IF (Mat_Idx < 1) OR (Mat_Idx > 20) THEN
            Mat_Idx := PersistentVars.Ret_Bin_Material_Mapping[i];
        END_IF;
        target_weight := 0.0;
        IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) THEN
            target_weight := GVL.Recipe_Weights[Mat_Idx];
        END_IF;
        IF (target_weight <= 0.0) AND (PersistentVars.Ret_Bin_Target_Weights[i] > 0.0) THEN
            target_weight := PersistentVars.Ret_Bin_Target_Weights[i];
        END_IF;
        IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) AND (target_weight > 0.0) THEN
            IF Actual_Weights[i] < (target_weight - 0.05) THEN
                j := i;
                EXIT;
            END_IF;
        END_IF;
    END_FOR;
    IF (j > 0) AND ((Cycle_Manager_State = 5) OR (Current_Step >= 7)) THEN
        PersistentVars.Ret_Process_Was_Active := TRUE;
        PersistentVars.Ret_Current_Step := j;
        PersistentVars.Ret_Cycle_Manager_State := 1;
        PersistentVars.Ret_Internal_FB_Start := TRUE;
        PersistentVars.Ret_Resume_Step := j;
    ELSE
        PersistentVars.Ret_Process_Was_Active := TRUE;
        PersistentVars.Ret_Current_Step := Current_Step;
        PersistentVars.Ret_Cycle_Manager_State := Cycle_Manager_State;
        PersistentVars.Ret_Internal_FB_Start := Internal_FB_Start;
        IF (Cycle_Manager_State = 1) AND (Current_Step >= 1) AND (Current_Step <= 6) THEN
            PersistentVars.Ret_Resume_Step := Current_Step;
        ELSIF (Cycle_Manager_State = 5) OR (Cycle_Manager_State = 4) THEN
            PersistentVars.Ret_Resume_Step := 0;
        END_IF;
    END_IF;
    PersistentVars.Ret_bin_last_weight := PersistentVars.bin_last_weight;
    PersistentVars.Ret_GVL_Run := GVL.Run;
    PersistentVars.Ret_Current_Batch_Cycle := GVL.Current_Batch_Cycle;
    PersistentVars.Ret_Completed_Batch_Cycles := GVL.Completed_Batch_Cycles;
    PersistentVars.Ret_Target_Batch_Cycles := GVL.Target_Batch_Cycles;
    PersistentVars.Ret_Active_Material_ID := Active_Material_ID;
    PersistentVars.Ret_Active_Bin_ID := Active_Bin_ID;
    PersistentVars.Ret_Active_Target_Weight := Active_Target_Weight;
    PersistentVars.Ret_Active_Live_Weight := Active_Live_Weight;
    FOR i := 1 TO 6 DO
        PersistentVars.Ret_Actual_Weights[i] := Actual_Weights[i];
        Mat_Idx := Auto_Bin_Material_Mapping[i];
        IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) THEN
            PersistentVars.Ret_Bin_Material_Mapping[i] := Mat_Idx;
            IF GVL.Recipe_Weights[Mat_Idx] > 0.0 THEN
                PersistentVars.Ret_Bin_Target_Weights[i] := GVL.Recipe_Weights[Mat_Idx];
            END_IF;
        END_IF;
    END_FOR;
END_IF;


    RETURN;
END_IF;

(* 4. MASTER CYCLE MANAGER STATE MACHINE *)
CASE Cycle_Manager_State OF
    0: (* IDLE *)
        Internal_FB_Start := FALSE;
        (* Do not clear shared GVL.Run if retain still shows mid-job (power resume / partner Semi) *)
        IF NOT PersistentVars.Ret_Process_Was_Active THEN
            GVL.Run := FALSE;
        END_IF;
        GVL.Next_Cycle_Start := FALSE;
        GVL.Auto_Sequence_Complete := FALSE;
        Current_Step := 0;
        GVL.Auto_Current_Step := 0;
        
        IF (Start_Button OR GVL.Start_Button OR Start_PB) AND NOT Auto_Mode_DI THEN
            Status_Message := 'Auto [State 0]: Cannot Start - Auto Mode DI is OFF';
        ELSIF GVL.Error_Code = 4 AND NOT Start_Cmd THEN
            Status_Message := 'Auto [State 0]: Error 4 - Empty scales (or Reset then Start bypass once)';
        ELSIF GVL.Error_Code = 0 AND NOT Start_Cmd THEN
            Status_Message := 'Auto [State 0 - Idle]: Ready - Waiting for Start (HMI or Start_PB)';
        END_IF;
        
        IF Start_Pulse THEN
            (* Use Target_Batch_Cycles from input, or fallback to GVL, or default to 1 *)
            IF Target_Batch_Cycles > 0 THEN
                GVL.Target_Batch_Cycles := Target_Batch_Cycles;
            ELSIF GVL.Target_Batch_Cycles <= 0 THEN
                GVL.Target_Batch_Cycles := 1;
            END_IF;
            
            IF NOT E_Stop_Active THEN
                GVL.Run := FALSE;
                Status_Message := 'Auto [State 0]: Cannot Start - Emergency Stop Contact Open!';
            ELSIF NOT Scale_Empty_OK THEN
                GVL.Run := FALSE;
                GVL.Error_Code := 4;
                Error_Code := 4;
                Status_Message := CONCAT('Auto [State 0]: Error 4 - Empty BOTH scales < ', CONCAT(REAL_TO_STRING(eff_empty_limit), ' kg before Start'));
            ELSIF (NOT Fresh_After_Reset) AND (
                  (GVL.Auto_Initial_Tolerance > 0.0 AND (GVL.load_cell_auto > GVL.Auto_Initial_Tolerance OR GVL.load_cell_auto < (-GVL.Auto_Initial_Tolerance))) OR 
                  (GVL.Semi_Auto_Initial_Tolerance > 0.0 AND (GVL.load_cell_semi_auto > GVL.Semi_Auto_Initial_Tolerance OR GVL.load_cell_semi_auto < (-GVL.Semi_Auto_Initial_Tolerance)))
                  ) THEN
                GVL.Run := FALSE;
                GVL.Error_Code := 4;
                Error_Code := 4;
                Status_Message := 'Auto [State 0]: Error 4 - Scale drift exceeds Initial Tolerance!';
            ELSE
                GVL.Error_Code := 0;
                Error_Code := 0;
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
                IF Scale_Empty_OK THEN
                    Tare_Pulse_Req := TRUE;
                END_IF;
                GVL.Start_Button := FALSE; (* Consume HMI Start one-shot pulse (%MX2.0) *)
                Fresh_After_Reset := FALSE; (* Error 4 bypass used once *)
            END_IF;
        END_IF;
        
    1: (* RUNNING CYCLE *)
        Internal_FB_Start := TRUE;
        GVL.Run := TRUE;
        
        (* Interlock: While process is actively running, Next_Cycle_Start MUST be FALSE *)
        GVL.Next_Cycle_Start := FALSE;
        
        (* Both Auto and Semi-Auto must complete to finish the cycle *)
        (* Require at least one side had bins to dose — prevents instant-complete fake handshake *)
        IF Sequence_Complete AND GVL.Semi_Auto_Sequence_Complete
            AND (Auto_Has_Active_Bins OR Semi_Has_Active_Bins) THEN
            GVL.Completed_Batch_Cycles := GVL.Current_Batch_Cycle;
            Auto_Completed_Batch_Cycles := GVL.Current_Batch_Cycle;
            IF GVL.Current_Batch_Cycle < GVL.Target_Batch_Cycles AND GVL.Error_Code = 0 THEN
                Internal_FB_Start := FALSE;
                Cycle_Manager_State := 5; (* Go to pause/hold to wait for scale empty & Next_Cycle_Start *)
                Between_Cycle_Hold := TRUE;
            ELSE
                Cycle_Manager_State := 4; (* All target cycles completed *)
                Between_Cycle_Hold := FALSE;
                GVL.Start_Button := FALSE; (* V14: clear HMI Start (%MX2.0) when Target batch done *)
            END_IF;
        ELSIF Sequence_Complete AND GVL.Semi_Auto_Sequence_Complete
            AND (NOT Auto_Has_Active_Bins) AND (NOT Semi_Has_Active_Bins) THEN
            (* Both sides nothing to dose — finish without Completed count / CMS5 *)
            Cycle_Manager_State := 4;
            Between_Cycle_Hold := FALSE;
            GVL.All_Cycles_Complete := TRUE;
            Auto_All_Cycles_Complete := TRUE;
            GVL.Run := FALSE;
            GVL.Start_Button := FALSE;
        END_IF;
        
    5: (* PAUSED BETWEEN CYCLES - Next_Cycle_Start / NextBatchStart *)
        (* Purpose: Target_Batch_Cycles > 1 AND at least one cycle completed (Completed >= 1)
           AND more cycles remain (Completed < Target). Operator empties tank (load_cell LT
           Empty_Weight_Limit), then presses Next_Cycle_Start. Same rule as Semi FB. *)
        Internal_FB_Start := FALSE;
        GVL.Run := TRUE;
        
        (* Tank minimum weight / empty threshold resolved once per scan at top of FB *)
        
        Status_Message := CONCAT('Auto [State 5]: Cycle ', CONCAT(INT_TO_STRING(GVL.Current_Batch_Cycle), ' Done. Empty scale < limit then Next_Cycle_Start.'));
        
        (* Accept ONLY on rising edge of Next_Cycle_Start (pin OR GVL) *)
        IF Next_Cycle_Rising THEN
            IF (GVL.Target_Batch_Cycles > 1) AND (GVL.Completed_Batch_Cycles >= 1) AND (GVL.Completed_Batch_Cycles < GVL.Target_Batch_Cycles) THEN
                IF Scale_Empty_OK THEN
                    (* Do NOT clear GVL.Next_Cycle_Start here - Semi runs later same scan and must see the pulse.
                       State 1 interlock clears it on the next scan. *)
                    (* One-shot Start: do not latch GVL.Start_Button; next cycles use Next_Cycle_Start *)
                    GVL.Error_Code := 0;
                    Error_Code := 0;
                    GVL.Current_Batch_Cycle := GVL.Current_Batch_Cycle + 1;
                    Auto_Current_Batch_Cycle := GVL.Current_Batch_Cycle;
                    Sequence_Complete := FALSE;
                    GVL.Auto_Sequence_Complete := FALSE;
                    GVL.Semi_Auto_Sequence_Complete := FALSE;
                    Current_Step := 0;
                    Internal_FB_Start := TRUE;
                    Cycle_Manager_State := 1;
                    Between_Cycle_Hold := FALSE;
                    IF Scale_Empty_OK THEN
                        Tare_Pulse_Req := TRUE;
                    END_IF;
                    FOR i := 1 TO 6 DO
                        Actual_Weights[i] := 0.0;
                        Auto_Bin[i] := FALSE;
                        auto_bin_cutoff[i] := FALSE;
                        auto_bin_motor[i] := FALSE;
                    END_FOR;
                ELSE
                    (* Scale not empty: reject, clear command so operator can press again after emptying *)
                    GVL.Next_Cycle_Start := FALSE;
                    Next_Cycle_Last := FALSE;
                    Status_Message := CONCAT('Auto [State 5]: Scale >= limit (', CONCAT(REAL_TO_STRING(eff_empty_limit), ' kg)! Empty then Next_Cycle_Start again.'));
                END_IF;
            ELSE
                GVL.Next_Cycle_Start := FALSE;
                Next_Cycle_Last := FALSE;
                Status_Message := 'Auto [State 5]: Next_Cycle_Start ignored (cycle gates not met)';
            END_IF;
        END_IF;
        
    4: (* ALL CYCLES COMPLETE - same as V14: force Start OFF while finished *)
        Internal_FB_Start := FALSE;
        Between_Cycle_Hold := FALSE;
        GVL.Run := FALSE;
        GVL.Start_Button := FALSE; (* HMI %MX2.0 must go FALSE; if Wecon SWITCH keeps writing TRUE, bit looks stuck *)
        Auto_All_Cycles_Complete := TRUE;
        GVL.All_Cycles_Complete := TRUE;
        Sequence_Complete := TRUE;
        GVL.Auto_Sequence_Complete := TRUE;
        GVL.Semi_Auto_Sequence_Complete := TRUE;
        Status_Message := CONCAT('Auto [State 4 - Finished]: All ', CONCAT(INT_TO_STRING(GVL.Target_Batch_Cycles), ' Batch Cycles Completed Successfully'));
        (* New start only on rising edge after Start has gone FALSE (one-shot). Do not level-hold like V14 pin OR. *)
        IF Start_Pulse THEN
            IF Scale_Empty_OK THEN
                (* Reset flags for new batch start — only when scales empty (dump batch first) *)
                Current_Step := 0;
                Auto_All_Cycles_Complete := FALSE;
                GVL.All_Cycles_Complete := FALSE;
                Sequence_Complete := FALSE;
                GVL.Auto_Sequence_Complete := FALSE;
                GVL.Semi_Auto_Sequence_Complete := FALSE;
                Cycle_Manager_State := 0;
            ELSE
                GVL.Error_Code := 4;
                Error_Code := 4;
                Status_Message := CONCAT('Auto [State 4]: Empty BOTH scales < ', CONCAT(REAL_TO_STRING(eff_empty_limit), ' kg before new Start'));
            END_IF;
        END_IF;
END_CASE;

(* Semi-only: all Mat_ID=0 / Target=0 — hold Step 8 + Seq Complete every scan while running *)
IF (NOT Auto_Has_Active_Bins) AND GVL.Run AND ((Cycle_Manager_State = 1) OR (Cycle_Manager_State = 5) OR Between_Cycle_Hold) THEN
    IF (Current_Step >= 1) AND (Current_Step <= 7) THEN
        Current_Step := 8;
        Completion_Timer(IN := FALSE);
    END_IF;
    IF (Current_Step = 8) OR ((Current_Step = 0) AND Internal_FB_Start) THEN
        Active_Material_ID := 0;
        Active_Bin_ID := 0;
        Active_Target_Weight := 0.0;
        Active_Live_Weight := 0.0;
        GVL.Auto_Active_Target_Weight := 0.0;
        GVL.Auto_Active_Live_Weight := 0.0;
        GVL.Auto_Active_Mat := 0;
        GVL.Auto_Active_Bin := 0;
        Sequence_Complete := TRUE;
        GVL.Auto_Sequence_Complete := TRUE;
        IF Current_Step = 0 THEN
            Current_Step := 8;
        END_IF;
        Status_Message := 'Auto [Step 8]: No Auto bins (Mat=0/Target=0) — complete';
    END_IF;
ELSIF (NOT Auto_Has_Active_Bins) AND (Current_Step = 7) THEN
    Current_Step := 8;
    Completion_Timer(IN := FALSE);
END_IF;

(* 5. AUTO SILOS 1..6 POURING SEQUENCE WITH DETAILED STATUS *)
IF Current_Step = 0 AND Internal_FB_Start THEN
    IF NOT Auto_Has_Active_Bins THEN
        (* Semi-only recipe: no Auto targets — instant complete for handshake *)
        Current_Step := 8;
        Active_Material_ID := 0;
        Active_Bin_ID := 0;
        Active_Target_Weight := 0.0;
        Active_Live_Weight := 0.0;
        GVL.Auto_Active_Target_Weight := 0.0;
        GVL.Auto_Active_Live_Weight := 0.0;
        GVL.Auto_Active_Mat := 0;
        GVL.Auto_Active_Bin := 0;
        Sequence_Complete := TRUE;
        GVL.Auto_Sequence_Complete := TRUE;
        Status_Message := 'Auto [Step 8]: No Auto bins — complete (Semi partner)';
    ELSE
        Current_Step := 1;
        PersistentVars.bin_last_weight := load_cell_value;
        Last_Dosing_Step := 1;
        Sequence_Complete := FALSE;
        GVL.Auto_Sequence_Complete := FALSE;
        Excess_Alarm := FALSE;
        Error_Code := 0;
        FOR i := 1 TO 6 DO
            Actual_Weights[i] := 0.0;
            Auto_Bin[i] := FALSE;
            auto_bin_cutoff[i] := FALSE;
            auto_bin_motor[i] := FALSE;
        END_FOR;
    END_IF;
END_IF;

(* All active Auto bins dosed but still on step 1..6 — advance to settle (bins 1..3 recipe) *)
IF GVL.Run AND (NOT Paused_By_Hold) AND (Current_Step >= 1) AND (Current_Step <= 6) AND Auto_Has_Active_Bins THEN
    j := 0;
    FOR i := 1 TO 6 DO
        Mat_Idx := Auto_Bin_Material_Mapping[i];
        IF (Mat_Idx < 1) OR (Mat_Idx > 20) THEN
            Mat_Idx := PersistentVars.Ret_Bin_Material_Mapping[i];
        END_IF;
        target_weight := 0.0;
        IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) THEN
            target_weight := GVL.Recipe_Weights[Mat_Idx];
        END_IF;
        IF (target_weight <= 0.0) AND (PersistentVars.Ret_Bin_Target_Weights[i] > 0.0) THEN
            target_weight := PersistentVars.Ret_Bin_Target_Weights[i];
        END_IF;
        IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) AND (target_weight > 0.0) THEN
            IF Actual_Weights[i] < (target_weight - 0.05) THEN
                j := i;
                EXIT;
            END_IF;
        END_IF;
    END_FOR;
    IF j = 0 THEN
        Current_Step := 7;
        Completion_Timer(IN := FALSE);
        Active_Material_ID := 0;
        Active_Bin_ID := 0;
        Active_Target_Weight := 0.0;
        Active_Live_Weight := 0.0;
        Status_Message := 'Auto: All bins done — Step 7 settle';
    END_IF;
END_IF;

CASE Current_Step OF
    0:
        Active_Material_ID := 0;
        Active_Bin_ID := 0;
        Excess_Alarm := FALSE;
        Sequence_Complete := FALSE;
        FOR i := 1 TO 6 DO
            Auto_Bin[i] := FALSE;
            auto_bin_cutoff[i] := FALSE;
            auto_bin_motor[i] := FALSE;
        END_FOR;
        Active_Target_Weight := GVL.Auto_Active_Target_Weight;
        Active_Live_Weight := 0.0;
        
    1..6:
        (* Skip bin when Mat_ID invalid OR Target<=0 (Mat_ID>0 with Target=0 still skips to next bin) *)
        WHILE Current_Step >= 1 AND Current_Step <= 6 DO
            Mat_Idx := Auto_Bin_Material_Mapping[Current_Step];
            IF (Mat_Idx < 1) OR (Mat_Idx > 20) THEN
                Mat_Idx := PersistentVars.Ret_Bin_Material_Mapping[Current_Step];
            END_IF;
            target_weight := 0.0;
            IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) THEN
                target_weight := GVL.Recipe_Weights[Mat_Idx];
            END_IF;
            IF (target_weight <= 0.0) AND (PersistentVars.Ret_Bin_Target_Weights[Current_Step] > 0.0) THEN
                target_weight := PersistentVars.Ret_Bin_Target_Weights[Current_Step];
            END_IF;
            IF (Mat_Idx < 1) OR (Mat_Idx > 20) OR (target_weight <= 0.0) THEN
                Auto_Bin[Current_Step] := FALSE;
                auto_bin_cutoff[Current_Step] := FALSE;
                auto_bin_motor[Current_Step] := FALSE;
                Actual_Weights[Current_Step] := 0.0;
                IF Current_Step = 6 THEN
                    IF Auto_Has_Active_Bins THEN
                        Current_Step := 7;
                    ELSE
                        Current_Step := 8;
                    END_IF;
                    EXIT;
                ELSE
                    Current_Step := Current_Step + 1;
                END_IF;
            ELSE
                EXIT; (* Valid active recipe silo found *)
            END_IF;
        END_WHILE;
        
        IF Inter_Bin_Settling THEN
            FOR i := 1 TO 6 DO
                Auto_Bin[i] := FALSE;
                auto_bin_cutoff[i] := FALSE;
                auto_bin_motor[i] := FALSE;
            END_FOR;
            IF Settle_Hold_Step >= 1 THEN
                (* InterBinDelay: feeders OFF — hold SAME bin ID/Mat until timer done (TRUE and FALSE) *)
                Active_Material_ID := Settle_Hold_Mat;
                Active_Bin_ID := Settle_Hold_Step;
                Active_Target_Weight := Settle_Hold_Target;
                GVL.Auto_Active_Target_Weight := Settle_Hold_Target;
                GVL.Auto_Active_Mat := Settle_Hold_Mat;
                GVL.Auto_Active_Bin := Settle_Hold_Step;
                actual_bin := load_cell_value - PersistentVars.bin_last_weight;
                IF actual_bin < 0.0 THEN
                    actual_bin := 0.0;
                END_IF;
                Actual_Weights[Settle_Hold_Step] := actual_bin;
                Active_Live_Weight := actual_bin;
                GVL.Auto_Active_Live_Weight := actual_bin;
                max_tol_weight := Settle_Hold_Target + Auto_Bin_Tolerance[Settle_Hold_Step];
                IF (NOT Excess_Allowed) AND (actual_bin > max_tol_weight) THEN
                    Excess_Alarm := TRUE;
                    Inter_Bin_Timer(IN := FALSE);
                    Inter_Bin_Settle_Arm := 0;
                    Status_Message := CONCAT('Auto [Step ', CONCAT(INT_TO_STRING(Settle_Hold_Step), ']: EXCESS tailings during settle — remove before next bin'));
                ELSE
                    Excess_Alarm := FALSE;
                    Status_Message := CONCAT('Auto [Step ', CONCAT(INT_TO_STRING(Settle_Hold_Step), ']: Inter-bin settle before next bin'));
                    IF Inter_Bin_Settle_Arm = 0 THEN
                        Inter_Bin_Timer(IN := FALSE);
                        Inter_Bin_Settle_Arm := 1;
                    ELSE
                        Inter_Bin_Timer(IN := TRUE, PT := Inter_Bin_Delay);
                        IF Inter_Bin_Timer.Q THEN
                            Inter_Bin_Timer(IN := FALSE);
                            Actual_Weights[Settle_Hold_Step] := actual_bin;
                            PersistentVars.bin_last_weight := load_cell_value;
                            Current_Step := Inter_Bin_Next_Step;
                            Last_Dosing_Step := 0;
                            Inter_Bin_Next_Step := 0;
                            Inter_Bin_Settling := FALSE;
                            Inter_Bin_Settle_Arm := 0;
                            Settle_Hold_Step := 0;
                            Settle_Hold_Mat := 0;
                            Settle_Hold_Target := 0.0;
                        END_IF;
                    END_IF;
                END_IF;
            ELSE
                (* Fallback: no hold captured — timer only; do not zero Active_* *)
                Status_Message := CONCAT('Auto [Step ', CONCAT(INT_TO_STRING(Current_Step), ']: Inter-bin settle before next bin'));
                IF Inter_Bin_Settle_Arm = 0 THEN
                    Inter_Bin_Timer(IN := FALSE);
                    Inter_Bin_Settle_Arm := 1;
                ELSE
                    Inter_Bin_Timer(IN := TRUE, PT := Inter_Bin_Delay);
                    IF Inter_Bin_Timer.Q THEN
                        Inter_Bin_Timer(IN := FALSE);
                        Inter_Bin_Settling := FALSE;
                        Inter_Bin_Settle_Arm := 0;
                    END_IF;
                END_IF;
            END_IF;
        ELSIF Current_Step = 7 THEN
            IF Auto_Has_Active_Bins THEN
                Active_Material_ID := 0;
                Active_Bin_ID := 0;
                Active_Target_Weight := 0.0;
                Active_Live_Weight := 0.0;
                GVL.Auto_Active_Target_Weight := 0.0;
                GVL.Auto_Active_Live_Weight := 0.0;
                Status_Message := 'Auto [Step 7]: Settling Delay in progress...';
                Completion_Timer(IN := TRUE, PT := Effective_Delay);
                IF Completion_Timer.Q THEN
                    Completion_Timer(IN := FALSE);
                    Current_Step := 8;
                END_IF;
            ELSE
                Current_Step := 8;
            END_IF;
        ELSIF (Current_Step >= 1) AND (Current_Step <= 6) THEN
            Mat_Idx := Auto_Bin_Material_Mapping[Current_Step];
            IF (Mat_Idx < 1) OR (Mat_Idx > 20) THEN
                Mat_Idx := PersistentVars.Ret_Bin_Material_Mapping[Current_Step];
            END_IF;
            target_weight := 0.0;
            IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) THEN
                target_weight := GVL.Recipe_Weights[Mat_Idx];
            END_IF;
            IF (target_weight <= 0.0) AND (PersistentVars.Ret_Bin_Target_Weights[Current_Step] > 0.0) THEN
                target_weight := PersistentVars.Ret_Bin_Target_Weights[Current_Step];
            END_IF;
            
            (* New bin step: snap gross tare so ATW=new target and ALW starts at 0 *)
            IF Current_Step <> Last_Dosing_Step THEN
                PersistentVars.bin_last_weight := load_cell_value;
                Last_Dosing_Step := Current_Step;
                Actual_Weights[Current_Step] := 0.0;
            END_IF;
            
            Active_Target_Weight := target_weight;
            GVL.Auto_Active_Target_Weight := target_weight;
            
            cutoff_trigger_weight := target_weight - Auto_Coarse_To_Fine_Speed[Current_Step];
            min_tol_weight := target_weight - Auto_Bin_Tolerance[Current_Step];
            max_tol_weight := target_weight + Auto_Bin_Tolerance[Current_Step];
            
            actual_bin := load_cell_value - PersistentVars.bin_last_weight;
            IF actual_bin < 0.0 THEN
                actual_bin := 0.0;
            END_IF;
            Actual_Weights[Current_Step] := actual_bin;
            Active_Live_Weight := actual_bin;
            GVL.Auto_Active_Live_Weight := actual_bin;
            Active_Material_ID := Mat_Idx;
            Active_Bin_ID := Current_Step;
            
            IF load_cell_value > 500.0 THEN
                Error_Code := 21;
                GVL.Error_Code := 21;
                Status_Message := CONCAT('Auto [Step ', CONCAT(INT_TO_STRING(Current_Step), ']: STUCK - Error 21: Scale Overloaded (> 500 kg)!'));
                Sequence_Complete := TRUE;
                GVL.Auto_Sequence_Complete := TRUE;
                Paused_By_Hold := TRUE;
            END_IF;
            
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
                    Status_Message := CONCAT('Auto [Step ', CONCAT(INT_TO_STRING(Current_Step), ']: Excess Allowed - Advancing'));
                    IF Current_Step >= 6 THEN
                        Inter_Bin_Settling := FALSE;
                        Settle_Hold_Step := 0;
                        PersistentVars.bin_last_weight := load_cell_value;
                        Active_Target_Weight := 0.0;
                        Active_Live_Weight := 0.0;
                        GVL.Auto_Active_Target_Weight := 0.0;
                        GVL.Auto_Active_Live_Weight := 0.0;
                        IF Auto_Has_Active_Bins THEN
                            Current_Step := 7;
                        ELSE
                            Current_Step := 8;
                        END_IF;
                    ELSE
                        Settle_Hold_Step := Current_Step;
                        Settle_Hold_Mat := Mat_Idx;
                        Settle_Hold_Target := target_weight;
                        j := Current_Step + 1;
                        WHILE j <= 6 DO
                            Mat_Idx := Auto_Bin_Material_Mapping[j];
                            IF (Mat_Idx < 1) OR (Mat_Idx > 20) THEN
                                Mat_Idx := PersistentVars.Ret_Bin_Material_Mapping[j];
                            END_IF;
                            target_weight := 0.0;
                            IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) THEN
                                target_weight := GVL.Recipe_Weights[Mat_Idx];
                            END_IF;
                            IF (target_weight <= 0.0) AND (PersistentVars.Ret_Bin_Target_Weights[j] > 0.0) THEN
                                target_weight := PersistentVars.Ret_Bin_Target_Weights[j];
                            END_IF;
                            IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) AND (target_weight > 0.0) THEN
                                EXIT;
                            END_IF;
                            j := j + 1;
                        END_WHILE;
                        IF j > 6 THEN
                            Inter_Bin_Settling := FALSE;
                            Settle_Hold_Step := 0;
                            PersistentVars.bin_last_weight := load_cell_value;
                            Active_Target_Weight := 0.0;
                            Active_Live_Weight := 0.0;
                            GVL.Auto_Active_Target_Weight := 0.0;
                            GVL.Auto_Active_Live_Weight := 0.0;
                            IF Auto_Has_Active_Bins THEN
                                Current_Step := 7;
                            ELSE
                                Current_Step := 8;
                            END_IF;
                        ELSIF Inter_Bin_Delay > T#0S THEN
                            Actual_Weights[Settle_Hold_Step] := actual_bin;
                            Inter_Bin_Next_Step := j;
                            Inter_Bin_Settling := TRUE;
                            Inter_Bin_Settle_Arm := 0;
                            Inter_Bin_Timer(IN := FALSE);
                        ELSE
                            PersistentVars.bin_last_weight := load_cell_value;
                            Active_Target_Weight := 0.0;
                            Active_Live_Weight := 0.0;
                            GVL.Auto_Active_Target_Weight := 0.0;
                            GVL.Auto_Active_Live_Weight := 0.0;
                            Current_Step := j;
                            Inter_Bin_Settling := FALSE;
                        END_IF;
                    END_IF;
                ELSE
                    Excess_Alarm := TRUE;
                    Status_Message := CONCAT('Auto [Step ', CONCAT(INT_TO_STRING(Current_Step), ']: STUCK - Excess Weight! Reduce weight or enable Excess Allowed.'));
                END_IF;
            ELSE
                Auto_Bin[Current_Step] := FALSE;
                auto_bin_cutoff[Current_Step] := FALSE;
                auto_bin_motor[Current_Step] := FALSE;
                Excess_Alarm := FALSE;
                Status_Message := CONCAT('Auto [Step ', CONCAT(INT_TO_STRING(Current_Step), ']: Target Reached - Advancing'));
                IF Current_Step >= 6 THEN
                    Inter_Bin_Settling := FALSE;
                    Settle_Hold_Step := 0;
                    PersistentVars.bin_last_weight := load_cell_value;
                    Active_Target_Weight := 0.0;
                    Active_Live_Weight := 0.0;
                    GVL.Auto_Active_Target_Weight := 0.0;
                    GVL.Auto_Active_Live_Weight := 0.0;
                    IF Auto_Has_Active_Bins THEN
                        Current_Step := 7;
                    ELSE
                        Current_Step := 8;
                    END_IF;
                ELSE
                    (* Capture completed bin before j-loop overwrites Mat_Idx/target_weight *)
                    Settle_Hold_Step := Current_Step;
                    Settle_Hold_Mat := Mat_Idx;
                    Settle_Hold_Target := target_weight;
                    j := Current_Step + 1;
                    WHILE j <= 6 DO
                        Mat_Idx := Auto_Bin_Material_Mapping[j];
                        IF (Mat_Idx < 1) OR (Mat_Idx > 20) THEN
                            Mat_Idx := PersistentVars.Ret_Bin_Material_Mapping[j];
                        END_IF;
                        target_weight := 0.0;
                        IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) THEN
                            target_weight := GVL.Recipe_Weights[Mat_Idx];
                        END_IF;
                        IF (target_weight <= 0.0) AND (PersistentVars.Ret_Bin_Target_Weights[j] > 0.0) THEN
                            target_weight := PersistentVars.Ret_Bin_Target_Weights[j];
                        END_IF;
                        IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) AND (target_weight > 0.0) THEN
                            EXIT;
                        END_IF;
                        j := j + 1;
                    END_WHILE;
                    IF j > 6 THEN
                        Inter_Bin_Settling := FALSE;
                        Settle_Hold_Step := 0;
                        PersistentVars.bin_last_weight := load_cell_value;
                        Active_Target_Weight := 0.0;
                        Active_Live_Weight := 0.0;
                        GVL.Auto_Active_Target_Weight := 0.0;
                        GVL.Auto_Active_Live_Weight := 0.0;
                        IF Auto_Has_Active_Bins THEN
                            Current_Step := 7;
                        ELSE
                            Current_Step := 8;
                        END_IF;
                    ELSIF Inter_Bin_Delay > T#0S THEN
                        Actual_Weights[Settle_Hold_Step] := actual_bin;
                        Inter_Bin_Next_Step := j;
                        Inter_Bin_Settling := TRUE;
                        Inter_Bin_Settle_Arm := 0;
                        Inter_Bin_Timer(IN := FALSE);
                    ELSE
                        PersistentVars.bin_last_weight := load_cell_value;
                        Active_Target_Weight := 0.0;
                        Active_Live_Weight := 0.0;
                        GVL.Auto_Active_Target_Weight := 0.0;
                        GVL.Auto_Active_Live_Weight := 0.0;
                        Current_Step := j;
                        Inter_Bin_Settling := FALSE;
                    END_IF;
                END_IF;
            END_IF;
        END_IF;

    7:
        IF Auto_Has_Active_Bins THEN
            Active_Material_ID := 0;
            Active_Bin_ID := 0;
            Excess_Alarm := FALSE;
            Status_Message := 'Auto [Step 7]: Settling Delay in progress...';
            Completion_Timer(IN := TRUE, PT := Effective_Delay);
            IF Completion_Timer.Q THEN
                Completion_Timer(IN := FALSE);
                Current_Step := 8;
            END_IF;
        ELSE
            Current_Step := 8;
        END_IF;
        
    8:
        Active_Material_ID := 0;
        Active_Bin_ID := 0;
        Excess_Alarm := FALSE;
        Sequence_Complete := TRUE;
        GVL.Auto_Sequence_Complete := TRUE;
        IF NOT GVL.Semi_Auto_Sequence_Complete THEN
            Status_Message := 'Auto [Step 8]: Auto Finished. Waiting for Semi-Auto to complete...';
        ELSE
            Status_Message := 'Auto [Step 8]: Cycle Sequences Complete';
        END_IF;
END_CASE;

(* Synchronize physical output arrays to GVL *)
FOR i := 1 TO 6 DO
    GVL.Auto_Bin[i] := Auto_Bin[i];
    GVL.auto_bin_cutoff[i] := auto_bin_cutoff[i];
    GVL.auto_bin_motor[i] := auto_bin_motor[i];
END_FOR;

(* Synchronize live cycle progress to outputs *)
Auto_Current_Batch_Cycle := GVL.Current_Batch_Cycle;
Auto_Completed_Batch_Cycles := GVL.Completed_Batch_Cycles;
Auto_All_Cycles_Complete := GVL.All_Cycles_Complete;

(* When cycle handshake done, show Step8 not last dosing step on HMI *)
IF Sequence_Complete AND (Current_Step >= 1) AND (Current_Step <= 6) THEN
    Current_Step := 8;
END_IF;
GVL.Auto_Current_Step := Current_Step;
(* HMI Active Mat/Bin: only while dosing steps 1..6 (clear at Step7/8/CMS4/CMS5 — stops AMID blink) *)
(* During inter-bin settle keep Settle_Hold_* for TRUE and FALSE — do not overwrite with next bin *)
IF Inter_Bin_Settling AND (Settle_Hold_Step >= 1) THEN
    Active_Material_ID := Settle_Hold_Mat;
    Active_Bin_ID := Settle_Hold_Step;
    Active_Target_Weight := Settle_Hold_Target;
    actual_bin := load_cell_value - PersistentVars.bin_last_weight;
    IF actual_bin < 0.0 THEN
        actual_bin := 0.0;
    END_IF;
    Actual_Weights[Settle_Hold_Step] := actual_bin;
    Active_Live_Weight := actual_bin;
    GVL.Auto_Current_Step := Settle_Hold_Step;
ELSIF (Current_Step >= 1) AND (Current_Step <= 6) AND (NOT Inter_Bin_Settling) THEN
    Mat_Idx := Auto_Bin_Material_Mapping[Current_Step];
    IF (Mat_Idx < 1) OR (Mat_Idx > 20) THEN
        Mat_Idx := PersistentVars.Ret_Bin_Material_Mapping[Current_Step];
    END_IF;
    target_weight := 0.0;
    IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) THEN
        target_weight := GVL.Recipe_Weights[Mat_Idx];
    END_IF;
    IF (target_weight <= 0.0) AND (PersistentVars.Ret_Bin_Target_Weights[Current_Step] > 0.0) THEN
        target_weight := PersistentVars.Ret_Bin_Target_Weights[Current_Step];
    END_IF;
    IF (Mat_Idx < 1) OR (Mat_Idx > 20) OR (target_weight <= 0.0) THEN
        Active_Material_ID := 0;
        Active_Bin_ID := 0;
        Active_Target_Weight := 0.0;
        Active_Live_Weight := 0.0;
    ELSE
        (* Dosing: keep Actual_Weights in sync with live scale (excess / tailings) *)
        actual_bin := load_cell_value - PersistentVars.bin_last_weight;
        IF actual_bin < 0.0 THEN
            actual_bin := 0.0;
        END_IF;
        Actual_Weights[Current_Step] := actual_bin;
        Active_Live_Weight := actual_bin;
    END_IF;
ELSE
    Active_Material_ID := 0;
    Active_Bin_ID := 0;
    Active_Target_Weight := 0.0;
    Active_Live_Weight := 0.0;
END_IF;
GVL.Auto_Active_Mat := Active_Material_ID;
GVL.Auto_Active_Bin := Active_Bin_ID;
GVL.Auto_Active_Target_Weight := Active_Target_Weight;
GVL.Auto_Active_Live_Weight := Active_Live_Weight;
(* Mirror Actual_Weights to HMI every scan — dosing, excess, inter-bin tailings *)
Auto_Sum_Act_Weight := 0.0;
FOR i := 1 TO 6 DO
    GVL.Auto_Weights[i] := Actual_Weights[i];
    Auto_Sum_Act_Weight := Auto_Sum_Act_Weight + Actual_Weights[i];
END_FOR;
GVL.Auto_Total_Actual_Weight := Auto_Sum_Act_Weight;
(* Per-bin target setpoints — bin index 1..6; mirror to GVL.Auto_Target_Weights (plant %MD400) *)
IF (Cycle_Manager_State = 0) AND (NOT GVL.Run) AND (NOT Internal_FB_Start) AND (NOT PersistentVars.Ret_Process_Was_Active) THEN
    FOR i := 1 TO 6 DO
        Auto_Total_Target_Set[i] := 0.0;
        GVL.Auto_Target_Weights[i] := 0.0;
    END_FOR;
ELSE
    FOR i := 1 TO 6 DO
        Mat_Idx := Auto_Bin_Material_Mapping[i];
        IF (Mat_Idx < 1) OR (Mat_Idx > 20) THEN
            Mat_Idx := PersistentVars.Ret_Bin_Material_Mapping[i];
        END_IF;
        target_weight := 0.0;
        IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) THEN
            target_weight := GVL.Recipe_Weights[Mat_Idx];
        END_IF;
        IF (target_weight <= 0.0) AND (PersistentVars.Ret_Bin_Target_Weights[i] > 0.0) THEN
            target_weight := PersistentVars.Ret_Bin_Target_Weights[i];
        END_IF;
        Auto_Total_Target_Set[i] := target_weight;
        GVL.Auto_Target_Weights[i] := target_weight;
    END_FOR;
END_IF;
(* Snapshot: Ret_Resume_Step while dosing; never store CMS5 if pending bins remain *)
(* Auto snapshot: only clear retain when all cycles finished (CMS4). Never clear on Run=FALSE power loss. *)
IF Cycle_Manager_State = 4 THEN
    PersistentVars.Ret_Process_Was_Active := FALSE;
    PersistentVars.Ret_GVL_Run := FALSE;
    PersistentVars.Ret_Cycle_Manager_State := 0;
    PersistentVars.Ret_Current_Step := 0;
    PersistentVars.Ret_Internal_FB_Start := FALSE;
    PersistentVars.Ret_Active_Material_ID := 0;
    PersistentVars.Ret_Active_Bin_ID := 0;
    PersistentVars.Ret_Active_Target_Weight := 0.0;
    PersistentVars.Ret_Active_Live_Weight := 0.0;
    PersistentVars.Ret_Resume_Step := 0;
ELSIF (Internal_FB_Start OR GVL.Run OR (Cycle_Manager_State = 1) OR (Cycle_Manager_State = 5)) AND (Cycle_Manager_State <> 4) THEN
    j := 0;
    FOR i := 1 TO 6 DO
        Mat_Idx := Auto_Bin_Material_Mapping[i];
        IF (Mat_Idx < 1) OR (Mat_Idx > 20) THEN
            Mat_Idx := PersistentVars.Ret_Bin_Material_Mapping[i];
        END_IF;
        target_weight := 0.0;
        IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) THEN
            target_weight := GVL.Recipe_Weights[Mat_Idx];
        END_IF;
        IF (target_weight <= 0.0) AND (PersistentVars.Ret_Bin_Target_Weights[i] > 0.0) THEN
            target_weight := PersistentVars.Ret_Bin_Target_Weights[i];
        END_IF;
        IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) AND (target_weight > 0.0) THEN
            IF Actual_Weights[i] < (target_weight - 0.05) THEN
                j := i;
                EXIT;
            END_IF;
        END_IF;
    END_FOR;
    IF (j > 0) AND ((Cycle_Manager_State = 5) OR (Current_Step >= 7)) THEN
        PersistentVars.Ret_Process_Was_Active := TRUE;
        PersistentVars.Ret_Current_Step := j;
        PersistentVars.Ret_Cycle_Manager_State := 1;
        PersistentVars.Ret_Internal_FB_Start := TRUE;
        PersistentVars.Ret_Resume_Step := j;
    ELSE
        PersistentVars.Ret_Process_Was_Active := TRUE;
        PersistentVars.Ret_Current_Step := Current_Step;
        PersistentVars.Ret_Cycle_Manager_State := Cycle_Manager_State;
        PersistentVars.Ret_Internal_FB_Start := Internal_FB_Start;
        IF (Cycle_Manager_State = 1) AND (Current_Step >= 1) AND (Current_Step <= 6) THEN
            PersistentVars.Ret_Resume_Step := Current_Step;
        ELSIF (Cycle_Manager_State = 5) OR (Cycle_Manager_State = 4) THEN
            PersistentVars.Ret_Resume_Step := 0;
        END_IF;
    END_IF;
    PersistentVars.Ret_bin_last_weight := PersistentVars.bin_last_weight;
    PersistentVars.Ret_GVL_Run := GVL.Run;
    PersistentVars.Ret_Current_Batch_Cycle := GVL.Current_Batch_Cycle;
    PersistentVars.Ret_Completed_Batch_Cycles := GVL.Completed_Batch_Cycles;
    PersistentVars.Ret_Target_Batch_Cycles := GVL.Target_Batch_Cycles;
    PersistentVars.Ret_Active_Material_ID := Active_Material_ID;
    PersistentVars.Ret_Active_Bin_ID := Active_Bin_ID;
    PersistentVars.Ret_Active_Target_Weight := Active_Target_Weight;
    PersistentVars.Ret_Active_Live_Weight := Active_Live_Weight;
    FOR i := 1 TO 6 DO
        PersistentVars.Ret_Actual_Weights[i] := Actual_Weights[i];
        Mat_Idx := Auto_Bin_Material_Mapping[i];
        IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) THEN
            PersistentVars.Ret_Bin_Material_Mapping[i] := Mat_Idx;
            IF GVL.Recipe_Weights[Mat_Idx] > 0.0 THEN
                PersistentVars.Ret_Bin_Target_Weights[i] := GVL.Recipe_Weights[Mat_Idx];
            END_IF;
        END_IF;
    END_FOR;
END_IF;


(* Drop any tare request if scales not empty (batch still on scale after cycle complete) *)
IF NOT Scale_Empty_OK THEN
    Tare_Pulse_Req := FALSE;
END_IF;

(* TARE PULSE — end of scan (after Start / Next_Cycle set Tare_Pulse_Req); BOTH scales LT limit *)
IF Tare_Pulse_Req THEN
    IF Scale_Empty_OK THEN
        Tare_Auto_Batch := TRUE;
        Status_Message := 'Auto [Tare]: Scales empty - Tare_Auto_Batch pulse';
    ELSE
        Tare_Auto_Batch := FALSE;
        Status_Message := CONCAT('Auto [Tare blocked]: Scale >= ', CONCAT(REAL_TO_STRING(eff_empty_limit), ' kg — dump batch first'));
    END_IF;
    Tare_Pulse_Req := FALSE;
END_IF;

(* Hard interlock: never Tare when live load >= Empty_Weight_Limit (either scale) *)
IF NOT Scale_Empty_OK THEN
    Tare_Auto_Batch := FALSE;
END_IF;

(* Waiting_Next_Batch: end-of-scan (after all RETURN paths) — HMI lamp / hide between cycles *)
Waiting_Next_Batch := ((Cycle_Manager_State = 5) OR Between_Cycle_Hold)
    AND (GVL.Target_Batch_Cycles > 1)
    AND (GVL.Current_Batch_Cycle < GVL.Target_Batch_Cycles);
GVL.Waiting_Next_batch_HMI_HIDE := Waiting_Next_Batch;

