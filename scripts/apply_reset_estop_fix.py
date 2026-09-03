import sys
import os

project_path = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\Rasi_feeds_batching.project"
log_path = r"C:\Users\kabish\.gemini\antigravity-ide\brain\6bb09710-7f3e-4443-b187-ad04e16ca8dc\scratch\apply_reset_estop_log.txt"

# 1. Auto_Batching_V13 Implementation with NC E-Stop & Step 0 Zeroing
st_code_auto_v13 = """(* Auto Batching FB V13 with Real-Time Instant Excess Verification & NC E-Stop Logic *)

Effective_Delay := Inter_Bin_Delay;
IF Effective_Delay = T#0S THEN
    Effective_Delay := T#2S;
END_IF;

(* 1. HARD RESET INTERLOCK *)
IF Reset THEN
    FOR i := 1 TO 6 DO
        Auto_Bin[i] := FALSE;
        auto_bin_cutoff[i] := FALSE;
        auto_bin_motor[i] := FALSE;
        Actual_Weights[i] := 0.0;
    END_FOR;
    Sequence_Complete := FALSE;
    Active_Material_ID := 0;
    Active_Bin_ID := 0;
    Active_Target_Weight := 0.0;
    Active_Live_Weight := 0.0;
    Excess_Alarm := FALSE;
    Error_Code := 0;
    Status_Message := '';
    Paused_By_EStop := FALSE;
    Step := 0;
    
    bin_last_weight := 0.0;
    Start_Sim_Weight := 0.0;
    
    Transition_Timer(IN := FALSE);
    Completion_Timer(IN := FALSE);
    Sim_Timer(IN := FALSE);
    RETURN;
END_IF;

(* 2. E-STOP PAUSE / HOLD LOGIC (NC Contact: FALSE = Pressed/Tripped, TRUE = Healthy) *)
IF NOT E_Stop_Active THEN
    Paused_By_EStop := TRUE;
END_IF;

IF Paused_By_EStop THEN
    FOR i := 1 TO 6 DO
        Auto_Bin[i] := FALSE;
        auto_bin_cutoff[i] := FALSE;
        auto_bin_motor[i] := FALSE;
    END_FOR;
    
    IF NOT E_Stop_Active THEN
        Status_Message := 'Auto Paused: Emergency Stop Active!';
    ELSE
        Status_Message := 'Auto Paused: Press Start to Resume';
        IF Start_Button THEN
            Paused_By_EStop := FALSE;
        END_IF;
    END_IF;
    
    Sim_Timer(IN := FALSE);
    Transition_Timer(IN := FALSE);
    Completion_Timer(IN := FALSE);
    RETURN;
END_IF;

(* 3. SIMULATION WEIGHT MANAGEMENT (WHEN ENABLED) *)
IF Simulation_Mode THEN
    IF Step = 0 AND NOT Start_Button AND NOT Sequence_Complete THEN
        load_cell_value := 0.0;
        bin_last_weight := 0.0;
        Start_Sim_Weight := 0.0;
        Sim_Timer(IN := FALSE);
    END_IF;
    
    Discharge_Active := FALSE;
    IF Step >= 1 AND Step <= 6 THEN
        Discharge_Active := auto_bin_motor[Step];
    END_IF;
    
    IF Discharge_Active THEN
        Sim_Timer(IN := TRUE, PT := T#1000S);
        load_cell_value := Start_Sim_Weight + (TIME_TO_REAL(Sim_Timer.ET) / 1000.0) * Sim_Rate;
    ELSE
        Sim_Timer(IN := FALSE);
        Start_Sim_Weight := load_cell_value;
    END_IF;
END_IF;

(* 4. RECIPE SEQUENCE START & CYCLIC RESET *)
IF Step = 0 AND Start_Button THEN
    Step := 1;
    bin_last_weight := load_cell_value;
    Sequence_Complete := FALSE;
    Excess_Alarm := FALSE;
    Error_Code := 0;
    Status_Message := 'Auto Pour Started';
    Active_Target_Weight := 0.0;
    Active_Live_Weight := 0.0;
    FOR i := 1 TO 6 DO
        Actual_Weights[i] := 0.0;
        Auto_Bin[i] := FALSE;
        auto_bin_cutoff[i] := FALSE;
        auto_bin_motor[i] := FALSE;
    END_FOR;
END_IF;

(* 5. SEQUENCE CONTROL STATE MACHINE *)
CASE Step OF
    0:
        Active_Material_ID := 0;
        Active_Bin_ID := 0;
        Active_Target_Weight := 0.0;
        Active_Live_Weight := 0.0;
        Excess_Alarm := FALSE;
        Sequence_Complete := FALSE;
        FOR i := 1 TO 6 DO
            Auto_Bin[i] := FALSE;
            auto_bin_cutoff[i] := FALSE;
            auto_bin_motor[i] := FALSE;
        END_FOR;
        IF Error_Code = 0 THEN Status_Message := 'Auto Idle'; END_IF;
        
    1..6: (* DISCHARGE SILOS 1 TO 6 *)
        Mat_Idx := Auto_Bin_Material_Mapping[Step];
        
        IF Mat_Idx = 0 OR (Mat_Idx <= 20 AND GVL.Recipe_Weights[Mat_Idx] = 0.0) THEN
            IF Step = 6 THEN
                Step := 7;
            ELSE
                Step := Step + 1;
            END_IF;
        ELSE
            target_weight := GVL.Recipe_Weights[Mat_Idx];
            cutoff_trigger_weight := target_weight - Auto_Bin_Cutoff_Weights[Step];
            min_tol_weight := target_weight - Auto_Bin_Tolerance[Step];
            max_tol_weight := target_weight + Auto_Bin_Tolerance[Step];
            
            Active_Target_Weight := target_weight;
            actual_bin := load_cell_value - bin_last_weight;
            Actual_Weights[Step] := actual_bin;
            Active_Live_Weight := actual_bin;
            
            Active_Material_ID := Mat_Idx;
            Active_Bin_ID := Step;
            
            IF load_cell_value > 500.0 THEN
                Error_Code := 21;
                Status_Message := 'Error 21: Scale Overloaded!';
                Sequence_Complete := TRUE;
                Paused_By_EStop := TRUE;
            END_IF;
            
            IF actual_bin < cutoff_trigger_weight THEN
                Auto_Bin[Step] := TRUE;
                auto_bin_cutoff[Step] := FALSE;
                auto_bin_motor[Step] := TRUE;
                Excess_Alarm := FALSE;
                Status_Message := 'Auto Pouring (Coarse Feed)';
                
            ELSIF actual_bin < min_tol_weight THEN
                Auto_Bin[Step] := FALSE;
                auto_bin_cutoff[Step] := TRUE;
                auto_bin_motor[Step] := TRUE;
                Excess_Alarm := FALSE;
                Status_Message := 'Auto Pouring (Fine Feed)';
                
            ELSIF actual_bin > max_tol_weight THEN
                Auto_Bin[Step] := FALSE;
                auto_bin_cutoff[Step] := FALSE;
                auto_bin_motor[Step] := FALSE;
                
                IF Excess_Allowed THEN
                    Excess_Alarm := FALSE;
                    Status_Message := 'Excess Weight Allowed: Advancing';
                    bin_last_weight := load_cell_value;
                    Active_Target_Weight := 0.0;
                    Active_Live_Weight := 0.0;
                    IF Step = 6 THEN
                        Step := 7;
                    ELSE
                        Step := Step + 1;
                    END_IF;
                ELSE
                    Excess_Alarm := TRUE;
                    Status_Message := 'Excess Alarm: Weight above max tolerance! Reduce weight.';
                END_IF;
                
            ELSE
                Auto_Bin[Step] := FALSE;
                auto_bin_cutoff[Step] := FALSE;
                auto_bin_motor[Step] := FALSE;
                Excess_Alarm := FALSE;
                bin_last_weight := load_cell_value;
                Active_Target_Weight := 0.0;
                Active_Live_Weight := 0.0;
                
                IF Step = 6 THEN
                    Step := 7;
                ELSE
                    Step := Step + 1;
                END_IF;
            END_IF;
        END_IF;

    7:
        Active_Material_ID := 0;
        Active_Bin_ID := 0;
        Active_Target_Weight := 0.0;
        Active_Live_Weight := 0.0;
        Excess_Alarm := FALSE;
        Status_Message := 'Final Settling Delay';
        Completion_Timer(IN := TRUE, PT := Effective_Delay);
        IF Completion_Timer.Q THEN
            Completion_Timer(IN := FALSE);
            Step := 8;
        END_IF;
        
    8:
        Active_Material_ID := 0;
        Active_Bin_ID := 0;
        Active_Target_Weight := 0.0;
        Active_Live_Weight := 0.0;
        Excess_Alarm := FALSE;
        Status_Message := 'Sequence Completed';
        Sequence_Complete := TRUE;
        
        IF NOT Start_Button THEN
            Step := 0;
            Sequence_Complete := FALSE;
            FOR i := 1 TO 6 DO
                Actual_Weights[i] := 0.0;
            END_FOR;
        END_IF;
END_CASE;
"""

# 2. Semi_Auto_Batching_V13 Implementation with NC E-Stop & Step 0 Zeroing
st_code_semi_v13 = """(* Semi-Auto Batching FB V13 with Real-Time Instant Excess Verification & NC E-Stop Logic *)

Effective_Delay := Inter_Bin_Delay;
IF Effective_Delay = T#0S THEN
    Effective_Delay := T#2S;
END_IF;

(* 1. HARD RESET INTERLOCK *)
IF Reset THEN
    FOR i := 1 TO 10 DO
        Semi_Auto_Bin[i] := FALSE;
        semi_auto_bin_cutoff[i] := FALSE;
        semi_auto_bin_motor[i] := FALSE;
        Actual_Weights[i] := 0.0;
    END_FOR;
    Sequence_Complete := FALSE;
    Active_Material_ID := 0;
    Active_Bin_ID := 0;
    Active_Target_Weight := 0.0;
    Active_Live_Weight := 0.0;
    Excess_Alarm := FALSE;
    Error_Code := 0;
    Status_Message := '';
    Paused_By_EStop := FALSE;
    Step := 0;
    
    bin_last_weight := 0.0;
    Start_Sim_Weight := 0.0;
    
    Transition_Timer(IN := FALSE);
    Completion_Timer(IN := FALSE);
    Sim_Timer(IN := FALSE);
    RETURN;
END_IF;

(* 2. E-STOP PAUSE / HOLD LOGIC (NC Contact: FALSE = Pressed/Tripped, TRUE = Healthy) *)
IF NOT E_Stop_Active THEN
    Paused_By_EStop := TRUE;
END_IF;

IF Paused_By_EStop THEN
    FOR i := 1 TO 10 DO
        Semi_Auto_Bin[i] := FALSE;
        semi_auto_bin_cutoff[i] := FALSE;
        semi_auto_bin_motor[i] := FALSE;
    END_FOR;
    
    IF NOT E_Stop_Active THEN
        Status_Message := 'Semi-Auto Paused: Emergency Stop Active!';
    ELSE
        Status_Message := 'Semi-Auto Paused: Press Start to Resume';
        IF Start_Button THEN
            Paused_By_EStop := FALSE;
        END_IF;
    END_IF;
    
    Sim_Timer(IN := FALSE);
    Transition_Timer(IN := FALSE);
    Completion_Timer(IN := FALSE);
    RETURN;
END_IF;

(* 3. SIMULATION WEIGHT MANAGEMENT (WHEN ENABLED) *)
IF Simulation_Mode THEN
    IF Step = 0 AND NOT Start_Button AND NOT Sequence_Complete THEN
        load_cell_value := 0.0;
        bin_last_weight := 0.0;
        Start_Sim_Weight := 0.0;
        Sim_Timer(IN := FALSE);
    END_IF;
    
    Discharge_Active := FALSE;
    IF Step >= 1 AND Step <= 10 THEN
        Discharge_Active := semi_auto_bin_motor[Step];
    END_IF;
    
    IF Discharge_Active THEN
        Sim_Timer(IN := TRUE, PT := T#1000S);
        load_cell_value := Start_Sim_Weight + (TIME_TO_REAL(Sim_Timer.ET) / 1000.0) * Sim_Rate;
    ELSE
        Sim_Timer(IN := FALSE);
        Start_Sim_Weight := load_cell_value;
    END_IF;
END_IF;

(* 4. RECIPE SEQUENCE START & CYCLIC RESET *)
IF Step = 0 AND Start_Button THEN
    Step := 1;
    bin_last_weight := load_cell_value;
    Sequence_Complete := FALSE;
    Excess_Alarm := FALSE;
    Error_Code := 0;
    Status_Message := 'Semi-Auto Pour Started';
    Active_Target_Weight := 0.0;
    Active_Live_Weight := 0.0;
    FOR i := 1 TO 10 DO
        Actual_Weights[i] := 0.0;
        Semi_Auto_Bin[i] := FALSE;
        semi_auto_bin_cutoff[i] := FALSE;
        semi_auto_bin_motor[i] := FALSE;
    END_FOR;
END_IF;

(* 5. SEQUENCE CONTROL STATE MACHINE *)
CASE Step OF
    0:
        Active_Material_ID := 0;
        Active_Bin_ID := 0;
        Active_Target_Weight := 0.0;
        Active_Live_Weight := 0.0;
        Excess_Alarm := FALSE;
        Sequence_Complete := FALSE;
        FOR i := 1 TO 10 DO
            Semi_Auto_Bin[i] := FALSE;
            semi_auto_bin_cutoff[i] := FALSE;
            semi_auto_bin_motor[i] := FALSE;
        END_FOR;
        IF Error_Code = 0 THEN Status_Message := 'Semi-Auto Idle'; END_IF;
        
    1..10: (* DISCHARGE SILOS 1 TO 10 *)
        Mat_Idx := Semi_Auto_Bin_Material_Mapping[Step];
        
        IF Mat_Idx = 0 OR (Mat_Idx <= 20 AND GVL.Recipe_Weights[Mat_Idx] = 0.0) THEN
            IF Step = 10 THEN
                Step := 31;
            ELSE
                Step := Step + 1;
            END_IF;
        ELSE
            target_weight := GVL.Recipe_Weights[Mat_Idx];
            cutoff_trigger_weight := target_weight - Semi_Auto_Bin_Cutoff_Weights[Step];
            min_tol_weight := target_weight - Semi_Auto_Bin_Tolerance[Step];
            max_tol_weight := target_weight + Semi_Auto_Bin_Tolerance[Step];
            
            Active_Target_Weight := target_weight;
            actual_bin := load_cell_value - bin_last_weight;
            Actual_Weights[Step] := actual_bin;
            Active_Live_Weight := actual_bin;
            
            Active_Material_ID := Mat_Idx;
            Active_Bin_ID := Step;
            
            IF load_cell_value > 500.0 THEN
                Error_Code := 21;
                Status_Message := 'Error 21: Scale Overloaded!';
                Sequence_Complete := TRUE;
                Paused_By_EStop := TRUE;
            END_IF;
            
            IF actual_bin < cutoff_trigger_weight THEN
                Semi_Auto_Bin[Step] := TRUE;
                semi_auto_bin_cutoff[Step] := FALSE;
                semi_auto_bin_motor[Step] := TRUE;
                Excess_Alarm := FALSE;
                Status_Message := 'Semi-Auto Pouring (Coarse Feed)';
                
            ELSIF actual_bin < min_tol_weight THEN
                Semi_Auto_Bin[Step] := FALSE;
                semi_auto_bin_cutoff[Step] := TRUE;
                semi_auto_bin_motor[Step] := TRUE;
                Excess_Alarm := FALSE;
                Status_Message := 'Semi-Auto Pouring (Fine Feed)';
                
            ELSIF actual_bin > max_tol_weight THEN
                Semi_Auto_Bin[Step] := FALSE;
                semi_auto_bin_cutoff[Step] := FALSE;
                semi_auto_bin_motor[Step] := FALSE;
                
                IF Excess_Allowed THEN
                    Excess_Alarm := FALSE;
                    Status_Message := 'Excess Weight Allowed: Advancing';
                    bin_last_weight := load_cell_value;
                    Active_Target_Weight := 0.0;
                    Active_Live_Weight := 0.0;
                    IF Step = 10 THEN
                        Step := 31;
                    ELSE
                        Step := Step + 1;
                    END_IF;
                ELSE
                    Excess_Alarm := TRUE;
                    Status_Message := 'Excess Alarm: Weight above max tolerance! Reduce weight.';
                END_IF;
                
            ELSE
                Semi_Auto_Bin[Step] := FALSE;
                semi_auto_bin_cutoff[Step] := FALSE;
                semi_auto_bin_motor[Step] := FALSE;
                Excess_Alarm := FALSE;
                bin_last_weight := load_cell_value;
                Active_Target_Weight := 0.0;
                Active_Live_Weight := 0.0;
                
                IF Step = 10 THEN
                    Step := 31;
                ELSE
                    Step := Step + 1;
                END_IF;
            END_IF;
        END_IF;

    31:
        Active_Material_ID := 0;
        Active_Bin_ID := 0;
        Active_Target_Weight := 0.0;
        Active_Live_Weight := 0.0;
        Excess_Alarm := FALSE;
        Status_Message := 'Final Settling Delay';
        Completion_Timer(IN := TRUE, PT := Effective_Delay);
        IF Completion_Timer.Q THEN
            Completion_Timer(IN := FALSE);
            Step := 32;
        END_IF;
        
    32:
        Active_Material_ID := 0;
        Active_Bin_ID := 0;
        Active_Target_Weight := 0.0;
        Active_Live_Weight := 0.0;
        Excess_Alarm := FALSE;
        Status_Message := 'Sequence Completed';
        Sequence_Complete := TRUE;
        
        IF NOT Start_Button THEN
            Step := 0;
            Sequence_Complete := FALSE;
            FOR i := 1 TO 10 DO
                Actual_Weights[i] := 0.0;
            END_FOR;
        END_IF;
END_CASE;
"""

# 3. batching13 Program Implementation with Full Reset & NC E-Stop
st_code_batching13 = """(* 1. STARTUP CONFIGURATION, RECIPE TOTALS, AND WEIGHT CHECKS *)
Duplicate_Found := FALSE;
Invalid_Material_Range := FALSE;
Weight_Limit_Error := FALSE;

(* Calculate Auto Total Target Weight & Material Count *)
GVL.Auto_Total_Target_Weight := 0.0;
GVL.Auto_Material_Count := 0;
FOR i := 1 TO 6 DO
    IF GVL.Auto_Bin_Material_Mapping[i] < 0 OR GVL.Auto_Bin_Material_Mapping[i] > 20 THEN
        Invalid_Material_Range := TRUE;
    END_IF;
    
    IF GVL.Auto_Bin_Material_Mapping[i] <> 0 AND GVL.Auto_Bin_Material_Mapping[i] <= 20 THEN
        FOR j := 1 TO 10 DO
            IF GVL.Auto_Bin_Material_Mapping[i] = GVL.Semi_Auto_Bin_Material_Mapping[j] THEN
                Duplicate_Found := TRUE;
            END_IF;
        END_FOR;
    END_IF;
    
    IF GVL.Auto_Bin_Material_Mapping[i] > 0 AND GVL.Auto_Bin_Material_Mapping[i] <= 20 THEN
        IF GVL.Recipe_Weights[GVL.Auto_Bin_Material_Mapping[i]] > 0.0 THEN
            GVL.Auto_Total_Target_Weight := GVL.Auto_Total_Target_Weight + GVL.Recipe_Weights[GVL.Auto_Bin_Material_Mapping[i]];
            GVL.Auto_Material_Count := GVL.Auto_Material_Count + 1;
            
            IF GVL.Recipe_Weights[GVL.Auto_Bin_Material_Mapping[i]] < (GVL.Auto_Bin_Cutoff_Weights[i] + GVL.Auto_Bin_Tolerance[i]) THEN
                Weight_Limit_Error := TRUE;
            END_IF;
        END_IF;
    END_IF;
END_FOR;

(* Calculate Semi-Auto Total Target Weight & Material Count *)
GVL.Semi_Auto_Total_Target_Weight := 0.0;
GVL.Semi_Auto_Material_Count := 0;
FOR j := 1 TO 10 DO
    IF GVL.Semi_Auto_Bin_Material_Mapping[j] < 0 OR GVL.Semi_Auto_Bin_Material_Mapping[j] > 20 THEN
        Invalid_Material_Range := TRUE;
    END_IF;
    
    IF GVL.Semi_Auto_Bin_Material_Mapping[j] > 0 AND GVL.Semi_Auto_Bin_Material_Mapping[j] <= 20 THEN
        IF GVL.Recipe_Weights[GVL.Semi_Auto_Bin_Material_Mapping[j]] > 0.0 THEN
            GVL.Semi_Auto_Total_Target_Weight := GVL.Semi_Auto_Total_Target_Weight + GVL.Recipe_Weights[GVL.Semi_Auto_Bin_Material_Mapping[j]];
            GVL.Semi_Auto_Material_Count := GVL.Semi_Auto_Material_Count + 1;
            
            IF GVL.Recipe_Weights[GVL.Semi_Auto_Bin_Material_Mapping[j]] < (GVL.Semi_Auto_Bin_Cutoff_Weights[j] + GVL.Semi_Auto_Bin_Tolerance[j]) THEN
                Weight_Limit_Error := TRUE;
            END_IF;
        END_IF;
    END_IF;
END_FOR;

(* Configuration Error Resolution *)
IF Duplicate_Found THEN
    GVL.Error_Code := 1;
    Status_Message := 'Error 1: Duplicate Material ID mapped in Auto and Semi-Auto!';
ELSIF Invalid_Material_Range THEN
    GVL.Error_Code := 2;
    Status_Message := 'Error 2: Material Index configuration out of range (1..20)!';
ELSIF Weight_Limit_Error THEN
    GVL.Error_Code := 3;
    Status_Message := 'Error 3: Recipe weight is less than Cutoff + Tolerance!';
ELSE
    IF GVL.Error_Code <= 3 THEN
        GVL.Error_Code := 0;
    END_IF;
END_IF;

(* Abort / Hard Reset Interlock *)
IF (GVL.Error_Code >= 1 AND GVL.Error_Code <= 3) OR GVL.Reset THEN
    FOR i := 1 TO 6 DO 
        GVL.Auto_Bin[i] := FALSE; 
        GVL.auto_bin_cutoff[i] := FALSE; 
        GVL.auto_bin_motor[i] := FALSE; 
        GVL.Auto_Weights[i] := 0.0;
    END_FOR;
    
    FOR i := 1 TO 10 DO 
        GVL.Semi_Auto_Bin[i] := FALSE; 
        GVL.semi_auto_bin_cutoff[i] := FALSE; 
        GVL.semi_auto_bin_motor[i] := FALSE; 
        GVL.Semi_Auto_Weights[i] := 0.0;
    END_FOR;
    
    Internal_FB_Start := FALSE;
    Auto_Ctrl(Start_Button := FALSE, E_Stop_Active := GVL.E_Stop_Active, Reset := GVL.Reset, load_cell_value := GVL.load_cell_auto, Inter_Bin_Delay := GVL.Auto_Inter_Bin_Delay, Excess_Allowed := GVL.Auto_Excess_Allowed);
    Semi_Auto_Ctrl(Start_Button := FALSE, E_Stop_Active := GVL.E_Stop_Active, Reset := GVL.Reset, load_cell_value := GVL.load_cell_semi_auto, Inter_Bin_Delay := GVL.Semi_Auto_Inter_Bin_Delay, Excess_Allowed := GVL.Semi_Auto_Excess_Allowed);
    
    GVL.Auto_Active_Target_Weight := 0.0;
    GVL.Auto_Active_Live_Weight := 0.0;
    GVL.Semi_Auto_Active_Target_Weight := 0.0;
    GVL.Semi_Auto_Active_Live_Weight := 0.0;
    
    Auto_Complete := TRUE;
    Semi_Auto_Complete := TRUE;
    All_Cycles_Complete := TRUE;
    
    GVL.Cycle_Hold_Active := FALSE;
    GVL.Run := FALSE;
    Cycle_Manager_State := 0;
    
    IF GVL.Reset THEN
        (* Reset Target Recipe Weights *)
        FOR i := 1 TO 20 DO
            GVL.Recipe_Weights[i] := 0.0;
        END_FOR;
        GVL.Auto_Total_Target_Weight := 0.0;
        GVL.Semi_Auto_Total_Target_Weight := 0.0;
        GVL.Auto_Material_Count := 0;
        GVL.Semi_Auto_Material_Count := 0;
        
        GVL.Error_Code := 0;
        GVL.Current_Batch_Cycle := 0;
        GVL.Target_Batch_Cycles := 0;
        GVL.Start_Button := FALSE;
        Completed_Batch_Cycles := 0;
        Status_Message := 'System Reset Activated';
        Auto_Complete := FALSE;
        Semi_Auto_Complete := FALSE;
        All_Cycles_Complete := FALSE;
        
        GVL.Auto_Active_Mat := 0;
        GVL.Auto_Active_Bin := 0;
        GVL.Semi_Auto_Active_Mat := 0;
        GVL.Semi_Auto_Active_Bin := 0;
        GVL.Auto_Excess_Alarm := FALSE;
        GVL.Semi_Auto_Excess_Alarm := FALSE;
        
        (* Auto-clearing trigger: set Reset back to FALSE *)
        GVL.Reset := FALSE;
    END_IF;
    RETURN;
END_IF;


(* 2. REPETITIVE CYCLE MANAGER STATE MACHINE WITH NC E-STOP & PRE-RUN INITIAL TOLERANCE CHECK *)
CASE Cycle_Manager_State OF
    0: (* IDLE STATE *)
        Internal_FB_Start := FALSE;
        All_Cycles_Complete := FALSE;
        GVL.Cycle_Hold_Active := FALSE;
        GVL.Run := FALSE;
        IF GVL.Error_Code = 0 AND Status_Message <> 'Error: Target Batch Cycles is 0!' AND Status_Message <> 'Error 4: Scale weight exceeds Initial Tolerance!' THEN 
            Status_Message := 'System Ready'; 
        END_IF;
        
        IF GVL.Start_Button THEN
            (* Guard: NC E-Stop must be Healthy (TRUE) to start *)
            IF NOT GVL.E_Stop_Active THEN
                GVL.Run := FALSE;
                Status_Message := 'Cannot Start: Emergency Stop Active!';
            (* Guard 1: Target_Batch_Cycles must be > 0 *)
            ELSIF GVL.Target_Batch_Cycles <= 0 THEN
                GVL.Run := FALSE;
                Status_Message := 'Error: Target Batch Cycles is 0!';
            (* Guard 2: Check Initial Tolerance ONLY before setting Run = TRUE *)
            ELSIF (GVL.load_cell_auto > GVL.Auto_Initial_Tolerance OR GVL.load_cell_auto < (-GVL.Auto_Initial_Tolerance)) OR 
                  (GVL.load_cell_semi_auto > GVL.Semi_Auto_Initial_Tolerance OR GVL.load_cell_semi_auto < (-GVL.Semi_Auto_Initial_Tolerance)) THEN
                GVL.Run := FALSE;
                GVL.Error_Code := 4;
                Status_Message := 'Error 4: Scale weight exceeds Initial Tolerance!';
            ELSE
                GVL.Error_Code := 0;
                GVL.Current_Batch_Cycle := 1;
                Completed_Batch_Cycles := 0;
                
                Auto_Complete := FALSE;
                Semi_Auto_Complete := FALSE;
                
                GVL.Run := TRUE;
                Cycle_Manager_State := 1;
            END_IF;
        END_IF;
        
    1: (* RUN STATE *)
        Internal_FB_Start := TRUE;
        GVL.Run := TRUE;
        Status_Message := CONCAT('Running Batch Cycle ', INT_TO_STRING(GVL.Current_Batch_Cycle));
        
        IF Auto_Complete AND Semi_Auto_Complete THEN
            Cycle_Manager_State := 2;
        END_IF;
        
    2: (* CHECK REPEAT CYCLE STATE *)
        Completed_Batch_Cycles := GVL.Current_Batch_Cycle;
        GVL.Run := TRUE;
        
        IF GVL.Current_Batch_Cycle < GVL.Target_Batch_Cycles AND GVL.Error_Code = 0 THEN
            GVL.Cycle_Hold_Active := TRUE;
            Internal_FB_Start := FALSE;
            Cycle_Manager_State := 5;
        ELSE
            Cycle_Manager_State := 4;
        END_IF;
        
    5: (* PAUSED BETWEEN CYCLES *)
        Internal_FB_Start := FALSE;
        GVL.Run := TRUE;
        Status_Message := CONCAT('Cycle ', CONCAT(INT_TO_STRING(GVL.Current_Batch_Cycle), ' Complete. Empty scale to 0 and release Cycle Hold.'));
        
        IF NOT GVL.Cycle_Hold_Active THEN
            IF (GVL.load_cell_auto > GVL.Auto_Initial_Tolerance OR GVL.load_cell_auto < (-GVL.Auto_Initial_Tolerance)) OR 
               (GVL.load_cell_semi_auto > GVL.Semi_Auto_Initial_Tolerance OR GVL.load_cell_semi_auto < (-GVL.Semi_Auto_Initial_Tolerance)) THEN
                GVL.Run := FALSE;
                GVL.Error_Code := 4;
                Status_Message := 'Error 4: Scale weight exceeds Initial Tolerance!';
                GVL.Cycle_Hold_Active := TRUE;
            ELSE
                GVL.Error_Code := 0;
                GVL.Current_Batch_Cycle := GVL.Current_Batch_Cycle + 1;
                Auto_Complete := FALSE;
                Semi_Auto_Complete := FALSE;
                Cycle_Manager_State := 1;
            END_IF;
        END_IF;
        
    4: (* SEQUENCE FULLY COMPLETED STATE *)
        Internal_FB_Start := FALSE;
        All_Cycles_Complete := TRUE;
        GVL.Run := FALSE;
        GVL.Start_Button := FALSE;
        Status_Message := 'All Batch Cycles Completed';
        
        Cycle_Manager_State := 0;
END_CASE;


(* 3. CONCURRENT EXECUTION OF FB INSTANCES WITH GVL ARRAYS & LIVE ACTIVE WEIGHTS *)
Auto_Ctrl(
    Start_Button := Internal_FB_Start,
    E_Stop_Active := GVL.E_Stop_Active,
    Reset := GVL.Reset,
    load_cell_value := GVL.load_cell_auto,
    Auto_Bin_Material_Mapping := GVL.Auto_Bin_Material_Mapping,
    Auto_Bin_Cutoff_Weights := GVL.Auto_Bin_Cutoff_Weights,
    Auto_Bin_Tolerance := GVL.Auto_Bin_Tolerance,
    Inter_Bin_Delay := GVL.Auto_Inter_Bin_Delay,
    Excess_Allowed := GVL.Auto_Excess_Allowed,
    Auto_Bin => GVL.Auto_Bin,
    auto_bin_cutoff => GVL.auto_bin_cutoff,
    auto_bin_motor => GVL.auto_bin_motor,
    Actual_Weights => GVL.Auto_Weights,
    Sequence_Complete => Auto_Complete,
    Active_Material_ID => GVL.Auto_Active_Mat,
    Active_Bin_ID => GVL.Auto_Active_Bin,
    Active_Target_Weight => GVL.Auto_Active_Target_Weight,
    Active_Live_Weight => GVL.Auto_Active_Live_Weight,
    Excess_Alarm => GVL.Auto_Excess_Alarm,
    Error_Code => Auto_Err,
    Status_Message => Auto_Msg
);

Semi_Auto_Ctrl(
    Start_Button := Internal_FB_Start,
    E_Stop_Active := GVL.E_Stop_Active,
    Reset := GVL.Reset,
    load_cell_value := GVL.load_cell_semi_auto,
    Semi_Auto_Bin_Material_Mapping := GVL.Semi_Auto_Bin_Material_Mapping,
    Semi_Auto_Bin_Cutoff_Weights := GVL.Semi_Auto_Bin_Cutoff_Weights,
    Semi_Auto_Bin_Tolerance := GVL.Semi_Auto_Bin_Tolerance,
    Inter_Bin_Delay := GVL.Semi_Auto_Inter_Bin_Delay,
    Excess_Allowed := GVL.Semi_Auto_Excess_Allowed,
    Semi_Auto_Bin => GVL.Semi_Auto_Bin,
    semi_auto_bin_cutoff => GVL.semi_auto_bin_cutoff,
    semi_auto_bin_motor => GVL.semi_auto_bin_motor,
    Actual_Weights => GVL.Semi_Auto_Weights,
    Sequence_Complete => Semi_Auto_Complete,
    Active_Material_ID => GVL.Semi_Auto_Active_Mat,
    Active_Bin_ID => GVL.Semi_Auto_Active_Bin,
    Active_Target_Weight => GVL.Semi_Auto_Active_Target_Weight,
    Active_Live_Weight => GVL.Semi_Auto_Active_Live_Weight,
    Excess_Alarm => GVL.Semi_Auto_Excess_Alarm,
    Error_Code => Semi_Auto_Err,
    Status_Message => Semi_Auto_Msg
);

(* Runtime Error Mapping & Aggregation *)
IF Auto_Err <> 0 THEN
    GVL.Error_Code := Auto_Err;
    Status_Message := CONCAT('Auto Error: ', Auto_Msg);
    Auto_Complete := TRUE;
    Semi_Auto_Complete := TRUE;
    All_Cycles_Complete := TRUE;
    GVL.Run := FALSE;
    GVL.Start_Button := FALSE;
ELSIF Semi_Auto_Err <> 0 THEN
    GVL.Error_Code := Semi_Auto_Err;
    Status_Message := CONCAT('Semi-Auto Error: ', Semi_Auto_Msg);
    Auto_Complete := TRUE;
    Semi_Auto_Complete := TRUE;
    All_Cycles_Complete := TRUE;
    GVL.Run := FALSE;
    GVL.Start_Button := FALSE;
ELSIF Cycle_Manager_State = 0 AND GVL.Error_Code <= 3 THEN
    GVL.Error_Code := 0;
END_IF;
"""

# 4. Auto_Batching_V14 Implementation with Full Reset & NC E-Stop
st_code_auto_v14 = """(* Auto Batching FB V14 with Full Reset, Cycle Manager, NC E-Stop & Tolerance Guards *)

Effective_Delay := Inter_Bin_Delay;
IF Effective_Delay = T#0S THEN
    Effective_Delay := T#2S;
END_IF;

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
            IF GVL.Recipe_Weights[Auto_Bin_Material_Mapping[i]] < (Auto_Bin_Cutoff_Weights[i] + Auto_Bin_Tolerance[i]) THEN
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
    Status_Message := 'Error 3: Recipe weight is less than Cutoff + Tolerance!';
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
    
    (* Wipe Recipe Target Weights *)
    FOR i := 1 TO 20 DO
        GVL.Recipe_Weights[i] := 0.0;
    END_FOR;
    GVL.Auto_Total_Target_Weight := 0.0;
    GVL.Semi_Auto_Total_Target_Weight := 0.0;
    GVL.Auto_Material_Count := 0;
    GVL.Semi_Auto_Material_Count := 0;
    
    Sequence_Complete := FALSE;
    Active_Material_ID := 0;
    Active_Bin_ID := 0;
    Active_Target_Weight := 0.0;
    Active_Live_Weight := 0.0;
    Excess_Alarm := FALSE;
    Error_Code := 0;
    GVL.Error_Code := 0;
    GVL.Current_Batch_Cycle := 0;
    GVL.Target_Batch_Cycles := 0;
    GVL.Start_Button := FALSE;
    GVL.Run := FALSE;
    GVL.Cycle_Hold_Active := FALSE;
    GVL.Auto_Active_Mat := 0;
    GVL.Auto_Active_Bin := 0;
    GVL.Auto_Active_Target_Weight := 0.0;
    GVL.Auto_Active_Live_Weight := 0.0;
    GVL.Auto_Excess_Alarm := FALSE;
    Status_Message := 'System Reset Activated';
    Paused_By_EStop := FALSE;
    Step := 0;
    Cycle_Manager_State := 0;
    Internal_FB_Start := FALSE;
    bin_last_weight := 0.0;
    Start_Sim_Weight := 0.0;
    Transition_Timer(IN := FALSE);
    Completion_Timer(IN := FALSE);
    Sim_Timer(IN := FALSE);
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
        Status_Message := 'Auto Paused: Emergency Stop Active!';
    ELSE
        Status_Message := 'Auto Paused: Press Start to Resume';
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
        GVL.Cycle_Hold_Active := FALSE;
        IF GVL.Error_Code = 0 AND Status_Message <> 'Error: Target Batch Cycles is 0!' AND Status_Message <> 'Error 4: Scale weight exceeds Initial Tolerance!' AND Status_Message <> 'Cannot Start: Emergency Stop Active!' THEN
            Status_Message := 'System Ready';
        END_IF;
        
        IF Start_Button OR GVL.Start_Button THEN
            IF NOT E_Stop_Active OR NOT GVL.E_Stop_Active THEN
                GVL.Run := FALSE;
                Status_Message := 'Cannot Start: Emergency Stop Active!';
            ELSIF GVL.Target_Batch_Cycles <= 0 THEN
                GVL.Run := FALSE;
                Status_Message := 'Error: Target Batch Cycles is 0!';
            ELSIF (GVL.load_cell_auto > GVL.Auto_Initial_Tolerance OR GVL.load_cell_auto < (-GVL.Auto_Initial_Tolerance)) OR 
                  (GVL.load_cell_semi_auto > GVL.Semi_Auto_Initial_Tolerance OR GVL.load_cell_semi_auto < (-GVL.Semi_Auto_Initial_Tolerance)) THEN
                GVL.Run := FALSE;
                GVL.Error_Code := 4;
                Error_Code := 4;
                Status_Message := 'Error 4: Scale weight exceeds Initial Tolerance!';
            ELSE
                GVL.Error_Code := 0;
                Error_Code := 0;
                GVL.Current_Batch_Cycle := 1;
                GVL.Run := TRUE;
                Internal_FB_Start := TRUE;
                Cycle_Manager_State := 1;
            END_IF;
        END_IF;
        
    1: (* RUNNING CYCLE *)
        Internal_FB_Start := TRUE;
        GVL.Run := TRUE;
        Status_Message := CONCAT('Running Batch Cycle ', INT_TO_STRING(GVL.Current_Batch_Cycle));
        
        IF Sequence_Complete AND (NOT GVL.Run OR (NOT GVL.Semi_Auto_Bin[1] AND NOT GVL.Semi_Auto_Bin[2] AND NOT GVL.Semi_Auto_Bin[3] AND NOT GVL.Semi_Auto_Bin[4] AND NOT GVL.Semi_Auto_Bin[5] AND NOT GVL.Semi_Auto_Bin[6] AND NOT GVL.Semi_Auto_Bin[7] AND NOT GVL.Semi_Auto_Bin[8] AND NOT GVL.Semi_Auto_Bin[9] AND NOT GVL.Semi_Auto_Bin[10])) THEN
            IF GVL.Current_Batch_Cycle < GVL.Target_Batch_Cycles AND GVL.Error_Code = 0 THEN
                GVL.Cycle_Hold_Active := TRUE;
                Internal_FB_Start := FALSE;
                Cycle_Manager_State := 5;
            ELSE
                Cycle_Manager_State := 4;
            END_IF;
        END_IF;
        
    5: (* PAUSED BETWEEN CYCLES IN HOLD *)
        Internal_FB_Start := FALSE;
        GVL.Run := TRUE;
        Status_Message := CONCAT('Cycle ', CONCAT(INT_TO_STRING(GVL.Current_Batch_Cycle), ' Complete. Empty scale to 0 and release Cycle Hold.'));
        
        IF NOT GVL.Cycle_Hold_Active THEN
            IF (GVL.load_cell_auto > GVL.Auto_Initial_Tolerance OR GVL.load_cell_auto < (-GVL.Auto_Initial_Tolerance)) OR 
               (GVL.load_cell_semi_auto > GVL.Semi_Auto_Initial_Tolerance OR GVL.load_cell_semi_auto < (-GVL.Semi_Auto_Initial_Tolerance)) THEN
                GVL.Run := FALSE;
                GVL.Error_Code := 4;
                Error_Code := 4;
                Status_Message := 'Error 4: Scale weight exceeds Initial Tolerance!';
                GVL.Cycle_Hold_Active := TRUE;
            ELSE
                GVL.Error_Code := 0;
                Error_Code := 0;
                GVL.Current_Batch_Cycle := GVL.Current_Batch_Cycle + 1;
                Sequence_Complete := FALSE;
                Step := 0;
                Internal_FB_Start := TRUE;
                Cycle_Manager_State := 1;
            END_IF;
        END_IF;
        
    4: (* ALL CYCLES COMPLETE *)
        Internal_FB_Start := FALSE;
        GVL.Run := FALSE;
        GVL.Start_Button := FALSE;
        Status_Message := 'All Batch Cycles Completed';
        Cycle_Manager_State := 0;
END_CASE;

(* 5. AUTO SILOS 1..6 POURING SEQUENCE *)
IF Step = 0 AND Internal_FB_Start THEN
    Step := 1;
    bin_last_weight := load_cell_value;
    Sequence_Complete := FALSE;
    Excess_Alarm := FALSE;
    Error_Code := 0;
    Active_Target_Weight := 0.0;
    Active_Live_Weight := 0.0;
    FOR i := 1 TO 6 DO
        Actual_Weights[i] := 0.0;
        Auto_Bin[i] := FALSE;
        auto_bin_cutoff[i] := FALSE;
        auto_bin_motor[i] := FALSE;
    END_FOR;
END_IF;

CASE Step OF
    0:
        Active_Material_ID := 0;
        Active_Bin_ID := 0;
        Active_Target_Weight := 0.0;
        Active_Live_Weight := 0.0;
        Excess_Alarm := FALSE;
        Sequence_Complete := FALSE;
        FOR i := 1 TO 6 DO
            Auto_Bin[i] := FALSE;
            auto_bin_cutoff[i] := FALSE;
            auto_bin_motor[i] := FALSE;
        END_FOR;
        
    1..6:
        Mat_Idx := Auto_Bin_Material_Mapping[Step];
        IF Mat_Idx = 0 OR (Mat_Idx <= 20 AND GVL.Recipe_Weights[Mat_Idx] = 0.0) THEN
            IF Step = 6 THEN
                Step := 7;
            ELSE
                Step := Step + 1;
            END_IF;
        ELSE
            target_weight := GVL.Recipe_Weights[Mat_Idx];
            cutoff_trigger_weight := target_weight - Auto_Bin_Cutoff_Weights[Step];
            min_tol_weight := target_weight - Auto_Bin_Tolerance[Step];
            max_tol_weight := target_weight + Auto_Bin_Tolerance[Step];
            Active_Target_Weight := target_weight;
            actual_bin := load_cell_value - bin_last_weight;
            Actual_Weights[Step] := actual_bin;
            Active_Live_Weight := actual_bin;
            Active_Material_ID := Mat_Idx;
            Active_Bin_ID := Step;
            
            IF load_cell_value > 500.0 THEN
                Error_Code := 21;
                GVL.Error_Code := 21;
                Status_Message := 'Error 21: Scale Overloaded!';
                Sequence_Complete := TRUE;
                Paused_By_EStop := TRUE;
            END_IF;
            
            IF actual_bin < cutoff_trigger_weight THEN
                Auto_Bin[Step] := TRUE;
                auto_bin_cutoff[Step] := FALSE;
                auto_bin_motor[Step] := TRUE;
                Excess_Alarm := FALSE;
                Status_Message := 'Auto Pouring (Coarse Feed)';
            ELSIF actual_bin < min_tol_weight THEN
                Auto_Bin[Step] := FALSE;
                auto_bin_cutoff[Step] := TRUE;
                auto_bin_motor[Step] := TRUE;
                Excess_Alarm := FALSE;
                Status_Message := 'Auto Pouring (Fine Feed)';
            ELSIF actual_bin > max_tol_weight THEN
                Auto_Bin[Step] := FALSE;
                auto_bin_cutoff[Step] := FALSE;
                auto_bin_motor[Step] := FALSE;
                IF Excess_Allowed THEN
                    Excess_Alarm := FALSE;
                    Status_Message := 'Excess Weight Allowed: Advancing';
                    bin_last_weight := load_cell_value;
                    Active_Target_Weight := 0.0;
                    Active_Live_Weight := 0.0;
                    IF Step = 6 THEN
                        Step := 7;
                    ELSE
                        Step := Step + 1;
                    END_IF;
                ELSE
                    Excess_Alarm := TRUE;
                    Status_Message := 'Excess Alarm: Weight above max tolerance! Reduce weight.';
                END_IF;
            ELSE
                Auto_Bin[Step] := FALSE;
                auto_bin_cutoff[Step] := FALSE;
                auto_bin_motor[Step] := FALSE;
                Excess_Alarm := FALSE;
                bin_last_weight := load_cell_value;
                Active_Target_Weight := 0.0;
                Active_Live_Weight := 0.0;
                IF Step = 6 THEN
                    Step := 7;
                ELSE
                    Step := Step + 1;
                END_IF;
            END_IF;
        END_IF;

    7:
        Active_Material_ID := 0;
        Active_Bin_ID := 0;
        Active_Target_Weight := 0.0;
        Active_Live_Weight := 0.0;
        Excess_Alarm := FALSE;
        Status_Message := 'Final Settling Delay';
        Completion_Timer(IN := TRUE, PT := Effective_Delay);
        IF Completion_Timer.Q THEN
            Completion_Timer(IN := FALSE);
            Step := 8;
        END_IF;
        
    8:
        Active_Material_ID := 0;
        Active_Bin_ID := 0;
        Active_Target_Weight := 0.0;
        Active_Live_Weight := 0.0;
        Excess_Alarm := FALSE;
        Status_Message := 'Sequence Completed';
        Sequence_Complete := TRUE;
        IF NOT Internal_FB_Start THEN
            Step := 0;
            Sequence_Complete := FALSE;
            FOR i := 1 TO 6 DO
                Actual_Weights[i] := 0.0;
            END_FOR;
        END_IF;
END_CASE;
"""

# 5. Semi_Auto_Batching_V14 Implementation with Full Reset & NC E-Stop
st_code_semi_v14 = """(* Semi-Auto Batching FB V14 with Full Reset, NC E-Stop & Step 0 Zeroing *)

Effective_Delay := Inter_Bin_Delay;
IF Effective_Delay = T#0S THEN
    Effective_Delay := T#2S;
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
    Status_Message := '';
    Paused_By_EStop := FALSE;
    Step := 0;
    bin_last_weight := 0.0;
    Start_Sim_Weight := 0.0;
    Transition_Timer(IN := FALSE);
    Completion_Timer(IN := FALSE);
    Sim_Timer(IN := FALSE);
    
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
        Status_Message := 'Semi-Auto Paused: Emergency Stop Active!';
    ELSE
        Status_Message := 'Semi-Auto Paused: Press Start to Resume';
        IF Start_Button OR GVL.Start_Button THEN
            Paused_By_EStop := FALSE;
        END_IF;
    END_IF;
    Sim_Timer(IN := FALSE);
    Transition_Timer(IN := FALSE);
    Completion_Timer(IN := FALSE);
    RETURN;
END_IF;

(* 4. SEQUENCE START (WHEN SYSTEM IS IN RUN MODE) *)
IF Step = 0 AND (GVL.Run OR Start_Button) AND GVL.Cycle_Hold_Active = FALSE THEN
    Step := 1;
    bin_last_weight := load_cell_value;
    Sequence_Complete := FALSE;
    Excess_Alarm := FALSE;
    Error_Code := 0;
    Status_Message := 'Semi-Auto Pour Started';
    Active_Target_Weight := 0.0;
    Active_Live_Weight := 0.0;
    FOR i := 1 TO 10 DO
        Actual_Weights[i] := 0.0;
        Semi_Auto_Bin[i] := FALSE;
        semi_auto_bin_cutoff[i] := FALSE;
        semi_auto_bin_motor[i] := FALSE;
    END_FOR;
END_IF;

CASE Step OF
    0:
        Active_Material_ID := 0;
        Active_Bin_ID := 0;
        Active_Target_Weight := 0.0;
        Active_Live_Weight := 0.0;
        Excess_Alarm := FALSE;
        Sequence_Complete := FALSE;
        FOR i := 1 TO 10 DO
            Semi_Auto_Bin[i] := FALSE;
            semi_auto_bin_cutoff[i] := FALSE;
            semi_auto_bin_motor[i] := FALSE;
        END_FOR;
        IF Error_Code = 0 THEN Status_Message := 'Semi-Auto Idle'; END_IF;
        
    1..10:
        Mat_Idx := Semi_Auto_Bin_Material_Mapping[Step];
        IF Mat_Idx = 0 OR (Mat_Idx <= 20 AND GVL.Recipe_Weights[Mat_Idx] = 0.0) THEN
            IF Step = 10 THEN
                Step := 31;
            ELSE
                Step := Step + 1;
            END_IF;
        ELSE
            target_weight := GVL.Recipe_Weights[Mat_Idx];
            cutoff_trigger_weight := target_weight - Semi_Auto_Bin_Cutoff_Weights[Step];
            min_tol_weight := target_weight - Semi_Auto_Bin_Tolerance[Step];
            max_tol_weight := target_weight + Semi_Auto_Bin_Tolerance[Step];
            Active_Target_Weight := target_weight;
            actual_bin := load_cell_value - bin_last_weight;
            Actual_Weights[Step] := actual_bin;
            Active_Live_Weight := actual_bin;
            Active_Material_ID := Mat_Idx;
            Active_Bin_ID := Step;
            
            IF load_cell_value > 500.0 THEN
                Error_Code := 21;
                GVL.Error_Code := 21;
                Status_Message := 'Error 21: Scale Overloaded!';
                Sequence_Complete := TRUE;
                Paused_By_EStop := TRUE;
            END_IF;
            
            IF actual_bin < cutoff_trigger_weight THEN
                Semi_Auto_Bin[Step] := TRUE;
                semi_auto_bin_cutoff[Step] := FALSE;
                semi_auto_bin_motor[Step] := TRUE;
                Excess_Alarm := FALSE;
                Status_Message := 'Semi-Auto Pouring (Coarse Feed)';
            ELSIF actual_bin < min_tol_weight THEN
                Semi_Auto_Bin[Step] := FALSE;
                semi_auto_bin_cutoff[Step] := TRUE;
                semi_auto_bin_motor[Step] := TRUE;
                Excess_Alarm := FALSE;
                Status_Message := 'Semi-Auto Pouring (Fine Feed)';
            ELSIF actual_bin > max_tol_weight THEN
                Semi_Auto_Bin[Step] := FALSE;
                semi_auto_bin_cutoff[Step] := FALSE;
                semi_auto_bin_motor[Step] := FALSE;
                IF Excess_Allowed THEN
                    Excess_Alarm := FALSE;
                    Status_Message := 'Excess Weight Allowed: Advancing';
                    bin_last_weight := load_cell_value;
                    Active_Target_Weight := 0.0;
                    Active_Live_Weight := 0.0;
                    IF Step = 10 THEN
                        Step := 31;
                    ELSE
                        Step := Step + 1;
                    END_IF;
                ELSE
                    Excess_Alarm := TRUE;
                    Status_Message := 'Excess Alarm: Weight above max tolerance! Reduce weight.';
                END_IF;
            ELSE
                Semi_Auto_Bin[Step] := FALSE;
                semi_auto_bin_cutoff[Step] := FALSE;
                semi_auto_bin_motor[Step] := FALSE;
                Excess_Alarm := FALSE;
                bin_last_weight := load_cell_value;
                Active_Target_Weight := 0.0;
                Active_Live_Weight := 0.0;
                IF Step = 10 THEN
                    Step := 31;
                ELSE
                    Step := Step + 1;
                END_IF;
            END_IF;
        END_IF;

    31:
        Active_Material_ID := 0;
        Active_Bin_ID := 0;
        Active_Target_Weight := 0.0;
        Active_Live_Weight := 0.0;
        Excess_Alarm := FALSE;
        Status_Message := 'Final Settling Delay';
        Completion_Timer(IN := TRUE, PT := Effective_Delay);
        IF Completion_Timer.Q THEN
            Completion_Timer(IN := FALSE);
            Step := 32;
        END_IF;
        
    32:
        Active_Material_ID := 0;
        Active_Bin_ID := 0;
        Active_Target_Weight := 0.0;
        Active_Live_Weight := 0.0;
        Excess_Alarm := FALSE;
        Status_Message := 'Sequence Completed';
        Sequence_Complete := TRUE;
        IF NOT GVL.Run THEN
            Step := 0;
            Sequence_Complete := FALSE;
            FOR i := 1 TO 10 DO
                Actual_Weights[i] := 0.0;
            END_FOR;
        END_IF;
END_CASE;
"""

with open(log_path, "w") as f:
    f.write("Starting update of POUs with NC E-Stop and Reset fix...\n")
    try:
        proj = projects.open(project_path)
        
        # 1. Update Auto_Batching_V13
        p = proj.find("Auto_Batching_V13", True)
        if len(p) > 0:
            p[0].textual_implementation.replace(st_code_auto_v13)
            f.write("Auto_Batching_V13 updated.\n")
            
        # 2. Update Semi_Auto_Batching_V13
        p = proj.find("Semi_Auto_Batching_V13", True)
        if len(p) > 0:
            p[0].textual_implementation.replace(st_code_semi_v13)
            f.write("Semi_Auto_Batching_V13 updated.\n")
            
        # 3. Update batching13
        p = proj.find("batching13", True)
        if len(p) > 0:
            p[0].textual_implementation.replace(st_code_batching13)
            f.write("batching13 updated.\n")
            
        # 4. Update Auto_Batching_V14
        p = proj.find("Auto_Batching_V14", True)
        if len(p) > 0:
            p[0].textual_implementation.replace(st_code_auto_v14)
            f.write("Auto_Batching_V14 updated.\n")
            
        # 5. Update Semi_Auto_Batching_V14
        p = proj.find("Semi_Auto_Batching_V14", True)
        if len(p) > 0:
            p[0].textual_implementation.replace(st_code_semi_v14)
            f.write("Semi_Auto_Batching_V14 updated.\n")
            
        proj.save()
        proj.close()
        f.write("All POUs updated successfully.\n")
    except Exception as e:
        f.write("Error: " + str(e) + "\n")
