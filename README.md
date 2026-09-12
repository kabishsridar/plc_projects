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

## Diagnostic Error Codes Reference & Handling Logic

The batching controller continuously monitors configuration validity, scale hardware, communications, and weight safety. Faults are aggregated into `Error_Code` (mirrored in `GVL.Error_Code` and `Auto_Error_Code`), and human-readable diagnostics are displayed in `Status_Message`.

### Error Codes Summary Table (Unified Single HMI Register: GVL.Error_Code %MW76)

| Error Code | Category | Type | HMI Diagnostic Message | Trigger Condition | Sequence Impact & Logic Handling | Recovery / Reset Action |
| :---: | :--- | :--- | :--- | :--- | :--- | :--- |
| **`0`** | Normal | Info | `System Healthy / Ready` | No active error | Normal execution permitted. | None. |
| **`1`** | Configuration | Auto-clearing | `Error 1: Duplicate Material ID within Auto bins!` | Two or more Auto silos share the same Material ID ($1..20$). | Blocks Start. Evaluated continuously; auto-clears when mapping is corrected. | Assign unique Material IDs to each active Auto silo. |
| **`2`** | Configuration | Auto-clearing | `Error 2: Auto Material Index out of range (1..20)!` | An Auto silo is assigned an ID $< 0$ or $> 20$. | Blocks Start. Outputs remain OFF. | Set mapping to valid range ($1..20$, or $0$ to skip). |
| **`3`** | Configuration | Auto-clearing | `Error 3: Auto Target < Coarse_To_Fine + Tolerance!` | Configured target weight on Auto is smaller than feeding speed transition offsets. | Blocks Start. Prevents valve chattering and incomplete feeding. | Increase recipe target weight or reduce `Auto_Coarse_To_Fine_Speed` / `Tolerance`. |
| **`4`** | Safety / Tare | Pre-Start Interlock | `Error 4: Auto Scale 1 not empty before Start!` | Auto Scale 1 gross weight $\ge \text{Empty\_Weight\_Limit}$ ($0.5\text{ kg}$) when Start/Next_Cycle is pressed. | Blocks cycle start; prevents tare pulse on loaded scale. | Discharge/empty Auto Scale 1 below $0.5\text{ kg}$. |
| **`5`** | Hardware / Comms | Latching / Hold | `Error 5: Auto Scale 1 Line Fault!` | Modbus/RS485 comms loss to Auto scale 1 (`Line_Fault = TRUE`). | **Immediate Process HOLD**: All feeding valves and motors forced OFF instantly. Retains dosed weights. | Restore scale comms, then pulse `Fault_Reset` (batch resumes without data loss). |
| **`6`** | Configuration | Auto-clearing | `Error 6: Mapping is all 0!` | All silos in Auto and Partner Semi mapping are set to $0$ (no materials assigned). | Blocks Start. Prevents running empty cycles. | Configure at least one active silo material mapping. |
| **`7`** | Cross-Channel | Auto-clearing | `Error 7: Material ID duplicated on Auto and Semi!` | Same Material ID ($1..20$) is mapped to both Auto and Semi-Auto silos. | Blocks Start. Prevents dual-scale dispensing conflict of same ingredient. | Ensure each Material ID is assigned to either Auto or Semi-Auto, not both. |
| **`8`** | Hardware / Comms | Latching / Hold | `Error 8: Semi Scale 2 Line Fault!` | Semi-Auto scale 2 communication lost (`Partner_Line_Fault = TRUE`). | **Immediate Process HOLD**: Feeders forced OFF to maintain batch synchronization. | Restore partner scale comms, then pulse `Fault_Reset`. |
| **`9`** | Configuration | Auto-clearing | `Error 9: Duplicate Material ID inside Semi mapping!` | Two or more Semi-Auto silos share the same Material ID. | Blocks Start. Auto-clears when corrected. | Assign unique Material IDs across Semi-Auto silos. |
| **`10`** | Safety / Tare | Pre-Start Interlock | `Error 10: Semi Scale 2 not empty before Start!` | Semi Scale 2 gross weight $\ge \text{Empty\_Weight\_Limit}$ ($0.5\text{ kg}$) when Start/Next_Cycle is pressed. | Blocks cycle start; prevents tare pulse on loaded scale. | Discharge/empty Semi Scale 2 below $0.5\text{ kg}$. |
| **`11`** | Configuration | Auto-clearing | `Error 11: Semi Material Index out of range (1..20)!` | A Semi silo is assigned an ID $< 0$ or $> 20$. | Blocks Start. Outputs remain OFF. | Set Semi mapping to valid range ($1..20$, or $0$ to skip). |
| **`12`** | Configuration | Auto-clearing | `Error 12: Semi Target < Tolerance!` | Configured target weight on Semi is smaller than allowable tolerance. | Blocks Start. Prevents improper manual dump configurations. | Increase recipe target weight or reduce `Semi_Auto_Bin_Tolerance`. |

---

### Logic Handling Principles in Structured Text

1. **Pre-Start Configuration Validation (Codes 1, 2, 3, 6, 7, 9, 11, 12)**:
   * Evaluated every scan before Start.
   * If any configuration error exists, `Start_Cmd` is blocked and `Status_Message` reflects the active error.
   * As soon as the operator corrects the HMI mapping or recipe values, the error code resets to `0` automatically.

2. **Runtime Safety & Hardware Faults (Codes 4, 5, 8, 10)**:
   * Evaluated continuously even during active dosing (Steps $1..6$ and $1..10$).
   * Immediately deactivates all physical outputs:
     ```st
     IF (GVL.Error_Code > 0) THEN
         FOR i := 1 TO 6 DO
             Auto_Bin[i] := FALSE;
             auto_motor_slow_trigger[i] := FALSE;
             auto_bin_motor[i] := FALSE;
         END_FOR;
     END_IF;
     ```
   * Enters `Paused_By_Hold := TRUE` to freeze timers and sequence step progression.

3. **Fault Reset vs. System Reset**:
   * **`Fault_Reset` (Non-Destructive)**:
     * Clears error codes when the underlying fault condition is resolved.
     * **Does NOT abort the batch**; allows the paused dosing step to resume cleanly.
   * **`Reset` (Production Abort)**:
     * Full batch cancellation: resets active steps to 0, clears cycle counters, zeroes actual weights, and returns system to Idle (`Cycle_Manager_State := 0`).

---

## Core File Directory

* **`St_Codes/Auto_Batching_V14.st`**: Automated silos function block source code.
* **`St_Codes/Semi_Auto_Batching_V14.st`**: Semi-automated silos function block source code.
* **`St_Codes/gvl`**: Global Variable List mapping definitions and memory addresses (`%M`).
* **`variables_explanation.md`**: Complete variable, pin, and memory address reference document.
* **`rasi_modaddress.xlsx`**: Modbus register mapping table.
