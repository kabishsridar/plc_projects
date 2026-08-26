# AC500 V3 Batching System Variable & Array Reference

This document explains the function of all major arrays and variables configured in **`batching13`** and its sub-blocks (`Auto_Batching_V13`, `Semi_Auto_Batching_V13`).

---

## 1. Global Variables (GVL)

*   **`GVL.Recipe_Weights : ARRAY[1..20] OF REAL`** (at `%MD100`)
    *   *Description:* Holds raw target weight setpoints (in kg) for up to 20 ingredients.
*   **`GVL.Auto_Bin_Material_Mapping : ARRAY[1..6] OF INT`** (at `%MW50`)
    *   *Description:* Maps physical Auto Silos `1..6` to GVL Material IDs `1..20`. A value of `0` skips that silo.
*   **`GVL.Semi_Auto_Bin_Material_Mapping : ARRAY[1..10] OF INT`** (at `%MW60`)
    *   *Description:* Maps physical Semi-Auto Silos `7..16` to GVL Material IDs `1..20`. A value of `0` skips that silo.
*   **`GVL.Auto_Bin_Cutoff_Weights : ARRAY[1..6] OF REAL`** (at `%MD120`)
    *   *Description:* Pre-cutoff weight offsets (in kg) triggering transition from Coarse to Fine feed.
*   **`GVL.Semi_Auto_Bin_Cutoff_Weights : ARRAY[1..10] OF REAL`** (at `%MD130`)
    *   *Description:* Pre-cutoff weight offsets (in kg) for Semi-Auto silos.
*   **`GVL.Auto_Bin_Tolerance : ARRAY[1..6] OF REAL`** (at `%MD150`)
    *   *Description:* Allowable tolerance window ($\pm\text{Tol}$) defining `Min_Tol = Target - Tol` and `Max_Tol = Target + Tol`.
*   **`GVL.Semi_Auto_Bin_Tolerance : ARRAY[1..10] OF REAL`** (at `%MD160`)
    *   *Description:* Allowable tolerance window ($\pm\text{Tol}$) for Semi-Auto silos.
*   **`GVL.Start_Button : BOOL`** (at `%MX1.0`)
    *   *Description:* Start/Resume command for batch sequencing.
*   **`GVL.E_Stop_Active : BOOL`** (at `%MX1.1`)
    *   *Description:* Emergency Stop pause signal. Holds step states and freezes execution without clearing cumulative progress.
*   **`GVL.Reset : BOOL`** (at `%MX1.3`)
    *   *Description:* Single-shot reset trigger. Instantly zeroes all outputs, weight registers, and step states, then auto-clears back to `FALSE`.
*   **`GVL.Cycle_Hold_Active : BOOL`** (at `%MX1.2`)
    *   *Description:* Inter-cycle hold toggle. Becomes `TRUE` after each batch loop; must be set to `FALSE` to begin the next cycle.
*   **`GVL.Run : BOOL`** (at `%MX1.4`)
    *   *Description:* Process running indicator (`TRUE` during active batching, `FALSE` when idle, completed, or aborted).
*   **`GVL.Excess_Allowed : BOOL`** (at `%MX1.5`)
    *   *Description:* Excess weight bypass toggle. When `TRUE`, if actual weight exceeds `Max_Tol`, it logs and proceeds. When `FALSE`, it asserts `Excess_Alarm` and holds execution until weight is reduced.
*   **`GVL.Auto_Excess_Alarm : BOOL`** (at `%MX1.6`)
    *   *Description:* Active excess weight alarm indicator for the automated batching system.
*   **`GVL.Semi_Auto_Excess_Alarm : BOOL`** (at `%MX1.7`)
    *   *Description:* Active excess weight alarm indicator for the semi-automatic batching system.
*   **`GVL.load_cell_auto : REAL`** (at `%MD170`)
    *   *Description:* Live scale weight feedback for the automated batching system.
*   **`GVL.load_cell_semi_auto : REAL`** (at `%MD180`)
    *   *Description:* Live scale weight feedback for the semi-automatic batching system.
*   **`GVL.Inter_Bin_Delay : TIME`** (at `%MD190`)
    *   *Description:* Global settling delay time between closing a silo and verifying scale tolerance (defaults to `T#2S` if `T#0S`).
*   **`GVL.Target_Batch_Cycles` / `GVL.Current_Batch_Cycle` (INT)** (at `%MW74`, `%MW75`)
    *   *Description:* Configured cycle loops and current cycle number.
*   **`GVL.Auto_Active_Mat` / `GVL.Auto_Active_Bin` / `GVL.Semi_Auto_Active_Mat` / `GVL.Semi_Auto_Active_Bin` (INT)** (at `%MW70`..`%MW73`)
    *   *Description:* Real-time active material and silo IDs.
*   **`GVL.Error_Code : INT`** (at `%MW76`)
    *   *Description:* Active system diagnostic error code.

---

## 2. Program Level Variables (`batching13`)

*   **`Auto_Ctrl` / `Semi_Auto_Ctrl`**: Instance calls of `Auto_Batching_V13` and `Semi_Auto_Batching_V13`.
*   **`Auto_Weights : ARRAY[1..6] OF REAL`**: Poured weights recorded per auto silo.
*   **`Semi_Auto_Weights : ARRAY[1..10] OF REAL`**: Poured weights recorded per semi-auto silo.
*   **`Auto_Complete` / `Semi_Auto_Complete` / `All_Cycles_Complete` (BOOL)**: Sequence completion flags.
*   **`Status_Message : STRING`**: Real-time HMI diagnostic and process status display.
