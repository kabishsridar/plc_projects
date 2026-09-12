import sys
import os

project_path = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\Rasi_feeds_batching.project"
log_path = r"C:\Users\kabish\.gemini\antigravity-ide\brain\6bb09710-7f3e-4443-b187-ad04e16ca8dc\scratch\status_steps_log.txt"

# 1. GVL Content with Step indicators and Status Messages
gvl_content = """{attribute 'qualified_only'}
VAR_GLOBAL
    Recipe_Weights AT %MD100 : ARRAY[1..20] OF REAL;
	Auto_Bin_Material_Mapping AT %MW50: ARRAY[1..6] OF INT;
	Semi_Auto_Bin_Material_Mapping AT %MW60: ARRAY[1..10] OF INT;
	Auto_Coarse_To_Fine_Speed AT %MD120: ARRAY[1..6] OF REAL;
	Semi_Auto_Coarse_To_Fine_Speed AT %MD130: ARRAY[1..10] OF REAL;
	Auto_Bin_Tolerance AT %MD150: ARRAY[1..6] OF REAL;
	Semi_Auto_Bin_Tolerance AT %MD160: ARRAY[1..10] OF REAL;
	Start_Button AT %MX2.0: BOOL;
	E_Stop_Active AT %MX2.1: BOOL;
	Reset AT %MX2.3: BOOL;
	Cycle_Hold_Active AT %MX2.4: BOOL;
	Auto_Active_Mat AT %MW70: INT;
	Auto_Active_Bin AT %MW71: INT;
	Semi_Auto_Active_Mat AT %MW72: INT;
	Semi_Auto_Active_Bin AT %MW73: INT;
	Target_Batch_Cycles AT %MW74: INT;
	Current_Batch_Cycle AT %MW75: INT;
	Error_Code AT %MW76: INT;
	Run AT %MX2.5 : BOOL;
	load_cell_auto AT %MD174 : REAL;
	load_cell_semi_auto AT %MD175 : REAL;
	Auto_Initial_Tolerance AT %MD176 : REAL;
	Semi_Auto_Initial_Tolerance AT %MD178 : REAL;
	Auto_Total_Target_Weight AT %MD180 : REAL;
	Semi_Auto_Total_Target_Weight AT %MD184 : REAL;
	Auto_Material_Count AT %MW77 : INT;
	Semi_Auto_Material_Count AT %MW78 : INT;
	Auto_Current_Step AT %MW80 : INT;
	Semi_Auto_Current_Step AT %MW81 : INT;
	Auto_Active_Target_Weight AT %MD220 : REAL;
	Semi_Auto_Active_Target_Weight AT %MD224 : REAL;
	Auto_Active_Live_Weight AT %MD228 : REAL;
	Semi_Auto_Active_Live_Weight AT %MD232 : REAL;
	Auto_Excess_Allowed AT %MX2.6 : BOOL;
	Semi_Auto_Excess_Allowed AT %MX2.9 : BOOL;
	Auto_Excess_Alarm AT %MX2.7 : BOOL;
	Semi_Auto_Excess_Alarm AT %MX2.8 : BOOL;
	Auto_Inter_Bin_Delay AT %MD190 : TIME;
	Semi_Auto_Inter_Bin_Delay AT %MD194 : TIME;
	Auto_Sequence_Complete AT %MX3.0 : BOOL;
	Semi_Auto_Sequence_Complete AT %MX3.1 : BOOL;
	Auto_Status_Message : STRING(80);
	Semi_Auto_Status_Message : STRING(80);
	
	(* 8 Process Output and Weight Arrays *)
	Auto_Bin : ARRAY[1..6] OF BOOL;
	auto_bin_cutoff : ARRAY[1..6] OF BOOL;
	auto_bin_motor : ARRAY[1..6] OF BOOL;
	Semi_Auto_Bin : ARRAY[1..10] OF BOOL;
	semi_auto_bin_cutoff : ARRAY[1..10] OF BOOL;
	semi_auto_bin_motor : ARRAY[1..10] OF BOOL;
	Auto_Weights : ARRAY[1..6] OF REAL;
	Semi_Auto_Weights : ARRAY[1..10] OF REAL;
END_VAR
"""

# 2. Auto_Batching_V14 Declaration with Current_Step
decl_auto_v14 = """FUNCTION_BLOCK Auto_Batching_V14
VAR_INPUT
    Start_Button : BOOL;
    E_Stop_Active : BOOL;
    Reset : BOOL;
    Auto_Bin_Material_Mapping : ARRAY[1..6] OF INT;
    Auto_Coarse_To_Fine_Speed : ARRAY[1..6] OF REAL;
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
    Current_Step : INT;
    Excess_Alarm : BOOL;
    Error_Code : INT;
    Status_Message : STRING(80);
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

# 3. Auto_Batching_V14 Implementation with Detailed Step & Diagnostics
code_auto_v14 = """(* Auto Batching FB V14 with Full Diagnostics, Step Tracking, and Precise Status Reporting *)

Effective_Delay := Inter_Bin_Delay;
IF Effective_Delay = T#0S THEN
    Effective_Delay := T#2S;
END_IF;

(* Update Output Step *)
Current_Step := Step;

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
    GVL.Target_Batch_Cycles := 0;
    GVL.Start_Button := FALSE;
    GVL.Run := FALSE;
    GVL.Cycle_Hold_Active := FALSE;
    GVL.Auto_Active_Mat := 0;
    GVL.Auto_Active_Bin := 0;
    GVL.Auto_Excess_Alarm := FALSE;
    Step := 0;
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
        Status_Message := CONCAT('Auto [PAUSED]: E-Stop Active at Step ', INT_TO_STRING(Step));
    ELSE
        Status_Message := CONCAT('Auto [HOLD]: E-Stop Cleared. Press Start to Resume Step ', INT_TO_STRING(Step));
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
        GVL.Auto_Sequence_Complete := FALSE;
        
        IF GVL.Error_Code = 0 THEN
            Status_Message := 'Auto [State 0 - Idle]: Ready - Waiting for Start Button';
        END_IF;
        
        IF Start_Button OR GVL.Start_Button THEN
            IF NOT E_Stop_Active OR NOT GVL.E_Stop_Active THEN
                GVL.Run := FALSE;
                Status_Message := 'Auto [State 0]: Cannot Start - Emergency Stop Contact Open!';
            ELSIF GVL.Target_Batch_Cycles <= 0 THEN
                GVL.Run := FALSE;
                Status_Message := 'Auto [State 0]: Cannot Start - Target Batch Cycles is 0!';
            ELSIF (GVL.load_cell_auto > GVL.Auto_Initial_Tolerance OR GVL.load_cell_auto < (-GVL.Auto_Initial_Tolerance)) OR 
                  (GVL.load_cell_semi_auto > GVL.Semi_Auto_Initial_Tolerance OR GVL.load_cell_semi_auto < (-GVL.Semi_Auto_Initial_Tolerance)) THEN
                GVL.Run := FALSE;
                GVL.Error_Code := 4;
                Error_Code := 4;
                Status_Message := 'Auto [State 0]: Error 4 - Scale weight exceeds Initial Tolerance!';
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
        
        (* Both Auto and Semi-Auto must complete to finish the cycle *)
        IF Sequence_Complete AND GVL.Semi_Auto_Sequence_Complete THEN
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
        Status_Message := CONCAT('Auto [State 5 - Hold]: Cycle ', CONCAT(INT_TO_STRING(GVL.Current_Batch_Cycle), ' Complete. Empty scale to 0 and release Cycle Hold.'));
        
        IF NOT GVL.Cycle_Hold_Active THEN
            IF (GVL.load_cell_auto > GVL.Auto_Initial_Tolerance OR GVL.load_cell_auto < (-GVL.Auto_Initial_Tolerance)) OR 
               (GVL.load_cell_semi_auto > GVL.Semi_Auto_Initial_Tolerance OR GVL.load_cell_semi_auto < (-GVL.Semi_Auto_Initial_Tolerance)) THEN
                GVL.Run := FALSE;
                GVL.Error_Code := 4;
                Error_Code := 4;
                Status_Message := 'Auto [State 5]: Error 4 - Scale not zeroed! Tare scale before continuing.';
                GVL.Cycle_Hold_Active := TRUE;
            ELSE
                GVL.Error_Code := 0;
                Error_Code := 0;
                GVL.Current_Batch_Cycle := GVL.Current_Batch_Cycle + 1;
                Sequence_Complete := FALSE;
                GVL.Auto_Sequence_Complete := FALSE;
                GVL.Semi_Auto_Sequence_Complete := FALSE;
                Step := 0;
                Internal_FB_Start := TRUE;
                Cycle_Manager_State := 1;
            END_IF;
        END_IF;
        
    4: (* ALL CYCLES COMPLETE *)
        Internal_FB_Start := FALSE;
        GVL.Run := FALSE;
        GVL.Start_Button := FALSE;
        GVL.Auto_Sequence_Complete := FALSE;
        GVL.Semi_Auto_Sequence_Complete := FALSE;
        Status_Message := CONCAT('Auto [State 4 - Finished]: All ', CONCAT(INT_TO_STRING(GVL.Target_Batch_Cycles), ' Batch Cycles Completed Successfully'));
        Cycle_Manager_State := 0;
END_CASE;

(* 5. AUTO SILOS 1..6 POURING SEQUENCE WITH DETAILED STATUS *)
IF Step = 0 AND Internal_FB_Start THEN
    Step := 1;
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

CASE Step OF
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
        Mat_Idx := Auto_Bin_Material_Mapping[Step];
        
        IF (Mat_Idx = 0 OR (Mat_Idx <= 20 AND GVL.Recipe_Weights[Mat_Idx] = 0.0)) AND GVL.Auto_Active_Target_Weight = 0.0 THEN
            Status_Message := CONCAT('Auto [Step ', CONCAT(INT_TO_STRING(Step), ']: Silo Skipped (Target = 0)'));
            IF Step = 6 THEN
                Step := 7;
            ELSE
                Step := Step + 1;
            END_IF;
        ELSE
            IF Mat_Idx > 0 AND Mat_Idx <= 20 AND GVL.Recipe_Weights[Mat_Idx] > 0.0 THEN
                target_weight := GVL.Recipe_Weights[Mat_Idx];
            ELSE
                target_weight := GVL.Auto_Active_Target_Weight;
            END_IF;
            
            Active_Target_Weight := target_weight;
            GVL.Auto_Active_Target_Weight := target_weight;
            
            cutoff_trigger_weight := target_weight - Auto_Coarse_To_Fine_Speed[Step];
            min_tol_weight := target_weight - Auto_Bin_Tolerance[Step];
            max_tol_weight := target_weight + Auto_Bin_Tolerance[Step];
            
            actual_bin := load_cell_value - bin_last_weight;
            Actual_Weights[Step] := actual_bin;
            Active_Live_Weight := actual_bin;
            GVL.Auto_Active_Live_Weight := actual_bin;
            Active_Material_ID := Mat_Idx;
            Active_Bin_ID := Step;
            
            IF load_cell_value > 500.0 THEN
                Error_Code := 21;
                GVL.Error_Code := 21;
                Status_Message := CONCAT('Auto [Step ', CONCAT(INT_TO_STRING(Step), ']: STUCK - Error 21: Scale Overloaded (> 500 kg)!'));
                Sequence_Complete := TRUE;
                GVL.Auto_Sequence_Complete := TRUE;
                Paused_By_EStop := TRUE;
            END_IF;
            
            IF actual_bin < cutoff_trigger_weight THEN
                Auto_Bin[Step] := TRUE;
                auto_bin_cutoff[Step] := FALSE;
                auto_bin_motor[Step] := TRUE;
                Excess_Alarm := FALSE;
                Status_Message := CONCAT('Auto [Step ', CONCAT(INT_TO_STRING(Step), ']: Coarse Feeding'));
            ELSIF actual_bin < min_tol_weight THEN
                Auto_Bin[Step] := FALSE;
                auto_bin_cutoff[Step] := TRUE;
                auto_bin_motor[Step] := TRUE;
                Excess_Alarm := FALSE;
                Status_Message := CONCAT('Auto [Step ', CONCAT(INT_TO_STRING(Step), ']: Fine Feeding'));
            ELSIF actual_bin > max_tol_weight THEN
                Auto_Bin[Step] := FALSE;
                auto_bin_cutoff[Step] := FALSE;
                auto_bin_motor[Step] := FALSE;
                IF Excess_Allowed THEN
                    Excess_Alarm := FALSE;
                    Status_Message := CONCAT('Auto [Step ', CONCAT(INT_TO_STRING(Step), ']: Excess Allowed - Advancing'));
                    bin_last_weight := load_cell_value;
                    IF Step = 6 THEN
                        Step := 7;
                    ELSE
                        Step := Step + 1;
                    END_IF;
                ELSE
                    Excess_Alarm := TRUE;
                    Status_Message := CONCAT('Auto [Step ', CONCAT(INT_TO_STRING(Step), ']: STUCK - Excess Weight! Reduce weight or enable Excess Allowed.'));
                END_IF;
            ELSE
                Auto_Bin[Step] := FALSE;
                auto_bin_cutoff[Step] := FALSE;
                auto_bin_motor[Step] := FALSE;
                Excess_Alarm := FALSE;
                bin_last_weight := load_cell_value;
                Status_Message := CONCAT('Auto [Step ', CONCAT(INT_TO_STRING(Step), ']: Target Reached - Advancing'));
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
        Excess_Alarm := FALSE;
        Status_Message := 'Auto [Step 7]: Settling Delay in progress...';
        Completion_Timer(IN := TRUE, PT := Effective_Delay);
        IF Completion_Timer.Q THEN
            Completion_Timer(IN := FALSE);
            Step := 8;
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
        
        IF NOT Internal_FB_Start THEN
            Step := 0;
            Sequence_Complete := FALSE;
            GVL.Auto_Sequence_Complete := FALSE;
            FOR i := 1 TO 6 DO
                Actual_Weights[i] := 0.0;
            END_FOR;
        END_IF;
END_CASE;
"""

# 4. Semi_Auto_Batching_V14 Declaration with Current_Step
decl_semi_v14 = """FUNCTION_BLOCK Semi_Auto_Batching_V14
VAR_INPUT
    Start_Button : BOOL;
    E_Stop_Active : BOOL;
    Reset : BOOL;
    Semi_Auto_Bin_Material_Mapping : ARRAY[1..10] OF INT;
    Semi_Auto_Coarse_To_Fine_Speed : ARRAY[1..10] OF REAL;
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
    Current_Step : INT;
    Excess_Alarm : BOOL;
    Error_Code : INT;
    Status_Message : STRING(80);
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

# 5. Semi_Auto_Batching_V14 Implementation with Detailed Step & Diagnostics
code_semi_v14 = """(* Semi-Auto Batching FB V14 with Full Diagnostics, Step Tracking, and Precise Status Reporting *)

Effective_Delay := Inter_Bin_Delay;
IF Effective_Delay = T#0S THEN
    Effective_Delay := T#2S;
END_IF;

(* Update Output Step *)
Current_Step := Step;

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
    Step := 0;
    Current_Step := 0;
    bin_last_weight := 0.0;
    Start_Sim_Weight := 0.0;
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
        Status_Message := CONCAT('Semi-Auto [PAUSED]: E-Stop Active at Step ', INT_TO_STRING(Step));
    ELSE
        Status_Message := CONCAT('Semi-Auto [HOLD]: E-Stop Cleared. Press Start to Resume Step ', INT_TO_STRING(Step));
        IF Start_Button OR GVL.Start_Button THEN
            Paused_By_EStop := FALSE;
        END_IF;
    END_IF;
    Sim_Timer(IN := FALSE);
    Transition_Timer(IN := FALSE);
    Completion_Timer(IN := FALSE);
    RETURN;
END_IF;

(* 4. CYCLE HOLD RESET *)
IF GVL.Cycle_Hold_Active THEN
    Step := 0;
    Sequence_Complete := FALSE;
    GVL.Semi_Auto_Sequence_Complete := FALSE;
    Status_Message := 'Semi-Auto [Cycle Hold]: Waiting for next cycle...';
END_IF;

(* 5. SEQUENCE START (WHEN SYSTEM IS IN RUN MODE) *)
IF Step = 0 AND (GVL.Run OR Start_Button) AND GVL.Cycle_Hold_Active = FALSE AND NOT GVL.Semi_Auto_Sequence_Complete THEN
    Step := 1;
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

CASE Step OF
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
        IF Error_Code = 0 AND NOT GVL.Cycle_Hold_Active THEN 
            Status_Message := 'Semi-Auto [Step 0 - Idle]: Ready - Waiting for Run Signal'; 
        END_IF;
        
    1..10:
        Mat_Idx := Semi_Auto_Bin_Material_Mapping[Step];
        
        IF (Mat_Idx = 0 OR (Mat_Idx <= 20 AND GVL.Recipe_Weights[Mat_Idx] = 0.0)) AND GVL.Semi_Auto_Active_Target_Weight = 0.0 THEN
            Status_Message := CONCAT('Semi-Auto [Step ', CONCAT(INT_TO_STRING(Step), ']: Silo Skipped (Target = 0)'));
            IF Step = 10 THEN
                Step := 31;
            ELSE
                Step := Step + 1;
            END_IF;
        ELSE
            IF Mat_Idx > 0 AND Mat_Idx <= 20 AND GVL.Recipe_Weights[Mat_Idx] > 0.0 THEN
                target_weight := GVL.Recipe_Weights[Mat_Idx];
            ELSE
                target_weight := GVL.Semi_Auto_Active_Target_Weight;
            END_IF;
            
            Active_Target_Weight := target_weight;
            GVL.Semi_Auto_Active_Target_Weight := target_weight;
            
            cutoff_trigger_weight := target_weight - Semi_Auto_Coarse_To_Fine_Speed[Step];
            min_tol_weight := target_weight - Semi_Auto_Bin_Tolerance[Step];
            max_tol_weight := target_weight + Semi_Auto_Bin_Tolerance[Step];
            
            actual_bin := load_cell_value - bin_last_weight;
            Actual_Weights[Step] := actual_bin;
            Active_Live_Weight := actual_bin;
            GVL.Semi_Auto_Active_Live_Weight := actual_bin;
            Active_Material_ID := Mat_Idx;
            Active_Bin_ID := Step;
            
            IF load_cell_value > 500.0 THEN
                Error_Code := 21;
                GVL.Error_Code := 21;
                Status_Message := CONCAT('Semi-Auto [Step ', CONCAT(INT_TO_STRING(Step), ']: STUCK - Error 21: Scale Overloaded (> 500 kg)!'));
                Sequence_Complete := TRUE;
                GVL.Semi_Auto_Sequence_Complete := TRUE;
                Paused_By_EStop := TRUE;
            END_IF;
            
            IF actual_bin < cutoff_trigger_weight THEN
                Semi_Auto_Bin[Step] := TRUE;
                semi_auto_bin_cutoff[Step] := FALSE;
                semi_auto_bin_motor[Step] := TRUE;
                Excess_Alarm := FALSE;
                Status_Message := CONCAT('Semi-Auto [Step ', CONCAT(INT_TO_STRING(Step), ']: Coarse Feeding'));
            ELSIF actual_bin < min_tol_weight THEN
                Semi_Auto_Bin[Step] := FALSE;
                semi_auto_bin_cutoff[Step] := TRUE;
                semi_auto_bin_motor[Step] := TRUE;
                Excess_Alarm := FALSE;
                Status_Message := CONCAT('Semi-Auto [Step ', CONCAT(INT_TO_STRING(Step), ']: Fine Feeding'));
            ELSIF actual_bin > max_tol_weight THEN
                Semi_Auto_Bin[Step] := FALSE;
                semi_auto_bin_cutoff[Step] := FALSE;
                semi_auto_bin_motor[Step] := FALSE;
                IF Excess_Allowed THEN
                    Excess_Alarm := FALSE;
                    Status_Message := CONCAT('Semi-Auto [Step ', CONCAT(INT_TO_STRING(Step), ']: Excess Allowed - Advancing'));
                    bin_last_weight := load_cell_value;
                    IF Step = 10 THEN
                        Step := 31;
                    ELSE
                        Step := Step + 1;
                    END_IF;
                ELSE
                    Excess_Alarm := TRUE;
                    Status_Message := CONCAT('Semi-Auto [Step ', CONCAT(INT_TO_STRING(Step), ']: STUCK - Excess Weight! Reduce weight or enable Excess Allowed.'));
                END_IF;
            ELSE
                Semi_Auto_Bin[Step] := FALSE;
                semi_auto_bin_cutoff[Step] := FALSE;
                semi_auto_bin_motor[Step] := FALSE;
                Excess_Alarm := FALSE;
                bin_last_weight := load_cell_value;
                Status_Message := CONCAT('Semi-Auto [Step ', CONCAT(INT_TO_STRING(Step), ']: Target Reached - Advancing'));
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
        Excess_Alarm := FALSE;
        Status_Message := 'Semi-Auto [Step 31]: Settling Delay in progress...';
        Completion_Timer(IN := TRUE, PT := Effective_Delay);
        IF Completion_Timer.Q THEN
            Completion_Timer(IN := FALSE);
            Step := 32;
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
        
        IF NOT GVL.Run THEN
            Step := 0;
            Sequence_Complete := FALSE;
            GVL.Semi_Auto_Sequence_Complete := FALSE;
            FOR i := 1 TO 10 DO
                Actual_Weights[i] := 0.0;
            END_FOR;
        END_IF;
END_CASE;
"""

# 6. PLCopen XML for batching14 with Current_Step and Status_Message wired to GVL
b14_diag_xml_path = r"C:\Users\kabish\.gemini\antigravity-ide\brain\6bb09710-7f3e-4443-b187-ad04e16ca8dc\scratch\batching14_diag.xml"
b14_diag_xml = """<?xml version="1.0" encoding="utf-8"?>
<project xmlns="http://www.plcopen.org/xml/tc6_0200">
  <fileHeader companyName="" productName="Automation Builder 2.7 - Basic" productVersion="Automation Builder 2.7" creationDateTime="2026-08-29T13:40:00" />
  <contentHeader name="Rasi_feeds_batching.project">
    <coordinateInfo>
      <fbd><scaling x="1" y="1" /></fbd>
      <ld><scaling x="1" y="1" /></ld>
      <sfc><scaling x="1" y="1" /></sfc>
    </coordinateInfo>
  </contentHeader>
  <types>
    <dataTypes />
    <pous>
      <pou name="batching14" pouType="program">
        <interface>
          <localVars>
            <variable name="Auto_Ctrl"><type><derived name="Auto_Batching_V14" /></type></variable>
            <variable name="Semi_Auto_Ctrl"><type><derived name="Semi_Auto_Batching_V14" /></type></variable>
            <variable name="Auto_Complete"><type><BOOL /></type></variable>
            <variable name="Semi_Auto_Complete"><type><BOOL /></type></variable>
            <variable name="Auto_Err"><type><INT /></type></variable>
            <variable name="Semi_Auto_Err"><type><INT /></type></variable>
          </localVars>
        </interface>
        <body>
          <FBD>
            <vendorElement localId="10000000000">
              <position x="0" y="0" />
              <alternativeText><xhtml xmlns="http://www.w3.org/1999/xhtml">FBD Implementation Attributes</xhtml></alternativeText>
              <addData>
                <data name="http://www.3s-software.com/plcopenxml/fbd/implementationattributes" handleUnknown="implementation">
                  <fbdattributes xmlns=""><attribute name="BoxInputFlagsSupported" value="true" /></fbdattributes>
                </data>
              </addData>
            </vendorElement>

            <!-- Network 1: Auto_Ctrl (Auto_Batching_V14) -->
            <block localId="1" typeName="Auto_Batching_V14" instanceName="Auto_Ctrl">
              <position x="300" y="100" />
              <inputVariables>
                <variable formalParameter="Start_Button"><connectionPointIn><connection refLocalId="10" /></connectionPointIn></variable>
                <variable formalParameter="E_Stop_Active"><connectionPointIn><connection refLocalId="11" /></connectionPointIn></variable>
                <variable formalParameter="Reset"><connectionPointIn><connection refLocalId="12" /></connectionPointIn></variable>
                <variable formalParameter="Auto_Bin_Material_Mapping"><connectionPointIn><connection refLocalId="13" /></connectionPointIn></variable>
                <variable formalParameter="Auto_Coarse_To_Fine_Speed"><connectionPointIn><connection refLocalId="14" /></connectionPointIn></variable>
                <variable formalParameter="Auto_Bin_Tolerance"><connectionPointIn><connection refLocalId="15" /></connectionPointIn></variable>
                <variable formalParameter="Inter_Bin_Delay"><connectionPointIn><connection refLocalId="16" /></connectionPointIn></variable>
                <variable formalParameter="Excess_Allowed"><connectionPointIn><connection refLocalId="17" /></connectionPointIn></variable>
              </inputVariables>
              <inOutVariables>
                <variable formalParameter="load_cell_value"><connectionPointIn><connection refLocalId="18" /></connectionPointIn></variable>
              </inOutVariables>
              <outputVariables>
                <variable formalParameter="Auto_Bin" />
                <variable formalParameter="auto_bin_cutoff" />
                <variable formalParameter="auto_bin_motor" />
                <variable formalParameter="Actual_Weights" />
                <variable formalParameter="Sequence_Complete" />
                <variable formalParameter="Active_Material_ID" />
                <variable formalParameter="Active_Bin_ID" />
                <variable formalParameter="Active_Target_Weight" />
                <variable formalParameter="Active_Live_Weight" />
                <variable formalParameter="Current_Step" />
                <variable formalParameter="Excess_Alarm" />
                <variable formalParameter="Error_Code" />
                <variable formalParameter="Status_Message" />
              </outputVariables>
            </block>
            <!-- InVariables for Auto_Ctrl -->
            <inVariable localId="10"><position x="50" y="100" /><connectionPointOut /><expression>GVL.Start_Button</expression></inVariable>
            <inVariable localId="11"><position x="50" y="120" /><connectionPointOut /><expression>GVL.E_Stop_Active</expression></inVariable>
            <inVariable localId="12"><position x="50" y="140" /><connectionPointOut /><expression>GVL.Reset</expression></inVariable>
            <inVariable localId="13"><position x="50" y="160" /><connectionPointOut /><expression>GVL.Auto_Bin_Material_Mapping</expression></inVariable>
            <inVariable localId="14"><position x="50" y="180" /><connectionPointOut /><expression>GVL.Auto_Coarse_To_Fine_Speed</expression></inVariable>
            <inVariable localId="15"><position x="50" y="200" /><connectionPointOut /><expression>GVL.Auto_Bin_Tolerance</expression></inVariable>
            <inVariable localId="16"><position x="50" y="220" /><connectionPointOut /><expression>GVL.Auto_Inter_Bin_Delay</expression></inVariable>
            <inVariable localId="17"><position x="50" y="240" /><connectionPointOut /><expression>GVL.Auto_Excess_Allowed</expression></inVariable>
            <inVariable localId="18"><position x="50" y="260" /><connectionPointOut /><expression>GVL.load_cell_auto</expression></inVariable>
            <!-- OutVariables for Auto_Ctrl -->
            <outVariable localId="30"><position x="650" y="100" /><connectionPointIn><connection refLocalId="1" formalParameter="Auto_Bin" /></connectionPointIn><expression>GVL.Auto_Bin</expression></outVariable>
            <outVariable localId="31"><position x="650" y="120" /><connectionPointIn><connection refLocalId="1" formalParameter="auto_bin_cutoff" /></connectionPointIn><expression>GVL.auto_bin_cutoff</expression></outVariable>
            <outVariable localId="32"><position x="650" y="140" /><connectionPointIn><connection refLocalId="1" formalParameter="auto_bin_motor" /></connectionPointIn><expression>GVL.auto_bin_motor</expression></outVariable>
            <outVariable localId="33"><position x="650" y="160" /><connectionPointIn><connection refLocalId="1" formalParameter="Actual_Weights" /></connectionPointIn><expression>GVL.Auto_Weights</expression></outVariable>
            <outVariable localId="34"><position x="650" y="180" /><connectionPointIn><connection refLocalId="1" formalParameter="Sequence_Complete" /></connectionPointIn><expression>Auto_Complete</expression></outVariable>
            <outVariable localId="35"><position x="650" y="200" /><connectionPointIn><connection refLocalId="1" formalParameter="Active_Material_ID" /></connectionPointIn><expression>GVL.Auto_Active_Mat</expression></outVariable>
            <outVariable localId="36"><position x="650" y="220" /><connectionPointIn><connection refLocalId="1" formalParameter="Active_Bin_ID" /></connectionPointIn><expression>GVL.Auto_Active_Bin</expression></outVariable>
            <outVariable localId="37"><position x="650" y="240" /><connectionPointIn><connection refLocalId="1" formalParameter="Active_Target_Weight" /></connectionPointIn><expression>GVL.Auto_Active_Target_Weight</expression></outVariable>
            <outVariable localId="38"><position x="650" y="260" /><connectionPointIn><connection refLocalId="1" formalParameter="Active_Live_Weight" /></connectionPointIn><expression>GVL.Auto_Active_Live_Weight</expression></outVariable>
            <outVariable localId="39"><position x="650" y="280" /><connectionPointIn><connection refLocalId="1" formalParameter="Current_Step" /></connectionPointIn><expression>GVL.Auto_Current_Step</expression></outVariable>
            <outVariable localId="40"><position x="650" y="300" /><connectionPointIn><connection refLocalId="1" formalParameter="Excess_Alarm" /></connectionPointIn><expression>GVL.Auto_Excess_Alarm</expression></outVariable>
            <outVariable localId="41"><position x="650" y="320" /><connectionPointIn><connection refLocalId="1" formalParameter="Error_Code" /></connectionPointIn><expression>Auto_Err</expression></outVariable>
            <outVariable localId="42"><position x="650" y="340" /><connectionPointIn><connection refLocalId="1" formalParameter="Status_Message" /></connectionPointIn><expression>GVL.Auto_Status_Message</expression></outVariable>

            <!-- Network 2: Semi_Auto_Ctrl (Semi_Auto_Batching_V14) -->
            <block localId="2" typeName="Semi_Auto_Batching_V14" instanceName="Semi_Auto_Ctrl">
              <position x="300" y="500" />
              <inputVariables>
                <variable formalParameter="Start_Button"><connectionPointIn><connection refLocalId="50" /></connectionPointIn></variable>
                <variable formalParameter="E_Stop_Active"><connectionPointIn><connection refLocalId="51" /></connectionPointIn></variable>
                <variable formalParameter="Reset"><connectionPointIn><connection refLocalId="52" /></connectionPointIn></variable>
                <variable formalParameter="Semi_Auto_Bin_Material_Mapping"><connectionPointIn><connection refLocalId="53" /></connectionPointIn></variable>
                <variable formalParameter="Semi_Auto_Coarse_To_Fine_Speed"><connectionPointIn><connection refLocalId="54" /></connectionPointIn></variable>
                <variable formalParameter="Semi_Auto_Bin_Tolerance"><connectionPointIn><connection refLocalId="55" /></connectionPointIn></variable>
                <variable formalParameter="Inter_Bin_Delay"><connectionPointIn><connection refLocalId="56" /></connectionPointIn></variable>
                <variable formalParameter="Excess_Allowed"><connectionPointIn><connection refLocalId="57" /></connectionPointIn></variable>
              </inputVariables>
              <inOutVariables>
                <variable formalParameter="load_cell_value"><connectionPointIn><connection refLocalId="58" /></connectionPointIn></variable>
              </inOutVariables>
              <outputVariables>
                <variable formalParameter="Semi_Auto_Bin" />
                <variable formalParameter="semi_auto_bin_cutoff" />
                <variable formalParameter="semi_auto_bin_motor" />
                <variable formalParameter="Actual_Weights" />
                <variable formalParameter="Sequence_Complete" />
                <variable formalParameter="Active_Material_ID" />
                <variable formalParameter="Active_Bin_ID" />
                <variable formalParameter="Active_Target_Weight" />
                <variable formalParameter="Active_Live_Weight" />
                <variable formalParameter="Current_Step" />
                <variable formalParameter="Excess_Alarm" />
                <variable formalParameter="Error_Code" />
                <variable formalParameter="Status_Message" />
              </outputVariables>
            </block>
            <!-- InVariables for Semi_Auto_Ctrl -->
            <inVariable localId="50"><position x="50" y="500" /><connectionPointOut /><expression>GVL.Start_Button</expression></inVariable>
            <inVariable localId="51"><position x="50" y="520" /><connectionPointOut /><expression>GVL.E_Stop_Active</expression></inVariable>
            <inVariable localId="52"><position x="50" y="540" /><connectionPointOut /><expression>GVL.Reset</expression></inVariable>
            <inVariable localId="53"><position x="50" y="560" /><connectionPointOut /><expression>GVL.Semi_Auto_Bin_Material_Mapping</expression></inVariable>
            <inVariable localId="54"><position x="50" y="580" /><connectionPointOut /><expression>GVL.Semi_Auto_Coarse_To_Fine_Speed</expression></inVariable>
            <inVariable localId="55"><position x="50" y="600" /><connectionPointOut /><expression>GVL.Semi_Auto_Bin_Tolerance</expression></inVariable>
            <inVariable localId="56"><position x="50" y="620" /><connectionPointOut /><expression>GVL.Semi_Auto_Inter_Bin_Delay</expression></inVariable>
            <inVariable localId="57"><position x="50" y="640" /><connectionPointOut /><expression>GVL.Semi_Auto_Excess_Allowed</expression></inVariable>
            <inVariable localId="58"><position x="50" y="660" /><connectionPointOut /><expression>GVL.load_cell_semi_auto</expression></inVariable>
            <!-- OutVariables for Semi_Auto_Ctrl -->
            <outVariable localId="70"><position x="650" y="500" /><connectionPointIn><connection refLocalId="2" formalParameter="Semi_Auto_Bin" /></connectionPointIn><expression>GVL.Semi_Auto_Bin</expression></outVariable>
            <outVariable localId="71"><position x="650" y="520" /><connectionPointIn><connection refLocalId="2" formalParameter="semi_auto_bin_cutoff" /></connectionPointIn><expression>GVL.semi_auto_bin_cutoff</expression></outVariable>
            <outVariable localId="72"><position x="650" y="540" /><connectionPointIn><connection refLocalId="2" formalParameter="semi_auto_bin_motor" /></connectionPointIn><expression>GVL.semi_auto_bin_motor</expression></outVariable>
            <outVariable localId="73"><position x="650" y="560" /><connectionPointIn><connection refLocalId="2" formalParameter="Actual_Weights" /></connectionPointIn><expression>GVL.Semi_Auto_Weights</expression></outVariable>
            <outVariable localId="74"><position x="650" y="580" /><connectionPointIn><connection refLocalId="2" formalParameter="Sequence_Complete" /></connectionPointIn><expression>Semi_Auto_Complete</expression></outVariable>
            <outVariable localId="75"><position x="650" y="600" /><connectionPointIn><connection refLocalId="2" formalParameter="Active_Material_ID" /></connectionPointIn><expression>GVL.Semi_Auto_Active_Mat</expression></outVariable>
            <outVariable localId="76"><position x="650" y="620" /><connectionPointIn><connection refLocalId="2" formalParameter="Active_Bin_ID" /></connectionPointIn><expression>GVL.Semi_Auto_Active_Bin</expression></outVariable>
            <outVariable localId="77"><position x="650" y="640" /><connectionPointIn><connection refLocalId="2" formalParameter="Active_Target_Weight" /></connectionPointIn><expression>GVL.Semi_Auto_Active_Target_Weight</expression></outVariable>
            <outVariable localId="78"><position x="650" y="660" /><connectionPointIn><connection refLocalId="2" formalParameter="Active_Live_Weight" /></connectionPointIn><expression>GVL.Semi_Auto_Active_Live_Weight</expression></outVariable>
            <outVariable localId="79"><position x="650" y="680" /><connectionPointIn><connection refLocalId="2" formalParameter="Current_Step" /></connectionPointIn><expression>GVL.Semi_Auto_Current_Step</expression></outVariable>
            <outVariable localId="80"><position x="650" y="700" /><connectionPointIn><connection refLocalId="2" formalParameter="Excess_Alarm" /></connectionPointIn><expression>GVL.Semi_Auto_Excess_Alarm</expression></outVariable>
            <outVariable localId="81"><position x="650" y="720" /><connectionPointIn><connection refLocalId="2" formalParameter="Error_Code" /></connectionPointIn><expression>Semi_Auto_Err</expression></outVariable>
            <outVariable localId="82"><position x="650" y="740" /><connectionPointIn><connection refLocalId="2" formalParameter="Status_Message" /></connectionPointIn><expression>GVL.Semi_Auto_Status_Message</expression></outVariable>
          </FBD>
        </body>
      </pou>
    </pous>
  </types>
  <instances><configurations /></instances>
</project>
"""

with open(b14_diag_xml_path, "w") as f:
    f.write(b14_diag_xml)

with open(log_path, "w") as f:
    f.write("Applying full diagnostics, step outputs, and status reporting...\n")
    try:
        proj = projects.open(project_path)
        app = proj.find("Application", True)[0]
        
        # 1. Update GVL
        gvl = proj.find("GVL", True)[0]
        gvl.textual_declaration.replace(gvl_content)
        f.write("GVL updated with Current_Step and Status_Message variables.\n")
        
        # 2. Update Auto_Batching_V14
        p_auto = proj.find("Auto_Batching_V14", True)[0]
        p_auto.textual_declaration.replace(decl_auto_v14)
        p_auto.textual_implementation.replace(code_auto_v14)
        f.write("Auto_Batching_V14 updated.\n")
        
        # 3. Update Semi_Auto_Batching_V14
        p_semi = proj.find("Semi_Auto_Batching_V14", True)[0]
        p_semi.textual_declaration.replace(decl_semi_v14)
        p_semi.textual_implementation.replace(code_semi_v14)
        f.write("Semi_Auto_Batching_V14 updated.\n")
        
        # 4. Re-import batching14 FBD with Current_Step and GVL Status Messages
        p_b14 = proj.find("batching14", True)
        for b in p_b14:
            b.remove()
        app.import_xml(b14_diag_xml_path)
        f.write("batching14 FBD re-imported with diagnostic pins.\n")
        
        proj.save()
        proj.close()
        f.write("All diagnostics and step reporting saved successfully.\n")
    except Exception as e:
        f.write("Error: " + str(e) + "\n")
