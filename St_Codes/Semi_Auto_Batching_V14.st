FUNCTION_BLOCK Semi_Auto_Batching_V14
VAR_INPUT
    Start_Button : BOOL;                                 // Command pulse/signal to start or resume the semi-auto batching sequence
    E_Stop_Active : BOOL;                                // Emergency Stop circuit status (NC contact: TRUE = Healthy/Run permitted, FALSE = E-Stop tripped)
    Reset : BOOL;                                        // System reset pulse (clears active steps, outputs, alarms, and error flags)
    Semi_Auto_Bin_Material_Mapping : ARRAY[1..10] OF INT;// Array mapping physical Silos 1..10 to Recipe Material IDs (1..20, 0 = Silo skipped)
    Semi_Auto_Coarse_To_Fine_Speed : ARRAY[1..10] OF REAL;// Weight offset threshold (kg) before target to transition from Coarse to Fine feeding
    Semi_Auto_Bin_Tolerance : ARRAY[1..10] OF REAL;      // Allowable weight tolerance window (±kg) around target weight for each silo
    Inter_Bin_Delay : TIME;                              // Settling delay duration after completing a bin before advancing to the next
    Excess_Allowed : BOOL;                               // Overfill handling policy: TRUE = proceed if target is exceeded, FALSE = raise alarm and halt
    load_cell_value : REAL;                              // Live gross weight input reading from the Semi-Auto scale load cell (kg)
    Target_Batch_Cycles : INT;                           // Target number of batch cycle repetitions configured from HMI (defaults to 1)
    Next_Cycle_Start : BOOL;                             // Command pulse/signal to start next batch cycle after hoppers are emptied
    Empty_Weight_Limit : REAL;                           // Maximum scale weight limit (kg) for scales to qualify as empty before starting next cycle
END_VAR
VAR_OUTPUT
    Semi_Auto_Bin : ARRAY[1..10] OF BOOL;                // Coarse feeding valve / gate actuation command outputs for Silos 1..10
    semi_auto_bin_cutoff : ARRAY[1..10] OF BOOL;         // Fine feeding valve / vibrator cutoff actuation command outputs for Silos 1..10
    semi_auto_bin_motor : ARRAY[1..10] OF BOOL;          // Feeder / screw conveyor motor run commands for Silos 1..10
    Actual_Weights : ARRAY[1..10] OF REAL;               // Net material weight (kg) successfully dosed for each silo in the current cycle
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
    Excess_Alarm : BOOL;                                 // Overfill alarm: TRUE when dosed weight exceeds target + tolerance (with Excess_Allowed=FALSE)
    Error_Code : INT;                                    // Fault diagnostic code:
                                                         //   0   = No Error / System Healthy
                                                         //   1   = Duplicate Material ID mapped across Auto and Semi-Auto
                                                         //   2   = Material index out of range (must be 1..20)
                                                         //   3   = Recipe weight is less than (Coarse_To_Fine_Speed + Tolerance)
                                                         //   4   = Initial scale tare error (scale not empty before start)
                                                         //   21  = Scale overload protection triggered (> 500 kg)
    Semi_Auto_Current_Batch_Cycle : INT;                 // Active batch cycle number currently processing (1..Target_Batch_Cycles)
    Semi_Auto_Completed_Batch_Cycles : INT;              // Total number of batch cycle loops completed successfully
    Semi_Auto_All_Cycles_Complete : BOOL;                // Master flag: TRUE when all Target_Batch_Cycles have finished
    Status_Message : STRING(80);                         // Real-time human-readable process status and diagnostic text message
END_VAR
VAR
    bin_last_weight : REAL;
    actual_bin : REAL;
    target_weight : REAL;
    cutoff_trigger_weight : REAL;
    min_tol_weight : REAL;
    max_tol_weight : REAL;
    Paused_By_EStop : BOOL;
    Effective_Delay : TIME;
    Mat_Idx : INT;
    i : INT;
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
END_VAR



(* Semi-Auto Batching FB V14 with Full Diagnostics, Step Tracking, and Precise Status Reporting *)

Effective_Delay := Inter_Bin_Delay;
IF Effective_Delay = T#0S THEN
    Effective_Delay := T#2S;
END_IF;

(* Track Master Cycle State *)
IF Target_Batch_Cycles > 0 THEN
    GVL.Target_Batch_Cycles := Target_Batch_Cycles;
END_IF;

(* Master Cycle State & Start Synchronization *)
Run_Rising := GVL.Run AND NOT Run_Last;
Run_Last := GVL.Run;

IF GVL.Run THEN
    IF Sequence_Complete AND GVL.Auto_Sequence_Complete THEN
        IF GVL.Current_Batch_Cycle >= GVL.Target_Batch_Cycles AND GVL.Target_Batch_Cycles > 0 THEN
            Cycle_Manager_State := 4;
        ELSE
            Cycle_Manager_State := 5;
        END_IF;
    ELSE
        Cycle_Manager_State := 1;
    END_IF;
ELSE
    Cycle_Manager_State := 0;
    Current_Step := 0;
    Last_Batch_Cycle := 0;
    Sequence_Complete := FALSE;
    GVL.Semi_Auto_Sequence_Complete := FALSE;
END_IF;

(* On fresh batch start (rising edge of Run), ensure clean start from Step 0 *)
IF Run_Rising THEN
    Current_Step := 0;
    Last_Batch_Cycle := 0;
    Sequence_Complete := FALSE;
    GVL.Semi_Auto_Sequence_Complete := FALSE;
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

(* 2. HARD RESET INTERLOCK *)
IF Reset OR GVL.Reset THEN
    FOR i := 1 TO 10 DO
        Semi_Auto_Bin[i] := FALSE;
        semi_auto_bin_cutoff[i] := FALSE;
        semi_auto_bin_motor[i] := FALSE;
        Actual_Weights[i] := 0.0;
        GVL.Semi_Auto_Bin[i] := FALSE;
        GVL.semi_auto_bin_cutoff[i] := FALSE;
        GVL.semi_auto_bin_motor[i] := FALSE;
        GVL.Semi_Auto_Weights[i] := 0.0;
    END_FOR;
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
    Paused_By_EStop := FALSE;
    Current_Step := 0;
    Last_Batch_Cycle := 0;
    Cycle_Manager_State := 0;
    Semi_Auto_Current_Batch_Cycle := 0;
    Semi_Auto_Completed_Batch_Cycles := 0;
    Semi_Auto_All_Cycles_Complete := FALSE;
    bin_last_weight := 0.0;
    Start_Sim_Weight := 0.0;
    Run_Last := FALSE;
    Run_Rising := FALSE;
    Transition_Timer(IN := FALSE);
    Completion_Timer(IN := FALSE);
    Sim_Timer(IN := FALSE);
    Status_Message := 'Semi-Auto [Reset]: System Reset Complete - System Idle';
    
    (* Clean Auto-Clearing: Reset has been processed by both blocks *)
    GVL.Reset := FALSE;
    RETURN;
END_IF;

(* 3. E-STOP PAUSE / HOLD LOGIC (NC Contact: FALSE = Pressed/Tripped, TRUE = Healthy) *)
IF NOT E_Stop_Active OR NOT GVL.E_Stop_Active THEN
    Paused_By_EStop := TRUE;
END_IF;

IF Paused_By_EStop THEN
    FOR i := 1 TO 10 DO
        Semi_Auto_Bin[i] := FALSE;
        semi_auto_bin_cutoff[i] := FALSE;
        semi_auto_bin_motor[i] := FALSE;
    END_FOR;
    IF NOT E_Stop_Active OR NOT GVL.E_Stop_Active THEN
        Status_Message := CONCAT('Semi-Auto [PAUSED]: E-Stop Active at Step ', INT_TO_STRING(Current_Step));
    ELSE
        Status_Message := CONCAT('Semi-Auto [HOLD]: E-Stop Cleared. Press Start to Resume Step ', INT_TO_STRING(Current_Step));
        IF Start_Button OR GVL.Start_Button THEN
            Paused_By_EStop := FALSE;
        END_IF;
    END_IF;
    Sim_Timer(IN := FALSE);
    Transition_Timer(IN := FALSE);
    Completion_Timer(IN := FALSE);
    RETURN;
END_IF;

(* 4. CYCLE COMPLETE / HOLD STATE *)
IF Cycle_Manager_State = 5 THEN
    Status_Message := 'Semi-Auto [Cycle Complete]: Waiting for scale empty & Next_Cycle_Start...';
END_IF;

(* 5. SEQUENCE START (FOR CYCLE 1 AND REPEAT CYCLES) *)
IF GVL.Run AND Cycle_Manager_State <> 5 THEN
    IF Current_Step = 0 THEN
        (* Initial cycle start *)
        Last_Batch_Cycle := GVL.Current_Batch_Cycle;
        Current_Step := 1;
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
    ELSIF Current_Step = 32 AND GVL.Current_Batch_Cycle <> Last_Batch_Cycle THEN
        (* Advance to next cycle loop (Cycle 2, 3, etc.) *)
        Last_Batch_Cycle := GVL.Current_Batch_Cycle;
        Current_Step := 1;
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
        (* Skip any bin where Material Mapping is 0, > 20, or Recipe Weight is 0 *)
        WHILE Current_Step >= 1 AND Current_Step <= 10 DO
            Mat_Idx := Semi_Auto_Bin_Material_Mapping[Current_Step];
            IF Mat_Idx = 0 OR Mat_Idx > 20 OR GVL.Recipe_Weights[Mat_Idx] <= 0.0 THEN
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
                EXIT; (* Valid active recipe silo found *)
            END_IF;
        END_WHILE;
        
        IF Current_Step = 31 THEN
            Active_Material_ID := 0;
            Active_Bin_ID := 0;
            Active_Target_Weight := 0.0;
            Active_Live_Weight := 0.0;
            GVL.Semi_Auto_Active_Target_Weight := 0.0;
            GVL.Semi_Auto_Active_Live_Weight := 0.0;
            Status_Message := 'Semi-Auto [Step 31]: Settling Delay in progress...';
            Completion_Timer(IN := TRUE, PT := Effective_Delay);
            IF Completion_Timer.Q THEN
                Completion_Timer(IN := FALSE);
                Current_Step := 32;
            END_IF;
        ELSE
            Mat_Idx := Semi_Auto_Bin_Material_Mapping[Current_Step];
            target_weight := GVL.Recipe_Weights[Mat_Idx];
            
            Active_Target_Weight := target_weight;
            GVL.Semi_Auto_Active_Target_Weight := target_weight;
            
            cutoff_trigger_weight := target_weight - Semi_Auto_Coarse_To_Fine_Speed[Current_Step];
            min_tol_weight := target_weight - Semi_Auto_Bin_Tolerance[Current_Step];
            max_tol_weight := target_weight + Semi_Auto_Bin_Tolerance[Current_Step];
            
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
                Paused_By_EStop := TRUE;
            END_IF;
            
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
                    Status_Message := CONCAT('Semi-Auto [Step ', CONCAT(INT_TO_STRING(Current_Step), ']: Excess Allowed - Advancing'));
                    bin_last_weight := load_cell_value;
                    Active_Target_Weight := 0.0;
                    Active_Live_Weight := 0.0;
                    GVL.Semi_Auto_Active_Target_Weight := 0.0;
                    GVL.Semi_Auto_Active_Live_Weight := 0.0;
                    IF Current_Step = 10 THEN
                        Current_Step := 31;
                    ELSE
                        Current_Step := Current_Step + 1;
                    END_IF;
                ELSE
                    Excess_Alarm := TRUE;
                    Status_Message := CONCAT('Semi-Auto [Step ', CONCAT(INT_TO_STRING(Current_Step), ']: STUCK - Excess Weight! Reduce weight or enable Excess Allowed.'));
                END_IF;
            ELSE
                Semi_Auto_Bin[Current_Step] := FALSE;
                semi_auto_bin_cutoff[Current_Step] := FALSE;
                semi_auto_bin_motor[Current_Step] := FALSE;
                Excess_Alarm := FALSE;
                bin_last_weight := load_cell_value;
                Active_Target_Weight := 0.0;
                Active_Live_Weight := 0.0;
                GVL.Semi_Auto_Active_Target_Weight := 0.0;
                GVL.Semi_Auto_Active_Live_Weight := 0.0;
                Status_Message := CONCAT('Semi-Auto [Step ', CONCAT(INT_TO_STRING(Current_Step), ']: Target Reached - Advancing'));
                IF Current_Step = 10 THEN
                    Current_Step := 31;
                ELSE
                    Current_Step := Current_Step + 1;
                END_IF;
            END_IF;
        END_IF;

    31:
        Active_Material_ID := 0;
        Active_Bin_ID := 0;
        Excess_Alarm := FALSE;
        Status_Message := 'Semi-Auto [Step 31]: Settling Delay in progress...';
        Completion_Timer(IN := TRUE, PT := Effective_Delay);
        IF Completion_Timer.Q THEN
            Completion_Timer(IN := FALSE);
            Current_Step := 32;
        END_IF;
        
    32:
        Active_Material_ID := 0;
        Active_Bin_ID := 0;
        Excess_Alarm := FALSE;
        Sequence_Complete := TRUE;
        GVL.Semi_Auto_Sequence_Complete := TRUE;
        IF NOT GVL.Auto_Sequence_Complete THEN
            Status_Message := 'Semi-Auto [Step 32]: Semi-Auto Finished. Waiting for Auto to complete...';
        ELSE
            Status_Message := 'Semi-Auto [Step 32]: Cycle Sequences Complete';
        END_IF;
END_CASE;

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
