# AC500 V3 Batching System Variable & Array Reference

This document explains the function of all major arrays and variables configured in **`batching13`** and its sub-blocks (`Auto_Batching_V13`, `Semi_Auto_Batching_V13`).

---

## 1. Global Variables (GVL)

### Recipes & Mappings
* **`GVL.Recipe_Weights : ARRAY[1..20] OF REAL`** (at `%MD100`)
  * Holds raw target weight setpoints (in kg) for up to 20 ingredients.
* **`GVL.Auto_Bin_Material_Mapping : ARRAY[1..6] OF INT`** (at `%MW50`)
  * Maps physical Auto Silos `1..6` to GVL Material IDs `1..20`. A value of `0` skips that silo.
* **`GVL.Semi_Auto_Bin_Material_Mapping : ARRAY[1..10] OF INT`** (at `%MW60`)
  * Maps physical Semi-Auto Silos `1..10` to GVL Material IDs `1..20`. A value of `0` skips that silo.

### Cutoff, Tolerance & Cumulative Totals
* **`GVL.Auto_Bin_Cutoff_Weights : ARRAY[1..6] OF REAL`** (at `%MD120`)
  * Pre-cutoff weight offsets (in kg) triggering transition from Coarse to Fine feed.
* **`GVL.Semi_Auto_Bin_Cutoff_Weights : ARRAY[1..10] OF REAL`** (at `%MD130`)
  * Pre-cutoff weight offsets (in kg) for Semi-Auto silos.
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

### Control Signals & Diagnostics
* **`GVL.Start_Button : BOOL`** (at `%MX2.0`)
  * Start/Resume command for batch sequencing.
* **`GVL.E_Stop_Active : BOOL`** (at `%MX2.1`)
  * Emergency Stop pause signal.
* **`GVL.Reset : BOOL`** (at `%MX2.3`)
  * Single-shot reset trigger. Instantly zeroes all outputs, weight registers, and step states.
* **`GVL.Cycle_Hold_Active : BOOL`** (at `%MX2.4`)
  * Inter-cycle hold toggle. Set to `FALSE` to start next cycle.
* **`GVL.Run : BOOL`** (at `%MX2.5`)
  * Process running indicator (`TRUE` during active batching).
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
