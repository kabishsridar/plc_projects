FUNCTION_BLOCK Semi_Auto_Batching_V15
VAR_INPUT
    Start_Button : BOOL;                                 // Optional start pin (legacy). Also ORed with GVL.Start_Button (%MX2.0 HMI) and Start_PB
    Start_PB : BOOL;                                     // Physical Start pushbutton DI (one-shot pulse)
    Auto_Mode_DI : BOOL;                                 // Auto Mode DI: TRUE = start/resume allowed; FALSE = HMI/PB start ignored
    E_Stop_Active : BOOL;                                // Emergency Stop circuit status (NC contact: TRUE = Healthy/Run permitted, FALSE = E-Stop tripped)
    Reset : BOOL;                                        // System reset pulse (clears active steps, outputs, alarms, and error flags)
    Semi_Auto_Bin_Material_Mapping : ARRAY[1..10] OF INT;// Array mapping physical Silos 1..10 to Recipe Material IDs (1..20, 0 = Silo skipped)
    Semi_Auto_Coarse_To_Fine_Speed : ARRAY[1..10] OF REAL;// Weight offset threshold (kg) before target to transition from Coarse to Fine feeding
    Semi_Auto_Bin_Tolerance : ARRAY[1..10] OF REAL;      // Allowable weight tolerance window (±kg) around target weight for each silo
    Inter_Bin_Delay : TIME;                              // Pause after Bin*=FALSE: tailings fall on SAME bin ID; then next mat (Semi e.g. T#2S)
    Excess_Allowed : BOOL;                               // Overfill handling policy: TRUE = proceed if target is exceeded, FALSE = raise alarm and halt
    load_cell_value : REAL;                              // Live gross weight input reading from the Semi-Auto scale load cell (kg)
    Target_Batch_Cycles : INT;                           // Target number of batch cycle repetitions configured from HMI (defaults to 1)
    Next_Cycle_Start : BOOL;                             // NextBatchStart: after a completed cycle (Target>1), press when this FB scale < Empty_Weight_Limit
    Empty_Weight_Limit : REAL;                           // Both scales must be LT this (kg) before dosing, Next_Cycle_Start, or Tare pulse
    Line_Fault : BOOL;                                   // Wire from FB_Samyak_Multi.arrLine_Fault[n] (Semi scale). TRUE = hold process (Over Dump Avoid)
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
    Error_Code : INT;                                    // Fault diagnostic code:
                                                         //   0   = No Error / System Healthy
                                                         //   1   = Duplicate Material ID mapped across Auto and Semi-Auto
                                                         //   2   = Material index out of range (must be 1..20)
                                                         //   3   = Recipe weight is less than (Coarse_To_Fine_Speed + Tolerance)
                                                         //   4   = Initial scale tare error (scale not empty before start)
                                                         //   5   = Communication Fault (Line_Fault from FB_Samyak_Multi; scale Modbus/line fault; Over Dump Avoid HOLD)
                                                         //   21  = Scale overload protection triggered (> 500 kg)
    Semi_Auto_Current_Batch_Cycle : INT;                 // Active batch cycle number currently processing (1..Target_Batch_Cycles)
    Semi_Auto_Completed_Batch_Cycles : INT;              // Total number of batch cycle loops completed successfully
    Semi_Auto_All_Cycles_Complete : BOOL;                // Master flag: TRUE when all Target_Batch_Cycles have finished
    Status_Message : STRING(80);                         // Real-time human-readable process status and diagnostic text message
    Tare_Semi_Auto_Batch : BOOL;                         // One-scan pulse to Samyak ONLY when BOTH scales LT Empty_Weight_Limit (never after batch with product on scale)
    Waiting_Next_Batch : BOOL;                           // TRUE in state 5 while Current < Target (HMI hide/lamp); FALSE when next cycle runs; never TRUE on last cycle
END_VAR
VAR
    bin_last_weight : REAL;
    actual_bin : REAL;
    target_weight : REAL;
    cutoff_trigger_weight : REAL;
    complete_weight : REAL;                             // Target + Tolerance: accept band [Target .. complete_weight]; excess if above
    min_tol_weight : REAL;
    max_tol_weight : REAL;
    Paused_By_Hold : BOOL;
    Effective_Delay : TIME;                              // Final settle Step 31 (Inter_Bin_Delay pin -> T#2S default if pin=0)
    Inter_Bin_Settling : BOOL;                           // TRUE: waiting Inter_Bin_Delay before feeding next bin
    Inter_Bin_Settle_Arm : INT;                          // 0=arm Inter_Bin_Timer, 1=counting
    Inter_Bin_Timer : TON;
    Settle_Hold_Step : INT;                              // Completed bin step held on HMI during inter-bin settle (Excess_Allowed=FALSE)
    Settle_Hold_Mat : INT;                               // Material ID of completed bin during settle hold
    Settle_Hold_Target : REAL;                           // Target kg of completed bin during settle hold
    Inter_Bin_Next_Step : INT;                           // Next active bin step — applied only when inter-bin timer completes
    Mat_Idx : INT;
    i : INT;
    j : INT;
    Last_Batch_Cycle : INT;
    Transition_Timer : TON;
    Completion_Timer : TON;
    Simulation_Mode : BOOL;
    Sim_Rate : REAL;
    Sim_Timer : TON;
    Start_Sim_Weight : REAL;
    Discharge_Active : BOOL;
    Run_Last : BOOL;
    Run_Rising : BOOL;
    Next_Cycle_Last : BOOL;                              // Edge memory for Next_Cycle_Start (same as Auto FB)
    Next_Cycle_Rising : BOOL;                            // Rising edge of Next_Cycle_Start OR GVL.Next_Cycle_Start
    Between_Cycle_Hold : BOOL;                           // TRUE while waiting for empty scale + Next_Cycle_Start (state 5)
    Paused_By_LineFault : BOOL;                          // Latched while Line_Fault is TRUE (outputs forced OFF)
    Tare_Pulse_Req : BOOL;                               // Internal request to emit Tare_Semi_Auto_Batch for one scan
    eff_empty_limit : REAL;
    Start_Cmd : BOOL;                                    // (Start_Button OR GVL.Start_Button OR Start_PB) AND Auto_Mode_DI
    Start_Cmd_Last : BOOL;                               // Edge memory for Start_Cmd
    Start_Pulse : BOOL;                                  // Rising edge of Start_Cmd (fresh start only; HOLD auto-resumes)
    Reset_Last : BOOL;
    Reset_Pulse : BOOL;
    First_Scan_Done : BOOL;                              // FALSE after PLC power-up (non-retain)
    Last_Step : INT;                                     // Previous scan step (detect Step 31 entry)
    Last_Dosing_Step : INT;                              // Last dosing step 1..10 (snap bin_last on new bin → ALW=0)
    Settle_Phase : INT;                                  // 0=arm settle timer, 1=count Inter_Bin_Delay
    Scale_Empty_OK : BOOL;                               // TRUE when this FB load AND partner Auto scale are LT Empty_Weight_Limit
    Pending_Resume_Job : BOOL;                           // TRUE when Ret_Semi weights show unfinished bins after power
    Semi_Has_Active_Bins : BOOL;                         // TRUE when any Semi bin 1..10 has target weight > 0
    Auto_Has_Active_Bins : BOOL;                         // Partner Auto: any bin 1..6 with target > 0 (from GVL mapping)
END_VAR



(* Uses Application.PersistentVars Ret_Semi_* (PERSISTENT RETAIN) - no FB VAR RETAIN *)
(* Semi-Auto Batching FB V15: Start pulse gated by Auto_Mode_DI (same as Auto); process follows GVL.Run *)

(* Inter_Bin_Delay: VAR_INPUT from batching14 only (no GVL) — between bins; Step 31 uses Effective_Delay *)
(* Sync working bin_last from persistent retain *)
bin_last_weight := PersistentVars.Ret_Semi_bin_last_weight;
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
(* Tare + Next_Cycle_Start only when BOTH Semi and Auto live weights are below limit *)
(* Both FB pin AND GVL mirror per scale — avoids stale zero input passing when tank still has batch *)
Scale_Empty_OK := (load_cell_value < eff_empty_limit) AND (GVL.load_cell_semi_auto < eff_empty_limit)
    AND (GVL.load_cell_auto < eff_empty_limit);

(* RESET first (batching14: Auto_Ctrl then Semi_Auto_Ctrl — Auto must NOT clear GVL.Reset before Semi) *)
Reset_Pulse := (Reset OR GVL.Reset) AND NOT Reset_Last;
Reset_Last := (Reset OR GVL.Reset);
IF (Reset OR GVL.Reset) THEN
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
    GVL.Semi_Auto_Excess_Alarm := FALSE;
    Excess_Alarm := FALSE;
    Error_Code := 0;
    Paused_By_Hold := FALSE;
    Paused_By_LineFault := FALSE;
    Current_Step := 0;
    Last_Batch_Cycle := 0;
    Cycle_Manager_State := 0;
    Semi_Auto_Current_Batch_Cycle := 0;
    Semi_Auto_Completed_Batch_Cycles := 0;
    Semi_Auto_All_Cycles_Complete := FALSE;
    bin_last_weight := 0.0;
    Between_Cycle_Hold := FALSE;
    Waiting_Next_Batch := FALSE;
    Tare_Pulse_Req := FALSE;
    Tare_Semi_Auto_Batch := FALSE;
    GVL.Semi_Auto_Current_Step := 0;
    GVL.Run := FALSE;
    GVL.Start_Button := FALSE;
    GVL.Next_Cycle_Start := FALSE;
    GVL.Current_Batch_Cycle := 0;
    GVL.Completed_Batch_Cycles := 0;
    GVL.All_Cycles_Complete := FALSE;
    PersistentVars.Ret_Semi_Process_Was_Active := FALSE;
    PersistentVars.Ret_Semi_GVL_Run := FALSE;
    PersistentVars.Ret_Semi_Current_Step := 0;
    PersistentVars.Ret_Semi_Cycle_Manager_State := 0;
    PersistentVars.Ret_Semi_Between_Cycle_Hold := FALSE;
    PersistentVars.Ret_Semi_Resume_Step := 0;
    PersistentVars.Ret_Semi_Active_Material_ID := 0;
    PersistentVars.Ret_Semi_Active_Bin_ID := 0;
    PersistentVars.Ret_Semi_Active_Target_Weight := 0.0;
    PersistentVars.Ret_Semi_Active_Live_Weight := 0.0;
    PersistentVars.Ret_Semi_bin_last_weight := 0.0;
    PersistentVars.Ret_Semi_Current_Batch_Cycle := 0;
    PersistentVars.Ret_Semi_Completed_Batch_Cycles := 0;
    FOR i := 1 TO 10 DO
        PersistentVars.Ret_Semi_Actual_Weights[i] := 0.0;
        PersistentVars.Ret_Semi_Bin_Target_Weights[i] := 0.0;
        (* Ret_Semi_Bin_Material_Mapping kept — GVL %MW60 restored from retain after power/Reset *)
    END_FOR;
    IF Reset_Pulse THEN
        Start_Sim_Weight := 0.0;
        Run_Last := FALSE;
        Run_Rising := FALSE;
        Next_Cycle_Last := FALSE;
        Next_Cycle_Rising := FALSE;
        Start_Cmd := FALSE;
        Start_Cmd_Last := FALSE;
        Start_Pulse := FALSE;
        First_Scan_Done := TRUE;
        Last_Step := -1;
        Last_Dosing_Step := 0;
        Settle_Phase := 0;
        Transition_Timer(IN := FALSE);
        Completion_Timer(IN := FALSE);
        Inter_Bin_Timer(IN := FALSE);
        Inter_Bin_Settling := FALSE;
        Inter_Bin_Settle_Arm := 0;
        Settle_Hold_Step := 0;
        Settle_Hold_Mat := 0;
        Settle_Hold_Target := 0.0;
        Inter_Bin_Next_Step := 0;
        Sim_Timer(IN := FALSE);
        Status_Message := 'Semi-Auto [Reset]: Fresh cycle ready (recipe kept).';
    ELSE
        Status_Message := 'Semi-Auto [Reset]: Held — Step/CMS idle.';
    END_IF;
    GVL.Reset := FALSE;
    RETURN;
END_IF;

(* Process Start/Resume pulse: HMI %MX2.0 OR Start_PB OR pin, only if Auto_Mode_DI *)
Start_Cmd := (Start_Button OR GVL.Start_Button OR Start_PB) AND Auto_Mode_DI;
Start_Pulse := Start_Cmd AND NOT Start_Cmd_Last;
Start_Cmd_Last := Start_Cmd;

(* Detect rising edge on Next_Cycle_Start trigger — same as Auto FB *)
Next_Cycle_Rising := (Next_Cycle_Start OR GVL.Next_Cycle_Start) AND NOT Next_Cycle_Last;
Next_Cycle_Last := (Next_Cycle_Start OR GVL.Next_Cycle_Start);

(* Active-bin flags BEFORE CMS handshake — Mat_ID>0 AND Target>0 required per bin *)
Semi_Has_Active_Bins := FALSE;
FOR i := 1 TO 10 DO
    Mat_Idx := Semi_Auto_Bin_Material_Mapping[i];
    IF (Mat_Idx < 1) OR (Mat_Idx > 20) THEN
        IF PersistentVars.Ret_Semi_Bin_Target_Weights[i] > 0.0 THEN
            Mat_Idx := PersistentVars.Ret_Semi_Bin_Material_Mapping[i];
        ELSE
            Mat_Idx := 0;
        END_IF;
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
Auto_Has_Active_Bins := FALSE;
FOR i := 1 TO 6 DO
    Mat_Idx := GVL.Auto_Bin_Material_Mapping[i];
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
        Auto_Has_Active_Bins := TRUE;
        EXIT;
    ELSIF (PersistentVars.Ret_Bin_Target_Weights[i] > 0.0) AND (target_weight > 0.0) THEN
        Auto_Has_Active_Bins := TRUE;
        EXIT;
    END_IF;
END_FOR;

(* Track Master Cycle State *)
IF Target_Batch_Cycles > 0 THEN
    GVL.Target_Batch_Cycles := Target_Batch_Cycles;
END_IF;

(* Master Cycle State & Start Synchronization *)
Run_Rising := GVL.Run AND NOT Run_Last;
Run_Last := GVL.Run;

IF GVL.Run THEN
    IF Sequence_Complete AND GVL.Auto_Sequence_Complete THEN
        IF Auto_Has_Active_Bins OR Semi_Has_Active_Bins THEN
            IF GVL.Current_Batch_Cycle >= GVL.Target_Batch_Cycles AND GVL.Target_Batch_Cycles > 0 THEN
                Cycle_Manager_State := 4;
                Between_Cycle_Hold := FALSE;
            ELSE
                (* More cycles remain — enter / stay in between-cycle hold (state 5) *)
                Cycle_Manager_State := 5;
                Between_Cycle_Hold := TRUE;
            END_IF;
        ELSIF (NOT Auto_Has_Active_Bins) AND (NOT Semi_Has_Active_Bins) THEN
            (* Both sides Mat=0/Target=0: instant SeqComplete must NOT fake a batch cycle *)
            Cycle_Manager_State := 4;
            Between_Cycle_Hold := FALSE;
            GVL.All_Cycles_Complete := TRUE;
        END_IF;
    ELSIF Between_Cycle_Hold THEN
        (* Stay in state 5 until Next_Cycle_Start accepted (empty scale + rising edge) *)
        Cycle_Manager_State := 5;
    ELSE
        Cycle_Manager_State := 1;
    END_IF;
ELSE
    (* Do not zero step on first scan after power — power-restore runs below *)
    (* Keep mid-job when GVL.Run drops (power loss). Keep FINISHED (CMS4) like Auto: do not
       clear Sequence_Complete / step when all cycles done — Auto CASE 4 sets Run=FALSE. *)
    IF GVL.All_Cycles_Complete OR ((Cycle_Manager_State = 4) AND GVL.Auto_Sequence_Complete) THEN
        Cycle_Manager_State := 4;
        Between_Cycle_Hold := FALSE;
        Sequence_Complete := TRUE;
        GVL.Semi_Auto_Sequence_Complete := TRUE;
        Semi_Auto_All_Cycles_Complete := TRUE;
        IF (Current_Step < 32) OR (Current_Step = 0) THEN
            Current_Step := 32;
        END_IF;
    ELSIF First_Scan_Done AND (NOT PersistentVars.Ret_Semi_Process_Was_Active) THEN
        Cycle_Manager_State := 0;
        Current_Step := 0;
        Last_Batch_Cycle := 0;
        Sequence_Complete := FALSE;
        GVL.Semi_Auto_Sequence_Complete := FALSE;
        Between_Cycle_Hold := FALSE;
    END_IF;
END_IF;

(* On fresh batch start (rising edge of Run), ensure clean start from Step 0 *)
(* Skip reset when retain shows mid-job resume — Run may re-assert after power loss *)
IF Run_Rising AND (NOT PersistentVars.Ret_Semi_Process_Was_Active) THEN
    Current_Step := 0;
    Last_Batch_Cycle := 0;
    Sequence_Complete := FALSE;
    GVL.Semi_Auto_Sequence_Complete := FALSE;
    Tare_Pulse_Req := FALSE;
    (* Fresh recipe start: drop retain on bins not in live mapping (prevents Mat9/Bin3 ghost) *)
    FOR i := 1 TO 10 DO
        Mat_Idx := Semi_Auto_Bin_Material_Mapping[i];
        target_weight := 0.0;
        IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) THEN
            target_weight := GVL.Recipe_Weights[Mat_Idx];
        END_IF;
        IF (Mat_Idx < 1) OR (Mat_Idx > 20) OR (target_weight <= 0.0) THEN
            PersistentVars.Ret_Semi_Bin_Target_Weights[i] := 0.0;
            PersistentVars.Ret_Semi_Actual_Weights[i] := 0.0;
            PersistentVars.Ret_Semi_Bin_Material_Mapping[i] := 0;
        ELSE
            PersistentVars.Ret_Semi_Bin_Material_Mapping[i] := Mat_Idx;
            PersistentVars.Ret_Semi_Bin_Target_Weights[i] := target_weight;
        END_IF;
    END_FOR;
    PersistentVars.Ret_Semi_Active_Material_ID := 0;
    PersistentVars.Ret_Semi_Active_Bin_ID := 0;
    PersistentVars.Ret_Semi_Resume_Step := 0;
    PersistentVars.Ret_Semi_Current_Step := 0;
    Active_Material_ID := 0;
    Active_Bin_ID := 0;
    (* Tare only on fresh Run rising edge when scales empty — not after batch complete with product on scale *)
    IF Scale_Empty_OK AND (NOT Sequence_Complete) AND (Current_Step = 0) THEN
        Tare_Pulse_Req := TRUE;
    END_IF;
END_IF;

(* 1. SEMI-AUTO RECIPE TOTALS & ACTIVE SILO COUNT *)
GVL.Semi_Auto_Total_Target_Weight := 0.0;
GVL.Semi_Auto_Material_Count := 0;
FOR i := 1 TO 10 DO
    IF Semi_Auto_Bin_Material_Mapping[i] > 0 AND Semi_Auto_Bin_Material_Mapping[i] <= 20 THEN
        IF GVL.Recipe_Weights[Semi_Auto_Bin_Material_Mapping[i]] > 0.0 THEN
            GVL.Semi_Auto_Total_Target_Weight := GVL.Semi_Auto_Total_Target_Weight + GVL.Recipe_Weights[Semi_Auto_Bin_Material_Mapping[i]];
            GVL.Semi_Auto_Material_Count := GVL.Semi_Auto_Material_Count + 1;
        END_IF;
    END_IF;
END_FOR;

(* 2b. POWER-RESTORE - Semi: never trust Step31/32/CMS5 if pending bins (Recipe %M lost after power) *)
IF NOT First_Scan_Done THEN
    First_Scan_Done := TRUE;
    (* Power-down scans clear Process_Was_Active while Ret weights/batch counts survive — rebuild *)
    Pending_Resume_Job := FALSE;
    IF NOT PersistentVars.Ret_Semi_Process_Was_Active THEN
        FOR i := 1 TO 10 DO
            Mat_Idx := Semi_Auto_Bin_Material_Mapping[i];
            IF (Mat_Idx < 1) OR (Mat_Idx > 20) THEN
                IF PersistentVars.Ret_Semi_Bin_Target_Weights[i] > 0.0 THEN
                    Mat_Idx := PersistentVars.Ret_Semi_Bin_Material_Mapping[i];
                ELSE
                    Mat_Idx := 0;
                END_IF;
            END_IF;
            IF PersistentVars.Ret_Semi_Bin_Target_Weights[i] > 0.0 THEN
                IF PersistentVars.Ret_Semi_Actual_Weights[i] < (PersistentVars.Ret_Semi_Bin_Target_Weights[i] - 0.05) THEN
                    Pending_Resume_Job := TRUE;
                    PersistentVars.Ret_Semi_Process_Was_Active := TRUE;
                    PersistentVars.Ret_Semi_Current_Step := i;
                    PersistentVars.Ret_Semi_Cycle_Manager_State := 1;
                    PersistentVars.Ret_Semi_Between_Cycle_Hold := FALSE;
                    PersistentVars.Ret_Semi_Resume_Step := i;
                    IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) THEN
                        PersistentVars.Ret_Semi_Active_Material_ID := Mat_Idx;
                    END_IF;
                    PersistentVars.Ret_Semi_Active_Bin_ID := i;
                    PersistentVars.Ret_Semi_Active_Target_Weight := PersistentVars.Ret_Semi_Bin_Target_Weights[i];
                    PersistentVars.Ret_Semi_bin_last_weight := 0.0;
                    IF i > 1 THEN
                        FOR j := 1 TO (i - 1) DO
                            PersistentVars.Ret_Semi_bin_last_weight := PersistentVars.Ret_Semi_bin_last_weight + PersistentVars.Ret_Semi_Actual_Weights[j];
                        END_FOR;
                    END_IF;
                    EXIT;
                END_IF;
            ELSIF PersistentVars.Ret_Semi_Actual_Weights[i] > 0.05 THEN
                (* Targets lost from %M after power but actual dose weights remain *)
                Pending_Resume_Job := TRUE;
                PersistentVars.Ret_Semi_Process_Was_Active := TRUE;
                PersistentVars.Ret_Semi_Current_Step := i;
                PersistentVars.Ret_Semi_Cycle_Manager_State := 1;
                PersistentVars.Ret_Semi_Between_Cycle_Hold := FALSE;
                PersistentVars.Ret_Semi_Resume_Step := i;
                IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) THEN
                    PersistentVars.Ret_Semi_Active_Material_ID := Mat_Idx;
                END_IF;
                PersistentVars.Ret_Semi_Active_Bin_ID := i;
                IF PersistentVars.Ret_Semi_Active_Target_Weight <= 0.0 THEN
                    PersistentVars.Ret_Semi_Active_Target_Weight := PersistentVars.Ret_Semi_Actual_Weights[i];
                END_IF;
                PersistentVars.Ret_Semi_bin_last_weight := 0.0;
                IF i > 1 THEN
                    FOR j := 1 TO (i - 1) DO
                        PersistentVars.Ret_Semi_bin_last_weight := PersistentVars.Ret_Semi_bin_last_weight + PersistentVars.Ret_Semi_Actual_Weights[j];
                    END_FOR;
                END_IF;
                EXIT;
            END_IF;
        END_FOR;
        IF (NOT Pending_Resume_Job) AND (PersistentVars.Ret_Semi_Target_Batch_Cycles > 0)
            AND (PersistentVars.Ret_Semi_Completed_Batch_Cycles < PersistentVars.Ret_Semi_Target_Batch_Cycles)
            AND (PersistentVars.Ret_Semi_Cycle_Manager_State = 5) THEN
            Pending_Resume_Job := TRUE;
            PersistentVars.Ret_Semi_Process_Was_Active := TRUE;
            PersistentVars.Ret_Semi_Between_Cycle_Hold := TRUE;
        END_IF;
    END_IF;
    IF PersistentVars.Ret_Semi_Process_Was_Active AND (PersistentVars.Ret_Semi_Resume_Step >= 1) AND (PersistentVars.Ret_Semi_Resume_Step <= 10) THEN
        PersistentVars.Ret_Semi_Current_Step := PersistentVars.Ret_Semi_Resume_Step;
        PersistentVars.Ret_Semi_Cycle_Manager_State := 1;
        PersistentVars.Ret_Semi_Between_Cycle_Hold := FALSE;
        IF PersistentVars.Ret_Semi_Current_Batch_Cycle < 1 THEN
            PersistentVars.Ret_Semi_Current_Batch_Cycle := 1;
        END_IF;
    END_IF;
    IF PersistentVars.Ret_Semi_Process_Was_Active AND Semi_Has_Active_Bins AND (
        (PersistentVars.Ret_Semi_Current_Step >= 31) OR (PersistentVars.Ret_Semi_Cycle_Manager_State = 5) OR PersistentVars.Ret_Semi_Between_Cycle_Hold
    ) THEN
        FOR i := 1 TO 10 DO
            Mat_Idx := Semi_Auto_Bin_Material_Mapping[i];
            IF (Mat_Idx < 1) OR (Mat_Idx > 20) THEN
                IF PersistentVars.Ret_Semi_Bin_Target_Weights[i] > 0.0 THEN
                    Mat_Idx := PersistentVars.Ret_Semi_Bin_Material_Mapping[i];
                ELSE
                    Mat_Idx := 0;
                END_IF;
            END_IF;
            IF ((Mat_Idx >= 1) AND (Mat_Idx <= 20)) OR (PersistentVars.Ret_Semi_Bin_Target_Weights[i] > 0.0) THEN
                IF PersistentVars.Ret_Semi_Bin_Target_Weights[i] > 0.0 THEN
                    IF PersistentVars.Ret_Semi_Actual_Weights[i] < (PersistentVars.Ret_Semi_Bin_Target_Weights[i] * 0.5) THEN
                        PersistentVars.Ret_Semi_Current_Step := i;
                        PersistentVars.Ret_Semi_Cycle_Manager_State := 1;
                        PersistentVars.Ret_Semi_Between_Cycle_Hold := FALSE;
                        PersistentVars.Ret_Semi_Resume_Step := i;
                        IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) THEN
                            PersistentVars.Ret_Semi_Active_Material_ID := Mat_Idx;
                        END_IF;
                        PersistentVars.Ret_Semi_Active_Bin_ID := i;
                        PersistentVars.Ret_Semi_Active_Target_Weight := PersistentVars.Ret_Semi_Bin_Target_Weights[i];
                        PersistentVars.Ret_Semi_bin_last_weight := 0.0;
                        IF i > 1 THEN
                            FOR j := 1 TO (i - 1) DO
                                PersistentVars.Ret_Semi_bin_last_weight := PersistentVars.Ret_Semi_bin_last_weight + PersistentVars.Ret_Semi_Actual_Weights[j];
                            END_FOR;
                        END_IF;
                        EXIT;
                    END_IF;
                ELSIF PersistentVars.Ret_Semi_Actual_Weights[i] <= 0.001 THEN
                    PersistentVars.Ret_Semi_Current_Step := i;
                    PersistentVars.Ret_Semi_Cycle_Manager_State := 1;
                    PersistentVars.Ret_Semi_Between_Cycle_Hold := FALSE;
                    PersistentVars.Ret_Semi_Resume_Step := i;
                    IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) THEN
                        PersistentVars.Ret_Semi_Active_Material_ID := Mat_Idx;
                    END_IF;
                    PersistentVars.Ret_Semi_Active_Bin_ID := i;
                    IF PersistentVars.Ret_Semi_Bin_Target_Weights[i] > 0.0 THEN
                        PersistentVars.Ret_Semi_Active_Target_Weight := PersistentVars.Ret_Semi_Bin_Target_Weights[i];
                    END_IF;
                    PersistentVars.Ret_Semi_bin_last_weight := 0.0;
                    IF i > 1 THEN
                        FOR j := 1 TO (i - 1) DO
                            PersistentVars.Ret_Semi_bin_last_weight := PersistentVars.Ret_Semi_bin_last_weight + PersistentVars.Ret_Semi_Actual_Weights[j];
                        END_FOR;
                    END_IF;
                    EXIT;
                END_IF;
            END_IF;
        END_FOR;
    END_IF;
    (* Auto-only: never restore to step 31 settle — go straight to step 32 complete *)
    IF PersistentVars.Ret_Semi_Process_Was_Active AND (NOT Semi_Has_Active_Bins) AND (PersistentVars.Ret_Semi_Current_Step >= 31) THEN
        PersistentVars.Ret_Semi_Current_Step := 32;
        PersistentVars.Ret_Semi_Resume_Step := 0;
        PersistentVars.Ret_Semi_Cycle_Manager_State := 1;
        PersistentVars.Ret_Semi_Between_Cycle_Hold := FALSE;
    END_IF;
    IF PersistentVars.Ret_Semi_Process_Was_Active AND (PersistentVars.Ret_Semi_Cycle_Manager_State <> 4) AND (
        ((PersistentVars.Ret_Semi_Current_Step >= 1) AND (PersistentVars.Ret_Semi_Current_Step <= 10))
        OR ((PersistentVars.Ret_Semi_Current_Step = 32) AND (NOT Semi_Has_Active_Bins))
        OR ((PersistentVars.Ret_Semi_Cycle_Manager_State = 5) AND (PersistentVars.Ret_Semi_Completed_Batch_Cycles < PersistentVars.Ret_Semi_Target_Batch_Cycles) AND (PersistentVars.Ret_Semi_Resume_Step = 0))
    ) THEN
        Current_Step := PersistentVars.Ret_Semi_Current_Step;
        Cycle_Manager_State := PersistentVars.Ret_Semi_Cycle_Manager_State;
        Between_Cycle_Hold := PersistentVars.Ret_Semi_Between_Cycle_Hold;
        Last_Batch_Cycle := PersistentVars.Ret_Semi_Last_Batch_Cycle;
        IF Cycle_Manager_State = 0 THEN
            Cycle_Manager_State := 1;
        END_IF;
        IF (Cycle_Manager_State = 5) OR Between_Cycle_Hold THEN
            Between_Cycle_Hold := TRUE;
        ELSE
            Between_Cycle_Hold := FALSE;
        END_IF;
        bin_last_weight := PersistentVars.Ret_Semi_bin_last_weight;
        IF E_Stop_Active AND Auto_Mode_DI THEN
            GVL.Run := TRUE;
        ELSIF PersistentVars.Ret_Semi_GVL_Run THEN
            GVL.Run := TRUE;
        END_IF;
        GVL.Current_Batch_Cycle := PersistentVars.Ret_Semi_Current_Batch_Cycle;
        GVL.Completed_Batch_Cycles := PersistentVars.Ret_Semi_Completed_Batch_Cycles;
        IF PersistentVars.Ret_Semi_Target_Batch_Cycles > 0 THEN
            GVL.Target_Batch_Cycles := PersistentVars.Ret_Semi_Target_Batch_Cycles;
        END_IF;
        FOR i := 1 TO 10 DO
            Actual_Weights[i] := PersistentVars.Ret_Semi_Actual_Weights[i];
            GVL.Semi_Auto_Weights[i] := PersistentVars.Ret_Semi_Actual_Weights[i];
        END_FOR;
        Semi_Auto_Sum_ActWeight := 0.0;
        FOR i := 1 TO 10 DO
            Semi_Auto_Sum_ActWeight := Semi_Auto_Sum_ActWeight + Actual_Weights[i];
        END_FOR;
        GVL.Semi_Auto_Total_Actual_Weight := Semi_Auto_Sum_ActWeight;
        IF (Current_Step >= 1) AND (Current_Step <= 10) THEN
            Mat_Idx := Semi_Auto_Bin_Material_Mapping[Current_Step];
            IF (Mat_Idx < 1) OR (Mat_Idx > 20) THEN
                IF PersistentVars.Ret_Semi_Bin_Target_Weights[Current_Step] > 0.0 THEN
                    Mat_Idx := PersistentVars.Ret_Semi_Bin_Material_Mapping[Current_Step];
                ELSE
                    Mat_Idx := 0;
                END_IF;
            END_IF;
            Active_Bin_ID := Current_Step;
            IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) THEN
                Active_Material_ID := Mat_Idx;
            ELSE
                Active_Material_ID := 0;
            END_IF;
            IF PersistentVars.Ret_Semi_Bin_Target_Weights[Current_Step] > 0.0 THEN
                Active_Target_Weight := PersistentVars.Ret_Semi_Bin_Target_Weights[Current_Step];
            ELSIF PersistentVars.Ret_Semi_Active_Target_Weight > 0.0 THEN
                Active_Target_Weight := PersistentVars.Ret_Semi_Active_Target_Weight;
            ELSIF (Mat_Idx >= 1) AND (Mat_Idx <= 20) AND (GVL.Recipe_Weights[Mat_Idx] > 0.0) THEN
                Active_Target_Weight := GVL.Recipe_Weights[Mat_Idx];
            ELSE
                Active_Target_Weight := 0.0;
            END_IF;
        ELSE
            Active_Material_ID := 0;
            Active_Bin_ID := 0;
            Active_Target_Weight := 0.0;
        END_IF;
        GVL.Semi_Auto_Active_Mat := Active_Material_ID;
        GVL.Semi_Auto_Active_Bin := Active_Bin_ID;
        GVL.Semi_Auto_Active_Target_Weight := Active_Target_Weight;
        PersistentVars.Ret_Semi_Active_Material_ID := Active_Material_ID;
        PersistentVars.Ret_Semi_Active_Bin_ID := Active_Bin_ID;
        PersistentVars.Ret_Semi_Active_Target_Weight := Active_Target_Weight;
        actual_bin := load_cell_value - bin_last_weight;
        IF actual_bin < 0.0 THEN
            actual_bin := 0.0;
        END_IF;
        IF (load_cell_value = 0.0) AND (PersistentVars.Ret_Semi_Active_Live_Weight > 0.0) THEN
            Active_Live_Weight := PersistentVars.Ret_Semi_Active_Live_Weight;
        ELSE
            Active_Live_Weight := actual_bin;
        END_IF;
        GVL.Semi_Auto_Active_Live_Weight := Active_Live_Weight;
        PersistentVars.Ret_Semi_Active_Live_Weight := Active_Live_Weight;
        Semi_Auto_Current_Batch_Cycle := GVL.Current_Batch_Cycle;
        Semi_Auto_Completed_Batch_Cycles := GVL.Completed_Batch_Cycles;
        GVL.All_Cycles_Complete := FALSE;
        Semi_Auto_All_Cycles_Complete := FALSE;
        IF (Current_Step = 32) AND (NOT Semi_Has_Active_Bins) THEN
            Sequence_Complete := TRUE;
            GVL.Semi_Auto_Sequence_Complete := TRUE;
            Status_Message := 'Semi-Auto [POWER]: Auto-only — Semi complete (no bins)';
        ELSIF (Cycle_Manager_State = 5) OR Between_Cycle_Hold THEN
            Sequence_Complete := TRUE;
            GVL.Semi_Auto_Sequence_Complete := TRUE;
            Status_Message := 'Semi-Auto [POWER]: Waiting next - empty scale then Next_Cycle_Start';
        ELSE
            Sequence_Complete := FALSE;
            GVL.Semi_Auto_Sequence_Complete := FALSE;
            Status_Message := CONCAT('Semi-Auto [POWER]: Pending Mat Step ', CONCAT(INT_TO_STRING(Current_Step), ' - continue'));
        END_IF;
        IF E_Stop_Active AND Auto_Mode_DI THEN
            Paused_By_Hold := FALSE;
        ELSE
            Paused_By_Hold := TRUE;
        END_IF;
    ELSE
        Pending_Resume_Job := FALSE;
        j := 0;
        FOR i := 1 TO 10 DO
            IF PersistentVars.Ret_Semi_Bin_Target_Weights[i] > 0.0 THEN
                IF PersistentVars.Ret_Semi_Actual_Weights[i] < (PersistentVars.Ret_Semi_Bin_Target_Weights[i] - 0.05) THEN
                    Pending_Resume_Job := TRUE;
                    j := i;
                    EXIT;
                END_IF;
            ELSIF PersistentVars.Ret_Semi_Actual_Weights[i] > 0.05 THEN
                Pending_Resume_Job := TRUE;
                j := i;
                EXIT;
            END_IF;
        END_FOR;
        IF Pending_Resume_Job OR PersistentVars.Ret_Semi_Process_Was_Active OR (PersistentVars.Ret_Semi_Current_Step <> 0) OR (PersistentVars.Ret_Semi_Cycle_Manager_State <> 0) THEN
            (* Fallback restore when flags were cleared but Ret weights/batch counts remain *)
            Current_Step := PersistentVars.Ret_Semi_Current_Step;
            IF (Current_Step < 1) OR (Current_Step > 31) THEN
                Current_Step := PersistentVars.Ret_Semi_Resume_Step;
            END_IF;
            IF ((Current_Step < 1) OR (Current_Step > 10)) AND (j > 0) THEN
                Current_Step := j;
            END_IF;
            Cycle_Manager_State := PersistentVars.Ret_Semi_Cycle_Manager_State;
            IF Cycle_Manager_State = 0 THEN
                Cycle_Manager_State := 1;
            END_IF;
            Between_Cycle_Hold := PersistentVars.Ret_Semi_Between_Cycle_Hold;
            Last_Batch_Cycle := PersistentVars.Ret_Semi_Last_Batch_Cycle;
            IF (PersistentVars.Ret_Semi_bin_last_weight <= 0.0) AND (j > 0) THEN
                bin_last_weight := 0.0;
                IF j > 1 THEN
                    FOR i := 1 TO (j - 1) DO
                        bin_last_weight := bin_last_weight + PersistentVars.Ret_Semi_Actual_Weights[i];
                    END_FOR;
                END_IF;
                PersistentVars.Ret_Semi_bin_last_weight := bin_last_weight;
            ELSE
                bin_last_weight := PersistentVars.Ret_Semi_bin_last_weight;
            END_IF;
            GVL.Current_Batch_Cycle := PersistentVars.Ret_Semi_Current_Batch_Cycle;
            GVL.Completed_Batch_Cycles := PersistentVars.Ret_Semi_Completed_Batch_Cycles;
            IF PersistentVars.Ret_Semi_Target_Batch_Cycles > 0 THEN
                GVL.Target_Batch_Cycles := PersistentVars.Ret_Semi_Target_Batch_Cycles;
            END_IF;
            FOR i := 1 TO 10 DO
                Actual_Weights[i] := PersistentVars.Ret_Semi_Actual_Weights[i];
                GVL.Semi_Auto_Weights[i] := PersistentVars.Ret_Semi_Actual_Weights[i];
            END_FOR;
            Semi_Auto_Sum_ActWeight := 0.0;
            FOR i := 1 TO 10 DO
                Semi_Auto_Sum_ActWeight := Semi_Auto_Sum_ActWeight + Actual_Weights[i];
            END_FOR;
            GVL.Semi_Auto_Total_Actual_Weight := Semi_Auto_Sum_ActWeight;
            IF (Current_Step >= 1) AND (Current_Step <= 10) THEN
                Active_Bin_ID := Current_Step;
                Mat_Idx := Semi_Auto_Bin_Material_Mapping[Current_Step];
                IF (Mat_Idx < 1) OR (Mat_Idx > 20) THEN
                    IF PersistentVars.Ret_Semi_Bin_Target_Weights[Current_Step] > 0.0 THEN
                        Mat_Idx := PersistentVars.Ret_Semi_Bin_Material_Mapping[Current_Step];
                    ELSE
                        Mat_Idx := 0;
                    END_IF;
                END_IF;
                IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) THEN
                    Active_Material_ID := Mat_Idx;
                ELSE
                    Active_Material_ID := 0;
                END_IF;
                IF PersistentVars.Ret_Semi_Bin_Target_Weights[Current_Step] > 0.0 THEN
                    Active_Target_Weight := PersistentVars.Ret_Semi_Bin_Target_Weights[Current_Step];
                ELSE
                    Active_Target_Weight := PersistentVars.Ret_Semi_Active_Target_Weight;
                END_IF;
            END_IF;
            GVL.Semi_Auto_Active_Mat := Active_Material_ID;
            GVL.Semi_Auto_Active_Bin := Active_Bin_ID;
            GVL.Semi_Auto_Active_Target_Weight := Active_Target_Weight;
            actual_bin := load_cell_value - bin_last_weight;
            IF actual_bin < 0.0 THEN
                actual_bin := 0.0;
            END_IF;
            Active_Live_Weight := actual_bin;
            GVL.Semi_Auto_Active_Live_Weight := actual_bin;
            PersistentVars.Ret_Semi_Process_Was_Active := TRUE;
            IF E_Stop_Active AND Auto_Mode_DI THEN
                GVL.Run := TRUE;
                Paused_By_Hold := FALSE;
            END_IF;
            IF (Current_Step = 32) AND (NOT Semi_Has_Active_Bins) THEN
                Sequence_Complete := TRUE;
                GVL.Semi_Auto_Sequence_Complete := TRUE;
                Status_Message := 'Semi-Auto [POWER-FIX]: Auto-only — Semi complete (no bins)';
            ELSE
                Sequence_Complete := FALSE;
                GVL.Semi_Auto_Sequence_Complete := FALSE;
                Status_Message := CONCAT('Semi-Auto [POWER-FIX]: Resumed Step ', INT_TO_STRING(Current_Step));
            END_IF;
        ELSE
            Current_Step := 0;
            Cycle_Manager_State := 0;
            Between_Cycle_Hold := FALSE;
            Sequence_Complete := FALSE;
            GVL.Semi_Auto_Sequence_Complete := FALSE;
            GVL.All_Cycles_Complete := FALSE;
            Semi_Auto_All_Cycles_Complete := FALSE;
            Active_Material_ID := 0;
            Active_Bin_ID := 0;
            Active_Target_Weight := 0.0;
            Active_Live_Weight := 0.0;
            Status_Message := 'Semi-Auto [POWER]: No mid-job retain - Idle. Press Start.';
            PersistentVars.Ret_Semi_Process_Was_Active := FALSE;
            PersistentVars.Ret_Semi_Current_Step := 0;
            PersistentVars.Ret_Semi_Cycle_Manager_State := 0;
            PersistentVars.Ret_Semi_Between_Cycle_Hold := FALSE;
            PersistentVars.Ret_Semi_GVL_Run := FALSE;
            PersistentVars.Ret_Semi_Active_Live_Weight := 0.0;
            PersistentVars.Ret_Semi_Resume_Step := 0;
        END_IF;
    END_IF;
END_IF;

(* Re-assert shared GVL.Run while Semi mid-job (Auto CMS0 may clear Run same scan / next scan) *)
IF PersistentVars.Ret_Semi_Process_Was_Active AND (Cycle_Manager_State = 1)
    AND (Current_Step >= 1) AND (Current_Step <= 31) AND (NOT GVL.Run)
    AND E_Stop_Active AND Auto_Mode_DI THEN
    GVL.Run := TRUE;
END_IF;

(* 2c. SAFETY NET - false Step31/32/CMS5 only: active bin Mat+Target>0 still under-dosed *)
(* Do NOT run at Step32/SeqComplete — was holding Step3 CMS1 after batch done *)
IF First_Scan_Done AND GVL.Run AND Semi_Has_Active_Bins AND (NOT Sequence_Complete)
    AND (Current_Step <> 32)
    AND ((Cycle_Manager_State = 5) OR Between_Cycle_Hold OR (Current_Step >= 31)) THEN
    FOR i := 1 TO 10 DO
        Mat_Idx := Semi_Auto_Bin_Material_Mapping[i];
        IF (Mat_Idx < 1) OR (Mat_Idx > 20) THEN
            IF PersistentVars.Ret_Semi_Bin_Target_Weights[i] > 0.0 THEN
                Mat_Idx := PersistentVars.Ret_Semi_Bin_Material_Mapping[i];
            ELSE
                Mat_Idx := 0;
            END_IF;
        END_IF;
        target_weight := 0.0;
        IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) THEN
            target_weight := GVL.Recipe_Weights[Mat_Idx];
        END_IF;
        IF (target_weight <= 0.0) AND (PersistentVars.Ret_Semi_Bin_Target_Weights[i] > 0.0) THEN
            target_weight := PersistentVars.Ret_Semi_Bin_Target_Weights[i];
        END_IF;
        IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) AND (target_weight > 0.0) THEN
            IF Actual_Weights[i] < (target_weight - 0.05) THEN
                Current_Step := i;
                Cycle_Manager_State := 1;
                Between_Cycle_Hold := FALSE;
                Sequence_Complete := FALSE;
                GVL.Semi_Auto_Sequence_Complete := FALSE;
                Waiting_Next_Batch := FALSE;
                Completion_Timer(IN := FALSE);
                Settle_Phase := 0;
                PersistentVars.Ret_Semi_Resume_Step := i;
                PersistentVars.Ret_Semi_Current_Step := i;
                PersistentVars.Ret_Semi_Cycle_Manager_State := 1;
                PersistentVars.Ret_Semi_bin_last_weight := 0.0;
                IF i > 1 THEN
                    FOR j := 1 TO (i - 1) DO
                        PersistentVars.Ret_Semi_bin_last_weight := PersistentVars.Ret_Semi_bin_last_weight + Actual_Weights[j];
                    END_FOR;
                END_IF;
                Active_Bin_ID := i;
                Active_Material_ID := Mat_Idx;
                Active_Target_Weight := target_weight;
                GVL.Semi_Auto_Active_Mat := Active_Material_ID;
                GVL.Semi_Auto_Active_Bin := Active_Bin_ID;
                GVL.Semi_Auto_Active_Target_Weight := Active_Target_Weight;
                Paused_By_Hold := FALSE;
                Status_Message := CONCAT('Semi-Auto [RESUME-FIX]: Pending Mat Step ', INT_TO_STRING(i));
                EXIT;
            END_IF;
        END_IF;
    END_FOR;
END_IF;

(* 3. PROCESS HOLD - E-Stop open OR Auto_Mode_DI OFF; auto-resume when both OK *)
IF (Cycle_Manager_State <> 0) OR GVL.Run OR (Current_Step <> 0) OR Between_Cycle_Hold THEN
    IF NOT E_Stop_Active OR NOT Auto_Mode_DI THEN
        Paused_By_Hold := TRUE;
    END_IF;
END_IF;

IF Paused_By_Hold THEN
    FOR i := 1 TO 10 DO
        Semi_Auto_Bin[i] := FALSE;
        semi_auto_bin_cutoff[i] := FALSE;
        semi_auto_bin_motor[i] := FALSE;
    END_FOR;
    (* Keep Active Target/Live on HMI while held — only if this step is in live recipe *)
    IF (Current_Step >= 1) AND (Current_Step <= 10) THEN
        Mat_Idx := Semi_Auto_Bin_Material_Mapping[Current_Step];
        IF (Mat_Idx < 1) OR (Mat_Idx > 20) THEN
            IF PersistentVars.Ret_Semi_Bin_Target_Weights[Current_Step] > 0.0 THEN
                Mat_Idx := PersistentVars.Ret_Semi_Bin_Material_Mapping[Current_Step];
            ELSE
                Mat_Idx := 0;
            END_IF;
        END_IF;
        target_weight := 0.0;
        IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) THEN
            target_weight := GVL.Recipe_Weights[Mat_Idx];
        END_IF;
        IF (target_weight <= 0.0) AND (PersistentVars.Ret_Semi_Bin_Target_Weights[Current_Step] > 0.0) THEN
            target_weight := PersistentVars.Ret_Semi_Bin_Target_Weights[Current_Step];
        END_IF;
        IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) AND (target_weight > 0.0) THEN
            Active_Material_ID := Mat_Idx;
            Active_Bin_ID := Current_Step;
            Active_Target_Weight := target_weight;
            GVL.Semi_Auto_Active_Mat := Mat_Idx;
            GVL.Semi_Auto_Active_Bin := Current_Step;
            GVL.Semi_Auto_Active_Target_Weight := Active_Target_Weight;
            actual_bin := load_cell_value - bin_last_weight;
            IF actual_bin < 0.0 THEN
                actual_bin := 0.0;
            END_IF;
            IF (load_cell_value = 0.0) AND (PersistentVars.Ret_Semi_Active_Live_Weight > 0.0) AND (actual_bin <= 0.0) THEN
                Active_Live_Weight := PersistentVars.Ret_Semi_Active_Live_Weight;
            ELSE
                Active_Live_Weight := actual_bin;
                IF actual_bin > 0.0 THEN
                    PersistentVars.Ret_Semi_Active_Live_Weight := actual_bin;
                END_IF;
            END_IF;
            Actual_Weights[Current_Step] := Active_Live_Weight;
            GVL.Semi_Auto_Active_Live_Weight := Active_Live_Weight;
        ELSE
            Active_Material_ID := 0;
            Active_Bin_ID := 0;
            GVL.Semi_Auto_Active_Mat := 0;
            GVL.Semi_Auto_Active_Bin := 0;
        END_IF;
    END_IF;
    IF Inter_Bin_Settling AND (Settle_Hold_Step >= 1) THEN
        actual_bin := load_cell_value - bin_last_weight;
        IF actual_bin < 0.0 THEN
            actual_bin := 0.0;
        END_IF;
        Actual_Weights[Settle_Hold_Step] := actual_bin;
        Active_Live_Weight := actual_bin;
        GVL.Semi_Auto_Active_Live_Weight := actual_bin;
    END_IF;
    IF NOT E_Stop_Active THEN
        Status_Message := CONCAT('Semi-Auto [HOLD]: E-Stop at Step ', INT_TO_STRING(Current_Step));
    ELSIF NOT Auto_Mode_DI THEN
        Status_Message := CONCAT('Semi-Auto [HOLD]: Auto Mode OFF at Step ', INT_TO_STRING(Current_Step));
    ELSE
        Paused_By_Hold := FALSE;
        Status_Message := CONCAT('Semi-Auto [RESUME]: Continuing Step ', INT_TO_STRING(Current_Step));
    END_IF;
    IF Paused_By_Hold THEN
        Sim_Timer(IN := FALSE);
        Transition_Timer(IN := FALSE);
        Completion_Timer(IN := FALSE);
        Inter_Bin_Timer(IN := FALSE);
        Inter_Bin_Settle_Arm := 0;
        GVL.Semi_Auto_Current_Step := Current_Step;
        Semi_Auto_Sum_ActWeight := 0.0;
        FOR i := 1 TO 10 DO
            GVL.Semi_Auto_Weights[i] := Actual_Weights[i];
            Semi_Auto_Sum_ActWeight := Semi_Auto_Sum_ActWeight + Actual_Weights[i];
            Mat_Idx := Semi_Auto_Bin_Material_Mapping[i];
            IF (Mat_Idx < 1) OR (Mat_Idx > 20) THEN
                IF PersistentVars.Ret_Semi_Bin_Target_Weights[i] > 0.0 THEN
                    Mat_Idx := PersistentVars.Ret_Semi_Bin_Material_Mapping[i];
                ELSE
                    Mat_Idx := 0;
                END_IF;
            END_IF;
            target_weight := 0.0;
            IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) THEN
                target_weight := GVL.Recipe_Weights[Mat_Idx];
            END_IF;
            IF (target_weight <= 0.0) AND (PersistentVars.Ret_Semi_Bin_Target_Weights[i] > 0.0) THEN
                target_weight := PersistentVars.Ret_Semi_Bin_Target_Weights[i];
            END_IF;
            Semi_Auto_Target_Weight[i] := target_weight;
            GVL.Semi_Auto_Target_Weights[i] := target_weight;
        END_FOR;
        GVL.Semi_Auto_Total_Actual_Weight := Semi_Auto_Sum_ActWeight;
        RETURN;
    END_IF;
END_IF;

(* 3b. LINE FAULT HOLD — Over Dump Avoid (wire Line_Fault from FB_Samyak_Multi.arrLine_Fault[n]) *)
Tare_Semi_Auto_Batch := FALSE;
IF Line_Fault THEN
    Paused_By_LineFault := TRUE;
END_IF;

IF Paused_By_LineFault THEN
    FOR i := 1 TO 10 DO
        Semi_Auto_Bin[i] := FALSE;
        semi_auto_bin_cutoff[i] := FALSE;
        semi_auto_bin_motor[i] := FALSE;
    END_FOR;
    Tare_Semi_Auto_Batch := FALSE;
    IF Line_Fault THEN
        Error_Code := 5; (* Communication Fault *)
        GVL.Error_Code := 5;
        Status_Message := CONCAT('Semi-Auto [HOLD]: Error 5 Communication Fault (Line_Fault) at Step ', INT_TO_STRING(Current_Step));
    ELSE
        Paused_By_LineFault := FALSE;
        IF Error_Code = 5 THEN
            Error_Code := 0;
        END_IF;
        IF GVL.Error_Code = 5 THEN
            GVL.Error_Code := 0;
        END_IF;
        Status_Message := CONCAT('Semi-Auto [RESUME]: Communication Fault cleared - continuing Step ', INT_TO_STRING(Current_Step));
    END_IF;
    IF (Current_Step >= 1) AND (Current_Step <= 10) THEN
        actual_bin := load_cell_value - bin_last_weight;
        IF actual_bin < 0.0 THEN
            actual_bin := 0.0;
        END_IF;
        Actual_Weights[Current_Step] := actual_bin;
        Active_Live_Weight := actual_bin;
        GVL.Semi_Auto_Active_Live_Weight := actual_bin;
    END_IF;
    IF Inter_Bin_Settling AND (Settle_Hold_Step >= 1) THEN
        actual_bin := load_cell_value - bin_last_weight;
        IF actual_bin < 0.0 THEN
            actual_bin := 0.0;
        END_IF;
        Actual_Weights[Settle_Hold_Step] := actual_bin;
        Active_Live_Weight := actual_bin;
        GVL.Semi_Auto_Active_Live_Weight := actual_bin;
    END_IF;
    Sim_Timer(IN := FALSE);
    Transition_Timer(IN := FALSE);
    Completion_Timer(IN := FALSE);
    Semi_Auto_Sum_ActWeight := 0.0;
    FOR i := 1 TO 10 DO
        GVL.Semi_Auto_Weights[i] := Actual_Weights[i];
        Semi_Auto_Sum_ActWeight := Semi_Auto_Sum_ActWeight + Actual_Weights[i];
        Mat_Idx := Semi_Auto_Bin_Material_Mapping[i];
        IF (Mat_Idx < 1) OR (Mat_Idx > 20) THEN
            IF PersistentVars.Ret_Semi_Bin_Target_Weights[i] > 0.0 THEN
                Mat_Idx := PersistentVars.Ret_Semi_Bin_Material_Mapping[i];
            ELSE
                Mat_Idx := 0;
            END_IF;
        END_IF;
        target_weight := 0.0;
        IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) THEN
            target_weight := GVL.Recipe_Weights[Mat_Idx];
        END_IF;
        IF (target_weight <= 0.0) AND (PersistentVars.Ret_Semi_Bin_Target_Weights[i] > 0.0) THEN
            target_weight := PersistentVars.Ret_Semi_Bin_Target_Weights[i];
        END_IF;
        Semi_Auto_Target_Weight[i] := target_weight;
        GVL.Semi_Auto_Target_Weights[i] := target_weight;
    END_FOR;
    GVL.Semi_Auto_Total_Actual_Weight := Semi_Auto_Sum_ActWeight;
    RETURN;
END_IF;

(* 4. BETWEEN-CYCLE HOLD — Next_Cycle_Start / NextBatchStart (same rule as Auto FB) *)
(* Purpose: Target_Batch_Cycles > 1 AND Completed_Batch_Cycles >= 1 AND Completed < Target.
   Operator empties THIS FB scale (load_cell LT Empty_Weight_Limit), then presses Next_Cycle_Start.
   Auto FB advances GVL.Current_Batch_Cycle; Semi releases hold and restarts dosing. *)
IF Cycle_Manager_State = 5 OR Between_Cycle_Hold THEN
    Cycle_Manager_State := 5;

    Status_Message := 'Semi-Auto [State 5]: Empty scale < limit then press Next_Cycle_Start';

    IF Next_Cycle_Rising THEN
        IF (GVL.Target_Batch_Cycles > 1) AND (GVL.Completed_Batch_Cycles >= 1) AND (GVL.Completed_Batch_Cycles < GVL.Target_Batch_Cycles) THEN
            IF Scale_Empty_OK THEN
                (* Accept: release hold. Do not clear GVL.Next_Cycle_Start (Auto may still need pulse same scan). *)
                Between_Cycle_Hold := FALSE;
                Sequence_Complete := FALSE;
                GVL.Semi_Auto_Sequence_Complete := FALSE;
                Current_Step := 0;
                Last_Batch_Cycle := GVL.Current_Batch_Cycle;
                Tare_Pulse_Req := TRUE;
                Excess_Alarm := FALSE;
                Error_Code := 0;
                FOR i := 1 TO 10 DO
                    Actual_Weights[i] := 0.0;
                    Semi_Auto_Bin[i] := FALSE;
                    semi_auto_bin_cutoff[i] := FALSE;
                    semi_auto_bin_motor[i] := FALSE;
                END_FOR;
                Cycle_Manager_State := 1;
                Status_Message := 'Semi-Auto [State 5]: Next_Cycle_Start accepted — starting next cycle';
            ELSE
                (* Reject: clear command so operator can press again after emptying *)
                GVL.Next_Cycle_Start := FALSE;
                Next_Cycle_Last := FALSE;
                Status_Message := CONCAT('Semi-Auto [State 5]: Scale >= limit (', CONCAT(REAL_TO_STRING(eff_empty_limit), ' kg)! Empty then Next_Cycle_Start again.'));
            END_IF;
        ELSE
            GVL.Next_Cycle_Start := FALSE;
            Next_Cycle_Last := FALSE;
            Status_Message := 'Semi-Auto [State 5]: Next_Cycle_Start ignored (cycle gates not met)';
        END_IF;
    END_IF;
END_IF;

(* Waiting_Next_Batch: TRUE only in between-cycle hold while Current < Target
   Example Target=3: after cycle 1 -> TRUE; next cycle runs -> FALSE; Current=3 (last) -> never TRUE.
   Same rule as Auto_Batching_V15. *)
Waiting_Next_Batch := ((Cycle_Manager_State = 5) OR Between_Cycle_Hold)
    AND (GVL.Target_Batch_Cycles > 1)
    AND (GVL.Current_Batch_Cycle < GVL.Target_Batch_Cycles);

(* 5. SEQUENCE START (FOR CYCLE 1 AND REPEAT CYCLES) — not while CMS4 finished (match Auto hold) *)
IF GVL.Run AND (Cycle_Manager_State <> 5) AND (Cycle_Manager_State <> 4) AND (NOT Between_Cycle_Hold) THEN
    IF Current_Step = 0 THEN
        IF NOT Semi_Has_Active_Bins THEN
            (* Auto-only recipe: no Semi targets — instant complete for handshake *)
            Last_Batch_Cycle := GVL.Current_Batch_Cycle;
            Current_Step := 32;
            Active_Material_ID := 0;
            Active_Bin_ID := 0;
            Active_Target_Weight := 0.0;
            Active_Live_Weight := 0.0;
            GVL.Semi_Auto_Active_Target_Weight := 0.0;
            GVL.Semi_Auto_Active_Live_Weight := 0.0;
            GVL.Semi_Auto_Active_Mat := 0;
            GVL.Semi_Auto_Active_Bin := 0;
            Sequence_Complete := TRUE;
            GVL.Semi_Auto_Sequence_Complete := TRUE;
            Status_Message := 'Semi-Auto [Step 32]: No Semi bins — complete (Auto partner)';
        ELSIF Scale_Empty_OK THEN
            Last_Batch_Cycle := GVL.Current_Batch_Cycle;
            Current_Step := 1;
            bin_last_weight := load_cell_value;
            PersistentVars.Ret_Semi_bin_last_weight := bin_last_weight;
            Last_Dosing_Step := 1;
            Sequence_Complete := FALSE;
            GVL.Semi_Auto_Sequence_Complete := FALSE;
            Excess_Alarm := FALSE;
            Error_Code := 0;
            FOR i := 1 TO 10 DO
                Actual_Weights[i] := 0.0;
                Semi_Auto_Bin[i] := FALSE;
                semi_auto_bin_cutoff[i] := FALSE;
                semi_auto_bin_motor[i] := FALSE;
            END_FOR;
        ELSE
            Status_Message := CONCAT('Semi-Auto [Hold]: Empty scale < ', CONCAT(REAL_TO_STRING(eff_empty_limit), ' kg required before dosing'));
        END_IF;
    ELSIF Current_Step = 32 AND GVL.Current_Batch_Cycle <> Last_Batch_Cycle THEN
        IF NOT Semi_Has_Active_Bins THEN
            Last_Batch_Cycle := GVL.Current_Batch_Cycle;
            Sequence_Complete := TRUE;
            GVL.Semi_Auto_Sequence_Complete := TRUE;
            Status_Message := 'Semi-Auto [Step 32]: New cycle — no Semi bins, complete';
        ELSIF Scale_Empty_OK THEN
            (* Advance to next cycle loop (Cycle 2, 3, etc.) — cycle number already bumped by Auto *)
            Last_Batch_Cycle := GVL.Current_Batch_Cycle;
            Tare_Pulse_Req := TRUE;
            Current_Step := 0;
            bin_last_weight := load_cell_value;
            Sequence_Complete := FALSE;
            GVL.Semi_Auto_Sequence_Complete := FALSE;
            Excess_Alarm := FALSE;
            Error_Code := 0;
            FOR i := 1 TO 10 DO
                Actual_Weights[i] := 0.0;
                Semi_Auto_Bin[i] := FALSE;
                semi_auto_bin_cutoff[i] := FALSE;
                semi_auto_bin_motor[i] := FALSE;
            END_FOR;
        END_IF;
    END_IF;
END_IF;

(* Auto-only: all Mat_ID=0 / Target=0 — hold Step 32 + Seq Complete every scan while running *)
IF (NOT Semi_Has_Active_Bins) AND GVL.Run AND ((Cycle_Manager_State = 1) OR (Cycle_Manager_State = 5) OR Between_Cycle_Hold) THEN
    IF (Current_Step >= 1) AND (Current_Step <= 31) THEN
        Current_Step := 32;
        Completion_Timer(IN := FALSE);
        Settle_Phase := 0;
    END_IF;
    IF (Current_Step = 32) OR (Current_Step = 0) THEN
        Active_Material_ID := 0;
        Active_Bin_ID := 0;
        Active_Target_Weight := 0.0;
        Active_Live_Weight := 0.0;
        GVL.Semi_Auto_Active_Target_Weight := 0.0;
        GVL.Semi_Auto_Active_Live_Weight := 0.0;
        GVL.Semi_Auto_Active_Mat := 0;
        GVL.Semi_Auto_Active_Bin := 0;
        Sequence_Complete := TRUE;
        GVL.Semi_Auto_Sequence_Complete := TRUE;
        IF Current_Step = 0 THEN
            Current_Step := 32;
            Last_Batch_Cycle := GVL.Current_Batch_Cycle;
        END_IF;
        Status_Message := 'Semi-Auto [Step 32]: No Semi bins (Mat=0/Target=0) — complete';
    END_IF;
ELSIF (NOT Semi_Has_Active_Bins) AND (Current_Step = 31) THEN
    Current_Step := 32;
    Completion_Timer(IN := FALSE);
    Settle_Phase := 0;
END_IF;

(* Step 31 entry: always reset settle timer (prevents instant skip if Completion_Timer.Q was latched) *)
IF (Current_Step = 31) AND (Last_Step <> 31) THEN
    Settle_Phase := 0;
    Completion_Timer(IN := FALSE);
END_IF;

(* All active Semi bins dosed but still on step 1..10 — advance to settle (bins 1..3 recipe) *)
IF GVL.Run AND (NOT Paused_By_Hold) AND (Current_Step >= 1) AND (Current_Step <= 10) AND Semi_Has_Active_Bins THEN
    j := 0;
    FOR i := 1 TO 10 DO
        Mat_Idx := Semi_Auto_Bin_Material_Mapping[i];
        IF (Mat_Idx < 1) OR (Mat_Idx > 20) THEN
            IF PersistentVars.Ret_Semi_Bin_Target_Weights[i] > 0.0 THEN
                Mat_Idx := PersistentVars.Ret_Semi_Bin_Material_Mapping[i];
            ELSE
                Mat_Idx := 0;
            END_IF;
        END_IF;
        target_weight := 0.0;
        IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) THEN
            target_weight := GVL.Recipe_Weights[Mat_Idx];
        END_IF;
        IF (target_weight <= 0.0) AND (PersistentVars.Ret_Semi_Bin_Target_Weights[i] > 0.0) THEN
            target_weight := PersistentVars.Ret_Semi_Bin_Target_Weights[i];
        END_IF;
        IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) AND (target_weight > 0.0) THEN
            IF Actual_Weights[i] < (target_weight - 0.05) THEN
                j := i;
                EXIT;
            END_IF;
        END_IF;
    END_FOR;
    IF j = 0 THEN
        Current_Step := 31;
        Settle_Phase := 0;
        Completion_Timer(IN := FALSE);
        Active_Material_ID := 0;
        Active_Bin_ID := 0;
        Active_Target_Weight := 0.0;
        Active_Live_Weight := 0.0;
        Status_Message := 'Semi-Auto: All bins done — Step 31 settle';
    END_IF;
END_IF;

CASE Current_Step OF
    0:
        Active_Material_ID := 0;
        Active_Bin_ID := 0;
        Excess_Alarm := FALSE;
        Sequence_Complete := FALSE;
        FOR i := 1 TO 10 DO
            Semi_Auto_Bin[i] := FALSE;
            semi_auto_bin_cutoff[i] := FALSE;
            semi_auto_bin_motor[i] := FALSE;
        END_FOR;
        Active_Target_Weight := GVL.Semi_Auto_Active_Target_Weight;
        Active_Live_Weight := 0.0;
        IF Error_Code = 0 AND Cycle_Manager_State <> 5 THEN 
            Status_Message := 'Semi-Auto [Step 0 - Idle]: Ready - Waiting for Run Signal'; 
        END_IF;
        
    1..10:
        (* Skip bin when Mat_ID invalid OR Target<=0 (Mat_ID>0 with Target=0 still skips to next bin) *)
        WHILE Current_Step >= 1 AND Current_Step <= 10 DO
            Mat_Idx := Semi_Auto_Bin_Material_Mapping[Current_Step];
            IF (Mat_Idx < 1) OR (Mat_Idx > 20) THEN
                IF PersistentVars.Ret_Semi_Bin_Target_Weights[Current_Step] > 0.0 THEN
                    Mat_Idx := PersistentVars.Ret_Semi_Bin_Material_Mapping[Current_Step];
                ELSE
                    Mat_Idx := 0;
                END_IF;
            END_IF;
            target_weight := 0.0;
            IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) THEN
                target_weight := GVL.Recipe_Weights[Mat_Idx];
            END_IF;
            IF (target_weight <= 0.0) AND (PersistentVars.Ret_Semi_Bin_Target_Weights[Current_Step] > 0.0) THEN
                target_weight := PersistentVars.Ret_Semi_Bin_Target_Weights[Current_Step];
            END_IF;
            IF (Mat_Idx < 1) OR (Mat_Idx > 20) OR (target_weight <= 0.0) THEN
                Semi_Auto_Bin[Current_Step] := FALSE;
                semi_auto_bin_cutoff[Current_Step] := FALSE;
                semi_auto_bin_motor[Current_Step] := FALSE;
                Actual_Weights[Current_Step] := 0.0;
                IF Current_Step = 10 THEN
                    IF Semi_Has_Active_Bins THEN
                        Current_Step := 31;
                        Settle_Phase := 0;
                    ELSE
                        Current_Step := 32;
                    END_IF;
                ELSE
                    Current_Step := Current_Step + 1;
                END_IF;
            ELSE
                EXIT; (* Valid active recipe silo found *)
            END_IF;
        END_WHILE;
        
        IF Inter_Bin_Settling THEN
            FOR i := 1 TO 10 DO
                Semi_Auto_Bin[i] := FALSE;
                semi_auto_bin_cutoff[i] := FALSE;
                semi_auto_bin_motor[i] := FALSE;
            END_FOR;
            IF Settle_Hold_Step >= 1 THEN
                (* InterBinDelay: feeders OFF — hold SAME bin ID/Mat until timer done (TRUE and FALSE) *)
                Active_Material_ID := Settle_Hold_Mat;
                Active_Bin_ID := Settle_Hold_Step;
                Active_Target_Weight := Settle_Hold_Target;
                GVL.Semi_Auto_Active_Target_Weight := Settle_Hold_Target;
                GVL.Semi_Auto_Active_Mat := Settle_Hold_Mat;
                GVL.Semi_Auto_Active_Bin := Settle_Hold_Step;
                actual_bin := load_cell_value - bin_last_weight;
                IF actual_bin < 0.0 THEN
                    actual_bin := 0.0;
                END_IF;
                Actual_Weights[Settle_Hold_Step] := actual_bin;
                Active_Live_Weight := actual_bin;
                GVL.Semi_Auto_Active_Live_Weight := actual_bin;
                complete_weight := Settle_Hold_Target + Semi_Auto_Bin_Tolerance[Settle_Hold_Step];
                IF (NOT Excess_Allowed) AND (actual_bin > complete_weight) THEN
                    Excess_Alarm := TRUE;
                    GVL.Semi_Auto_Excess_Alarm := TRUE;
                    Inter_Bin_Timer(IN := FALSE);
                    Inter_Bin_Settle_Arm := 0;
                    Status_Message := CONCAT('Semi-Auto [Step ', CONCAT(INT_TO_STRING(Settle_Hold_Step), ']: EXCESS tailings during settle — remove before next bin'));
                ELSE
                    Excess_Alarm := FALSE;
                    GVL.Semi_Auto_Excess_Alarm := FALSE;
                    Status_Message := CONCAT('Semi-Auto [Step ', CONCAT(INT_TO_STRING(Settle_Hold_Step), ']: Inter-bin settle before next bin'));
                    IF Inter_Bin_Settle_Arm = 0 THEN
                        Inter_Bin_Timer(IN := FALSE);
                        Inter_Bin_Settle_Arm := 1;
                    ELSE
                        Inter_Bin_Timer(IN := TRUE, PT := Inter_Bin_Delay);
                        IF Inter_Bin_Timer.Q THEN
                            Inter_Bin_Timer(IN := FALSE);
                            Actual_Weights[Settle_Hold_Step] := actual_bin;
                            bin_last_weight := load_cell_value;
                            PersistentVars.Ret_Semi_bin_last_weight := bin_last_weight;
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
                Status_Message := CONCAT('Semi-Auto [Step ', CONCAT(INT_TO_STRING(Current_Step), ']: Inter-bin settle before next bin'));
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
        ELSIF Current_Step >= 1 AND Current_Step <= 10 THEN
            Mat_Idx := Semi_Auto_Bin_Material_Mapping[Current_Step];
            IF (Mat_Idx < 1) OR (Mat_Idx > 20) THEN
                IF PersistentVars.Ret_Semi_Bin_Target_Weights[Current_Step] > 0.0 THEN
                    Mat_Idx := PersistentVars.Ret_Semi_Bin_Material_Mapping[Current_Step];
                ELSE
                    Mat_Idx := 0;
                END_IF;
            END_IF;
            target_weight := 0.0;
            IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) THEN
                target_weight := GVL.Recipe_Weights[Mat_Idx];
            END_IF;
            IF (target_weight <= 0.0) AND (PersistentVars.Ret_Semi_Bin_Target_Weights[Current_Step] > 0.0) THEN
                target_weight := PersistentVars.Ret_Semi_Bin_Target_Weights[Current_Step];
            END_IF;
            
            (* New bin step: snap gross tare so ATW=new target and ALW starts at 0 *)
            IF Current_Step <> Last_Dosing_Step THEN
                bin_last_weight := load_cell_value;
                PersistentVars.Ret_Semi_bin_last_weight := bin_last_weight;
                Last_Dosing_Step := Current_Step;
                Actual_Weights[Current_Step] := 0.0;
            END_IF;
            
            Active_Target_Weight := target_weight;
            GVL.Semi_Auto_Active_Target_Weight := target_weight;
            
            cutoff_trigger_weight := target_weight - Semi_Auto_Coarse_To_Fine_Speed[Current_Step];
            IF cutoff_trigger_weight < 0.0 THEN
                cutoff_trigger_weight := 0.0;
            END_IF;
            (* Accept band [Target .. Target+Tol]. Advance in band; excess only above Target+Tol. *)
            complete_weight := target_weight + Semi_Auto_Bin_Tolerance[Current_Step];
            min_tol_weight := target_weight;
            max_tol_weight := complete_weight;
            
            actual_bin := load_cell_value - bin_last_weight;
            IF actual_bin < 0.0 THEN
                actual_bin := 0.0;
            END_IF;
            Actual_Weights[Current_Step] := actual_bin;
            Active_Live_Weight := actual_bin;
            GVL.Semi_Auto_Active_Live_Weight := actual_bin;
            Active_Material_ID := Mat_Idx;
            Active_Bin_ID := Current_Step;
            
            IF load_cell_value > 500.0 THEN
                Error_Code := 21;
                GVL.Error_Code := 21;
                Status_Message := CONCAT('Semi-Auto [Step ', CONCAT(INT_TO_STRING(Current_Step), ']: STUCK - Error 21: Scale Overloaded (> 500 kg)!'));
                Sequence_Complete := TRUE;
                GVL.Semi_Auto_Sequence_Complete := TRUE;
                Paused_By_Hold := TRUE;
            END_IF;
            
            IF actual_bin < cutoff_trigger_weight THEN
                Semi_Auto_Bin[Current_Step] := TRUE;
                semi_auto_bin_cutoff[Current_Step] := FALSE;
                semi_auto_bin_motor[Current_Step] := TRUE;
                Excess_Alarm := FALSE;
                GVL.Semi_Auto_Excess_Alarm := FALSE;
                Status_Message := CONCAT('Semi-Auto [Step ', CONCAT(INT_TO_STRING(Current_Step), ']: Coarse Feeding'));
            ELSIF actual_bin < target_weight THEN
                (* Below target: fine feed until Live >= Target *)
                Semi_Auto_Bin[Current_Step] := FALSE;
                semi_auto_bin_cutoff[Current_Step] := TRUE;
                semi_auto_bin_motor[Current_Step] := TRUE;
                Excess_Alarm := FALSE;
                GVL.Semi_Auto_Excess_Alarm := FALSE;
                Status_Message := CONCAT(CONCAT(CONCAT('Semi-Auto [Step ', INT_TO_STRING(Current_Step)), ']: Fine Feeding to '), CONCAT(REAL_TO_STRING(target_weight), ' kg'));
            ELSIF (NOT Excess_Allowed) AND (actual_bin > complete_weight) THEN
                (* Over Target+Tolerance: stop feeders; remove excess until Live <= Target+Tol *)
                Semi_Auto_Bin[Current_Step] := FALSE;
                semi_auto_bin_cutoff[Current_Step] := FALSE;
                semi_auto_bin_motor[Current_Step] := FALSE;
                Excess_Alarm := TRUE;
                GVL.Semi_Auto_Excess_Alarm := TRUE;
                Status_Message := CONCAT(CONCAT(CONCAT('Semi-Auto [Step ', INT_TO_STRING(Current_Step)), ']: EXCESS - Remove material (>'), CONCAT(REAL_TO_STRING(complete_weight), ' kg)'));
            ELSE
                (* Target <= Live <= Target+Tol (or Excess_Allowed overfill): advance to next bin *)
                Semi_Auto_Bin[Current_Step] := FALSE;
                semi_auto_bin_cutoff[Current_Step] := FALSE;
                semi_auto_bin_motor[Current_Step] := FALSE;
                Excess_Alarm := FALSE;
                GVL.Semi_Auto_Excess_Alarm := FALSE;
                IF actual_bin > complete_weight THEN
                    Status_Message := CONCAT('Semi-Auto [Step ', CONCAT(INT_TO_STRING(Current_Step), ']: Excess Allowed - Advancing'));
                ELSE
                    Status_Message := CONCAT('Semi-Auto [Step ', CONCAT(INT_TO_STRING(Current_Step), ']: Target+Tol OK - Advancing'));
                END_IF;
                IF Current_Step >= 10 THEN
                    Inter_Bin_Settling := FALSE;
                    Settle_Hold_Step := 0;
                    bin_last_weight := load_cell_value;
                    PersistentVars.Ret_Semi_bin_last_weight := bin_last_weight;
                    Active_Target_Weight := 0.0;
                    Active_Live_Weight := 0.0;
                    GVL.Semi_Auto_Active_Target_Weight := 0.0;
                    GVL.Semi_Auto_Active_Live_Weight := 0.0;
                    IF Semi_Has_Active_Bins THEN
                        Current_Step := 31;
                        Settle_Phase := 0;
                    ELSE
                        Current_Step := 32;
                    END_IF;
                ELSE
                    (* Capture completed bin before j-loop overwrites Mat_Idx/target_weight *)
                    Settle_Hold_Step := Current_Step;
                    Settle_Hold_Mat := Mat_Idx;
                    Settle_Hold_Target := target_weight;
                    j := Current_Step + 1;
                    WHILE j <= 10 DO
                        Mat_Idx := Semi_Auto_Bin_Material_Mapping[j];
                        IF (Mat_Idx < 1) OR (Mat_Idx > 20) THEN
                            IF PersistentVars.Ret_Semi_Bin_Target_Weights[j] > 0.0 THEN
                                Mat_Idx := PersistentVars.Ret_Semi_Bin_Material_Mapping[j];
                            ELSE
                                Mat_Idx := 0;
                            END_IF;
                        END_IF;
                        target_weight := 0.0;
                        IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) THEN
                            target_weight := GVL.Recipe_Weights[Mat_Idx];
                        END_IF;
                        IF (target_weight <= 0.0) AND (PersistentVars.Ret_Semi_Bin_Target_Weights[j] > 0.0) THEN
                            target_weight := PersistentVars.Ret_Semi_Bin_Target_Weights[j];
                        END_IF;
                        IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) AND (target_weight > 0.0) THEN
                            EXIT;
                        END_IF;
                        j := j + 1;
                    END_WHILE;
                    IF j > 10 THEN
                        Inter_Bin_Settling := FALSE;
                        Settle_Hold_Step := 0;
                        bin_last_weight := load_cell_value;
                        PersistentVars.Ret_Semi_bin_last_weight := bin_last_weight;
                        Active_Target_Weight := 0.0;
                        Active_Live_Weight := 0.0;
                        GVL.Semi_Auto_Active_Target_Weight := 0.0;
                        GVL.Semi_Auto_Active_Live_Weight := 0.0;
                        IF Semi_Has_Active_Bins THEN
                            Current_Step := 31;
                            Settle_Phase := 0;
                        ELSE
                            Current_Step := 32;
                        END_IF;
                    ELSIF Inter_Bin_Delay > T#0S THEN
                        Actual_Weights[Settle_Hold_Step] := actual_bin;
                        Inter_Bin_Next_Step := j;
                        Inter_Bin_Settling := TRUE;
                        Inter_Bin_Settle_Arm := 0;
                        Inter_Bin_Timer(IN := FALSE);
                    ELSE
                        bin_last_weight := load_cell_value;
                        PersistentVars.Ret_Semi_bin_last_weight := bin_last_weight;
                        Active_Target_Weight := 0.0;
                        Active_Live_Weight := 0.0;
                        GVL.Semi_Auto_Active_Target_Weight := 0.0;
                        GVL.Semi_Auto_Active_Live_Weight := 0.0;
                        Current_Step := j;
                        Inter_Bin_Settling := FALSE;
                    END_IF;
                END_IF;
            END_IF;
        END_IF;

    31:
        IF Semi_Has_Active_Bins THEN
            Active_Material_ID := 0;
            Active_Bin_ID := 0;
            Active_Target_Weight := 0.0;
            Active_Live_Weight := 0.0;
            GVL.Semi_Auto_Active_Target_Weight := 0.0;
            GVL.Semi_Auto_Active_Live_Weight := 0.0;
            Excess_Alarm := FALSE;
            GVL.Semi_Auto_Excess_Alarm := FALSE;
            FOR i := 1 TO 10 DO
                Semi_Auto_Bin[i] := FALSE;
                semi_auto_bin_cutoff[i] := FALSE;
                semi_auto_bin_motor[i] := FALSE;
            END_FOR;
            Status_Message := 'Semi-Auto [Step 31]: Settling Delay in progress...';
            IF Settle_Phase = 0 THEN
                Completion_Timer(IN := FALSE);
                Settle_Phase := 1;
            ELSE
                Completion_Timer(IN := TRUE, PT := Effective_Delay);
                IF Completion_Timer.Q THEN
                    Completion_Timer(IN := FALSE);
                    Settle_Phase := 0;
                    Current_Step := 32;
                END_IF;
            END_IF;
        ELSE
            Current_Step := 32;
        END_IF;
        
    32:
        Active_Material_ID := 0;
        Active_Bin_ID := 0;
        Excess_Alarm := FALSE;
        Sequence_Complete := TRUE;
        GVL.Semi_Auto_Sequence_Complete := TRUE;
        IF NOT GVL.Auto_Sequence_Complete THEN
            Status_Message := 'Semi-Auto [Step 32]: Semi done — waiting for Auto to finish';
        ELSIF (Cycle_Manager_State = 5) OR Between_Cycle_Hold THEN
            Status_Message := 'Semi-Auto [Step 32]: Cycle done — empty BOTH scales then Next_Cycle_Start';
        ELSIF (GVL.Target_Batch_Cycles > 1) AND (GVL.Completed_Batch_Cycles >= 1)
            AND (GVL.Completed_Batch_Cycles < GVL.Target_Batch_Cycles) THEN
            Status_Message := 'Semi-Auto [Step 32]: Both done — waiting State 5 / Next_Cycle_Start';
        ELSIF (GVL.Current_Batch_Cycle >= GVL.Target_Batch_Cycles) AND (GVL.Target_Batch_Cycles > 0) THEN
            Status_Message := 'Semi-Auto [Step 32]: All target batch cycles complete';
        ELSE
            Status_Message := 'Semi-Auto [Step 32]: Cycle sequences complete';
        END_IF;
END_CASE;

Last_Step := Current_Step;

(* Synchronize physical output arrays to GVL *)
FOR i := 1 TO 10 DO
    GVL.Semi_Auto_Bin[i] := Semi_Auto_Bin[i];
    GVL.semi_auto_bin_cutoff[i] := semi_auto_bin_cutoff[i];
    GVL.semi_auto_bin_motor[i] := semi_auto_bin_motor[i];
END_FOR;

(* Synchronize live cycle progress to outputs *)
Semi_Auto_Current_Batch_Cycle := GVL.Current_Batch_Cycle;
Semi_Auto_Completed_Batch_Cycles := GVL.Completed_Batch_Cycles;
Semi_Auto_All_Cycles_Complete := GVL.All_Cycles_Complete;

(* When cycle handshake done, show Step32 not last dosing step on HMI *)
IF Sequence_Complete AND (Current_Step >= 1) AND (Current_Step <= 10) THEN
    Current_Step := 32;
END_IF;
GVL.Semi_Auto_Current_Step := Current_Step;
(* HMI Active Mat/Bin: only while dosing steps 1..10 with valid live mapping *)
(* During inter-bin settle keep Settle_Hold_* for TRUE and FALSE — do not overwrite with next bin *)
IF Inter_Bin_Settling AND (Settle_Hold_Step >= 1) THEN
    Active_Material_ID := Settle_Hold_Mat;
    Active_Bin_ID := Settle_Hold_Step;
    Active_Target_Weight := Settle_Hold_Target;
    actual_bin := load_cell_value - bin_last_weight;
    IF actual_bin < 0.0 THEN
        actual_bin := 0.0;
    END_IF;
    Actual_Weights[Settle_Hold_Step] := actual_bin;
    Active_Live_Weight := actual_bin;
    GVL.Semi_Auto_Current_Step := Settle_Hold_Step;
ELSIF (Current_Step >= 1) AND (Current_Step <= 10) AND (NOT Inter_Bin_Settling) THEN
    Mat_Idx := Semi_Auto_Bin_Material_Mapping[Current_Step];
    target_weight := 0.0;
    IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) THEN
        target_weight := GVL.Recipe_Weights[Mat_Idx];
    END_IF;
    IF (target_weight <= 0.0) AND (PersistentVars.Ret_Semi_Bin_Target_Weights[Current_Step] > 0.0) THEN
        target_weight := PersistentVars.Ret_Semi_Bin_Target_Weights[Current_Step];
        IF (Mat_Idx < 1) OR (Mat_Idx > 20) THEN
            IF PersistentVars.Ret_Semi_Bin_Target_Weights[Current_Step] > 0.0 THEN
                Mat_Idx := PersistentVars.Ret_Semi_Bin_Material_Mapping[Current_Step];
            ELSE
                Mat_Idx := 0;
            END_IF;
        END_IF;
    END_IF;
    IF (Mat_Idx < 1) OR (Mat_Idx > 20) OR (target_weight <= 0.0) THEN
        Active_Material_ID := 0;
        Active_Bin_ID := 0;
        Active_Target_Weight := 0.0;
        Active_Live_Weight := 0.0;
    ELSE
        (* Dosing: keep Actual_Weights in sync with live scale (excess / tailings) *)
        actual_bin := load_cell_value - bin_last_weight;
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
GVL.Semi_Auto_Active_Mat := Active_Material_ID;
GVL.Semi_Auto_Active_Bin := Active_Bin_ID;
GVL.Semi_Auto_Active_Target_Weight := Active_Target_Weight;
GVL.Semi_Auto_Active_Live_Weight := Active_Live_Weight;
(* Mirror Actual_Weights to HMI every scan — dosing, excess, inter-bin tailings *)
Semi_Auto_Sum_ActWeight := 0.0;
FOR i := 1 TO 10 DO
    GVL.Semi_Auto_Weights[i] := Actual_Weights[i];
    Semi_Auto_Sum_ActWeight := Semi_Auto_Sum_ActWeight + Actual_Weights[i];
END_FOR;
GVL.Semi_Auto_Total_Actual_Weight := Semi_Auto_Sum_ActWeight;
(* Per-bin target setpoints — bin index 1..10; mirror to GVL.Semi_Auto_Target_Weights (plant %MD410) *)
(* Do not zero on CMS4 / All_Cycles_Complete (Auto holds recipe targets after last cycle) *)
IF (Cycle_Manager_State = 0) AND (NOT GVL.Run) AND (NOT PersistentVars.Ret_Semi_Process_Was_Active)
    AND (NOT GVL.All_Cycles_Complete) AND (Cycle_Manager_State <> 4) THEN
    FOR i := 1 TO 10 DO
        Semi_Auto_Target_Weight[i] := 0.0;
        GVL.Semi_Auto_Target_Weights[i] := 0.0;
    END_FOR;
ELSE
    FOR i := 1 TO 10 DO
        Mat_Idx := Semi_Auto_Bin_Material_Mapping[i];
        IF (Mat_Idx < 1) OR (Mat_Idx > 20) THEN
            IF PersistentVars.Ret_Semi_Bin_Target_Weights[i] > 0.0 THEN
                Mat_Idx := PersistentVars.Ret_Semi_Bin_Material_Mapping[i];
            ELSE
                Mat_Idx := 0;
            END_IF;
        END_IF;
        target_weight := 0.0;
        IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) THEN
            target_weight := GVL.Recipe_Weights[Mat_Idx];
        END_IF;
        IF (target_weight <= 0.0) AND (PersistentVars.Ret_Semi_Bin_Target_Weights[i] > 0.0) THEN
            target_weight := PersistentVars.Ret_Semi_Bin_Target_Weights[i];
        END_IF;
        Semi_Auto_Target_Weight[i] := target_weight;
        GVL.Semi_Auto_Target_Weights[i] := target_weight;
    END_FOR;
END_IF;
(* Semi snapshot: only clear retain when all cycles finished (CMS4). Never clear on Run=FALSE power loss. *)
IF Cycle_Manager_State = 4 THEN
    PersistentVars.Ret_Semi_Process_Was_Active := FALSE;
    PersistentVars.Ret_Semi_GVL_Run := FALSE;
    PersistentVars.Ret_Semi_Cycle_Manager_State := 0;
    PersistentVars.Ret_Semi_Current_Step := 0;
    PersistentVars.Ret_Semi_Between_Cycle_Hold := FALSE;
    PersistentVars.Ret_Semi_Active_Material_ID := 0;
    PersistentVars.Ret_Semi_Active_Bin_ID := 0;
    PersistentVars.Ret_Semi_Active_Target_Weight := 0.0;
    PersistentVars.Ret_Semi_Active_Live_Weight := 0.0;
    PersistentVars.Ret_Semi_Resume_Step := 0;
ELSIF (GVL.Run OR (Cycle_Manager_State = 1) OR (Cycle_Manager_State = 5) OR Between_Cycle_Hold) AND (Cycle_Manager_State <> 4) THEN
    j := 0;
    FOR i := 1 TO 10 DO
        Mat_Idx := Semi_Auto_Bin_Material_Mapping[i];
        IF (Mat_Idx < 1) OR (Mat_Idx > 20) THEN
            IF PersistentVars.Ret_Semi_Bin_Target_Weights[i] > 0.0 THEN
                Mat_Idx := PersistentVars.Ret_Semi_Bin_Material_Mapping[i];
            ELSE
                Mat_Idx := 0;
            END_IF;
        END_IF;
        target_weight := 0.0;
        IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) THEN
            target_weight := GVL.Recipe_Weights[Mat_Idx];
        END_IF;
        IF (target_weight <= 0.0) AND (PersistentVars.Ret_Semi_Bin_Target_Weights[i] > 0.0) THEN
            target_weight := PersistentVars.Ret_Semi_Bin_Target_Weights[i];
        END_IF;
        IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) AND (target_weight > 0.0) THEN
            IF Actual_Weights[i] < (target_weight - 0.05) THEN
                j := i;
                EXIT;
            END_IF;
        END_IF;
    END_FOR;
    IF (j > 0) AND ((Cycle_Manager_State = 5) OR (Current_Step >= 31) OR Between_Cycle_Hold) THEN
        PersistentVars.Ret_Semi_Process_Was_Active := TRUE;
        PersistentVars.Ret_Semi_Current_Step := j;
        PersistentVars.Ret_Semi_Cycle_Manager_State := 1;
        PersistentVars.Ret_Semi_Between_Cycle_Hold := FALSE;
        PersistentVars.Ret_Semi_Resume_Step := j;
    ELSE
        PersistentVars.Ret_Semi_Process_Was_Active := TRUE;
        PersistentVars.Ret_Semi_Current_Step := Current_Step;
        PersistentVars.Ret_Semi_Cycle_Manager_State := Cycle_Manager_State;
        PersistentVars.Ret_Semi_Between_Cycle_Hold := Between_Cycle_Hold;
        PersistentVars.Ret_Semi_Last_Batch_Cycle := Last_Batch_Cycle;
        IF (Cycle_Manager_State = 1) AND (Current_Step >= 1) AND (Current_Step <= 10) THEN
            PersistentVars.Ret_Semi_Resume_Step := Current_Step;
        ELSIF (Cycle_Manager_State = 5) OR (Cycle_Manager_State = 4) OR (Current_Step >= 31) THEN
            PersistentVars.Ret_Semi_Resume_Step := 0;
        END_IF;
    END_IF;
    PersistentVars.Ret_Semi_bin_last_weight := bin_last_weight;
    PersistentVars.Ret_Semi_GVL_Run := GVL.Run;
    PersistentVars.Ret_Semi_Current_Batch_Cycle := GVL.Current_Batch_Cycle;
    PersistentVars.Ret_Semi_Completed_Batch_Cycles := GVL.Completed_Batch_Cycles;
    PersistentVars.Ret_Semi_Target_Batch_Cycles := GVL.Target_Batch_Cycles;
    PersistentVars.Ret_Semi_Active_Material_ID := Active_Material_ID;
    PersistentVars.Ret_Semi_Active_Bin_ID := Active_Bin_ID;
    PersistentVars.Ret_Semi_Active_Target_Weight := Active_Target_Weight;
    PersistentVars.Ret_Semi_Active_Live_Weight := Active_Live_Weight;
    FOR i := 1 TO 10 DO
        PersistentVars.Ret_Semi_Actual_Weights[i] := Actual_Weights[i];
        Mat_Idx := Semi_Auto_Bin_Material_Mapping[i];
        IF (Mat_Idx < 1) OR (Mat_Idx > 20) THEN
            IF PersistentVars.Ret_Semi_Bin_Target_Weights[i] > 0.0 THEN
                Mat_Idx := PersistentVars.Ret_Semi_Bin_Material_Mapping[i];
            ELSE
                Mat_Idx := 0;
            END_IF;
        END_IF;
        IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) THEN
            PersistentVars.Ret_Semi_Bin_Material_Mapping[i] := Mat_Idx;
            IF GVL.Recipe_Weights[Mat_Idx] > 0.0 THEN
                PersistentVars.Ret_Semi_Bin_Target_Weights[i] := GVL.Recipe_Weights[Mat_Idx];
            END_IF;
        END_IF;
    END_FOR;
END_IF;

(* Drop any tare request if scales not empty (batch still on scale after cycle complete) *)
IF NOT Scale_Empty_OK THEN
    Tare_Pulse_Req := FALSE;
END_IF;

(* TARE PULSE — end of scan (after sequence / Next_Cycle set Tare_Pulse_Req); BOTH scales LT limit *)
IF Tare_Pulse_Req THEN
    IF Scale_Empty_OK THEN
        Tare_Semi_Auto_Batch := TRUE;
        Status_Message := 'Semi-Auto [Tare]: Scales empty - Tare_Semi_Auto_Batch pulse';
    ELSE
        Tare_Semi_Auto_Batch := FALSE;
        Status_Message := CONCAT('Semi-Auto [Tare blocked]: Scale >= ', CONCAT(REAL_TO_STRING(eff_empty_limit), ' kg — dump batch first'));
    END_IF;
    Tare_Pulse_Req := FALSE;
END_IF;

(* Hard interlock: never Tare when live load >= Empty_Weight_Limit (either scale) *)
IF NOT Scale_Empty_OK THEN
    Tare_Semi_Auto_Batch := FALSE;
END_IF;

