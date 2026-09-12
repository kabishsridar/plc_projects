import sys
import os

project_path = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\Rasi_feeds_batching.project"
log_path = r"C:\Users\kabish\.gemini\antigravity-ide\brain\6bb09710-7f3e-4443-b187-ad04e16ca8dc\scratch\apply_fix_log.txt"

# 1. Semi_Auto_Batching_V13 Declaration
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
    Excess_Alarm : BOOL;       // Excess weight alarm output
    Error_Code : INT;          // Active error code
    Status_Message : STRING;   // Diagnostic text message
END_VAR
VAR
    Step : INT;                // State machine index (0: Idle, 1..10: Pour, 11..20: Delay, 21..30: Tol Check, 31: Settling, 32: Complete)
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

# 2. Semi_Auto_Batching_V13 Implementation
st_code_semi = """(* Semi-Auto Batching FB V13 with Closed-Loop Tolerance Verification & Excess Handling *)

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
    Excess_Alarm := FALSE;
    Error_Code := 0;
    Status_Message := '';
    Paused_By_EStop := FALSE;
    Step := 0;
    
    load_cell_value := 0.0;
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
    IF (Step >= 1 AND Step <= 10) OR (Step >= 21 AND Step <= 30) THEN
        IF Step <= 10 THEN
            Discharge_Active := semi_auto_bin_motor[Step];
        ELSE
            Discharge_Active := semi_auto_bin_motor[Step - 20];
        END_IF;
    END_IF;
    
    IF Discharge_Active THEN
        Sim_Timer(IN := TRUE, PT := T#1000S);
        load_cell_value := Start_Sim_Weight + (TIME_TO_REAL(Sim_Timer.ET) / 1000.0) * Sim_Rate;
    ELSE
        Sim_Timer(IN := FALSE);
        Start_Sim_Weight := load_cell_value;
    END_IF;
END_IF;

(* 4. RECIPE SEQUENCE START *)
IF Step = 0 AND Start_Button THEN
    Step := 1;
    bin_last_weight := load_cell_value;
    Sequence_Complete := FALSE;
    Excess_Alarm := FALSE;
    Error_Code := 0;
    Status_Message := 'Semi-Auto Pour Started';
    Active_Target_Weight := 0.0;
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
        Excess_Alarm := FALSE;
        IF Error_Code = 0 THEN Status_Message := 'Semi-Auto Idle'; END_IF;
        
    1..10: (* DISCHARGE SILOS 1 TO 10 (COARSE & FINE FEED) *)
        Mat_Idx := Semi_Auto_Bin_Material_Mapping[Step];
        
        (* Skip this step instantly if material mapping is 0 OR target weight is 0.0 kg *)
        IF Mat_Idx = 0 OR (Mat_Idx <= 20 AND GVL.Recipe_Weights[Mat_Idx] = 0.0) THEN
            IF Step = 10 THEN
                Step := 31; (* Transition directly to final settling delay! *)
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
            
            Active_Material_ID := Mat_Idx;
            Active_Bin_ID := Step; (* Direct 1..10 *)
            Status_Message := 'Semi-Auto Pouring Active';
            
            (* Coarse vs Fine Feed *)
            IF actual_bin < cutoff_trigger_weight THEN
                Semi_Auto_Bin[Step] := TRUE;
                semi_auto_bin_cutoff[Step] := FALSE;
                semi_auto_bin_motor[Step] := TRUE;
            ELSIF actual_bin < min_tol_weight THEN
                Semi_Auto_Bin[Step] := FALSE;
                semi_auto_bin_cutoff[Step] := TRUE;
                semi_auto_bin_motor[Step] := TRUE;
            ELSE
                Semi_Auto_Bin[Step] := FALSE;
                semi_auto_bin_cutoff[Step] := FALSE;
                semi_auto_bin_motor[Step] := FALSE;
                Step := 10 + Step; // Transition to Settling Delay (11..20)
            END_IF;
            
            (* Scale Limits *)
            IF load_cell_value > 500.0 THEN
                Error_Code := 21;
                Status_Message := 'Error 21: Scale Overloaded!';
                Sequence_Complete := TRUE;
                Paused_By_EStop := TRUE;
            ELSIF load_cell_value < 0.0 THEN
                Error_Code := 22;
                Status_Message := 'Error 22: Scale Underloaded/Fault!';
                Sequence_Complete := TRUE;
                Paused_By_EStop := TRUE;
            END_IF;
        END_IF;

    11..20: (* INTER-BIN SETTLING DELAY *)
        Semi_Auto_Bin[Step - 10] := FALSE;
        semi_auto_bin_cutoff[Step - 10] := FALSE;
        semi_auto_bin_motor[Step - 10] := FALSE;
        Status_Message := 'Settling Delay';
        
        Transition_Timer(IN := TRUE, PT := Effective_Delay);
        IF Transition_Timer.Q THEN
            Transition_Timer(IN := FALSE);
            Step := 20 + (Step - 10); // Proceed to Tolerance Verification (21..30)
        END_IF;

    21..30: (* POST-DELAY TOLERANCE & EXCESS VERIFICATION *)
        Mat_Idx := Semi_Auto_Bin_Material_Mapping[Step - 20];
        IF Mat_Idx > 0 AND Mat_Idx <= 20 THEN
            target_weight := GVL.Recipe_Weights[Mat_Idx];
        ELSE
            target_weight := 0.0;
        END_IF;
        min_tol_weight := target_weight - Semi_Auto_Bin_Tolerance[Step - 20];
        max_tol_weight := target_weight + Semi_Auto_Bin_Tolerance[Step - 20];
        actual_bin := load_cell_value - bin_last_weight;
        Actual_Weights[Step - 20] := actual_bin;
        Active_Bin_ID := Step - 20; (* Direct 1..10 *)
        
        (* CASE A: UNDERFILLED -> TOP UP *)
        IF actual_bin < min_tol_weight THEN
            Semi_Auto_Bin[Step - 20] := FALSE;
            semi_auto_bin_cutoff[Step - 20] := TRUE;
            semi_auto_bin_motor[Step - 20] := TRUE;
            Status_Message := 'Underfilled: Topping up to target tolerance';
            Excess_Alarm := FALSE;
            
            IF actual_bin >= min_tol_weight THEN
                Semi_Auto_Bin[Step - 20] := FALSE;
                semi_auto_bin_cutoff[Step - 20] := FALSE;
                semi_auto_bin_motor[Step - 20] := FALSE;
                Step := 10 + (Step - 20); // Re-enter settling delay to verify
            END_IF;
            
        (* CASE B: OVERFILLED / EXCESS *)
        ELSIF actual_bin > max_tol_weight THEN
            Semi_Auto_Bin[Step - 20] := FALSE;
            semi_auto_bin_cutoff[Step - 20] := FALSE;
            semi_auto_bin_motor[Step - 20] := FALSE;
            
            IF Excess_Allowed THEN
                Excess_Alarm := FALSE;
                Status_Message := 'Excess Weight Allowed: Advancing';
                bin_last_weight := load_cell_value;
                Active_Target_Weight := 0.0;
                IF (Step - 20) = 10 THEN
                    Step := 31; (* Transition to Step 31 for Final Settle *)
                ELSE
                    Step := (Step - 20) + 1;
                END_IF;
            ELSE
                Excess_Alarm := TRUE;
                Status_Message := 'Excess Alarm: Weight above max tolerance! Reduce weight.';
            END_IF;
            
        (* CASE C: IN RANGE [Min_Tol .. Max_Tol] *)
        ELSE
            Semi_Auto_Bin[Step - 20] := FALSE;
            semi_auto_bin_cutoff[Step - 20] := FALSE;
            semi_auto_bin_motor[Step - 20] := FALSE;
            Excess_Alarm := FALSE;
            bin_last_weight := load_cell_value;
            Active_Target_Weight := 0.0;
            IF (Step - 20) = 10 THEN
                Step := 31; (* Transition to Step 31 for Final Settle *)
            ELSE
                Step := (Step - 20) + 1;
            END_IF;
        END_IF;

    31: (* POST-SEQUENCE FINAL SETTLING DELAY *)
        Active_Material_ID := 0;
        Active_Bin_ID := 0;
        Active_Target_Weight := 0.0;
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
        Excess_Alarm := FALSE;
        Status_Message := 'Sequence Completed';
        bin_last_weight := 0.0;
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

with open(log_path, "w") as f:
    f.write("Opening project...\n")
    try:
        proj = projects.open(project_path)
        for child in proj.get_children(True):
            if child.get_name().lower() == "semi_auto_batching_v13":
                f.write("Replacing Semi_Auto_Batching_V13...\n")
                child.textual_declaration.replace(st_decl_semi)
                child.textual_implementation.replace(st_code_semi)
                f.write("Successfully updated Semi_Auto_Batching_V13.\n")
        proj.save()
        proj.close()
        f.write("Project saved and closed.\n")
    except Exception as e:
        f.write("Error: " + str(e) + "\n")
