PROGRAM batching13
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


(* 1. STARTUP CONFIGURATION, RECIPE TOTALS, AND WEIGHT CHECKS *)
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
            IF GVL.Recipe_Weights[GVL.Auto_Bin_Material_Mapping[i]] < (GVL.Auto_Coarse_To_Fine_speed[i] + GVL.Auto_Bin_Tolerance[i]) THEN
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
            IF GVL.Recipe_Weights[GVL.Semi_Auto_Bin_Material_Mapping[j]] < (GVL.Semi_Auto_Coarse_To_Fine_speed[j] + GVL.Semi_Auto_Bin_Tolerance[j]) THEN
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
    Auto_Coarse_To_Fine_speed := GVL.Auto_Coarse_To_Fine_speed,
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
    Semi_Auto_Coarse_To_Fine_speed := GVL.Semi_Auto_Coarse_To_Fine_speed,
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
