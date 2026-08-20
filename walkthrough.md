# Walkthrough - PROGRAM Batching Cycle Manager (batching10)

I have successfully updated the project to implement **`batching10`** featuring automatic sequence cycle repetition controls inside `Rasi_feeds_batching.project` and pushed it to GitHub.

## Changes Made

1. **Repetitive Cycle Loop Management State Machine**:
   - Implemented a state machine (`Cycle_Manager_State`) in the main program `batching10` that manages execution cycles.
   - Wraps concurrent `Auto_Ctrl` and `Manual_Ctrl` starts via `Internal_FB_Start` instead of physical `Start_Button`.
   - **Reset Cycle Pulse**: When a cycle finishes, the manager pulses the start signal low for one scan cycle to reset block step indices, then increments the cycle counter and sets start high to begin the next run.
2. **Repetition Variables**:
   - **`Target_Batch_Cycles : INT := 2;`**: Setpoint configuration for total cycles (default: `2`).
   - **`Current_Batch_Cycle : INT`**: Displays active loop sequence number.
   - **`Completed_Batch_Cycles : INT`**: Tracks number of finished cycles.
   - **`All_Cycles_Complete : BOOL`**: Set to `TRUE` once the full loop finishes, resetting only when `Start_Button` is released.
3. **Compilation**:
   - Verified that the project builds successfully with **0 errors**.

### Main POU Code (`batching10` PROGRAM)

**Declaration**:
```pascal
PROGRAM batching10
VAR
    Auto_Ctrl : Auto_Batching_V10;
    Manual_Ctrl : Manual_Batching_V10;
    
    (* Global Inputs & Toggles *)
    Start_Button : BOOL;
    E_Stop_Active : BOOL;
    
    (* Parallel Weight Feedbacks *)
    load_cell_auto : REAL;
    load_cell_manual : REAL;
    
    (* Repetitive Cycle Configurations & Status *)
    Target_Batch_Cycles : INT := 2;      // Number of cycles to run automatically (Default: 2)
    Current_Batch_Cycle : INT := 0;      // Current running cycle index
    Completed_Batch_Cycles : INT := 0;  // Total completed batch cycle loops
    All_Cycles_Complete : BOOL;         // Indicator for full set completion
    
    (* Sub-Block Diagnostic Indicators - Ordered exactly below loadcell *)
    Auto_Active_Mat : INT;
    Auto_Active_Bin : INT;
    Auto_Active_Target : REAL; // Active Target Weight for Auto (displays GVL setpoint - Tolerance)
    Auto_Err : INT;
    Auto_Msg : STRING;
    
    Manual_Active_Mat : INT;
    Manual_Active_Bin : INT;
    Manual_Active_Target : REAL; // Active Target Weight for Manual (displays GVL setpoint - Tolerance)
    Manual_Err : INT;
    Manual_Msg : STRING;
    
    (* Process Outputs *)
    Auto_Bin : ARRAY[1..6] OF BOOL; // Valve control outputs (Coarse)
    auto_bin_cutoff : ARRAY[1..6] OF BOOL; // Cutoff indicators (Fine)
    auto_bin_motor : ARRAY[1..6] OF BOOL; // Conveyor/feeder motor outputs
    
    Manual_Bin : ARRAY[1..10] OF BOOL; // Prompt indicators (Coarse)
    manual_bin_cutoff : ARRAY[1..10] OF BOOL; // Cutoff indicators (Fine)
    manual_bin_motor : ARRAY[1..10] OF BOOL; // Conveyor/feeder motor outputs
    
    Auto_Weights : ARRAY[1..6] OF REAL;
    Manual_Weights : ARRAY[1..10] OF REAL;
    
    Auto_Complete : BOOL;
    Manual_Complete : BOOL;
    
    (* Diagnostics & Interlocks *)
    Error_Code : INT := 0;
    Status_Message : STRING := 'System Ready';
    
    (* Array Configurations & Mapping - Renamed for clarity *)
    Auto_Bin_Material_Mapping : ARRAY[1..6] OF INT := [1, 2, 0, 4, 5, 6];
    Manual_Bin_Material_Mapping : ARRAY[1..10] OF INT := [7, 8, 0, 10, 11, 12, 13, 14, 15, 16];
    Auto_Bin_Cutoff_Weights : ARRAY[1..6] OF REAL := [2.0, 1.5, 0.0, 3.0, 5.0, 1.0]; // Cutoff margins (kg)
    Manual_Bin_Cutoff_Weights : ARRAY[1..10] OF REAL := [2.0, 1.5, 0.0, 3.0, 5.0, 1.0, 2.0, 2.0, 2.0, 2.0];
    Auto_Bin_Tolerance : ARRAY[1..6] OF REAL := [1.0, 0.5, 0.0, 1.0, 2.0, 0.5]; // Tolerance offsets (kg)
    Manual_Bin_Tolerance : ARRAY[1..10] OF REAL := [1.0, 0.5, 0.0, 1.0, 2.0, 0.5, 1.0, 1.0, 1.0, 1.0];
    
    i : INT;
    j : INT;
    Duplicate_Found : BOOL;
    Invalid_Material_Range : BOOL;
    Zero_Target_Found : BOOL;
    Conf_Err_Id : INT;
    
    (* Cycle Manager state variables *)
    Cycle_Manager_State : INT := 0;     // State index for loop management
    Internal_FB_Start : BOOL := FALSE;  // Controlled command to restart sub-blocks
END_VAR
```

**ST Implementation**:
```pascal
(* 1. STARTUP CONFIGURATION CHECKS *)
Duplicate_Found := FALSE;
Invalid_Material_Range := FALSE;
Zero_Target_Found := FALSE;

FOR i := 1 TO 6 DO
    (* Check 2: Out of Range (Auto) *)
    IF Auto_Bin_Material_Mapping[i] < 0 OR Auto_Bin_Material_Mapping[i] > 20 THEN
        Invalid_Material_Range := TRUE;
    END_IF;
    
    (* Check 3: Zero Target (Auto) *)
    IF Auto_Bin_Material_Mapping[i] <> 0 AND Auto_Bin_Material_Mapping[i] <= 20 THEN
        IF GVL.Recipe_Weights[Auto_Bin_Material_Mapping[i]] = 0.0 THEN
            Zero_Target_Found := TRUE;
        END_IF;
    END_IF;
    
    (* Check 1: Duplicate Cross-Array Material ID *)
    IF Auto_Bin_Material_Mapping[i] <> 0 AND Auto_Bin_Material_Mapping[i] <= 20 THEN
        FOR j := 1 TO 10 DO
            IF Auto_Bin_Material_Mapping[i] = Manual_Bin_Material_Mapping[j] THEN
                Duplicate_Found := TRUE;
            END_IF;
        END_FOR;
    END_IF;
END_FOR;

FOR j := 1 TO 10 DO
    (* Check 2: Out of Range (Manual) *)
    IF Manual_Bin_Material_Mapping[j] < 0 OR Manual_Bin_Material_Mapping[j] > 20 THEN
        Invalid_Material_Range := TRUE;
    END_IF;
    
    (* Check 3: Zero Target (Manual) *)
    IF Manual_Bin_Material_Mapping[j] <> 0 AND Manual_Bin_Material_Mapping[j] <= 20 THEN
        IF GVL.Recipe_Weights[Manual_Bin_Material_Mapping[j]] = 0.0 THEN
            Zero_Target_Found := TRUE;
        END_IF;
    END_IF;
END_FOR;

(* Configuration Error Resolution *)
IF Duplicate_Found THEN
    Error_Code := 1;
    Status_Message := 'Error 1: Duplicate Material ID mapped in Auto and Manual!';
ELSIF Invalid_Material_Range THEN
    Error_Code := 2;
    Status_Message := 'Error 2: Material Index configuration out of range (1..20)!';
ELSIF Zero_Target_Found THEN
    Error_Code := 3;
    Status_Message := 'Error 3: Configured Material ID has a 0.0 kg target weight!';
ELSE
    IF Error_Code <= 3 THEN
        Error_Code := 0;
    END_IF;
END_IF;

(* Abort sequences if a configuration error exists or E-stop is active *)
IF (Error_Code >= 1 AND Error_Code <= 3) OR E_Stop_Active THEN
    FOR i := 1 TO 6 DO Auto_Bin[i] := FALSE; auto_bin_cutoff[i] := FALSE; auto_bin_motor[i] := FALSE; END_FOR;
    FOR i := 1 TO 10 DO Manual_Bin[i] := FALSE; manual_bin_cutoff[i] := FALSE; manual_bin_motor[i] := FALSE; END_FOR;
    
    Internal_FB_Start := FALSE;
    Auto_Ctrl(Start_Button := FALSE, E_Stop_Active := TRUE, load_cell_value := load_cell_auto);
    Manual_Ctrl(Start_Button := FALSE, E_Stop_Active := TRUE, load_cell_value := load_cell_manual);
    
    Auto_Active_Target := 0.0;
    Manual_Active_Target := 0.0;
    All_Cycles_Complete := FALSE;
    Cycle_Manager_State := 0;
    
    IF E_Stop_Active THEN
        Error_Code := 12;
        Status_Message := 'Error 12: Emergency Stop Active!';
    END_IF;
    RETURN;
END_IF;


(* 2. REPETITIVE CYCLE MANAGER STATE MACHINE *)
CASE Cycle_Manager_State OF
    0: (* IDLE STATE *)
        Internal_FB_Start := FALSE;
        All_Cycles_Complete := FALSE;
        IF Error_Code = 0 THEN Status_Message := 'System Ready'; END_IF;
        
        IF Start_Button THEN
            Current_Batch_Cycle := 1;
            Completed_Batch_Cycles := 0;
            Cycle_Manager_State := 1;
        END_IF;
        
    1: (* RUN STATE (Run Sub-Blocks) *)
        Internal_FB_Start := TRUE;
        Status_Message := CONCAT('Running Batch Cycle ', INT_TO_STRING(Current_Batch_Cycle));
        
        (* Monitor completion of active step *)
        IF Auto_Complete AND Manual_Complete THEN
            Cycle_Manager_State := 2;
        END_IF;
        
    2: (* CHECK REPEAT CYCLE STATE *)
        Completed_Batch_Cycles := Current_Batch_Cycle;
        
        IF Current_Batch_Cycle < Target_Batch_Cycles THEN
            (* Transition to reset pulse to restart FBs *)
            Cycle_Manager_State := 3;
        else
            (* All loop cycles complete *)
            Cycle_Manager_State := 4;
        END_IF;
        
    3: (* AUTO-RESET PULSE (Pulse Start command low to reset state machines) *)
        Internal_FB_Start := FALSE;
        Status_Message := 'Resetting Sequence for Next Cycle';
        
        (* Verify sub-blocks have fully reset to idle step *)
        IF NOT Auto_Complete AND NOT Manual_Complete THEN
            Current_Batch_Cycle := Current_Batch_Cycle + 1;
            Cycle_Manager_State := 1; // Start next cycle
        END_IF;
        
    4: (* SEQUENCE FULLY COMPLETED STATE *)
        Internal_FB_Start := FALSE;
        All_Cycles_Complete := TRUE;
        Status_Message := 'All Batch Cycles Completed';
        
        IF NOT Start_Button THEN
            Cycle_Manager_State := 0;
        END_IF;
END_CASE;


(* 3. CONCURRENT EXECUTION OF FB INSTANCES *)
Auto_Ctrl(
    Start_Button := Internal_FB_Start,
    E_Stop_Active := E_Stop_Active,
    load_cell_value := load_cell_auto,
    Auto_Bin_Material_Mapping := Auto_Bin_Material_Mapping,
    Auto_Bin_Cutoff_Weights := Auto_Bin_Cutoff_Weights,
    Auto_Bin_Tolerance := Auto_Bin_Tolerance,
    Auto_Bin => Auto_Bin,
    auto_bin_cutoff => auto_bin_cutoff,
    auto_bin_motor => auto_bin_motor,
    Actual_Weights => Auto_Weights,
    Sequence_Complete => Auto_Complete,
    Active_Material_ID => Auto_Active_Mat,
    Active_Bin_ID => Auto_Active_Bin,
    Active_Target_Weight => Auto_Active_Target,
    Error_Code => Auto_Err,
    Status_Message => Auto_Msg
);

Manual_Ctrl(
    Start_Button := Internal_FB_Start,
    E_Stop_Active := E_Stop_Active,
    load_cell_value := load_cell_manual,
    Manual_Bin_Material_Mapping := Manual_Bin_Material_Mapping,
    Manual_Bin_Cutoff_Weights := Manual_Bin_Cutoff_Weights,
    Manual_Bin_Tolerance := Manual_Bin_Tolerance,
    Manual_Bin => Manual_Bin,
    manual_bin_cutoff => manual_bin_cutoff,
    manual_bin_motor => manual_bin_motor,
    Actual_Weights => Manual_Weights,
    Sequence_Complete => Manual_Complete,
    Active_Material_ID => Manual_Active_Mat,
    Active_Bin_ID => Manual_Active_Bin,
    Active_Target_Weight => Manual_Active_Target,
    Error_Code => Manual_Err,
    Status_Message => Manual_Msg
);

(* Runtime Error Mapping & Aggregation *)
IF Auto_Err <> 0 THEN
    Error_Code := Auto_Err;
    Status_Message := CONCAT('Auto Error: ', Auto_Msg);
ELSIF Manual_Err <> 0 THEN
    Error_Code := Manual_Err;
    Status_Message := CONCAT('Manual Error: ', Manual_Msg);
ELSIF Cycle_Manager_State = 0 THEN
    Error_Code := 0;
END_IF;
```
