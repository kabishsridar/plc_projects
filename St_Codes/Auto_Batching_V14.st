FUNCTION_BLOCK Auto_Batching_V14
VAR_INPUT
    Start_Button : BOOL;                            // Command pulse/signal to start or resume the auto batching sequence
    E_Stop_Active : BOOL;                           // Emergency Stop circuit status (NC contact: TRUE = Healthy/Run permitted, FALSE = E-Stop tripped)
    Reset : BOOL;                                   // System reset pulse (clears active steps, outputs, alarms, and error flags)
    Auto_Bin_Material_Mapping : ARRAY[1..6] OF INT; // Array mapping physical Silos 1..6 to Recipe Material IDs (1..20, 0 = Silo skipped)
    Auto_Coarse_To_Fine_Speed : ARRAY[1..6] OF REAL;// Weight offset threshold (kg) before target to transition from Coarse to Fine feeding
    Auto_Bin_Tolerance : ARRAY[1..6] OF REAL;       // Allowable weight tolerance window (±kg) around target weight for each silo
    Inter_Bin_Delay : TIME;                         // Settling delay duration after completing a bin before advancing to the next
    Excess_Allowed : BOOL;                          // Overfill handling policy: TRUE = proceed if target is exceeded, FALSE = raise alarm and halt
    load_cell_value : REAL;                         // Live gross weight input reading from the Auto scale load cell (kg)
    Target_Batch_Cycles : INT;                      // Target number of batch cycle repetitions configured from HMI (defaults to 1)
    Next_Cycle_Start : BOOL;                        // Command pulse/signal to start next batch cycle after hoppers are emptied
    Empty_Weight_Limit : REAL;                      // Maximum scale weight limit (kg) for scales to qualify as empty before starting next cycle
END_VAR
VAR_OUTPUT
    Auto_Bin : ARRAY[1..6] OF BOOL;                 // Coarse feeding valve / gate actuation command outputs for Silos 1..6
    auto_bin_cutoff : ARRAY[1..6] OF BOOL;          // Fine feeding valve / vibrator cutoff actuation command outputs for Silos 1..6
    auto_bin_motor : ARRAY[1..6] OF BOOL;           // Feeder / screw conveyor motor run commands for Silos 1..6
    Actual_Weights : ARRAY[1..6] OF REAL;           // Net material weight (kg) successfully dosed for each silo in the current cycle
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
                                                    //   21 = Scale overload protection triggered (> 500 kg)
    Auto_Current_Batch_Cycle : INT;                     // Active batch cycle number currently processing (1..Target_Batch_Cycles)
    Auto_Completed_Batch_Cycles : INT;                  // Total number of batch cycle loops completed successfully
    Auto_All_Cycles_Complete : BOOL;                    // Master flag: TRUE when all Target_Batch_Cycles have finished
    Status_Message : STRING(80);                    // Real-time human-readable process status and diagnostic text message
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
    Next_Cycle_Last : BOOL;
    Next_Cycle_Rising : BOOL;
END_VAR



(* Auto Batching FB V14 with Full Diagnostics, Step Tracking, and Precise Status Reporting *)

Effective_Delay := Inter_Bin_Delay;
IF Effective_Delay = T#0S THEN
    Effective_Delay := T#2S;
END_IF;

(* Detect rising edge on Next_Cycle_Start trigger *)
Next_Cycle_Rising := (Next_Cycle_Start OR GVL.Next_Cycle_Start) AND NOT Next_Cycle_Last;
Next_Cycle_Last := (Next_Cycle_Start OR GVL.Next_Cycle_Start);

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
IF Reset OR GVL.Reset THEN
    FOR i := 1 TO 6 DO
        Auto_Bin[i] := FALSE;
        auto_bin_cutoff[i] := FALSE;
        auto_bin_motor[i] := FALSE;
        Actual_Weights[i] := 0.0;
        GVL.Auto_Bin[i] := FALSE;
        GVL.auto_bin_cutoff[i] := FALSE;
        GVL.auto_bin_motor[i] := FALSE;
        GVL.Auto_Weights[i] := 0.0;
    END_FOR;
    
    (* Reset Recipe & Active Target Setpoints *)
    FOR i := 1 TO 20 DO
        GVL.Recipe_Weights[i] := 0.0;
    END_FOR;
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
    bin_last_weight := 0.0;
    Start_Sim_Weight := 0.0;
    Transition_Timer(IN := FALSE);
    Completion_Timer(IN := FALSE);
    Sim_Timer(IN := FALSE);
    Status_Message := 'Auto [Reset]: System Reset Complete - System Idle';
    RETURN;
END_IF;

(* 3. E-STOP PAUSE / HOLD LOGIC (NC Contact: FALSE = Pressed/Tripped, TRUE = Healthy) *)
IF NOT E_Stop_Active OR NOT GVL.E_Stop_Active THEN
    Paused_By_EStop := TRUE;
END_IF;

IF Paused_By_EStop THEN
    FOR i := 1 TO 6 DO
        Auto_Bin[i] := FALSE;
        auto_bin_cutoff[i] := FALSE;
        auto_bin_motor[i] := FALSE;
    END_FOR;
    IF NOT E_Stop_Active OR NOT GVL.E_Stop_Active THEN
        Status_Message := CONCAT('Auto [PAUSED]: E-Stop Active at Step ', INT_TO_STRING(Current_Step));
    ELSE
        Status_Message := CONCAT('Auto [HOLD]: E-Stop Cleared. Press Start to Resume Step ', INT_TO_STRING(Current_Step));
        IF Start_Button OR GVL.Start_Button THEN
            Paused_By_EStop := FALSE;
        END_IF;
    END_IF;
    Sim_Timer(IN := FALSE);
    Transition_Timer(IN := FALSE);
    Completion_Timer(IN := FALSE);
    RETURN;
END_IF;

(* 4. MASTER CYCLE MANAGER STATE MACHINE *)
CASE Cycle_Manager_State OF
    0: (* IDLE *)
        Internal_FB_Start := FALSE;
        GVL.Run := FALSE;
        GVL.Next_Cycle_Start := FALSE;
        GVL.Auto_Sequence_Complete := FALSE;
        
        IF GVL.Error_Code = 0 AND NOT (Start_Button OR GVL.Start_Button) THEN
            Status_Message := 'Auto [State 0 - Idle]: Ready - Waiting for Start Button';
        END_IF;
        
        IF Start_Button OR GVL.Start_Button THEN
            (* Use Target_Batch_Cycles from input, or fallback to GVL, or default to 1 *)
            IF Target_Batch_Cycles > 0 THEN
                GVL.Target_Batch_Cycles := Target_Batch_Cycles;
            ELSIF GVL.Target_Batch_Cycles <= 0 THEN
                GVL.Target_Batch_Cycles := 1;
            END_IF;
            
            IF NOT E_Stop_Active OR NOT GVL.E_Stop_Active THEN
                GVL.Run := FALSE;
                Status_Message := 'Auto [State 0]: Cannot Start - Emergency Stop Contact Open!';
            ELSIF (GVL.Auto_Initial_Tolerance > 0.0 AND (GVL.load_cell_auto > GVL.Auto_Initial_Tolerance OR GVL.load_cell_auto < (-GVL.Auto_Initial_Tolerance))) OR 
                  (GVL.Semi_Auto_Initial_Tolerance > 0.0 AND (GVL.load_cell_semi_auto > GVL.Semi_Auto_Initial_Tolerance OR GVL.load_cell_semi_auto < (-GVL.Semi_Auto_Initial_Tolerance))) THEN
                GVL.Run := FALSE;
                GVL.Error_Code := 4;
                Error_Code := 4;
                Status_Message := 'Auto [State 0]: Error 4 - Scale not zeroed (exceeds Initial Tolerance)!';
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
                Sequence_Complete := FALSE;
                GVL.Auto_Sequence_Complete := FALSE;
                GVL.Semi_Auto_Sequence_Complete := FALSE;
                Cycle_Manager_State := 1;
                Current_Step := 0;
            END_IF;
        END_IF;
        
    1: (* RUNNING CYCLE *)
        Internal_FB_Start := TRUE;
        GVL.Run := TRUE;
        
        (* Interlock: While process is actively running, Next_Cycle_Start MUST be FALSE *)
        GVL.Next_Cycle_Start := FALSE;
        
        (* Both Auto and Semi-Auto must complete to finish the cycle *)
        IF Sequence_Complete AND GVL.Semi_Auto_Sequence_Complete THEN
            GVL.Completed_Batch_Cycles := GVL.Current_Batch_Cycle;
            Auto_Completed_Batch_Cycles := GVL.Current_Batch_Cycle;
            IF GVL.Current_Batch_Cycle < GVL.Target_Batch_Cycles AND GVL.Error_Code = 0 THEN
                Internal_FB_Start := FALSE;
                Cycle_Manager_State := 5; (* Go to pause/hold to wait for scale empty & Next_Cycle_Start *)
            ELSE
                Cycle_Manager_State := 4; (* All target cycles completed *)
            END_IF;
        END_IF;
        
    5: (* PAUSED BETWEEN CYCLES - WAITING FOR HOPPERS EMPTIED & NEXT CYCLE START *)
        Internal_FB_Start := FALSE;
        GVL.Run := TRUE;
        
        (* Determine effective empty weight threshold (defaults to 5.0 kg if <= 0.0) *)
        eff_empty_limit := Empty_Weight_Limit;
        IF eff_empty_limit <= 0.0 THEN
            eff_empty_limit := GVL.Empty_Weight_Limit;
        END_IF;
        IF eff_empty_limit <= 0.0 THEN
            eff_empty_limit := 5.0;
        END_IF;
        
        Status_Message := CONCAT('Auto [State 5]: Cycle ', CONCAT(INT_TO_STRING(GVL.Current_Batch_Cycle), ' Done. Empty scales < limit and trigger Next_Cycle_Start.'));
        
        (* Check ONLY on a new trigger pulse (rising edge) of Next_Cycle_Start *)
        IF Next_Cycle_Rising THEN
            (* Check both scales are below the empty weight limit at the moment of trigger *)
            IF (GVL.load_cell_auto < eff_empty_limit) AND (GVL.load_cell_semi_auto < eff_empty_limit) THEN
                (* Scale is empty: momentary reset of command, advance to next cycle *)
                GVL.Next_Cycle_Start := FALSE;
                Next_Cycle_Last := FALSE;
                GVL.Start_Button := TRUE; (* Keep Start_Button TRUE until all cycles are complete! *)
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
                FOR i := 1 TO 6 DO
                    Actual_Weights[i] := 0.0;
                    Auto_Bin[i] := FALSE;
                    auto_bin_cutoff[i] := FALSE;
                    auto_bin_motor[i] := FALSE;
                END_FOR;
            ELSE
                (* Scale not empty yet: reject trigger, reset command, and wait for operator to trigger again *)
                GVL.Next_Cycle_Start := FALSE;
                Next_Cycle_Last := FALSE;
                Status_Message := CONCAT('Auto [State 5]: Scale weight exceeds limit (', CONCAT(REAL_TO_STRING(eff_empty_limit), ' kg)! Empty scales and trigger Next_Cycle_Start again.'));
            END_IF;
        END_IF;
        
    4: (* ALL CYCLES COMPLETE *)
        Internal_FB_Start := FALSE;
        GVL.Run := FALSE;
        GVL.Start_Button := FALSE;
        Auto_All_Cycles_Complete := TRUE;
        GVL.All_Cycles_Complete := TRUE;
        Sequence_Complete := TRUE;
        GVL.Auto_Sequence_Complete := TRUE;
        GVL.Semi_Auto_Sequence_Complete := TRUE;
        Status_Message := CONCAT('Auto [State 4 - Finished]: All ', CONCAT(INT_TO_STRING(GVL.Target_Batch_Cycles), ' Batch Cycles Completed Successfully'));
        IF Start_Button OR GVL.Start_Button THEN
            (* Reset flags for new batch start *)
            Current_Step := 0;
            Auto_All_Cycles_Complete := FALSE;
            GVL.All_Cycles_Complete := FALSE;
            Sequence_Complete := FALSE;
            GVL.Auto_Sequence_Complete := FALSE;
            GVL.Semi_Auto_Sequence_Complete := FALSE;
            Cycle_Manager_State := 0;
        END_IF;
END_CASE;

(* 5. AUTO SILOS 1..6 POURING SEQUENCE WITH DETAILED STATUS *)
IF Current_Step = 0 AND Internal_FB_Start THEN
    Current_Step := 1;
    bin_last_weight := load_cell_value;
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
        (* Skip any bin where Material Mapping is 0, > 20, or Recipe Weight is 0 *)
        WHILE Current_Step >= 1 AND Current_Step <= 6 DO
            Mat_Idx := Auto_Bin_Material_Mapping[Current_Step];
            IF Mat_Idx = 0 OR Mat_Idx > 20 OR GVL.Recipe_Weights[Mat_Idx] <= 0.0 THEN
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
                EXIT; (* Valid active recipe silo found *)
            END_IF;
        END_WHILE;
        
        IF Current_Step = 7 THEN
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
            Mat_Idx := Auto_Bin_Material_Mapping[Current_Step];
            target_weight := GVL.Recipe_Weights[Mat_Idx];
            
            Active_Target_Weight := target_weight;
            GVL.Auto_Active_Target_Weight := target_weight;
            
            cutoff_trigger_weight := target_weight - Auto_Coarse_To_Fine_Speed[Current_Step];
            min_tol_weight := target_weight - Auto_Bin_Tolerance[Current_Step];
            max_tol_weight := target_weight + Auto_Bin_Tolerance[Current_Step];
            
            actual_bin := load_cell_value - bin_last_weight;
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
                Paused_By_EStop := TRUE;
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
                    bin_last_weight := load_cell_value;
                    Active_Target_Weight := 0.0;
                    Active_Live_Weight := 0.0;
                    GVL.Auto_Active_Target_Weight := 0.0;
                    GVL.Auto_Active_Live_Weight := 0.0;
                    IF Current_Step = 6 THEN
                        Current_Step := 7;
                    ELSE
                        Current_Step := Current_Step + 1;
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
                bin_last_weight := load_cell_value;
                Active_Target_Weight := 0.0;
                Active_Live_Weight := 0.0;
                GVL.Auto_Active_Target_Weight := 0.0;
                GVL.Auto_Active_Live_Weight := 0.0;
                Status_Message := CONCAT('Auto [Step ', CONCAT(INT_TO_STRING(Current_Step), ']: Target Reached - Advancing'));
                IF Current_Step = 6 THEN
                    Current_Step := 7;
                ELSE
                    Current_Step := Current_Step + 1;
                END_IF;
            END_IF;
        END_IF;

    7:
        Active_Material_ID := 0;
        Active_Bin_ID := 0;
        Excess_Alarm := FALSE;
        Status_Message := 'Auto [Step 7]: Settling Delay in progress...';
        Completion_Timer(IN := TRUE, PT := Effective_Delay);
        IF Completion_Timer.Q THEN
            Completion_Timer(IN := FALSE);
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
