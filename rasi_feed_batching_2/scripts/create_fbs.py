import sys
import os

project_path = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\Rasi_feeds_batching.project"
log_path = r"C:\Users\kabish\.gemini\antigravity-ide\brain\6bb09710-7f3e-4443-b187-ad04e16ca8dc\scratch\create_fbs_output.txt"

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
    Transition_Timer : TON;
    Completion_Timer : TON;
    Simulation_Mode : BOOL;
    Sim_Rate : REAL;
    Sim_Timer : TON;
    Start_Sim_Weight : REAL;
    Discharge_Active : BOOL;
END_VAR
"""

st_code_auto = """(* Auto Batching FB V14 *)
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

(* 2. E-STOP PAUSE / HOLD LOGIC *)
IF E_Stop_Active THEN
    Paused_By_EStop := TRUE;
END_IF;

IF Paused_By_EStop THEN
    FOR i := 1 TO 6 DO
        Auto_Bin[i] := FALSE;
        auto_bin_cutoff[i] := FALSE;
        auto_bin_motor[i] := FALSE;
    END_FOR;
    IF E_Stop_Active THEN
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

(* 3. SIMULATION WEIGHT MANAGEMENT *)
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

st_code_semi = """(* Semi-Auto Batching FB V14 *)
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

(* 2. E-STOP PAUSE / HOLD LOGIC *)
IF E_Stop_Active THEN
    Paused_By_EStop := TRUE;
END_IF;

IF Paused_By_EStop THEN
    FOR i := 1 TO 10 DO
        Semi_Auto_Bin[i] := FALSE;
        semi_auto_bin_cutoff[i] := FALSE;
        semi_auto_bin_motor[i] := FALSE;
    END_FOR;
    IF E_Stop_Active THEN
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

(* 3. SIMULATION WEIGHT MANAGEMENT *)
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

st_decl_supervisor = """FUNCTION_BLOCK Batch_Supervisor_V14
VAR_INPUT
    Start_Button : BOOL;
    E_Stop_Active : BOOL;
    Reset : BOOL;
    Cycle_Hold_Active : BOOL;
    Target_Batch_Cycles : INT;
    Auto_Complete : BOOL;
    Semi_Auto_Complete : BOOL;
    Auto_Err : INT;
    Auto_Msg : STRING;
    Semi_Auto_Err : INT;
    Semi_Auto_Msg : STRING;
    load_cell_auto : REAL;
    load_cell_semi_auto : REAL;
    Auto_Initial_Tolerance : REAL;
    Semi_Auto_Initial_Tolerance : REAL;
END_VAR
VAR_OUTPUT
    Internal_FB_Start : BOOL;
    Run : BOOL;
    Current_Batch_Cycle : INT;
    Completed_Batch_Cycles : INT;
    All_Cycles_Complete : BOOL;
    Error_Code : INT;
    Status_Message : STRING;
    Auto_Total_Target_Weight : REAL;
    Semi_Auto_Total_Target_Weight : REAL;
    Auto_Material_Count : INT;
    Semi_Auto_Material_Count : INT;
END_VAR
VAR
    Cycle_Manager_State : INT;
    Duplicate_Found : BOOL;
    Invalid_Material_Range : BOOL;
    Weight_Limit_Error : BOOL;
    i : INT;
    j : INT;
END_VAR
"""

st_code_supervisor = """(* Batch Supervisor FB V14 *)
Duplicate_Found := FALSE;
Invalid_Material_Range := FALSE;
Weight_Limit_Error := FALSE;

(* Calculate Auto Total Target Weight & Material Count *)
Auto_Total_Target_Weight := 0.0;
Auto_Material_Count := 0;
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
            Auto_Total_Target_Weight := Auto_Total_Target_Weight + GVL.Recipe_Weights[GVL.Auto_Bin_Material_Mapping[i]];
            Auto_Material_Count := Auto_Material_Count + 1;
            IF GVL.Recipe_Weights[GVL.Auto_Bin_Material_Mapping[i]] < (GVL.Auto_Bin_Cutoff_Weights[i] + GVL.Auto_Bin_Tolerance[i]) THEN
                Weight_Limit_Error := TRUE;
            END_IF;
        END_IF;
    END_IF;
END_FOR;

(* Calculate Semi-Auto Total Target Weight & Material Count *)
Semi_Auto_Total_Target_Weight := 0.0;
Semi_Auto_Material_Count := 0;
FOR j := 1 TO 10 DO
    IF GVL.Semi_Auto_Bin_Material_Mapping[j] < 0 OR GVL.Semi_Auto_Bin_Material_Mapping[j] > 20 THEN
        Invalid_Material_Range := TRUE;
    END_IF;
    IF GVL.Semi_Auto_Bin_Material_Mapping[j] > 0 AND GVL.Semi_Auto_Bin_Material_Mapping[j] <= 20 THEN
        IF GVL.Recipe_Weights[GVL.Semi_Auto_Bin_Material_Mapping[j]] > 0.0 THEN
            Semi_Auto_Total_Target_Weight := Semi_Auto_Total_Target_Weight + GVL.Recipe_Weights[GVL.Semi_Auto_Bin_Material_Mapping[j]];
            Semi_Auto_Material_Count := Semi_Auto_Material_Count + 1;
            IF GVL.Recipe_Weights[GVL.Semi_Auto_Bin_Material_Mapping[j]] < (GVL.Semi_Auto_Bin_Cutoff_Weights[j] + GVL.Semi_Auto_Bin_Tolerance[j]) THEN
                Weight_Limit_Error := TRUE;
            END_IF;
        END_IF;
    END_IF;
END_FOR;

(* Configuration Error Resolution *)
IF Duplicate_Found THEN
    Error_Code := 1;
    Status_Message := 'Error 1: Duplicate Material ID mapped in Auto and Semi-Auto!';
ELSIF Invalid_Material_Range THEN
    Error_Code := 2;
    Status_Message := 'Error 2: Material Index configuration out of range (1..20)!';
ELSIF Weight_Limit_Error THEN
    Error_Code := 3;
    Status_Message := 'Error 3: Recipe weight is less than Cutoff + Tolerance!';
ELSE
    IF Error_Code <= 3 THEN
        Error_Code := 0;
    END_IF;
END_IF;

(* Hard Reset & Abort *)
IF (Error_Code >= 1 AND Error_Code <= 3) OR Reset THEN
    Internal_FB_Start := FALSE;
    Run := FALSE;
    All_Cycles_Complete := TRUE;
    Cycle_Manager_State := 0;
    GVL.Auto_Active_Target_Weight := 0.0;
    GVL.Auto_Active_Live_Weight := 0.0;
    GVL.Semi_Auto_Active_Target_Weight := 0.0;
    GVL.Semi_Auto_Active_Live_Weight := 0.0;
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
    IF Reset THEN
        Error_Code := 0;
        Current_Batch_Cycle := 0;
        GVL.Current_Batch_Cycle := 0;
        GVL.Target_Batch_Cycles := 0;
        GVL.Start_Button := FALSE;
        Completed_Batch_Cycles := 0;
        Status_Message := 'System Reset Activated';
        All_Cycles_Complete := FALSE;
        GVL.Auto_Active_Mat := 0;
        GVL.Auto_Active_Bin := 0;
        GVL.Semi_Auto_Active_Mat := 0;
        GVL.Semi_Auto_Active_Bin := 0;
        GVL.Auto_Excess_Alarm := FALSE;
        GVL.Semi_Auto_Excess_Alarm := FALSE;
        GVL.Reset := FALSE;
    END_IF;
    RETURN;
END_IF;

(* Cycle Manager State Machine *)
CASE Cycle_Manager_State OF
    0:
        Internal_FB_Start := FALSE;
        All_Cycles_Complete := FALSE;
        Run := FALSE;
        IF Error_Code = 0 AND Status_Message <> 'Error: Target Batch Cycles is 0!' AND Status_Message <> 'Error 4: Scale weight exceeds Initial Tolerance!' THEN
            Status_Message := 'System Ready';
        END_IF;
        IF Start_Button THEN
            IF Target_Batch_Cycles <= 0 THEN
                Run := FALSE;
                Status_Message := 'Error: Target Batch Cycles is 0!';
            ELSIF (load_cell_auto > Auto_Initial_Tolerance OR load_cell_auto < (-Auto_Initial_Tolerance)) OR 
                  (load_cell_semi_auto > Semi_Auto_Initial_Tolerance OR load_cell_semi_auto < (-Semi_Auto_Initial_Tolerance)) THEN
                Run := FALSE;
                Error_Code := 4;
                Status_Message := 'Error 4: Scale weight exceeds Initial Tolerance!';
            ELSE
                Error_Code := 0;
                Current_Batch_Cycle := 1;
                GVL.Current_Batch_Cycle := 1;
                Completed_Batch_Cycles := 0;
                Run := TRUE;
                Cycle_Manager_State := 1;
            END_IF;
        END_IF;
        
    1:
        Internal_FB_Start := TRUE;
        Run := TRUE;
        Status_Message := CONCAT('Running Batch Cycle ', INT_TO_STRING(Current_Batch_Cycle));
        IF Auto_Complete AND Semi_Auto_Complete THEN
            Cycle_Manager_State := 2;
        END_IF;
        
    2:
        Completed_Batch_Cycles := Current_Batch_Cycle;
        Run := TRUE;
        IF Current_Batch_Cycle < Target_Batch_Cycles AND Error_Code = 0 THEN
            GVL.Cycle_Hold_Active := TRUE;
            Internal_FB_Start := FALSE;
            Cycle_Manager_State := 5;
        ELSE
            Cycle_Manager_State := 4;
        END_IF;
        
    5:
        Internal_FB_Start := FALSE;
        Run := TRUE;
        Status_Message := CONCAT('Cycle ', CONCAT(INT_TO_STRING(Current_Batch_Cycle), ' Complete. Empty scale to 0 and release Cycle Hold.'));
        IF NOT GVL.Cycle_Hold_Active THEN
            IF (load_cell_auto > Auto_Initial_Tolerance OR load_cell_auto < (-Auto_Initial_Tolerance)) OR 
               (load_cell_semi_auto > Semi_Auto_Initial_Tolerance OR load_cell_semi_auto < (-Semi_Auto_Initial_Tolerance)) THEN
                Run := FALSE;
                Error_Code := 4;
                Status_Message := 'Error 4: Scale weight exceeds Initial Tolerance!';
                GVL.Cycle_Hold_Active := TRUE;
            ELSE
                Error_Code := 0;
                Current_Batch_Cycle := Current_Batch_Cycle + 1;
                GVL.Current_Batch_Cycle := Current_Batch_Cycle;
                Cycle_Manager_State := 1;
            END_IF;
        END_IF;
        
    4:
        Internal_FB_Start := FALSE;
        All_Cycles_Complete := TRUE;
        Run := FALSE;
        GVL.Start_Button := FALSE;
        Status_Message := 'All Batch Cycles Completed';
        Cycle_Manager_State := 0;
END_CASE;

(* Runtime Error Mapping & Aggregation *)
IF Auto_Err <> 0 THEN
    Error_Code := Auto_Err;
    Status_Message := CONCAT('Auto Error: ', Auto_Msg);
    Run := FALSE;
    GVL.Start_Button := FALSE;
ELSIF Semi_Auto_Err <> 0 THEN
    Error_Code := Semi_Auto_Err;
    Status_Message := CONCAT('Semi-Auto Error: ', Semi_Auto_Msg);
    Run := FALSE;
    GVL.Start_Button := FALSE;
ELSIF Cycle_Manager_State = 0 AND Error_Code <= 3 THEN
    Error_Code := 0;
END_IF;
"""

with open(log_path, "w") as f:
    f.write("Starting creation of V14 blocks...\n")
    try:
        proj = projects.open(project_path)
        app = proj.find("Application", True)[0]
        
        # Check and create/replace Auto_Batching_V14
        auto_pous = proj.find("Auto_Batching_V14", True)
        if len(auto_pous) == 0:
            f.write("Creating Auto_Batching_V14...\n")
            auto_fb = app.create_pou("Auto_Batching_V14", PouType.FunctionBlock)
        else:
            auto_fb = auto_pous[0]
        auto_fb.textual_declaration.replace(st_decl_auto)
        auto_fb.textual_implementation.replace(st_code_auto)
        
        # Check and create/replace Semi_Auto_Batching_V14
        semi_pous = proj.find("Semi_Auto_Batching_V14", True)
        if len(semi_pous) == 0:
            f.write("Creating Semi_Auto_Batching_V14...\n")
            semi_fb = app.create_pou("Semi_Auto_Batching_V14", PouType.FunctionBlock)
        else:
            semi_fb = semi_pous[0]
        semi_fb.textual_declaration.replace(st_decl_semi)
        semi_fb.textual_implementation.replace(st_code_semi)
        
        # Check and create/replace Batch_Supervisor_V14
        sup_pous = proj.find("Batch_Supervisor_V14", True)
        if len(sup_pous) == 0:
            f.write("Creating Batch_Supervisor_V14...\n")
            sup_fb = app.create_pou("Batch_Supervisor_V14", PouType.FunctionBlock)
        else:
            sup_fb = sup_pous[0]
        sup_fb.textual_declaration.replace(st_decl_supervisor)
        sup_fb.textual_implementation.replace(st_code_supervisor)
        
        proj.save()
        proj.close()
        f.write("V14 Function Blocks saved successfully.\n")
    except Exception as e:
        f.write("Error: " + str(e) + "\n")
