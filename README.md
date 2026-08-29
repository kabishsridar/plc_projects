# AC500 V3 PLC Batching System Documentation

This repository contains CODESYS project files implementing automatic and semi-automatic batching sequences for the **PM5032-T-ETH (AC500 V3)** PLC. The batching system controls up to 6 automatic silos and 10 semi-automatic silos in parallel using cumulative gain-in-weight measurements.

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
*   **`batching11`**: Renames Manual parameters to Semi-Auto, adds inter-cycle hold triggers, E-Stop pause/resume, and immediate hard reset logic.
*   **`batching13`**: Monolithic Structured Text (ST) implementation with global recipe supervisory checks.
*   **`batching14` / `V14 Modular Architecture` (Active Production)**:
    *   **Native FBD Integration**: Calls `Auto_Ctrl : Auto_Batching_V14` and `Semi_Auto_Ctrl : Semi_Auto_Batching_V14` concurrently.
    *   **Independent Encapsulation**: Supervisory checks (Errors 1, 2, 3, 4, 21), scale overload, three-stage feeding, and cumulative taring are fully encapsulated within the function blocks.
    *   **Interlocked Inter-Cycle Hold & Scale Tare Verification**: After completing a cycle, system enters State 5 (Hold). Both scales must be emptied below `Empty_Weight_Limit` (default 5.0 kg) before a rising edge of `Next_Cycle_Start` triggers the next cycle loop.
    *   **Dedicated Cycle Diagnostics Outputs**: Exposes `Auto_Current_Batch_Cycle`, `Auto_Completed_Batch_Cycles`, `Auto_All_Cycles_Complete`, and their corresponding `Semi_Auto_` counterparts directly as block pins and GVL registers.
    *   **Robust Edge-Triggered Cycle Progression**: Eliminates accidental auto-starting upon scale emptying; requires explicit operator trigger to advance cycles.
    *   **Persistent Latched Start Button**: `Start_Button` remains `TRUE` across all active cycles until all `Target_Batch_Cycles` are finished or a Master `Reset` is commanded.

---

## Master Cycle Manager State Machine (`Cycle_Manager_State`)

| State | Name | Description |
| :---: | :--- | :--- |
| **`0`** | **Idle / Stopped** | Ready and waiting for `Start_Button` pulse. Outputs and active weights are reset. |
| **`1`** | **Running Active Cycle** | Active dosing in progress. `Auto_Ctrl` (Steps 1..6) and `Semi_Auto_Ctrl` (Steps 1..10) feed in parallel. `Next_Cycle_Start` is interlocked to `FALSE`. |
| **`4`** | **All Cycles Finished** | All configured `Target_Batch_Cycles` have successfully completed. `All_Cycles_Complete` turns `TRUE`. `Start_Button` and `Run` auto-clear to `FALSE`. |
| **`5`** | **Paused Between Cycles** | Cycle finished. Waits for hoppers to be discharged below `Empty_Weight_Limit`. Requires operator trigger of `Next_Cycle_Start` to start the next cycle. |

---

## Step Progression Reference

### Auto Sequence Steps (`Auto_Current_Step`)
* **`0`**: Idle / Ready for Start
* **`1..6`**: Dosing physical Auto Silos 1 to 6 (Coarse Feed $\rightarrow$ Fine Feed $\rightarrow$ In-Tolerance check $\rightarrow$ Settling delay)
* **`7`**: Post-sequence settling delay timer
* **`8`**: Auto Sequence Complete (`Auto_Sequence_Complete := TRUE`)

### Semi-Auto Sequence Steps (`Semi_Auto_Current_Step`)
* **`0`**: Idle / Ready for Start
* **`1..10`**: Dosing physical Semi-Auto Silos 1 to 10 (Coarse Feed $\rightarrow$ Fine Feed $\rightarrow$ In-Tolerance check $\rightarrow$ Settling delay)
* **`31`**: Post-sequence settling delay timer
* **`32`**: Semi-Auto Sequence Complete (`Semi_Auto_Sequence_Complete := TRUE`)

---

## Diagnostic Error Codes Reference (V14)

The system aggregates configuration and runtime faults into an integer `Error_Code` and displays corresponding HMI text in `Status_Message`.

| Error Code | Category | HMI Message | Description | Recovery |
| :---: | :--- | :--- | :--- | :--- |
| **`0`** | Normal | `System Healthy` | No active error. | Normal operation. |
| **`1`** | Configuration | `Error 1: Duplicate Material ID mapped in Auto and Semi-Auto!` | Same Material ID ($1..20$) is mapped to both Auto and Semi-Auto arrays. | Change mapping so each material ID is assigned to only one block. |
| **`2`** | Configuration | `Error 2: Material Index configuration out of range (1..20)!` | A silo is mapped to an index $> 20$ or $< 0$. | Set mapping to `1..20` (or `0` to skip). |
| **`3`** | Configuration | `Error 3: Recipe weight is less than (Coarse_To_Fine_Speed + Tolerance)!` | Configured target weight is smaller than feeding speed transition offsets. | Adjust recipe weight setpoint or reduce coarse-to-fine offset. |
| **`4`** | Safety / Tare | `Error 4: Scale not zeroed (exceeds Initial Tolerance)!` | Scale gross weight exceeds `Auto_Initial_Tolerance` or `Semi_Auto_Initial_Tolerance` when starting. | Empty hopper or re-tare load cell. |
| **`21`** | Hardware | `Error 21: Scale Overloaded (> 500 kg)!` | Live load cell weight exceeds physical safe limit of 500.0 kg. | Remove weight from hopper, inspect load cell wiring. |

---

## Core File Directory

* **`St_Codes/Auto_Batching_V14.st`**: Automated silos function block source code.
* **`St_Codes/Semi_Auto_Batching_V14.st`**: Semi-automated silos function block source code.
* **`St_Codes/gvl`**: Global Variable List mapping definitions and memory addresses (`%M`).
* **`variables_explanation.md`**: Complete variable, pin, and memory address reference document.
* **`rasi_modaddress.xlsx`**: Modbus register mapping table.
