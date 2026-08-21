# Walkthrough - PROGRAM Batching Control (batching11)

I have successfully updated the project to implement **`batching11`** featuring the renaming of all manual tags to **`Semi_Auto`**, E-Stop pause/resume holds, immediate reset commands, and inter-cycle loop pauses inside `Rasi_feeds_batching.project` and pushed it to GitHub.

## Changes Made

1. **Renamed Manual to Semi-Auto**:
   - Replaced all declarations and sequence references of `Manual` with **`Semi_Auto`** across the FBs, program variables, and execution calls.
2. **E-Stop Pause/Hold & Resume**:
   - Instead of hard-aborting on E-Stop, the FBs now pause (holding `Step` index and suspending transition, completion, and safety timers).
   - Once the E-Stop is released, the operator presses the `Start_Button` to resume pouring seamlessly from where they left off.
3. **Immediate Reset Command (`Reset`)**:
   - Implemented a dedicated `Reset` input that immediately clears all load cell weights to `0.0` kg, turns off all valve/cutoff/motor outputs, and resets the sequence states to step `0` instantly.
4. **Inter-Cycle Loop Pause (`Cycle_Hold_Active`)**:
   - Toggled `TRUE` automatically at the end of each cycle. The Cycle Manager holds the program in state `5` and does not proceed to the next cycle until the user toggles `Cycle_Hold_Active := FALSE`.
5. **Compilation**:
   - Verified that the project builds successfully with **0 errors**.

### Program ST Code (`batching11`)

**ST Implementation**:
```pascal
(* 1. STARTUP CONFIGURATION CHECKS *)
Duplicate_Found := FALSE;
Invalid_Material_Range := FALSE;

FOR i := 1 TO 6 DO
    IF Auto_Bin_Material_Mapping[i] < 0 OR Auto_Bin_Material_Mapping[i] > 20 THEN
        Invalid_Material_Range := TRUE;
    END_IF;
    
    IF Auto_Bin_Material_Mapping[i] <> 0 AND Auto_Bin_Material_Mapping[i] <= 20 THEN
        FOR j := 1 TO 10 DO
            IF Auto_Bin_Material_Mapping[i] = Semi_Auto_Bin_Material_Mapping[j] THEN
                Duplicate_Found := TRUE;
            END_IF;
        END_FOR;
    END_IF;
END_FOR;

FOR j := 1 TO 10 DO
    IF Semi_Auto_Bin_Material_Mapping[j] < 0 OR Semi_Auto_Bin_Material_Mapping[j] > 20 THEN
        Invalid_Material_Range := TRUE;
    END_IF;
END_FOR;

(* Configuration Error Resolution *)
IF Duplicate_Found THEN
    Error_Code := 1;
    Status_Message := 'Error 1: Duplicate Material ID mapped in Auto and Semi-Auto!';
ELSIF Invalid_Material_Range THEN
    Error_Code := 2;
    Status_Message := 'Error 2: Material Index configuration out of range (1..20)!';
ELSE
    IF Error_Code <= 2 THEN
        Error_Code := 0;
    END_IF;
END_IF;

(* Abort/Clear arrays if Configuration error is active or Hard Reset is pressed *)
IF (Error_Code >= 1 AND Error_Code <= 2) OR Reset THEN
    FOR i := 1 TO 6 DO Auto_Bin[i] := FALSE; auto_bin_cutoff[i] := FALSE; auto_bin_motor[i] := FALSE; END_FOR;
    FOR i := 1 TO 10 DO Semi_Auto_Bin[i] := FALSE; semi_auto_bin_cutoff[i] := FALSE; semi_auto_bin_motor[i] := FALSE; END_FOR;
    
    Internal_FB_Start := FALSE;
    Auto_Ctrl(Start_Button := FALSE, E_Stop_Active := FALSE, Reset := TRUE, load_cell_value := load_cell_auto);
    Semi_Auto_Ctrl(Start_Button := FALSE, E_Stop_Active := FALSE, Reset := TRUE, load_cell_value := load_cell_semi_auto);
    
    Auto_Active_Target := 0.0;
    Semi_Auto_Active_Target := 0.0;
    All_Cycles_Complete := FALSE;
    Cycle_Hold_Active := FALSE;
    Cycle_Manager_State := 0;
    
    IF Reset THEN
        Error_Code := 0;
        Status_Message := 'System Reset Activated';
    END_IF;
    RETURN;
END_IF;


(* 2. REPETITIVE CYCLE MANAGER STATE MACHINE WITH HOLD RELEASE *)
CASE Cycle_Manager_State OF
    0: (* IDLE STATE *)
        Internal_FB_Start := FALSE;
        All_Cycles_Complete := FALSE;
        Cycle_Hold_Active := FALSE;
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
        IF Auto_Complete AND Semi_Auto_Complete THEN
            Cycle_Manager_State := 2;
        END_IF;
        
    2: (* CHECK REPEAT CYCLE STATE *)
        Completed_Batch_Cycles := Current_Batch_Cycle;
        
        IF Current_Batch_Cycle < Target_Batch_Cycles THEN
            (* Hold cycle loop progression *)
            Cycle_Hold_Active := TRUE;
            Cycle_Manager_State := 5; // Go to hold wait state
        else
            (* All loop cycles complete *)
            Cycle_Manager_State := 4;
        END_IF;
        
    5: (* PAUSED BETWEEN CYCLES (Holds program until Cycle_Hold_Active turns FALSE) *)
        Internal_FB_Start := TRUE; // Keep FBs active in finished step state
        Status_Message := CONCAT('Cycle ', CONCAT(INT_TO_STRING(Current_Batch_Cycle), ' Complete. Waiting to Release.'));
        
        (* Operator toggles hold status back to FALSE to proceed *)
        IF NOT Cycle_Hold_Active THEN
            Cycle_Manager_State := 3; // Go to auto-reset pulse
        END_IF;
        
    3: (* AUTO-RESET PULSE (Pulse Start command low to reset state machines) *)
        Internal_FB_Start := FALSE;
        Status_Message := 'Resetting Sequence for Next Cycle';
        
        (* Verify sub-blocks have fully reset to idle step *)
        IF NOT Auto_Complete AND NOT Semi_Auto_Complete THEN
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
    Reset := Reset,
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

Semi_Auto_Ctrl(
    Start_Button := Internal_FB_Start,
    E_Stop_Active := E_Stop_Active,
    Reset := Reset,
    load_cell_value := load_cell_semi_auto,
    Semi_Auto_Bin_Material_Mapping := Semi_Auto_Bin_Material_Mapping,
    Semi_Auto_Bin_Cutoff_Weights := Semi_Auto_Bin_Cutoff_Weights,
    Semi_Auto_Bin_Tolerance := Semi_Auto_Bin_Tolerance,
    Semi_Auto_Bin => Semi_Auto_Bin,
    semi_auto_bin_cutoff => semi_auto_bin_cutoff,
    semi_auto_bin_motor => semi_auto_bin_motor,
    Actual_Weights => Semi_Auto_Weights,
    Sequence_Complete => Semi_Auto_Complete,
    Active_Material_ID => Semi_Auto_Active_Mat,
    Active_Bin_ID => Semi_Auto_Active_Bin,
    Active_Target_Weight => Semi_Auto_Active_Target,
    Error_Code => Semi_Auto_Err,
    Status_Message => Semi_Auto_Msg
);

(* Runtime Error Mapping & Aggregation *)
IF Auto_Err <> 0 THEN
    Error_Code := Auto_Err;
    Status_Message := CONCAT('Auto Error: ', Auto_Msg);
ELSIF Semi_Auto_Err <> 0 THEN
    Error_Code := Semi_Auto_Err;
    Status_Message := CONCAT('Semi-Auto Error: ', Semi_Auto_Msg);
ELSIF Cycle_Manager_State = 0 THEN
    Error_Code := 0;
END_IF;
```
