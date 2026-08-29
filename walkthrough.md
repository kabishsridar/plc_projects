# Walkthrough - Batching V14 Modular FBD Implementation & Cycle Management

This walkthrough documents the full architecture, bug resolutions, and verification of **`batching14`** using **`Auto_Batching_V14`** and **`Semi_Auto_Batching_V14`** on the ABB AC500 V3 PLC.

---

## 1. Modular FBD Architecture (`batching14`)

The batching control system is decoupled into two parallel modular function blocks:
* **`Auto_Ctrl : Auto_Batching_V14`**: Controls 6 automated silos with 3-stage feeding (Coarse Valve, Fine Cutoff, Feeder Motor), supervisor checks, and master cycle loops.
* **`Semi_Auto_Ctrl : Semi_Auto_Batching_V14`**: Controls 10 semi-automated silos with 3-stage feeding operating concurrently with Auto.

---

## 2. Key Issues Resolved

### A. Initial Negative Live Weight (`-30.0 kg`)
* **Cause**: On initial start from State 0, `Current_Step` was set directly to `1`, bypassing the `IF Current_Step = 0` tare initialization logic. `bin_last_weight` retained the previous test's scale value (`30 kg`), resulting in $0 - 30 = -30\text{ kg}$.
* **Fix**: State 0 initializes `Current_Step := 0`, ensuring `bin_last_weight := load_cell_value` executes on scan 1 to snapshot the empty scale reading. Additionally, live net weight is clamped to a minimum of `0.0 kg` to prevent negative numbers from noise.

### B. Auto-Starting on Scale Emptying
* **Cause**: In State 5 (Hold between cycles), `Start_Button` remained `TRUE`. When the operator emptied the scale to 0 kg, the state transition evaluated `TRUE` continuously and started Cycle 2 without waiting for operator input.
* **Fix**: Removed `Start_Button` from State 5 and implemented rising-edge trigger detection (`Next_Cycle_Rising`) on `Next_Cycle_Start`. The system now evaluates scale weights **only when `Next_Cycle_Start` is pulsed**, and will never auto-start simply because the scale was emptied.

### C. `Semi_Auto_Complete` Stuck `TRUE` on Cycle 1
* **Cause**: On starting a new batch, `Auto` reset `GVL.Current_Batch_Cycle` to 1, but `Semi_Auto` was still in Step 32 with `Last_Batch_Cycle = 1`. Since `1 <> 1` was `FALSE`, Semi-Auto never detected the restart and remained latched in Step 32.
* **Fix**: Added edge detection on `GVL.Run` (`Run_Rising`) and idle reset logic (`NOT GVL.Run`). Semi-Auto cleanly resets to Step 0 whenever a new batch starts or the machine is stopped.

### D. `Active_Live_Weight` Stuck at `0.0 kg`
* **Cause**: A level-triggered condition `IF GVL.Start_Button AND GVL.Current_Batch_Cycle <= 1 THEN Current_Step := 0;` was executing on every single scan because `Start_Button` stayed latched. This re-tared `bin_last_weight := load_cell_value` on every scan ($41 - 41 = 0$).
* **Fix**: Replaced the continuous reset with the single-scan rising edge `Run_Rising`. Initial tare is now taken only on scan 1, and live net weight correctly updates as material is dosed.

---

## 3. Dedicated Cycle Output Pins

Both function blocks have been updated with dedicated output pins:

### Auto Block (`Auto_Ctrl`):
* **`Auto_Current_Batch_Cycle : INT`**: Real-time active cycle number ($1..N$).
* **`Auto_Completed_Batch_Cycles : INT`**: Total cycles successfully completed.
* **`Auto_All_Cycles_Complete : BOOL`**: Turns `TRUE` when all target cycles have finished.

### Semi-Auto Block (`Semi_Auto_Ctrl`):
* **`Semi_Auto_Current_Batch_Cycle : INT`**: Real-time active cycle number ($1..N$).
* **`Semi_Auto_Completed_Batch_Cycles : INT`**: Total cycles successfully completed.
* **`Semi_Auto_All_Cycles_Complete : BOOL`**: Turns `TRUE` when all target cycles have finished.

---

## 4. Current File Status

* [`Auto_Batching_V14.st`](file:///d:/kabish/plc_projects/St_Codes/Auto_Batching_V14.st): Complete & verified.
* [`Semi_Auto_Batching_V14.st`](file:///d:/kabish/plc_projects/St_Codes/Semi_Auto_Batching_V14.st): Complete & verified.
* [`gvl`](file:///d:/kabish/plc_projects/St_Codes/gvl): Global variable declarations and `%M` memory addresses updated.
* [`README.md`](file:///d:/kabish/plc_projects/README.md): Updated with V14 specifications, state machine table, and error codes.
* [`variables_explanation.md`](file:///d:/kabish/plc_projects/variables_explanation.md): Complete reference of GVL registers and FBD block pins.
