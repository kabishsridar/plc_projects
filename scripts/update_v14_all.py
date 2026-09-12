import sys
import os

project_path = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\Rasi_feeds_batching.project"
log_path = r"C:\Users\kabish\.gemini\antigravity-ide\brain\6bb09710-7f3e-4443-b187-ad04e16ca8dc\scratch\update_v14_all_log.txt"

st_decl_auto = """FUNCTION_BLOCK Auto_Batching_V14
VAR_INPUT
    Start_Button : BOOL;
    E_Stop_Active : BOOL;
    Reset : BOOL;
    Auto_Bin_Material_Mapping : ARRAY[1..6] OF INT;
    Auto_Bin_Cutoff_Weights : ARRAY[1..6] OF REAL;
    Auto_Bin_Tolerance : ARRAY[1..6] OF REAL;
    Inter_Bin_Delay : TIME;
    Excess_Allowed : BOOL;
END_VAR
VAR_IN_OUT
    load_cell_value : REAL;
END_VAR
VAR_OUTPUT
    Auto_Bin : ARRAY[1..6] OF BOOL;
    auto_bin_cutoff : ARRAY[1..6] OF BOOL;
    auto_bin_motor : ARRAY[1..6] OF BOOL;
    Actual_Weights : ARRAY[1..6] OF REAL;
    Sequence_Complete : BOOL;
    Active_Material_ID : INT;
    Active_Bin_ID : INT;
    Active_Target_Weight : REAL;
    Active_Live_Weight : REAL;
    Excess_Alarm : BOOL;
    Error_Code : INT;
    Status_Message : STRING;
END_VAR
VAR
    Step : INT;
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
    Cycle_Manager_State : INT;
    Internal_FB_Start : BOOL;
    Duplicate_Found : BOOL;
    Invalid_Material_Range : BOOL;
    Weight_Limit_Error : BOOL;
END_VAR
"""

st_code_auto = """(* Auto Batching FB V14 with Full Supervisor, Cycle Manager & Pre-Run Initial Tolerance Checks *)

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
    GVL.Reset := FALSE;
    RETURN;
END_IF;

(* 3. E-STOP PAUSE / HOLD LOGIC *)
IF E_Stop_Active OR GVL.E_Stop_Active THEN
    Paused_By_EStop := TRUE;
END_IF;

IF Paused_By_EStop THEN
    FOR i := 1 TO 6 DO
        Auto_Bin[i] := FALSE;
        auto_bin_cutoff[i] := FALSE;
        auto_bin_motor[i] := FALSE;
    END_FOR;
    IF E_Stop_Active OR GVL.E_Stop_Active THEN
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
        IF GVL.Error_Code = 0 AND Status_Message <> 'Error: Target Batch Cycles is 0!' AND Status_Message <> 'Error 4: Scale weight exceeds Initial Tolerance!' THEN
            Status_Message := 'System Ready';
        END_IF;
        
        IF Start_Button OR GVL.Start_Button THEN
            IF GVL.Target_Batch_Cycles <= 0 THEN
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
        
        (* When Auto finishes and Semi-Auto finishes *)
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

st_decl_semi = """FUNCTION_BLOCK Semi_Auto_Batching_V14
VAR_INPUT
    Start_Button : BOOL;
    E_Stop_Active : BOOL;
    Reset : BOOL;
    Semi_Auto_Bin_Material_Mapping : ARRAY[1..10] OF INT;
    Semi_Auto_Bin_Cutoff_Weights : ARRAY[1..10] OF REAL;
    Semi_Auto_Bin_Tolerance : ARRAY[1..10] OF REAL;
    Inter_Bin_Delay : TIME;
    Excess_Allowed : BOOL;
END_VAR
VAR_IN_OUT
    load_cell_value : REAL;
END_VAR
VAR_OUTPUT
    Semi_Auto_Bin : ARRAY[1..10] OF BOOL;
    semi_auto_bin_cutoff : ARRAY[1..10] OF BOOL;
    semi_auto_bin_motor : ARRAY[1..10] OF BOOL;
    Actual_Weights : ARRAY[1..10] OF REAL;
    Sequence_Complete : BOOL;
    Active_Material_ID : INT;
    Active_Bin_ID : INT;
    Active_Target_Weight : REAL;
    Active_Live_Weight : REAL;
    Excess_Alarm : BOOL;
    Error_Code : INT;
    Status_Message : STRING;
END_VAR
VAR
    Step : INT;
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
    Transition_Timer : TON;
    Completion_Timer : TON;
    Simulation_Mode : BOOL;
    Sim_Rate : REAL;
    Sim_Timer : TON;
    Start_Sim_Weight : REAL;
    Discharge_Active : BOOL;
END_VAR
"""

st_code_semi = """(* Semi-Auto Batching FB V14 with Independent Totals, Real-Time Feeding & Instant Excess Alarm *)

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

(* 3. E-STOP PAUSE / HOLD LOGIC *)
IF E_Stop_Active OR GVL.E_Stop_Active THEN
    Paused_By_EStop := TRUE;
END_IF;

IF Paused_By_EStop THEN
    FOR i := 1 TO 10 DO
        Semi_Auto_Bin[i] := FALSE;
        semi_auto_bin_cutoff[i] := FALSE;
        semi_auto_bin_motor[i] := FALSE;
    END_FOR;
    IF E_Stop_Active OR GVL.E_Stop_Active THEN
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
    f.write("Updating V14 blocks with all supervisor and cycle conditions...\n")
    try:
        proj = projects.open(project_path)
        app = proj.find("Application", True)[0]
        
        # 1. Update Auto_Batching_V14
        auto_pous = proj.find("Auto_Batching_V14", True)
        if len(auto_pous) > 0:
            auto_fb = auto_pous[0]
            auto_fb.textual_declaration.replace(st_decl_auto)
            auto_fb.textual_implementation.replace(st_code_auto)
            f.write("Auto_Batching_V14 updated.\n")
            
        # 2. Update Semi_Auto_Batching_V14
        semi_pous = proj.find("Semi_Auto_Batching_V14", True)
        if len(semi_pous) > 0:
            semi_fb = semi_pous[0]
            semi_fb.textual_declaration.replace(st_decl_semi)
            semi_fb.textual_implementation.replace(st_code_semi)
            f.write("Semi_Auto_Batching_V14 updated.\n")
            
        # 3. Remove Batch_Supervisor_V14 if present
        sup_pous = proj.find("Batch_Supervisor_V14", True)
        for s in sup_pous:
            s.remove()
            f.write("Batch_Supervisor_V14 removed.\n")
            
        proj.save()
        proj.close()
        f.write("All updates completed successfully.\n")
    except Exception as e:
        f.write("Error: " + str(e) + "\n")
