import sys
import os

project_path = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\Rasi_feeds_batching.project"
log_path = r"C:\Users\kabish\.gemini\antigravity-ide\brain\6bb09710-7f3e-4443-b187-ad04e16ca8dc\scratch\update_v13_rename_log.txt"

decl_auto_v13 = """FUNCTION_BLOCK Auto_Batching_V13
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

decl_semi_v13 = """FUNCTION_BLOCK Semi_Auto_Batching_V13
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

with open(log_path, "w") as f:
    f.write("Updating V13 POUs with renamed variables...\n")
    try:
        proj = projects.open(project_path)
        
        # 1. Update Auto_Batching_V13
        p_auto = proj.find("Auto_Batching_V13", True)[0]
        p_auto.textual_declaration.replace(decl_auto_v13)
        code = p_auto.textual_implementation.text
        code = code.replace("Auto_Bin_Cutoff_Weights", "Auto_Coarse_To_Fine_Speed")
        p_auto.textual_implementation.replace(code)
        f.write("Auto_Batching_V13 updated.\n")
        
        # 2. Update Semi_Auto_Batching_V13
        p_semi = proj.find("Semi_Auto_Batching_V13", True)[0]
        p_semi.textual_declaration.replace(decl_semi_v13)
        code = p_semi.textual_implementation.text
        code = code.replace("Semi_Auto_Bin_Cutoff_Weights", "Semi_Auto_Coarse_To_Fine_Speed")
        p_semi.textual_implementation.replace(code)
        f.write("Semi_Auto_Batching_V13 updated.\n")
        
        # 3. Update batching13
        p_b13 = proj.find("batching13", True)[0]
        code = p_b13.textual_implementation.text
        code = code.replace("GVL.Auto_Bin_Cutoff_Weights", "GVL.Auto_Coarse_To_Fine_Speed")
        code = code.replace("GVL.Semi_Auto_Bin_Cutoff_Weights", "GVL.Semi_Auto_Coarse_To_Fine_Speed")
        code = code.replace("Auto_Bin_Cutoff_Weights :=", "Auto_Coarse_To_Fine_Speed :=")
        code = code.replace("Semi_Auto_Bin_Cutoff_Weights :=", "Semi_Auto_Coarse_To_Fine_Speed :=")
        p_b13.textual_implementation.replace(code)
        f.write("batching13 updated.\n")
        
        proj.save()
        proj.close()
        f.write("V13 updates completed.\n")
    except Exception as e:
        f.write("Error: " + str(e) + "\n")
