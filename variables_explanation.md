# AC500 V3 Batching System Variable & Array Reference

This document explains the function of all major arrays and variables configured in **`batching12`** and its sub-blocks (`Auto_Batching_V12`, `Semi_Auto_Batching_V12`).

---

## 1. Global Variables (GVL)

*   **`GVL.Recipe_Weights : ARRAY[1..20] OF REAL`**
    *   *Description:* Global recipe targets. Holds the raw target weight setpoint (in kg) for up to 20 different materials. 
*   **`GVL.Run : BOOL`**
    *   *Description:* Process running indicator. Automatically set `TRUE` when sequence is executing and toggles `FALSE` upon completion, resets, or startup error aborts.
*   **`GVL.load_cell_auto : REAL`**
    *   *Description:* Physical load cell weight feedback (in kg) for the automated batching system, mapped to `%MD170`.
*   **`GVL.load_cell_semi_auto : REAL`**
    *   *Description:* Physical load cell weight feedback (in kg) for the semi-automatic batching system, mapped to `%MD180`.

---

## 2. Program Level Variables (`batching12`)

These variables govern the parallel orchestration, configuration parameters, and main HMI/diagnostic mappings:

### Control & Status Toggles
*   **`Start_Button : BOOL`**
    *   *Description:* The main process start button. Toggled `TRUE` to start the batch sequence or resume from an E-Stop pause.
*   **`E_Stop_Active : BOOL`**
    *   *Description:* Emergency Stop active input. When `TRUE`, immediately pauses the execution and turns off all outputs without clearing cumulative weights or cycle states.
*   **`Reset : BOOL`**
    *   *Description:* Dedicated hard reset. Toggling `TRUE` immediately clears all load cell weights to `0.0` kg and resets all sequence steps, error codes, and cycle counts.
*   **`Cycle_Hold_Active : BOOL`**
    *   *Description:* Inter-cycle hold toggle. Set `TRUE` automatically at the end of each batch loop. The operator must set it to `FALSE` to release and begin the next cycle.
*   **`Target_Batch_Cycles : INT`**
    *   *Description:* Configured input for the number of consecutive batch loops to execute automatically (e.g. `2` runs the entire sequence twice).
*   **`Current_Batch_Cycle : INT`**
    *   *Description:* Status indicator showing the sequence cycle number currently running (e.g. cycle `1` or `2`).
*   **`Completed_Batch_Cycles : INT`**
    *   *Description:* Counter tracking how many full sequence loop cycles have successfully finished.
*   **`All_Cycles_Complete : BOOL`**
    *   *Description:* Status boolean. Becomes `TRUE` once the number of completed loops reaches `Target_Batch_Cycles`.
*   **`Error_Code : INT`**
    *   *Description:* Main system diagnostic indicator. Represents active startup or runtime error IDs.
*   **`Status_Message : STRING`**
    *   *Description:* Text status message displayed on HMI panels showing process state or error details.

### Silo Material Mapping
*   **`Auto_Bin_Material_Mapping : ARRAY[1..6] OF INT`**
    *   *Description:* Maps physical Auto Silos `1..6` to GVL Material IDs `1..20`. A value of `0` tells the sequencer to skip that silo.
*   **`Semi_Auto_Bin_Material_Mapping : ARRAY[1..10] OF INT`**
    *   *Description:* Maps physical Semi-Auto Silos `7..16` to GVL Material IDs `1..20`. A value of `0` tells the sequencer to skip that silo.

### Cutoff & Tolerance Configurations
*   **`Auto_Bin_Cutoff_Weights : ARRAY[1..6] OF REAL`**
    *   *Description:* Pre-cutoff weight offset margins (in kg) for the 6 Auto silos. (e.g. `2.0` kg offset on a `50.0` kg target triggers fine feed at `48.0` kg).
*   **`Semi_Auto_Bin_Cutoff_Weights : ARRAY[1..10] OF REAL`**
    *   *Description:* Pre-cutoff weight offset margins (in kg) for the 10 Semi-Auto silos.
*   **`Auto_Bin_Tolerance : ARRAY[1..6] OF REAL`**
    *   *Description:* Tolerance weight offset margins (in kg) for the 6 Auto silos. Subtracted from target to prevent overshoot due to material in-flight after feeder shuts down.
*   **`Semi_Auto_Bin_Tolerance : ARRAY[1..10] OF REAL`**
    *   *Description:* Tolerance weight offset margins (in kg) for the 10 Semi-Auto silos.

### Control Outputs
*   **`Auto_Bin : ARRAY[1..6] OF BOOL`**
    *   *Description:* Coarse feed control valve outputs for Auto silos.
*   **`auto_bin_cutoff : ARRAY[1..6] OF BOOL`**
    *   *Description:* Fine feed control valve outputs for Auto silos.
*   **`auto_bin_motor : ARRAY[1..6] OF BOOL`**
    *   *Description:* Feeder/conveyor motor outputs running during active Auto bin cycles.
*   **`Semi_Auto_Bin : ARRAY[1..10] OF BOOL`**
    *   *Description:* Coarse prompt indicators for Semi-Auto silos.
*   **`semi_auto_bin_cutoff : ARRAY[1..10] OF BOOL`**
    *   *Description:* Fine prompt indicators for Semi-Auto silos.
*   **`semi_auto_bin_motor : ARRAY[1..10] OF BOOL`**
    *   *Description:* Feeder/conveyor motor outputs running during active Semi-Auto bin cycles.

### Dynamic Step Monitors
*   **`Auto_Active_Mat` / `Semi_Auto_Active_Mat` (INT)**
    *   *Description:* Material ID currently being processed in the active sequence step.
*   **`Auto_Active_Bin` / `Semi_Auto_Active_Bin` (INT)**
    *   *Description:* Physical Silo ID currently being processed in the active sequence step.
*   **`Auto_Active_Target` / `Semi_Auto_Active_Target` (REAL)**
    *   *Description:* Displays the effective target weight of the active bin (calculated as GVL Target Weight minus Tolerance).

---

## 3. Function Block Internal Variables (`Auto_Batching_V12` & `Semi_Auto_Batching_V12`)

*   **`Step : INT`**
    *   *Description:* Current active state in the state machine (e.g. `0` = Idle, `1..6` = Active discharge, `11..16` = Settling delays, `99` = Aborted).
*   **`bin_last_weight : REAL`**
    *   *Description:* Scale weight snapshot (baseline) captured right before starting the current step.
*   **`actual_bin : REAL`**
    *   *Description:* Poured weight added during the current step, calculated as `load_cell_value - bin_last_weight`.
*   **`target_act_bin : REAL`**
    *   *Description:* Effective target weight calculated for the active step: `bin_set_value - Tolerance`.
*   **`cutoff_trigger_weight : REAL`**
    *   *Description:* The weight at which the system transitions from Coarse to Fine feed, calculated as: `bin_set_value - Tolerance - Cutoff_Weight`.
*   **`Transition_Timer : TON` / `Completion_Timer : TON`**
    *   *Description:* Standard CODESYS timers governing inter-step transition delays (2 seconds) and scale settling delays (2 seconds).
