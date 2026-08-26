# Walkthrough - PROGRAM Batching Control (batching12)

I have successfully updated the project to implement **`batching12`** featuring process execution run flags (`GVL.Run`), startup target weight underflow protection checks, and automatic completion triggers on execution halts inside `Rasi_feeds_batching.project` and pushed it to GitHub.

## Changes Made

1. **Process Run Flag (`GVL.Run`)**:
   - Toggles `TRUE` as soon as the start button begins a batch execution cycle.
   - Automatically toggles `FALSE` when the sequence finishes, a startup configuration error halts execution, or a manual reset is pulsed.
2. **Startup Target Weight Check**:
   - Validates that every mapped material target weight (`GVL.Recipe_Weights[Mat_Idx]`) is greater than or equal to `Cutoff_Weight[i] + Tolerance[i]` for that silo.
   - If a target is too small (causing mathematical underflow), it aborts, sets `GVL.Error_Code := 3` (`Error 3: Recipe weight is less than Cutoff + Tolerance!`), and registers the sequence as completed.
3. **Completion Flags on Halt**:
   - Whenever an error occurs or the sequencer aborts, all completion status outputs (`Auto_Complete`, `Semi_Auto_Complete`, and `All_Cycles_Complete`) evaluate to `TRUE` as requested.
4. **Compilation**:
   - Verified that the project builds successfully with **0 errors**.

### Program ST Code (`batching12`)

**ST Implementation**:
```pascal
(* 1. STARTUP CONFIGURATION AND WEIGHT CHECKS *)
Duplicate_Found := FALSE;
Invalid_Material_Range := FALSE;
Weight_Limit_Error := FALSE;

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
    
    (* Check 3: Recipe weight is less than Cutoff + Tolerance *)
    IF GVL.Auto_Bin_Material_Mapping[i] <> 0 AND GVL.Auto_Bin_Material_Mapping[i] <= 20 THEN
        IF GVL.Recipe_Weights[GVL.Auto_Bin_Material_Mapping[i]] > 0.0 THEN
            IF GVL.Recipe_Weights[GVL.Auto_Bin_Material_Mapping[i]] < (GVL.Auto_Bin_Cutoff_Weights[i] + GVL.Auto_Bin_Tolerance[i]) THEN
                Weight_Limit_Error := TRUE;
            END_IF;
        END_IF;
    END_IF;
END_FOR;

FOR j := 1 TO 10 DO
    (* Check 2: Out of Range (Semi-Auto) *)
    IF GVL.Semi_Auto_Bin_Material_Mapping[j] < 0 OR GVL.Semi_Auto_Bin_Material_Mapping[j] > 20 THEN
        Invalid_Material_Range := TRUE;
    END_IF;
    
    (* Check 3: Recipe weight check (Semi-Auto) *)
    IF GVL.Semi_Auto_Bin_Material_Mapping[j] <> 0 AND GVL.Semi_Auto_Bin_Material_Mapping[j] <= 20 THEN
        IF GVL.Recipe_Weights[GVL.Semi_Auto_Bin_Material_Mapping[j]] > 0.0 THEN
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

(* Abort/Clear arrays if Configuration error is active or Hard Reset is pressed *)
IF (GVL.Error_Code >= 1 AND GVL.Error_Code <= 3) OR GVL.Reset THEN
    FOR i := 1 TO 6 DO Auto_Bin[i] := FALSE; auto_bin_cutoff[i] := FALSE; auto_bin_motor[i] := FALSE; END_FOR;
    FOR i := 1 TO 10 DO Semi_Auto_Bin[i] := FALSE; semi_auto_bin_cutoff[i] := FALSE; semi_auto_bin_motor[i] := FALSE; END_FOR;
    
    Internal_FB_Start := FALSE;
    Auto_Ctrl(Start_Button := FALSE, E_Stop_Active := FALSE, Reset := GVL.Reset, load_cell_value := load_cell_auto);
    Semi_Auto_Ctrl(Start_Button := FALSE, E_Stop_Active := FALSE, Reset := GVL.Reset, load_cell_value := load_cell_semi_auto);
    
    Auto_Active_Target := 0.0;
    Semi_Auto_Active_Target := 0.0;
    
    (* Wherever it stops, completion outputs must register TRUE *)
    Auto_Complete := TRUE;
    Semi_Auto_Complete := TRUE;
    All_Cycles_Complete := TRUE;
    
    GVL.Cycle_Hold_Active := FALSE;
    GVL.Run := FALSE;
    Cycle_Manager_State := 0;
    
    IF GVL.Reset THEN
        GVL.Error_Code := 0;
        Status_Message := 'System Reset Activated';
        Auto_Complete := FALSE;
        Semi_Auto_Complete := FALSE;
        All_Cycles_Complete := FALSE;
    END_IF;
    RETURN;
END_IF;


(* 2. REPETITIVE CYCLE MANAGER STATE MACHINE WITH HOLD RELEASE *)
CASE Cycle_Manager_State OF
    0: (* IDLE STATE *)
        Internal_FB_Start := FALSE;
        All_Cycles_Complete := FALSE;
        GVL.Cycle_Hold_Active := FALSE;
        GVL.Run := FALSE;
        IF GVL.Error_Code = 0 THEN Status_Message := 'System Ready'; END_IF;
        
        IF GVL.Start_Button THEN
            GVL.Current_Batch_Cycle := 1;
            Completed_Batch_Cycles := 0;
            GVL.Run := TRUE;
            Cycle_Manager_State := 1;
        END_IF;
        
    1: (* RUN STATE (Run Sub-Blocks) *)
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
        
        IF GVL.Current_Batch_Cycle < GVL.Target_Batch_Cycles THEN
            (* Hold cycle loop progression *)
            GVL.Cycle_Hold_Active := TRUE;
            Cycle_Manager_State := 5; // Go to hold wait state
        else
            (* All loop cycles complete *)
            Cycle_Manager_State := 4;
        END_IF;
        
    5: (* PAUSED BETWEEN CYCLES (Holds program until GVL.Cycle_Hold_Active turns FALSE) *)
        Internal_FB_Start := TRUE; // Keep FBs active in finished step state
        GVL.Run := TRUE;
        Status_Message := CONCAT('Cycle ', CONCAT(INT_TO_STRING(GVL.Current_Batch_Cycle), ' Complete. Waiting to Release.'));
        
        (* Operator toggles hold status back to FALSE to proceed *)
        IF NOT GVL.Cycle_Hold_Active THEN
            Cycle_Manager_State := 3; // Go to auto-reset pulse
        END_IF;
        
    3: (* AUTO-RESET PULSE (Pulse Start command low to reset state machines) *)
        Internal_FB_Start := FALSE;
        GVL.Run := TRUE;
        Status_Message := 'Resetting Sequence for Next Cycle';
        
        (* Verify sub-blocks have fully reset to idle step *)
        IF NOT Auto_Complete AND NOT Semi_Auto_Complete THEN
            GVL.Current_Batch_Cycle := GVL.Current_Batch_Cycle + 1;
            Cycle_Manager_State := 1; // Start next cycle
        END_IF;
        
    4: (* SEQUENCE FULLY COMPLETED STATE *)
        Internal_FB_Start := FALSE;
        All_Cycles_Complete := TRUE;
        GVL.Run := FALSE;
        Status_Message := 'All Batch Cycles Completed';
        
        IF NOT GVL.Start_Button THEN
            Cycle_Manager_State := 0;
        END_IF;
END_CASE;
```
