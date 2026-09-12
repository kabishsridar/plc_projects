import sys
import os

project_path = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\Rasi_feeds_batching.project"
log_path = r"C:\Users\kabish\.gemini\antigravity-ide\brain\6bb09710-7f3e-4443-b187-ad04e16ca8dc\scratch\create_b14_log.txt"

# V14 Declarations and Implementations
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

# batching14 FBD Program Declaration
fbd_decl_batching14 = """PROGRAM batching14
VAR
    Auto_Ctrl : Auto_Batching_V14;
    Semi_Auto_Ctrl : Semi_Auto_Batching_V14;
END_VAR
"""

with open(log_path, "w") as f:
    f.write("Starting creation of batching14 FBD and V14 blocks...\n")
    try:
        import System
        from System import Guid
        
        proj = projects.open(project_path)
        app = proj.find("Application", True)[0]
        
        # 1. Update/Create Auto_Batching_V14
        auto_pous = proj.find("Auto_Batching_V14", True)
        if len(auto_pous) == 0:
            f.write("Creating Auto_Batching_V14...\n")
            auto_fb = app.create_pou("Auto_Batching_V14", PouType.FunctionBlock)
        else:
            auto_fb = auto_pous[0]
        auto_fb.textual_declaration.replace(st_decl_auto)
        auto_fb.textual_implementation.replace(st_code_auto)
        
        # 2. Update/Create Semi_Auto_Batching_V14
        semi_pous = proj.find("Semi_Auto_Batching_V14", True)
        if len(semi_pous) == 0:
            f.write("Creating Semi_Auto_Batching_V14...\n")
            semi_fb = app.create_pou("Semi_Auto_Batching_V14", PouType.FunctionBlock)
        else:
            semi_fb = semi_pous[0]
        semi_fb.textual_declaration.replace(st_decl_semi)
        semi_fb.textual_implementation.replace(st_code_semi)
        
        # 3. Remove old batching14 if exists
        old_b14 = proj.find("batching14", True)
        for b in old_b14:
            f.write("Removing existing batching14...\n")
            b.remove()
            
        # 4. Create native FBD batching14 Program
        f.write("Creating native FBD batching14...\n")
        fbd_guid = Guid("c2e2244b-c806-41b4-8ad3-7a0e25ce1393")
        b14_fbd = app.create_pou("batching14", PouType.Program, fbd_guid)
        b14_fbd.textual_declaration.replace(fbd_decl_batching14)
        
        proj.save()
        proj.close()
        f.write("batching14 FBD created successfully!\n")
    except Exception as e:
        f.write("Error: " + str(e) + "\n")
