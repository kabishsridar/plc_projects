# AC500 V3 PLC Batching System Documentation

This repository contains CODESYS project files implementing automatic and manual batching sequences for the **PM5032-T-ETH (AC500 V3)** PLC. The batching system handles up to 6 automatic silos and 10 manual silos in parallel using cumulative gain-in-weight measurements.

---

## Program Versions Overview

*   **`batching3`**: Sequential cumulative gain-in-weight batching for 6 bins using recipe indexing (20 materials, skips `0` index).
*   **`batching4`**: Implements the dynamic `Actual_Weights` array (tracks active weights, freezes previous steps, resets on complete) as a self-contained program.
*   **`batching5`**: Introduces percentage-based slow-down transitions (coarse-to-fine speed selection outputs `Discharge_Bin_Coarse` and `Discharge_Bin_Fine`) and diagnostic HMI statuses.
*   **`batching6`**: Restructures the project into parallel blocks using GVL weights:
    *   `Auto_Batching` (FB): Handles 6 automated bins.
    *   `Manual_Batching` (FB): Handles 10 manual operator bins.
    *   `batching6` (PROGRAM): Calls both FBs concurrently.
*   **`batching7`**: Adds cross-array distinct material verification, active material logging outputs, and active bin integer outputs.
*   **`batching8`**: Integrates a comprehensive set of diagnostic error checks and device interlocks.
*   **`batching9`**: Implements a three-stage feed sequence (Coarse Valve, Fine Cutoff, and main Conveyor Motor) with tolerance weight offset compensation configuration arrays (`Auto_Bin_Tolerance` and `Manual_Bin_Tolerance`) to offset in-flight overshoots.
*   **`batching10`**: Implements repetitive batch cycle manager loop controls (`Target_Batch_Cycles`, `Completed_Batch_Cycles`, `All_Cycles_Complete`) enabling automatic sequence execution repetitions.
*   **`batching11`**: Renames Manual parameters to Semi-Auto, adds inter-cycle hold triggers (`Cycle_Hold_Active`), E-Stop pause/resume, and immediate hard reset logic.

---

## Diagnostic Error Codes Reference (`batching11`)

The system aggregates configuration and runtime faults into an integer `Error_Code` and displays corresponding HMI text in `Status_Message`.

| Error Code | Category | HMI Message | Description | Recovery |
| :---: | :--- | :--- | :--- | :--- |
| **`1`** | Configuration | `Error 1: Duplicate Material ID mapped in Auto and Semi-Auto!` | Same active Material ID (excluding 0) is mapped to both Auto and Semi-Auto arrays. | Re-configure mapping list. |
| **`2`** | Configuration | `Error 2: Material Index configuration out of range (1..20)!` | A bin is mapped to an index higher than the 20 available recipe slots. | Change index to `1..20` (or `0` to skip). |
| **`3`** | Configuration | `Error 3: Configured Material ID has a 0.0 kg target weight!` | An active bin is mapped to a material that has its recipe weight set to 0.0 kg. | Configure target weight > 0.0 kg in GVL. |
| **`10`** | Hardware | `Auto Error: Error 10: Silo Valve failed to open!` | Auto valve commanded open, but limits did not register open within 5 seconds. | Check valve solenoids and feedback limit switches. |
| **`11`** | Hardware | `Auto Error: Error 11: Silo Valve failed to close!` | Auto valve commanded closed, but feedback remained open for over 5 seconds. | Check for valve jams or stuck solenoids. |
| **`12`** | Safety | `Error 12: Emergency Stop Active!` | The Emergency Stop input (`E_Stop_Active`) is triggered. | Reset E-Stop button and restart. |
| **`20`** | Measurement | `Auto Error: Error 20: Silo Clogged / No Material Flow!` | Auto valve is open, but scale does not register weight increase of $\ge$ 0.1 kg over 5s. | Check for bridge formation/clog in silo. |
| **`21`** | Measurement | `Error 21: Scale Overloaded!` | The load cell feedback value exceeds the scale capacity limit of 500.0 kg. | Empty scale, inspect load cell alignment. |
| **`22`** | Measurement | `Error 22: Scale Underloaded/Fault!` | The load cell reads a negative value (less than 0.0 kg). | Recalibrate load cell, check sensor wiring. |
| **`30`** | Operator | `Semi-Auto Error: Error 30: Semi-Auto Operator Timeout!` | Semi-Auto prompt active for longer than 300 seconds (5 minutes) without completion. | Confirm operator interaction or reset sequence. |

### Abort Sequence Behavior
If any error (`Error_Code > 0`) is detected during start or execution:
1. All physical control outputs (e.g. `Auto_Bin[1..6]`, `auto_bin_cutoff[1..6]`, `auto_bin_motor[1..6]`, `Semi_Auto_Bin[1..10]`, `semi_auto_bin_cutoff[1..10]`, `semi_auto_bin_motor[1..10]`) are forced **FALSE** immediately.
2. The sequence drops into state **`99`** (Error Abort state).
3. The system remains locked until `Start_Button` is released (toggled `FALSE`), which resets the state machine back to `Step := 0` (Idle) once the error source is cleared.
