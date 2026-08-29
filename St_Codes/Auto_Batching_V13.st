FUNCTION_BLOCK Auto_Batching_V13
VAR_INPUT
    Start_Button : BOOL;      // Signal to start/resume the batching sequence
    E_Stop_Active : BOOL;     // Emergency Stop (Pause/Hold signal)
    Reset : BOOL;             // Hard reset sequence trigger
    Auto_Bin_Material_Mapping : ARRAY[1..6] OF INT; // Material index mapping for 6 bins
    Auto_Coarse_To_Fine_speed : ARRAY[1..6] OF REAL; // Cutoff weight thresholds (kg)
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

(* Auto Batching FB V13 with Real-Time Instant Excess Verification & Clean Multi-Cycle Reset *)

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
            cutoff_trigger_weight := target_weight - Auto_Coarse_To_Fine_speed[Step];
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

