# AC500 V3 Batching System Variable & Array Reference

This document explains the function of all major arrays and variables configured in the AC500 V3 project, covering **`batching14`** (FBD) and its underlying modular function blocks:
* **`Auto_Batching_V14`** (Auto Silos 1..6)
* **`Semi_Auto_Batching_V14`** (Semi-Auto Silos 1..10)

---

## 1. System Architecture Overview (`batching14` FBD)

The system operates using two parallel function blocks executing in the main cyclic task:
* **`Auto_Ctrl : Auto_Batching_V14`**: Master cycle controller and automated silo dosing engine (Silos 1..6).
* **`Semi_Auto_Ctrl : Semi_Auto_Batching_V14`**: Semi-automated silo dosing engine (Silos 1..10) operating in parallel.

### Key Operational Features:
1. **Parallel Execution with Synchronized Handoff**: Auto and Semi-Auto run concurrently. When both complete their dosing steps, the system transitions to State 5 (Hold between cycles).
2. **Interlocked Scale Empty Verification**: Before Cycle $N+1$ is allowed to start, both `load_cell_auto` and `load_cell_semi_auto` must read below `Empty_Weight_Limit` (default 5.0 kg).
3. **Edge-Triggered Progression**: Advancing to the next cycle requires a rising edge trigger on `Next_Cycle_Start`. It will not auto-start simply by emptying the scale.
4. **Persistent Start Button Latching**: `Start_Button` remains `TRUE` throughout all active cycles, and automatically turns `FALSE` only when all `Target_Batch_Cycles` are finished (State 4) or on a Master `Reset`.
5. **Cumulative Net Taring**: Each silo captures the scale reading at start as its tare offset (`bin_last_weight := load_cell_value`), allowing progressive gain-in-weight dosing with automatic negative weight suppression (`clamped >= 0.0 kg`).

---

## 2. Global Variables List (GVL) Reference

### Recipe Data & Physical Silo Mapping
* **`GVL.Recipe_Weights : ARRAY[1..20] OF REAL`** (at `%MD100`)
  * Target weight setpoints (in kg) for up to 20 recipe ingredients.
* **`GVL.Auto_Bin_Material_Mapping : ARRAY[1..6] OF INT`** (at `%MW50`)
  * Maps physical Auto Silos `1..6` to GVL Material IDs `1..20`. Set to `0` to skip that silo.
* **`GVL.Semi_Auto_Bin_Material_Mapping : ARRAY[1..10] OF INT`** (at `%MW60`)
  * Maps physical Semi-Auto Silos `1..10` to GVL Material IDs `1..20`. Set to `0` to skip that silo.

### Cutoff Speeds, Tolerances & Scale Thresholds
* **`GVL.Auto_Bin_Cutoff_Weights : ARRAY[1..6] OF REAL`** (at `%MD120`)
  * Weight offset (in kg) before reaching target that triggers the transition from Coarse Feed to Fine Feed (`Cutoff_Trigger = Target - Cutoff`). Wired to input `Auto_Coarse_To_Fine_Speed`.
* **`GVL.Semi_Auto_Bin_Cutoff_Weights : ARRAY[1..10] OF REAL`** (at `%MD130`)
  * Weight offset (in kg) before reaching target for Semi-Auto silos. Wired to input `Semi_Auto_Coarse_To_Fine_Speed`.
* **`GVL.Auto_Bin_Tolerance : ARRAY[1..6] OF REAL`** (at `%MD150`)
  * Allowable in-tolerance window ($\pm\text{Tol}$) defining `Min_Tol = Target - Tol` and `Max_Tol = Target + Tol`.
* **`GVL.Semi_Auto_Bin_Tolerance : ARRAY[1..10] OF REAL`** (at `%MD160`)
  * Allowable in-tolerance window ($\pm\text{Tol}$) for Semi-Auto silos.
* **`GVL.Auto_Initial_Tolerance : REAL`** (at `%MD176`)
  * Maximum allowable tare offset on Auto scale before starting (Error 4 check). Default `5.0 kg`.
* **`GVL.Semi_Auto_Initial_Tolerance : REAL`** (at `%MD178`)
  * Maximum allowable tare offset on Semi-Auto scale before starting (Error 4 check). Default `5.0 kg`.
* **`GVL.Empty_Weight_Limit : REAL`** (at `%MD186`)
  * Maximum gross weight (kg) permitted on scales to qualify as empty before starting the next batch cycle. Default `5.0 kg`.
* **`GVL.Auto_Total_Target_Weight : REAL`** (at `%MD180`)
  * Cumulative recipe target weight summed across all active Auto bins ($1..6$).
* **`GVL.Semi_Auto_Total_Target_Weight : REAL`** (at `%MD184`)
  * Cumulative recipe target weight summed across all active Semi-Auto bins ($1..10$).
* **`GVL.Auto_Material_Count : INT`** (at `%MW77`)
  * Count of active non-zero recipe silos in Auto.
* **`GVL.Semi_Auto_Material_Count : INT`** (at `%MW78`)
  * Count of active non-zero recipe silos in Semi-Auto.

### Live Gross Load Cell Inputs
* **`GVL.load_cell_auto : REAL`** (at `%MD174`)
  * Live gross scale weight reading from the Auto scale load cell (kg).
* **`GVL.load_cell_semi_auto : REAL`** (at `%MD175`)
  * Live gross scale weight reading from the Semi-Auto scale load cell (kg).

### Step Tracking, Status & Diagnostics
* **`GVL.Auto_Current_Step : INT`** (at `%MW80`)
  * Real-time state of Auto sequence:
    * `0` = Idle / Ready
    * `1..6` = Dosing Auto Silos 1 to 6
    * `7` = Settling delay in progress
    * `8` = Auto sequence completed
* **`GVL.Semi_Auto_Current_Step : INT`** (at `%MW81`)
  * Real-time state of Semi-Auto sequence:
    * `0` = Idle / Ready
    * `1..10` = Dosing Semi-Auto Silos 1 to 10
    * `31` = Settling delay in progress
    * `32` = Semi-Auto sequence completed
* **`GVL.Auto_Status_Message : STRING(80)`**
  * Real-time human-readable status, feeding phase, or diagnostic message for Auto.
* **`GVL.Semi_Auto_Status_Message : STRING(80)`**
  * Real-time human-readable status, feeding phase, or diagnostic message for Semi-Auto.
* **`GVL.Error_Code : INT`** (at `%MW76`)
  * Master fault diagnostic code:
    * `0` = System Healthy
    * `1` = Duplicate Material ID mapped in both Auto and Semi-Auto
    * `2` = Material index out of range ($> 20$)
    * `3` = Recipe weight is less than `Coarse_To_Fine_Speed + Tolerance`
    * `4` = Initial scale tare error (scale not empty before start)
    * `21` = Scale overload protection triggered ($> 500.0\text{ kg}$)

### Active Ingredient HMI Display Registers
* **`GVL.Auto_Active_Mat : INT`** (at `%MW70`): Material ID currently being dosed in Auto.
* **`GVL.Auto_Active_Bin : INT`** (at `%MW71`): Physical Silo ID currently being dosed in Auto.
* **`GVL.Semi_Auto_Active_Mat : INT`** (at `%MW72`): Material ID currently being dosed in Semi-Auto.
* **`GVL.Semi_Auto_Active_Bin : INT`** (at `%MW73`): Physical Silo ID currently being dosed in Semi-Auto.
* **`GVL.Auto_Active_Target_Weight : REAL`** (at `%MD220`): Target setpoint (kg) of active Auto silo.
* **`GVL.Semi_Auto_Active_Target_Weight : REAL`** (at `%MD224`): Target setpoint (kg) of active Semi-Auto silo.
* **`GVL.Auto_Active_Live_Weight : REAL`** (at `%MD228`): Live net dosed weight (kg) into Auto scale for active silo.
* **`GVL.Semi_Auto_Active_Live_Weight : REAL`** (at `%MD232`): Live net dosed weight (kg) into Semi-Auto scale for active silo.

### Master Control Signals & Loop Management
* **`GVL.Start_Button : BOOL`** (at `%MX2.0`)
  * Master start command. Latches `TRUE` on start and remains `TRUE` through all cycle loops until State 4 (All Cycles Finished) or Master `Reset`.
* **`GVL.E_Stop_Active : BOOL`** (at `%MX2.1`)
  * Emergency Stop contact (`TRUE` = Healthy / Run permitted, `FALSE` = Tripped / Paused).
* **`GVL.Reset : BOOL`** (at `%MX2.3`)
  * Single-shot master reset trigger. Immediately halts all outputs, resets steps to 0, zeroes cycle counters, and clears error codes.
* **`GVL.Next_Cycle_Start : BOOL`** (at `%MX2.4`)
  * Interlocked momentary pulse command to start the next cycle when in State 5. Evaluated strictly on rising edge. Automatically reset to `FALSE` upon processing. Forced `FALSE` during active dosing (State 1).
* **`GVL.Run : BOOL`** (at `%MX2.5`)
  * Master process running indicator (`TRUE` during active batching).
* **`GVL.Auto_Sequence_Complete : BOOL`** (at `%MX3.0`)
  * Handshake flag indicating Auto Silos 1..6 have completed current cycle dosing.
* **`GVL.Semi_Auto_Sequence_Complete : BOOL`** (at `%MX3.1`)
  * Handshake flag indicating Semi-Auto Silos 1..10 have completed current cycle dosing.
* **`GVL.All_Cycles_Complete : BOOL`** (at `%MX3.2`)
  * Master batch completed indicator: turns `TRUE` when all configured `Target_Batch_Cycles` are finished.
* **`GVL.Target_Batch_Cycles : INT`** (at `%MW74`)
  * Configured number of batch cycle loop repetitions (defaults to 1).
* **`GVL.Current_Batch_Cycle : INT`** (at `%MW75`)
  * Currently active batch cycle index ($1..\text{Target}$).
* **`GVL.Completed_Batch_Cycles : INT`** (at `%MW79`)
  * Count of fully completed batch cycle loops.
* **`GVL.Auto_Excess_Allowed : BOOL`** (at `%MX2.6`): Auto overfill bypass toggle.
* **`GVL.Semi_Auto_Excess_Allowed : BOOL`** (at `%MX2.9`): Semi-Auto overfill bypass toggle.
* **`GVL.Auto_Excess_Alarm : BOOL`** (at `%MX2.7`): Overfill alarm indicator for Auto.
* **`GVL.Semi_Auto_Excess_Alarm : BOOL`** (at `%MX2.8`): Overfill alarm indicator for Semi-Auto.
* **`GVL.Auto_Inter_Bin_Delay : TIME`** (at `%MD190`): Settling delay duration between Auto bins.
* **`GVL.Semi_Auto_Inter_Bin_Delay : TIME`** (at `%MD194`): Settling delay duration between Semi-Auto bins.

### Physical Output & Actual Weight Arrays
* **`GVL.Auto_Bin : ARRAY[1..6] OF BOOL`**: Coarse valve actuation commands for Auto Silos 1..6.
* **`GVL.auto_bin_cutoff : ARRAY[1..6] OF BOOL`**: Fine feed cutoff commands for Auto Silos 1..6.
* **`GVL.auto_bin_motor : ARRAY[1..6] OF BOOL`**: Conveyor/feeder motor commands for Auto Silos 1..6.
* **`GVL.Semi_Auto_Bin : ARRAY[1..10] OF BOOL`**: Coarse valve actuation commands for Semi-Auto Silos 1..10.
* **`GVL.semi_auto_bin_cutoff : ARRAY[1..10] OF BOOL`**: Fine feed cutoff commands for Semi-Auto Silos 1..10.
* **`GVL.semi_auto_bin_motor : ARRAY[1..10] OF BOOL`**: Conveyor/feeder motor commands for Semi-Auto Silos 1..10.
* **`GVL.Auto_Weights : ARRAY[1..6] OF REAL`**: Net weight dosed into each Auto bin for current cycle.
* **`GVL.Semi_Auto_Weights : ARRAY[1..10] OF REAL`**: Net weight dosed into each Semi-Auto bin for current cycle.

---

## 3. Function Block Output Pin Reference

### Auto Function Block (`Auto_Batching_V14` / `Auto_Ctrl`)
| Output Pin | Data Type | Description |
| :--- | :---: | :--- |
| **`Auto_Bin`** | `ARRAY[1..6] OF BOOL` | Coarse valve actuation outputs for Silos 1..6 |
| **`auto_bin_cutoff`** | `ARRAY[1..6] OF BOOL` | Fine feed cutoff outputs for Silos 1..6 |
| **`auto_bin_motor`** | `ARRAY[1..6] OF BOOL` | Feeder motor run commands for Silos 1..6 |
| **`Actual_Weights`** | `ARRAY[1..6] OF REAL` | Net material weights dosed in active cycle (kg) |
| **`Sequence_Complete`** | `BOOL` | TRUE when Silos 1..6 and settling delay are finished |
| **`Active_Material_ID`** | `INT` | Recipe Material ID currently being dosed (1..20) |
| **`Active_Bin_ID`** | `INT` | Physical Silo ID currently being dosed (1..6) |
| **`Active_Target_Weight`**| `REAL` | Target weight setpoint of active silo (kg) |
| **`Active_Live_Weight`** | `REAL` | Net tared live weight dosed into active silo (kg) |
| **`Current_Step`** | `INT` | Step sequence indicator (0=Idle, 1..6=Silos, 7=Delay, 8=Done) |
| **`Cycle_Manager_State`** | `INT` | Master supervisor state (0=Idle, 1=Run, 4=All Done, 5=Hold) |
| **`Excess_Alarm`** | `BOOL` | Overfill alarm active when dosed weight exceeds target+tol |
| **`Error_Code`** | `INT` | Active fault diagnostic code (0, 1, 2, 3, 4, 21) |
| **`Auto_Current_Batch_Cycle`** | `INT` | Currently active cycle index ($1..\text{Target}$) |
| **`Auto_Completed_Batch_Cycles`**| `INT` | Number of cycles fully finished |
| **`Auto_All_Cycles_Complete`** | `BOOL` | TRUE when all target batch cycles have completed |
| **`Status_Message`** | `STRING(80)` | Real-time human-readable process status text |

### Semi-Auto Function Block (`Semi_Auto_Batching_V14` / `Semi_Auto_Ctrl`)
| Output Pin | Data Type | Description |
| :--- | :---: | :--- |
| **`Semi_Auto_Bin`** | `ARRAY[1..10] OF BOOL` | Coarse valve actuation outputs for Silos 1..10 |
| **`semi_auto_bin_cutoff`** | `ARRAY[1..10] OF BOOL` | Fine feed cutoff outputs for Silos 1..10 |
| **`semi_auto_bin_motor`** | `ARRAY[1..10] OF BOOL` | Feeder motor run commands for Silos 1..10 |
| **`Actual_Weights`** | `ARRAY[1..10] OF REAL` | Net material weights dosed in active cycle (kg) |
| **`Sequence_Complete`** | `BOOL` | TRUE when Silos 1..10 and settling delay are finished |
| **`Active_Material_ID`** | `INT` | Recipe Material ID currently being dosed (1..20) |
| **`Active_Bin_ID`** | `INT` | Physical Silo ID currently being dosed (1..10) |
| **`Active_Target_Weight`**| `REAL` | Target weight setpoint of active silo (kg) |
| **`Active_Live_Weight`** | `REAL` | Net tared live weight dosed into active silo (kg) |
| **`Current_Step`** | `INT` | Step sequence indicator (0=Idle, 1..10=Silos, 31=Delay, 32=Done) |
| **`Cycle_Manager_State`** | `INT` | Master supervisor state (0=Idle, 1=Run, 4=All Done, 5=Hold) |
| **`Excess_Alarm`** | `BOOL` | Overfill alarm active when dosed weight exceeds target+tol |
| **`Error_Code`** | `INT` | Active fault diagnostic code (0, 1, 2, 3, 4, 21) |
| **`Semi_Auto_Current_Batch_Cycle`** | `INT` | Currently active cycle index ($1..\text{Target}$) |
| **`Semi_Auto_Completed_Batch_Cycles`**| `INT` | Number of cycles fully finished |
| **`Semi_Auto_All_Cycles_Complete`** | `BOOL` | TRUE when all target batch cycles have completed |
| **`Status_Message`** | `STRING(80)` | Real-time human-readable process status text |
