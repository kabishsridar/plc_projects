import sys
import os

project_path = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\Rasi_feeds_batching.project"
log_path = r"C:\Users\kabish\modify_output.txt"

# 1. GVL content with Active Target and Live Weights
new_gvl_content = """{attribute 'qualified_only'}
VAR_GLOBAL
    Recipe_Weights AT %MD100 : ARRAY[1..20] OF REAL;
	Auto_Bin_Material_Mapping AT %MW50: ARRAY[1..6] OF INT;
	Semi_Auto_Bin_Material_Mapping AT %MW60: ARRAY[1..10] OF INT;
	Auto_Bin_Cutoff_Weights AT %MD120: ARRAY[1..6] OF REAL;
	Semi_Auto_Bin_Cutoff_Weights AT %MD130: ARRAY[1..10] OF REAL;
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

# 2. Auto_Batching_V13 Declaration
st_decl_auto = """FUNCTION_BLOCK Auto_Batching_V13
VAR_INPUT
    Start_Button : BOOL;      // Signal to start/resume the batching sequence
    E_Stop_Active : BOOL;     // Emergency Stop (Pause/Hold signal)
    Reset : BOOL;             // Hard reset sequence trigger
    Auto_Bin_Material_Mapping : ARRAY[1..6] OF INT; // Material index mapping for 6 bins
    Auto_Bin_Cutoff_Weights : ARRAY[1..6] OF REAL; // Cutoff weight thresholds (kg)
    Auto_Bin_Tolerance : ARRAY[1..6] OF REAL; // Tolerance weight offset values (kg)
    Inter_Bin_Delay : TIME;   // Global inter-bin delay time
    Excess_Allowed : BOOL;    // Global toggle: TRUE = skip excess check, FALSE = trigger alarm & hold
END_VAR
VAR_IN_OUT
    load_cell_value : REAL;   // Weight value read/written from load cell
END_VAR
VAR_OUTPUT
    Auto_Bin : ARRAY[1..6] OF BOOL; // Coarse feed valve outputs
    auto_bin_cutoff : ARRAY[1..6] OF BOOL; // Fine feed cutoff trigger indicators
    auto_bin_motor : ARRAY[1..6] OF BOOL; // Main conveyor motor outputs
    Actual_Weights : ARRAY[1..6] OF REAL; // Actual weight poured per silo
    Sequence_Complete : BOOL;  // Batch complete flag
    Active_Material_ID : INT;  // Currently active ingredient ID
    Active_Bin_ID : INT;       // Currently active physical Bin ID (1..6)
    Active_Target_Weight : REAL; // Recipe target weight of active bin
    Active_Live_Weight : REAL; // Live tared weight poured from active bin
    Excess_Alarm : BOOL;       // Excess weight alarm output
    Error_Code : INT;          // Active error code
    Status_Message : STRING;   // Diagnostic text message
END_VAR
VAR
    Step : INT;                // State machine index (0: Idle, 1..6: Pour, 7: Settling, 8: Complete)
    bin_last_weight : REAL;   // Baseline weight snapshot before starting current bin
    actual_bin : REAL;        // Current weight added from active bin
    target_weight : REAL;     // Target recipe weight
    cutoff_trigger_weight : REAL; // Calculated cutoff trigger threshold (Target - Cutoff)
    min_tol_weight : REAL;    // Minimum allowable tolerance (Target - Tol)
    max_tol_weight : REAL;    // Maximum allowable tolerance (Target + Tol)
    Paused_By_EStop : BOOL;    // Pause status latch
    Effective_Delay : TIME;   // Resolved delay time (defaults to T#2S if T#0S configured)
    
    Mat_Idx : INT;
    i : INT;                  // General loop index
    
    (* TIMERS FOR TRANSITIONS & DELAYS *)
    Transition_Timer : TON;
    Completion_Timer : TON;
    
    (* SELF-CONTAINED SIMULATION VARIABLES *)
    Simulation_Mode : BOOL;    // Simulation disabled for physical PLC use
    Sim_Rate : REAL;
    Sim_Timer : TON;
    Start_Sim_Weight : REAL;
    Discharge_Active : BOOL;
END_VAR
"""

# 3. Auto_Batching_V13 Implementation
st_code_auto = """(* Auto Batching FB V13 with Real-Time Instant Excess Verification & Clean Multi-Cycle Reset *)

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
    bin_last_weight := load_cell_value; (* Snapshot relative tare at whatever weight scale is *)
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
        
        (* Skip this step instantly if material mapping is 0 OR target weight is 0.0 kg *)
        IF Mat_Idx = 0 OR (Mat_Idx <= 20 AND GVL.Recipe_Weights[Mat_Idx] = 0.0) THEN
            IF Step = 6 THEN
                Step := 7; (* Transition directly to final settling delay *)
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
            Active_Live_Weight := actual_bin; (* Live tared weight of active bin *)
            
            Active_Material_ID := Mat_Idx;
            Active_Bin_ID := Step;
            
            (* Scale Overload Protection *)
            IF load_cell_value > 500.0 THEN
                Error_Code := 21;
                Status_Message := 'Error 21: Scale Overloaded!';
                Sequence_Complete := TRUE;
                Paused_By_EStop := TRUE;
            END_IF;
            
            (* Real-Time Feed & Instant Excess Alarm *)
            IF actual_bin < cutoff_trigger_weight THEN
                (* Coarse Feed *)
                Auto_Bin[Step] := TRUE;
                auto_bin_cutoff[Step] := FALSE;
                auto_bin_motor[Step] := TRUE;
                Excess_Alarm := FALSE;
                Status_Message := 'Auto Pouring (Coarse Feed)';
                
            ELSIF actual_bin < min_tol_weight THEN
                (* Fine Feed *)
                Auto_Bin[Step] := FALSE;
                auto_bin_cutoff[Step] := TRUE;
                auto_bin_motor[Step] := TRUE;
                Excess_Alarm := FALSE;
                Status_Message := 'Auto Pouring (Fine Feed)';
                
            ELSIF actual_bin > max_tol_weight THEN
                (* Excess Weight -> Instant Alarm, No Delay! *)
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
                    Excess_Alarm := TRUE; (* Immediate Trigger! *)
                    Status_Message := 'Excess Alarm: Weight above max tolerance! Reduce weight.';
                END_IF;
                
            ELSE
                (* In Tolerance Window [Min_Tol .. Max_Tol] *)
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

    7: (* POST-SEQUENCE FINAL SETTLING DELAY *)
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
        
    8: (* COMPLETE *)
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

# 4. Semi_Auto_Batching_V13 Declaration
st_decl_semi = """FUNCTION_BLOCK Semi_Auto_Batching_V13
VAR_INPUT
    Start_Button : BOOL;      // Signal to start/resume the batching sequence
    E_Stop_Active : BOOL;     // Emergency Stop (Pause/Hold signal)
    Reset : BOOL;             // Hard reset sequence trigger
    Semi_Auto_Bin_Material_Mapping : ARRAY[1..10] OF INT; // Material index mapping for 10 manual silos
    Semi_Auto_Bin_Cutoff_Weights : ARRAY[1..10] OF REAL; // Cutoff weight thresholds (kg)
    Semi_Auto_Bin_Tolerance : ARRAY[1..10] OF REAL; // Tolerance weight offset values (kg)
    Inter_Bin_Delay : TIME;   // Global inter-bin delay time
    Excess_Allowed : BOOL;    // Global toggle: TRUE = skip excess check, FALSE = trigger alarm & hold
END_VAR
VAR_IN_OUT
    load_cell_value : REAL;   // Weight value read/written from load cell
END_VAR
VAR_OUTPUT
    Semi_Auto_Bin : ARRAY[1..10] OF BOOL; // Prompts/indicators for Bins 1..10
    semi_auto_bin_cutoff : ARRAY[1..10] OF BOOL; // Manual pre-cutoff indicators
    semi_auto_bin_motor : ARRAY[1..10] OF BOOL; // Main manual feeder motor outputs
    Actual_Weights : ARRAY[1..10] OF REAL; // Actual weight poured per silo
    Sequence_Complete : BOOL;  // Batch complete flag
    Active_Material_ID : INT;  // Currently active ingredient ID
    Active_Bin_ID : INT;       // Currently active physical Bin ID (1..10)
    Active_Target_Weight : REAL; // Recipe target weight of active bin
    Active_Live_Weight : REAL; // Live tared weight poured from active bin
    Excess_Alarm : BOOL;       // Excess weight alarm output
    Error_Code : INT;          // Active error code
    Status_Message : STRING;   // Diagnostic text message
END_VAR
VAR
    Step : INT;                // State machine index (0: Idle, 1..10: Pour, 31: Settling, 32: Complete)
    bin_last_weight : REAL;   // Baseline weight snapshot before starting current bin
    actual_bin : REAL;        // Current weight added from active bin
    target_weight : REAL;     // Target recipe weight
    cutoff_trigger_weight : REAL; // Calculated target threshold weight (Target - Cutoff)
    min_tol_weight : REAL;    // Minimum allowable tolerance (Target - Tol)
    max_tol_weight : REAL;    // Maximum allowable tolerance (Target + Tol)
    Paused_By_EStop : BOOL;    // Pause status latch
    Effective_Delay : TIME;   // Resolved delay time (defaults to T#2S if T#0S configured)
    
    Mat_Idx : INT;
    i : INT;                  // General loop index
    
    (* TIMERS FOR TRANSITIONS & DELAYS *)
    Transition_Timer : TON;
    Completion_Timer : TON;
    
    (* SELF-CONTAINED SIMULATION VARIABLES *)
    Simulation_Mode : BOOL;    // Simulation disabled for physical PLC use
    Sim_Rate : REAL;
    Sim_Timer : TON;
    Start_Sim_Weight : REAL;
    Discharge_Active : BOOL;
END_VAR
"""

# 5. Semi_Auto_Batching_V13 Implementation
st_code_semi = """(* Semi-Auto Batching FB V13 with Real-Time Instant Excess Verification & Clean Multi-Cycle Reset *)

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
    bin_last_weight := load_cell_value; (* Snapshot relative tare at whatever weight scale is *)
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
        
        (* Skip this step instantly if material mapping is 0 OR target weight is 0.0 kg *)
        IF Mat_Idx = 0 OR (Mat_Idx <= 20 AND GVL.Recipe_Weights[Mat_Idx] = 0.0) THEN
            IF Step = 10 THEN
                Step := 31; (* Transition directly to final settling delay *)
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
            Active_Live_Weight := actual_bin; (* Live tared weight of active bin *)
            
            Active_Material_ID := Mat_Idx;
            Active_Bin_ID := Step; (* Direct 1..10 *)
            
            (* Scale Overload Protection *)
            IF load_cell_value > 500.0 THEN
                Error_Code := 21;
                Status_Message := 'Error 21: Scale Overloaded!';
                Sequence_Complete := TRUE;
                Paused_By_EStop := TRUE;
            END_IF;
            
            (* Real-Time Feed & Instant Excess Alarm *)
            IF actual_bin < cutoff_trigger_weight THEN
                (* Coarse Feed *)
                Semi_Auto_Bin[Step] := TRUE;
                semi_auto_bin_cutoff[Step] := FALSE;
                semi_auto_bin_motor[Step] := TRUE;
                Excess_Alarm := FALSE;
                Status_Message := 'Semi-Auto Pouring (Coarse Feed)';
                
            ELSIF actual_bin < min_tol_weight THEN
                (* Fine Feed *)
                Semi_Auto_Bin[Step] := FALSE;
                semi_auto_bin_cutoff[Step] := TRUE;
                semi_auto_bin_motor[Step] := TRUE;
                Excess_Alarm := FALSE;
                Status_Message := 'Semi-Auto Pouring (Fine Feed)';
                
            ELSIF actual_bin > max_tol_weight THEN
                (* Excess Weight -> Instant Alarm, No Delay! *)
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
                    Excess_Alarm := TRUE; (* Immediate Trigger! *)
                    Status_Message := 'Excess Alarm: Weight above max tolerance! Reduce weight.';
                END_IF;
                
            ELSE
                (* In Tolerance Window [Min_Tol .. Max_Tol] *)
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

    31: (* POST-SEQUENCE FINAL SETTLING DELAY *)
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
        
    32: (* COMPLETE *)
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

# 6. batching13 Program Declaration
st_declaration_batching13 = """PROGRAM batching13
VAR
    Auto_Ctrl : Auto_Batching_V13;
    Semi_Auto_Ctrl : Semi_Auto_Batching_V13;
    
    (* Sub-Block Diagnostic Indicators *)
    Auto_Err : INT;
    Auto_Msg : STRING;
    
    Semi_Auto_Err : INT;
    Semi_Auto_Msg : STRING;
    
    Auto_Complete : BOOL;
    Semi_Auto_Complete : BOOL;
    
    (* Repetitive Cycle Status *)
    Completed_Batch_Cycles : INT;      // Total completed batch cycle loops
    All_Cycles_Complete : BOOL;         // Indicator for full set completion
    
    (* Diagnostics & Interlocks *)
    Status_Message : STRING;
    
    i : INT;
    j : INT;
    Duplicate_Found : BOOL;
    Invalid_Material_Range : BOOL;
    Weight_Limit_Error : BOOL;
    
    (* Cycle Manager state variables *)
    Cycle_Manager_State : INT;         // State index for loop management
    Internal_FB_Start : BOOL;          // Controlled command to restart sub-blocks
END_VAR
"""

# 7. batching13 Program Implementation
st_code_batching13 = """(* 1. STARTUP CONFIGURATION, RECIPE TOTALS, AND WEIGHT CHECKS *)
Duplicate_Found := FALSE;
Invalid_Material_Range := FALSE;
Weight_Limit_Error := FALSE;

(* Calculate Auto Total Target Weight & Material Count *)
GVL.Auto_Total_Target_Weight := 0.0;
GVL.Auto_Material_Count := 0;
FOR i := 1 TO 6 DO
    (* Check 2: Out of Range (Auto) *)
    IF GVL.Auto_Bin_Material_Mapping[i] < 0 OR GVL.Auto_Bin_Material_Mapping[i] > 20 THEN
        Invalid_Material_Range := TRUE;
    END_IF;
    
    (* Check 1: Duplicate Cross-Array Material ID *)
    IF GVL.Auto_Bin_Material_Mapping[i] <> 0 AND GVL.Auto_Bin_Material_Mapping[i] <= 20 THEN
        FOR j := 1 TO 10 DO
            IF GVL.Auto_Bin_Material_Mapping[i] = GVL.Semi_Auto_Bin_Material_Mapping[j] THEN
                Duplicate_Found := TRUE;
            END_IF;
        END_FOR;
    END_IF;
    
    (* Accumulate Auto Total Target Weight and Active Count *)
    IF GVL.Auto_Bin_Material_Mapping[i] > 0 AND GVL.Auto_Bin_Material_Mapping[i] <= 20 THEN
        IF GVL.Recipe_Weights[GVL.Auto_Bin_Material_Mapping[i]] > 0.0 THEN
            GVL.Auto_Total_Target_Weight := GVL.Auto_Total_Target_Weight + GVL.Recipe_Weights[GVL.Auto_Bin_Material_Mapping[i]];
            GVL.Auto_Material_Count := GVL.Auto_Material_Count + 1;
            
            (* Check 3: Recipe weight is less than Cutoff + Tolerance *)
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
    (* Check 2: Out of Range (Semi-Auto) *)
    IF GVL.Semi_Auto_Bin_Material_Mapping[j] < 0 OR GVL.Semi_Auto_Bin_Material_Mapping[j] > 20 THEN
        Invalid_Material_Range := TRUE;
    END_IF;
    
    (* Accumulate Semi-Auto Total Target Weight and Active Count *)
    IF GVL.Semi_Auto_Bin_Material_Mapping[j] > 0 AND GVL.Semi_Auto_Bin_Material_Mapping[j] <= 20 THEN
        IF GVL.Recipe_Weights[GVL.Semi_Auto_Bin_Material_Mapping[j]] > 0.0 THEN
            GVL.Semi_Auto_Total_Target_Weight := GVL.Semi_Auto_Total_Target_Weight + GVL.Recipe_Weights[GVL.Semi_Auto_Bin_Material_Mapping[j]];
            GVL.Semi_Auto_Material_Count := GVL.Semi_Auto_Material_Count + 1;
            
            (* Check 3: Recipe weight check (Semi-Auto) *)
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
    Auto_Ctrl(Start_Button := FALSE, E_Stop_Active := FALSE, Reset := GVL.Reset, load_cell_value := GVL.load_cell_auto, Inter_Bin_Delay := GVL.Auto_Inter_Bin_Delay, Excess_Allowed := GVL.Auto_Excess_Allowed);
    Semi_Auto_Ctrl(Start_Button := FALSE, E_Stop_Active := FALSE, Reset := GVL.Reset, load_cell_value := GVL.load_cell_semi_auto, Inter_Bin_Delay := GVL.Semi_Auto_Inter_Bin_Delay, Excess_Allowed := GVL.Semi_Auto_Excess_Allowed);
    
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


(* 2. REPETITIVE CYCLE MANAGER STATE MACHINE WITH PRE-RUN INITIAL TOLERANCE CHECK *)
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
            (* Guard 1: Target_Batch_Cycles must be > 0 *)
            IF GVL.Target_Batch_Cycles <= 0 THEN
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
        
    1: (* RUN STATE (Run Sub-Blocks - Initial Tolerance is NOT checked here while pouring) *)
        Internal_FB_Start := TRUE;
        GVL.Run := TRUE;
        Status_Message := CONCAT('Running Batch Cycle ', INT_TO_STRING(GVL.Current_Batch_Cycle));
        
        (* Monitor completion of active step *)
        IF Auto_Complete AND Semi_Auto_Complete THEN
            Cycle_Manager_State := 2;
        END_IF;
        
    2: (* CHECK REPEAT CYCLE STATE *)
        Completed_Batch_Cycles := GVL.Current_Batch_Cycle;
        GVL.Run := TRUE;
        
        (* Block cycle repeat in case of active error *)
        IF GVL.Current_Batch_Cycle < GVL.Target_Batch_Cycles AND GVL.Error_Code = 0 THEN
            (* Hold cycle loop progression *)
            GVL.Cycle_Hold_Active := TRUE;
            Internal_FB_Start := FALSE; (* Reset FBs to 0 while waiting in hold *)
            Cycle_Manager_State := 5; // Go to hold wait state
        ELSE
            (* All loop cycles complete *)
            Cycle_Manager_State := 4;
        END_IF;
        
    5: (* PAUSED BETWEEN CYCLES *)
        Internal_FB_Start := FALSE; (* Keeps sub-blocks in Step 0 *)
        GVL.Run := TRUE;
        Status_Message := CONCAT('Cycle ', CONCAT(INT_TO_STRING(GVL.Current_Batch_Cycle), ' Complete. Empty scale to 0 and release Cycle Hold.'));
        
        IF NOT GVL.Cycle_Hold_Active THEN
            (* Check Initial Tolerance before starting next cycle *)
            IF (GVL.load_cell_auto > GVL.Auto_Initial_Tolerance OR GVL.load_cell_auto < (-GVL.Auto_Initial_Tolerance)) OR 
               (GVL.load_cell_semi_auto > GVL.Semi_Auto_Initial_Tolerance OR GVL.load_cell_semi_auto < (-GVL.Semi_Auto_Initial_Tolerance)) THEN
                GVL.Run := FALSE;
                GVL.Error_Code := 4;
                Status_Message := 'Error 4: Scale weight exceeds Initial Tolerance!';
                GVL.Cycle_Hold_Active := TRUE; (* Keep hold active until scale is emptied *)
            ELSE
                GVL.Error_Code := 0;
                GVL.Current_Batch_Cycle := GVL.Current_Batch_Cycle + 1;
                Auto_Complete := FALSE;
                Semi_Auto_Complete := FALSE;
                Cycle_Manager_State := 1; (* Start next cycle! *)
            END_IF;
        END_IF;
        
    4: (* SEQUENCE FULLY COMPLETED STATE *)
        Internal_FB_Start := FALSE;
        All_Cycles_Complete := TRUE;
        GVL.Run := FALSE;
        GVL.Start_Button := FALSE; (* Auto-turn off Start_Button when process completes! *)
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

with open(log_path, "w") as f:
    f.write("Starting modify script for batching13...\\n")
    try:
        proj = projects.open(project_path)
        for child in proj.get_children(True):
            name = child.get_name().lower()
            if name == "gvl":
                f.write("Updating GVL...\\n")
                child.textual_declaration.replace(new_gvl_content)
            elif name == "auto_batching_v13":
                f.write("Updating Auto_Batching_V13...\\n")
                child.textual_declaration.replace(st_decl_auto)
                child.textual_implementation.replace(st_code_auto)
            elif name == "semi_auto_batching_v13":
                f.write("Updating Semi_Auto_Batching_V13...\\n")
                child.textual_declaration.replace(st_decl_semi)
                child.textual_implementation.replace(st_code_semi)
            elif name == "batching13":
                f.write("Updating batching13...\\n")
                child.textual_declaration.replace(st_declaration_batching13)
                child.textual_implementation.replace(st_code_batching13)
                
        proj.save()
        proj.close()
        f.write("Project saved and closed successfully.\\n")
    except Exception as e:
        f.write("Error: " + str(e) + "\\n")
