# AC500 V3 Batching System Variable & Array Reference

This document explains the function of all major arrays and variables configured in **`batching14`** (FBD) and **`batching13`** (ST) along with their sub-blocks (`Auto_Batching_V14`/`V13`, `Semi_Auto_Batching_V14`/`V13`).

---

## 1. Global Variables (GVL)

### Recipes & Mappings
* **`GVL.Recipe_Weights : ARRAY[1..20] OF REAL`** (at `%MD100`)
  * Holds raw target weight setpoints (in kg) for up to 20 ingredients.
* **`GVL.Auto_Bin_Material_Mapping : ARRAY[1..6] OF INT`** (at `%MW50`)
  * Maps physical Auto Silos `1..6` to GVL Material IDs `1..20`. A value of `0` skips that silo.
* **`GVL.Semi_Auto_Bin_Material_Mapping : ARRAY[1..10] OF INT`** (at `%MW60`)
  * Maps physical Semi-Auto Silos `1..10` to GVL Material IDs `1..20`. A value of `0` skips that silo.

### Coarse to Fine Transition, Tolerance & Cumulative Totals
* **`GVL.Auto_Coarse_To_Fine_Speed : ARRAY[1..6] OF REAL`** (at `%MD120`)
  * Weight offset (in kg) before reaching target that triggers the transition from Coarse Feed to Fine Feed (`Cutoff_Trigger = Target - Coarse_To_Fine_Speed`).
* **`GVL.Semi_Auto_Coarse_To_Fine_Speed : ARRAY[1..10] OF REAL`** (at `%MD130`)
  * Weight offset (in kg) before reaching target that triggers the transition from Coarse Feed to Fine Feed for Semi-Auto silos.
* **`GVL.Auto_Bin_Tolerance : ARRAY[1..6] OF REAL`** (at `%MD150`)
  * Allowable tolerance window ($\pm\text{Tol}$) defining `Min_Tol = Target - Tol` and `Max_Tol = Target + Tol`.
* **`GVL.Semi_Auto_Bin_Tolerance : ARRAY[1..10] OF REAL`** (at `%MD160`)
  * Allowable tolerance window ($\pm\text{Tol}$) for Semi-Auto silos.
* **`GVL.Auto_Initial_Tolerance : REAL`** (at `%MD176`)
  * Maximum allowable tare offset on scale before starting Auto sequence (checked only before setting `Run = TRUE`).
* **`GVL.Semi_Auto_Initial_Tolerance : REAL`** (at `%MD178`)
  * Maximum allowable tare offset on scale before starting Semi-Auto sequence (checked only before setting `Run = TRUE`).
* **`GVL.Auto_Total_Target_Weight : REAL`** (at `%MD180`)
  * Cumulative recipe target weight summed across all active Auto bins ($1..6$).
* **`GVL.Semi_Auto_Total_Target_Weight : REAL`** (at `%MD184`)
  * Cumulative recipe target weight summed across all active Semi-Auto bins ($1..10$).
* **`GVL.Auto_Material_Count : INT`** (at `%MW77`)
  * Count of active non-zero silos in Auto.
* **`GVL.Semi_Auto_Material_Count : INT`** (at `%MW78`)
  * Count of active non-zero silos in Semi-Auto.

### Active Bin Real-Time Target & Live Tared Weights (HMI Bidirectional)
* **`GVL.Auto_Active_Target_Weight : REAL`** (at `%MD220`)
  * Target weight (kg) of the currently active pouring Auto bin. Can be loaded from `Recipe_Weights` or entered directly from the HMI. In Idle, HMI inputs are preserved and not overwritten.
* **`GVL.Semi_Auto_Active_Target_Weight : REAL`** (at `%MD224`)
  * Target weight (kg) of the currently active pouring Semi-Auto bin. Can be loaded from `Recipe_Weights` or entered directly from the HMI. In Idle, HMI inputs are preserved and not overwritten.
* **`GVL.Auto_Active_Live_Weight : REAL`** (at `%MD228`)
  * Live tared weight (kg) poured from the currently active Auto bin (`load_cell - bin_last_weight`).
* **`GVL.Semi_Auto_Active_Live_Weight : REAL`** (at `%MD232`)
  * Live tared weight (kg) poured from the currently active Semi-Auto bin (`load_cell - bin_last_weight`).

### Control Signals, Sequence Synchronization & Diagnostics
* **`GVL.Start_Button : BOOL`** (at `%MX2.0`)
  * Start/Resume command for batch sequencing. Auto-cleared to `FALSE` when all cycles complete.
* **`GVL.E_Stop_Active : BOOL`** (at `%MX2.1`)
  * Standard Normally Closed (NC) Emergency Stop input:
    * `TRUE` = Circuit closed, Healthy (E-Stop not pressed).
    * `FALSE` = Circuit open, E-Stop Pressed/Tripped! All outputs immediately shut off.
* **`GVL.Reset : BOOL`** (at `%MX2.3`)
  * Single-shot reset trigger. Zeroes all target recipe weights, active target weights, live weights, and cycle counters across both blocks without race conditions.
* **`GVL.Cycle_Hold_Active : BOOL`** (at `%MX2.4`)
  * Inter-cycle hold toggle. Set to `TRUE` between cycles; clear to `FALSE` to proceed to next cycle after tare scale check.
* **`GVL.Run : BOOL`** (at `%MX2.5`)
  * Process running indicator (`TRUE` during active batching).
* **`GVL.Auto_Sequence_Complete : BOOL`** (at `%MX3.0`)
  * Handshake flag indicating Auto Silos 1..6 have completed their active cycle.
* **`GVL.Semi_Auto_Sequence_Complete : BOOL`** (at `%MX3.1`)
  * Handshake flag indicating Semi-Auto Silos 1..10 have completed their active cycle.
* **`GVL.Auto_Excess_Allowed : BOOL`** (at `%MX2.6`)
  * Auto excess weight bypass toggle.
* **`GVL.Semi_Auto_Excess_Allowed : BOOL`** (at `%MX2.9`)
  * Semi-Auto excess weight bypass toggle.
* **`GVL.Auto_Excess_Alarm : BOOL`** (at `%MX2.7`)
  * Active excess weight alarm indicator for Auto.
* **`GVL.Semi_Auto_Excess_Alarm : BOOL`** (at `%MX2.8`)
  * Active excess weight alarm indicator for Semi-Auto.
* **`GVL.load_cell_auto : REAL`** (at `%MD174`)
  * Live scale weight feedback for Auto.
* **`GVL.load_cell_semi_auto : REAL`** (at `%MD175`)
  * Live scale weight feedback for Semi-Auto.
* **`GVL.Auto_Inter_Bin_Delay : TIME`** (at `%MD190`)
  * Settling delay time between Auto silos.
* **`GVL.Semi_Auto_Inter_Bin_Delay : TIME`** (at `%MD194`)
  * Settling delay time between Semi-Auto silos.
* **`GVL.Target_Batch_Cycles` / `GVL.Current_Batch_Cycle` (INT)** (at `%MW74`, `%MW75`)
* **`GVL.Auto_Active_Mat` / `GVL.Auto_Active_Bin` / `GVL.Semi_Auto_Active_Mat` / `GVL.Semi_Auto_Active_Bin` (INT)** (at `%MW70`..`%MW73`)
* **`GVL.Error_Code : INT`** (at `%MW76`)

### Process Outputs & Actual Weights
* **`GVL.Auto_Bin : ARRAY[1..6] OF BOOL`**
* **`GVL.auto_bin_cutoff : ARRAY[1..6] OF BOOL`**
* **`GVL.auto_bin_motor : ARRAY[1..6] OF BOOL`**
* **`GVL.Semi_Auto_Bin : ARRAY[1..10] OF BOOL`**
* **`GVL.semi_auto_bin_cutoff : ARRAY[1..10] OF BOOL`**
* **`GVL.semi_auto_bin_motor : ARRAY[1..10] OF BOOL`**
* **`GVL.Auto_Weights : ARRAY[1..6] OF REAL`**
* **`GVL.Semi_Auto_Weights : ARRAY[1..10] OF REAL`**
