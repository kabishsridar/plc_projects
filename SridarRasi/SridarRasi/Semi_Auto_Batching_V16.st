FUNCTION_BLOCK Semi_Auto_Batching_V16
VAR_INPUT
    Master_Run : BOOL;                                  // Master Run command from Auto_Batching_V16.Master_Run (or GVL.Run)
    Reset : BOOL;                                       // System reset pulse (clears active steps, outputs, and actual weights)
    Fault_Reset : BOOL;                                 // Rising-edge fault acknowledge
    E_Stop_Active : BOOL;                               // Emergency Stop status (NC: TRUE = Healthy, FALSE = E-Stop tripped)
    Semi_Auto_Bin_Material_Mapping : ARRAY[1..10] OF INT;// Physical Silos 1..10 to Recipe Material IDs (1..20, 0=skip)
    Semi_Auto_Bin_Tolerance : ARRAY[1..10] OF REAL;     // Allowable weight tolerance window (±kg)
    Inter_Bin_Delay : TIME := T#2S;                     // Settle delay between bins (Semi e.g. T#2S)
    Excess_Allowed : BOOL := FALSE;                     // TRUE = proceed if overfilled; FALSE = raise alarm and halt
    load_cell_value : REAL;                             // Live gross weight input from Semi-Auto scale (kg)
    Line_Fault : BOOL;                                  // Semi scale communication fault
END_VAR
VAR_OUTPUT
    Semi_Auto_Bin : ARRAY[1..10] OF BOOL;               // Bin indicator lamps / dump guidance for Silos 1..10
    Actual_Weights : ARRAY[1..10] OF REAL;              // Net material weight (kg) successfully dosed for each silo
    Semi_Auto_Sum_ActWeight : REAL;                     // Sum of Actual_Weights[1..10]
    Semi_Auto_Target_Weight : ARRAY[1..10] OF REAL;     // Per-bin target kg (bin index 1..10)
    Sequence_Complete : BOOL;                           // Handshake flag: TRUE when all mapped Semi silos complete dosing & settling
    Active_Material_ID : INT;                           // Recipe Material ID currently being dosed (1..20, 0 when idle/complete)
    Active_Bin_ID : INT;                                // Physical Silo index currently being dosed (1..10, 0 when idle/complete)
    Active_Target_Weight : REAL;                        // Target weight setpoint (kg) of active ingredient
    Active_Live_Weight : REAL;                          // Live net/tared weight (kg) of active silo
    Current_Step : INT;                                 // Real-time sequence step: 0=Idle, 1..10=Dosing, 31=Settle, 32=Complete
    Excess_Alarm : BOOL;                                // Overfill alarm
    Status_Message : STRING(80);                        // Diagnostic status message
    Tare_Semi_Auto_Batch : BOOL;                        // One-scan pulse to Semi load cell indicator
    Semi_Auto_Current_Batch_Cycle : INT;                // Active batch cycle number currently processing
    Semi_Auto_Completed_Batch_Cycles : INT;             // Total number of batch cycle loops completed successfully
    Semi_Auto_All_Cycles_Complete : BOOL;               // Flag: TRUE when all Target_Batch_Cycles have finished
END_VAR
VAR
    bin_last_weight : REAL;
    actual_bin : REAL;
    target_weight : REAL;
    min_tol_weight : REAL;
    max_tol_weight : REAL;
    Paused_By_Hold : BOOL;
    Effective_Delay : TIME;
    Inter_Bin_Settling : BOOL;
    Inter_Bin_Settle_Arm : INT;
    Inter_Bin_Timer : TON;
    Settle_Hold_Step : INT;
    Settle_Hold_Mat : INT;
    Settle_Hold_Target : REAL;
    Inter_Bin_Next_Step : INT;
    Mat_Idx : INT;
    j_Mat : INT;
    i : INT;
    j : INT;
    Completion_Timer : TON;
    eff_empty_limit : REAL;
    Scale_Empty_OK : BOOL;
    Semi_Has_Active_Bins : BOOL;
    Auto_Has_Active_Bins : BOOL;
    Duplicate_Found : BOOL;
    Duplicate_Vs_Auto : BOOL;
    Invalid_Material_Range : BOOL;
    Weight_Limit_Error : BOOL;
    Semi_Mapping_All_Zero : BOOL;
    Last_Dosing_Step : INT;
    First_Scan_Done : BOOL;
    Reset_Last : BOOL;
    Reset_Pulse : BOOL;
    Fault_Reset_Last : BOOL;
    Fault_Reset_Pulse : BOOL;
    Master_Run_Last : BOOL;
    Master_Run_Rising : BOOL;
    Effective_Run : BOOL;
    Tare_Pulse_Req : BOOL;
    Last_Batch_Cycle : INT;
END_VAR

// -----------------------------------------------------------------------------
// 0. TIMINGS, THRESHOLDS & EDGE DETECTION
// -----------------------------------------------------------------------------
Effective_Delay := Inter_Bin_Delay;
IF Effective_Delay = T#0S THEN
    Effective_Delay := T#2S;
END_IF;

eff_empty_limit := GVL.Empty_Weight_Limit;
IF eff_empty_limit <= 0.0 THEN
    eff_empty_limit := 0.5;
END_IF;

Scale_Empty_OK := (load_cell_value < eff_empty_limit) AND (GVL.load_cell_semi_auto < eff_empty_limit);

Reset_Pulse := (Reset OR GVL.Reset) AND NOT Reset_Last;
Reset_Last := (Reset OR GVL.Reset);

Fault_Reset_Pulse := Fault_Reset AND NOT Fault_Reset_Last;
Fault_Reset_Last := Fault_Reset;

// Follow Master Run signal (fallback to GVL.Run if pin not connected)
Effective_Run := Master_Run OR GVL.Run;
Master_Run_Rising := Effective_Run AND NOT Master_Run_Last;
Master_Run_Last := Effective_Run;

// -----------------------------------------------------------------------------
// 1. FIRST SCAN POWER-RESUME & RETAIN RESTORE
// -----------------------------------------------------------------------------
IF NOT First_Scan_Done THEN
    First_Scan_Done := TRUE;
    
    // Restore Mapping Retain if GVL uninitialized
    FOR i := 1 TO 10 DO
        IF (GVL.Semi_Auto_Bin_Material_Mapping[i] = 0) AND (PersistentVars.Ret_Semi_Bin_Material_Mapping[i] > 0) THEN
            GVL.Semi_Auto_Bin_Material_Mapping[i] := PersistentVars.Ret_Semi_Bin_Material_Mapping[i];
        END_IF;
    END_FOR;

    // Power Resume: restore exact state without live load cell overwrite
    IF PersistentVars.Ret_Semi_Process_Was_Active AND (PersistentVars.Ret_Semi_Resume_Step >= 1) AND (PersistentVars.Ret_Semi_Resume_Step <= 10) THEN
        Current_Step := PersistentVars.Ret_Semi_Resume_Step;
        Last_Dosing_Step := Current_Step;

        bin_last_weight := PersistentVars.Ret_Semi_bin_last_weight;

        // Reconcile with live load cell weight to account for extra material dumped while power was off
        IF (load_cell_value >= bin_last_weight) AND NOT Line_Fault THEN
            Active_Live_Weight := load_cell_value - bin_last_weight;
            Actual_Weights[Current_Step] := Active_Live_Weight;
        ELSE
            Active_Live_Weight := PersistentVars.Ret_Semi_Active_Live_Weight;
            Actual_Weights[Current_Step] := Active_Live_Weight;
        END_IF;

        Semi_Auto_Sum_ActWeight := 0.0;
        FOR i := 1 TO 10 DO
            IF i <> Current_Step THEN
                Actual_Weights[i] := PersistentVars.Ret_Semi_Actual_Weights[i];
            END_IF;
            GVL.Semi_Auto_Weights[i] := Actual_Weights[i];
            Semi_Auto_Sum_ActWeight := Semi_Auto_Sum_ActWeight + Actual_Weights[i];
        END_FOR;
        GVL.Semi_Auto_Total_Actual_Weight := Semi_Auto_Sum_ActWeight;

        GVL.Semi_Auto_Active_Live_Weight := Active_Live_Weight;
        Active_Material_ID := PersistentVars.Ret_Semi_Active_Material_ID;
        Active_Bin_ID := PersistentVars.Ret_Semi_Active_Bin_ID;
        Active_Target_Weight := PersistentVars.Ret_Semi_Active_Target_Weight;
        GVL.Semi_Auto_Active_Mat := Active_Material_ID;
        GVL.Semi_Auto_Active_Bin := Active_Bin_ID;
        GVL.Semi_Auto_Active_Target_Weight := Active_Target_Weight;

        Paused_By_Hold := TRUE;
        Tare_Semi_Auto_Batch := FALSE;

        // Check if manual dump during power-off has already reached or exceeded target weight
        IF (Active_Target_Weight > 0.0) AND (Active_Live_Weight >= (Active_Target_Weight - Semi_Auto_Bin_Tolerance[Current_Step])) THEN
            IF Active_Live_Weight > (Active_Target_Weight + Semi_Auto_Bin_Tolerance[Current_Step]) THEN
                Status_Message := CONCAT('Semi-Auto [POWER RESUME]: Step ', CONCAT(INT_TO_STRING(Current_Step), ' Overfilled — Waiting Resume'));
            ELSE
                Status_Message := CONCAT('Semi-Auto [POWER RESUME]: Step ', CONCAT(INT_TO_STRING(Current_Step), ' Target Reached — Advancing on Resume'));
            END_IF;
        ELSE
            Status_Message := CONCAT('Semi-Auto [POWER RESUME]: Step ', CONCAT(INT_TO_STRING(Current_Step), ' Resumed — Ready to Feed'));
        END_IF;

    ELSIF PersistentVars.Ret_Semi_Current_Step = 32 THEN
        Current_Step := 32;
        Sequence_Complete := TRUE;
        GVL.Semi_Auto_Sequence_Complete := TRUE;
        FOR i := 1 TO 10 DO
            Actual_Weights[i] := PersistentVars.Ret_Semi_Actual_Weights[i];
            GVL.Semi_Auto_Weights[i] := Actual_Weights[i];
        END_FOR;
        Tare_Semi_Auto_Batch := FALSE;
        Status_Message := 'Semi-Auto [POWER RESUME]: Complete — Waiting for Next Cycle';

    ELSE
        Current_Step := 0;
        Sequence_Complete := FALSE;
        Tare_Semi_Auto_Batch := FALSE;
        Status_Message := 'Semi-Auto [Idle]: Ready — Waiting for Master Start';
    END_IF;
    Last_Batch_Cycle := PersistentVars.Ret_Semi_Last_Batch_Cycle;
END_IF;

// Retain snapshot of mappings
FOR i := 1 TO 10 DO
    PersistentVars.Ret_Semi_Bin_Material_Mapping[i] := GVL.Semi_Auto_Bin_Material_Mapping[i];
END_FOR;

// -----------------------------------------------------------------------------
// 2. CONFIGURATION CHECKS & ERROR DIAGNOSTICS
// -----------------------------------------------------------------------------
Duplicate_Found := FALSE;
Duplicate_Vs_Auto := FALSE;
Semi_Mapping_All_Zero := TRUE;
Invalid_Material_Range := FALSE;
Weight_Limit_Error := FALSE;
Semi_Has_Active_Bins := FALSE;
Auto_Has_Active_Bins := FALSE;

GVL.Semi_Auto_Total_Target_Weight := 0.0;
GVL.Semi_Auto_Material_Count := 0;

FOR i := 1 TO 10 DO
    Mat_Idx := Semi_Auto_Bin_Material_Mapping[i];
    IF (Mat_Idx < 1) OR (Mat_Idx > 20) THEN
        Mat_Idx := GVL.Semi_Auto_Bin_Material_Mapping[i];
    END_IF;
    IF Mat_Idx <> 0 THEN
        Semi_Mapping_All_Zero := FALSE;
    END_IF;
    IF (Mat_Idx < 0) OR (Mat_Idx > 20) THEN
        Invalid_Material_Range := TRUE;
    END_IF;
    IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) THEN
        FOR j := 1 TO 10 DO
            IF j <> i THEN
                j_Mat := Semi_Auto_Bin_Material_Mapping[j];
                IF (j_Mat < 1) OR (j_Mat > 20) THEN
                    j_Mat := GVL.Semi_Auto_Bin_Material_Mapping[j];
                END_IF;
                IF (j_Mat = Mat_Idx) THEN
                    Duplicate_Found := TRUE;
                END_IF;
            END_IF;
        END_FOR;
        FOR j := 1 TO 6 DO
            j_Mat := GVL.Auto_Bin_Material_Mapping[j];
            IF (j_Mat = Mat_Idx) THEN
                Duplicate_Vs_Auto := TRUE;
            END_IF;
        END_FOR;
        target_weight := GVL.Recipe_Weights[Mat_Idx];
        IF target_weight > 0.0 THEN
            GVL.Semi_Auto_Total_Target_Weight := GVL.Semi_Auto_Total_Target_Weight + target_weight;
            GVL.Semi_Auto_Material_Count := GVL.Semi_Auto_Material_Count + 1;
            Semi_Has_Active_Bins := TRUE;
            IF target_weight < Semi_Auto_Bin_Tolerance[i] THEN
                Weight_Limit_Error := TRUE;
            END_IF;
        END_IF;
    END_IF;
END_FOR;

FOR i := 1 TO 6 DO
    Mat_Idx := GVL.Auto_Bin_Material_Mapping[i];
    IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) THEN
        IF GVL.Recipe_Weights[Mat_Idx] > 0.0 THEN
            Auto_Has_Active_Bins := TRUE;
        END_IF;
    END_IF;
END_FOR;

// -----------------------------------------------------------------------------
// 3. MASTER RESET & FAULT RESET
// -----------------------------------------------------------------------------
IF Reset_Pulse THEN
    FOR i := 1 TO 10 DO
        Semi_Auto_Bin[i] := FALSE;
        Actual_Weights[i] := 0.0;
        Semi_Auto_Target_Weight[i] := 0.0;
        GVL.Semi_Auto_Bin[i] := FALSE;
        GVL.Semi_Auto_Weights[i] := 0.0;
        GVL.Semi_Auto_Target_Weights[i] := 0.0;
        PersistentVars.Ret_Semi_Actual_Weights[i] := 0.0;
        PersistentVars.Ret_Semi_Bin_Target_Weights[i] := 0.0;
    END_FOR;
    Semi_Auto_Sum_ActWeight := 0.0;
    GVL.Semi_Auto_Total_Actual_Weight := 0.0;
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
    Excess_Alarm := FALSE;
    Current_Step := 0;
    Tare_Semi_Auto_Batch := FALSE;
    Paused_By_Hold := FALSE;
    PersistentVars.Ret_Semi_Process_Was_Active := FALSE;
    PersistentVars.Ret_Semi_Current_Step := 0;
    PersistentVars.Ret_Semi_Resume_Step := 0;
    PersistentVars.Ret_Semi_bin_last_weight := 0.0;
    bin_last_weight := 0.0;
    Last_Batch_Cycle := 0;
    Status_Message := 'Semi-Auto [Reset]: System Reset complete.';
    RETURN;
END_IF;

IF Fault_Reset_Pulse THEN
    IF NOT Line_Fault AND (GVL.Error_Code = 0) THEN
        Paused_By_Hold := FALSE;
    END_IF;
END_IF;

// Safety & Master Error Hold
IF (NOT E_Stop_Active) OR (GVL.Error_Code > 0) OR Line_Fault THEN
    Paused_By_Hold := TRUE;
    FOR i := 1 TO 10 DO
        Semi_Auto_Bin[i] := FALSE;
        GVL.Semi_Auto_Bin[i] := FALSE;
    END_FOR;
ELSE
    Paused_By_Hold := FALSE;
END_IF;

// -----------------------------------------------------------------------------
// 4. FOLLOWER EXECUTION (CONTROLLED BY MASTER_RUN & BATCH CYCLE ADVANCEMENT)
// -----------------------------------------------------------------------------
// Trigger fresh cycle start on Master_Run rising edge OR when GVL.Current_Batch_Cycle increments
IF Master_Run_Rising 
   OR (Effective_Run AND (Current_Step = 0) AND (GVL.Current_Batch_Cycle > 0)) 
   OR (Effective_Run AND (GVL.Current_Batch_Cycle > Last_Batch_Cycle) AND (GVL.Current_Batch_Cycle > 0)) THEN

    Last_Batch_Cycle := GVL.Current_Batch_Cycle;
    IF NOT Semi_Has_Active_Bins THEN
        Current_Step := 32;
        Sequence_Complete := TRUE;
        GVL.Semi_Auto_Sequence_Complete := TRUE;
    ELSE
        Current_Step := 1;
        Last_Dosing_Step := 1;
        bin_last_weight := load_cell_value;
        PersistentVars.Ret_Semi_bin_last_weight := bin_last_weight;
        Sequence_Complete := FALSE;
        GVL.Semi_Auto_Sequence_Complete := FALSE;
        FOR i := 1 TO 10 DO
            Actual_Weights[i] := 0.0;
            PersistentVars.Ret_Semi_Actual_Weights[i] := 0.0;
        END_FOR;
        IF Scale_Empty_OK THEN
            Tare_Pulse_Req := TRUE;
        END_IF;
    END_IF;
END_IF;

// Tare pulse emission
IF Tare_Pulse_Req THEN
    IF Scale_Empty_OK AND Effective_Run AND (Current_Step <= 1) THEN
        Tare_Semi_Auto_Batch := TRUE;
    ELSE
        Tare_Semi_Auto_Batch := FALSE;
    END_IF;
    Tare_Pulse_Req := FALSE;
ELSE
    Tare_Semi_Auto_Batch := FALSE;
END_IF;

// -----------------------------------------------------------------------------
// 5. SEMI-AUTO DOSING SEQUENCE (STEPS 1..10, SETTLE 31, COMPLETE 32)
// -----------------------------------------------------------------------------
CASE Current_Step OF
    0:
        Active_Material_ID := 0;
        Active_Bin_ID := 0;
        Active_Target_Weight := 0.0;
        Active_Live_Weight := 0.0;
        FOR i := 1 TO 10 DO
            Semi_Auto_Bin[i] := FALSE;
        END_FOR;

    1..10:
        WHILE (Current_Step >= 1) AND (Current_Step <= 10) DO
            Mat_Idx := Semi_Auto_Bin_Material_Mapping[Current_Step];
            IF (Mat_Idx < 1) OR (Mat_Idx > 20) THEN
                Mat_Idx := GVL.Semi_Auto_Bin_Material_Mapping[Current_Step];
            END_IF;
            target_weight := 0.0;
            IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) THEN
                target_weight := GVL.Recipe_Weights[Mat_Idx];
            END_IF;

            IF (Mat_Idx < 1) OR (Mat_Idx > 20) OR (target_weight <= 0.0) THEN
                Semi_Auto_Bin[Current_Step] := FALSE;
                Actual_Weights[Current_Step] := 0.0;
                IF Current_Step = 10 THEN
                    Current_Step := 31;
                    EXIT;
                ELSE
                    Current_Step := Current_Step + 1;
                END_IF;
            ELSE
                EXIT;
            END_IF;
        END_WHILE;

        IF Inter_Bin_Settling THEN
            FOR i := 1 TO 10 DO
                Semi_Auto_Bin[i] := FALSE;
            END_FOR;
            Active_Material_ID := Settle_Hold_Mat;
            Active_Bin_ID := Settle_Hold_Step;
            Active_Target_Weight := Settle_Hold_Target;
            
            IF Inter_Bin_Settle_Arm = 0 THEN
                Inter_Bin_Timer(IN := FALSE);
                Inter_Bin_Settle_Arm := 1;
            ELSE
                Inter_Bin_Timer(IN := TRUE, PT := Effective_Delay);
                IF Inter_Bin_Timer.Q THEN
                    Inter_Bin_Timer(IN := FALSE);
                    bin_last_weight := load_cell_value;
                    PersistentVars.Ret_Semi_bin_last_weight := bin_last_weight;
                    Current_Step := Inter_Bin_Next_Step;
                    Last_Dosing_Step := Current_Step;
                    Inter_Bin_Settling := FALSE;
                    Inter_Bin_Settle_Arm := 0;
                END_IF;
            END_IF;

        ELSIF (Current_Step >= 1) AND (Current_Step <= 10) THEN
            Mat_Idx := Semi_Auto_Bin_Material_Mapping[Current_Step];
            IF (Mat_Idx < 1) OR (Mat_Idx > 20) THEN
                Mat_Idx := GVL.Semi_Auto_Bin_Material_Mapping[Current_Step];
            END_IF;
            target_weight := GVL.Recipe_Weights[Mat_Idx];
            
            IF Current_Step <> Last_Dosing_Step THEN
                bin_last_weight := load_cell_value;
                PersistentVars.Ret_Semi_bin_last_weight := bin_last_weight;
                Last_Dosing_Step := Current_Step;
            END_IF;

            min_tol_weight := target_weight - Semi_Auto_Bin_Tolerance[Current_Step];
            max_tol_weight := target_weight + Semi_Auto_Bin_Tolerance[Current_Step];

            actual_bin := load_cell_value - bin_last_weight;
            IF actual_bin < 0.0 THEN
                actual_bin := 0.0;
            END_IF;

            Active_Material_ID := Mat_Idx;
            Active_Bin_ID := Current_Step;
            Active_Target_Weight := target_weight;

            // Continually track live weight during both Run and Safety Hold (captures extra manual power-off dump)
            Actual_Weights[Current_Step] := actual_bin;
            Active_Live_Weight := actual_bin;

            IF (NOT Paused_By_Hold) AND Effective_Run AND (GVL.Error_Code = 0) THEN
                IF actual_bin < min_tol_weight THEN
                    Semi_Auto_Bin[Current_Step] := TRUE;
                    Excess_Alarm := FALSE;
                    Status_Message := CONCAT('Semi-Auto [Step ', CONCAT(INT_TO_STRING(Current_Step), ']: Human Dumping...'));
                ELSIF actual_bin > max_tol_weight THEN
                    Semi_Auto_Bin[Current_Step] := FALSE;
                    IF Excess_Allowed THEN
                        Excess_Alarm := FALSE;
                        Status_Message := CONCAT('Semi-Auto [Step ', CONCAT(INT_TO_STRING(Current_Step), ']: Target Reached (Excess Allowed)'));
                        Settle_Hold_Step := Current_Step;
                        Settle_Hold_Mat := Mat_Idx;
                        Settle_Hold_Target := target_weight;
                        IF Current_Step >= 10 THEN
                            Current_Step := 31;
                        ELSE
                            Inter_Bin_Next_Step := Current_Step + 1;
                            Inter_Bin_Settling := TRUE;
                            Inter_Bin_Settle_Arm := 0;
                        END_IF;
                    ELSE
                        Excess_Alarm := TRUE;
                        Status_Message := CONCAT('Semi-Auto [Step ', CONCAT(INT_TO_STRING(Current_Step), ']: Excess Weight Alarm!'));
                    END_IF;
                ELSE
                    Semi_Auto_Bin[Current_Step] := FALSE;
                    Excess_Alarm := FALSE;
                    Status_Message := CONCAT('Semi-Auto [Step ', CONCAT(INT_TO_STRING(Current_Step), ']: Target Reached - Advancing'));
                    Settle_Hold_Step := Current_Step;
                    Settle_Hold_Mat := Mat_Idx;
                    Settle_Hold_Target := target_weight;
                    IF Current_Step >= 10 THEN
                        Current_Step := 31;
                    ELSE
                        Inter_Bin_Next_Step := Current_Step + 1;
                        Inter_Bin_Settling := TRUE;
                        Inter_Bin_Settle_Arm := 0;
                    END_IF;
                END_IF;
            END_IF;
        END_IF;

    31: // FINAL SETTLING DELAY
        Active_Material_ID := 0;
        Active_Bin_ID := 0;
        Active_Target_Weight := 0.0;
        Active_Live_Weight := 0.0;
        FOR i := 1 TO 10 DO
            Semi_Auto_Bin[i] := FALSE;
        END_FOR;
        Status_Message := 'Semi-Auto [Step 31]: Settling Delay in progress...';
        Completion_Timer(IN := TRUE, PT := Effective_Delay);
        IF Completion_Timer.Q THEN
            Completion_Timer(IN := FALSE);
            Current_Step := 32;
        END_IF;

    32: // SEMI-AUTO SEQUENCE COMPLETE (WAITS FOR MASTER/PARTNER ASYNCHRONOUSLY)
        Active_Material_ID := 0;
        Active_Bin_ID := 0;
        Active_Target_Weight := 0.0;
        Active_Live_Weight := 0.0;
        FOR i := 1 TO 10 DO
            Semi_Auto_Bin[i] := FALSE;
        END_FOR;
        Sequence_Complete := TRUE;
        GVL.Semi_Auto_Sequence_Complete := TRUE;
        IF NOT GVL.Auto_Sequence_Complete THEN
            Status_Message := 'Semi-Auto [Step 32]: Semi Finished — Waiting for Auto to complete...';
        ELSE
            Status_Message := 'Semi-Auto [Step 32]: Both Sequences Complete';
        END_IF;
END_CASE;

// -----------------------------------------------------------------------------
// 6. OUTPUT SYNCHRONIZATION & PERSISTENT SNAPSHOT
// -----------------------------------------------------------------------------
FOR i := 1 TO 10 DO
    GVL.Semi_Auto_Bin[i] := Semi_Auto_Bin[i];
    GVL.Semi_Auto_Weights[i] := Actual_Weights[i];
END_FOR;

Semi_Auto_Sum_ActWeight := 0.0;
FOR i := 1 TO 10 DO
    Semi_Auto_Sum_ActWeight := Semi_Auto_Sum_ActWeight + Actual_Weights[i];
END_FOR;
GVL.Semi_Auto_Total_Actual_Weight := Semi_Auto_Sum_ActWeight;

GVL.Semi_Auto_Active_Mat := Active_Material_ID;
GVL.Semi_Auto_Active_Bin := Active_Bin_ID;
GVL.Semi_Auto_Active_Target_Weight := Active_Target_Weight;
GVL.Semi_Auto_Active_Live_Weight := Active_Live_Weight;
GVL.Semi_Auto_Current_Step := Current_Step;
GVL.Semi_Auto_Excess_Alarm := Excess_Alarm;

Semi_Auto_Current_Batch_Cycle := GVL.Current_Batch_Cycle;
Semi_Auto_Completed_Batch_Cycles := GVL.Completed_Batch_Cycles;
Semi_Auto_All_Cycles_Complete := GVL.All_Cycles_Complete;

FOR i := 1 TO 10 DO
    Mat_Idx := Semi_Auto_Bin_Material_Mapping[i];
    IF (Mat_Idx < 1) OR (Mat_Idx > 20) THEN
        Mat_Idx := GVL.Semi_Auto_Bin_Material_Mapping[i];
    END_IF;
    target_weight := 0.0;
    IF (Mat_Idx >= 1) AND (Mat_Idx <= 20) THEN
        target_weight := GVL.Recipe_Weights[Mat_Idx];
    END_IF;
    Semi_Auto_Target_Weight[i] := target_weight;
    GVL.Semi_Auto_Target_Weights[i] := target_weight;
END_FOR;

// Persistent Snapshot
IF NOT Effective_Run AND (Current_Step = 0 OR Current_Step = 32) THEN
    PersistentVars.Ret_Semi_Process_Was_Active := FALSE;
    PersistentVars.Ret_Semi_Current_Step := 0;
    PersistentVars.Ret_Semi_Resume_Step := 0;
    PersistentVars.Ret_Semi_Active_Live_Weight := 0.0;
    PersistentVars.Ret_Semi_bin_last_weight := 0.0;
    FOR i := 1 TO 10 DO
        PersistentVars.Ret_Semi_Actual_Weights[i] := 0.0;
    END_FOR;
ELSIF Effective_Run THEN
    PersistentVars.Ret_Semi_Process_Was_Active := TRUE;
    PersistentVars.Ret_Semi_Current_Step := Current_Step;
    IF (Current_Step >= 1) AND (Current_Step <= 10) THEN
        PersistentVars.Ret_Semi_Resume_Step := Current_Step;
    END_IF;
    PersistentVars.Ret_Semi_Active_Material_ID := Active_Material_ID;
    PersistentVars.Ret_Semi_Active_Bin_ID := Active_Bin_ID;
    PersistentVars.Ret_Semi_Active_Target_Weight := Active_Target_Weight;
    PersistentVars.Ret_Semi_Active_Live_Weight := Active_Live_Weight;
    PersistentVars.Ret_Semi_bin_last_weight := bin_last_weight;
    PersistentVars.Ret_Semi_Last_Batch_Cycle := Last_Batch_Cycle;
    FOR i := 1 TO 10 DO
        PersistentVars.Ret_Semi_Actual_Weights[i] := Actual_Weights[i];
    END_FOR;
END_IF;
END_FUNCTION_BLOCK
