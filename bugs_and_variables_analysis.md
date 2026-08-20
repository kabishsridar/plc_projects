# Bugs and Variables Analysis - `batching10`

This document details the analysis of potential code bugs, runtime constraints, and unnecessary/redundant variables found inside the `batching10` POU blocks.

---

## 1. Unnecessary or Redundant Variables

### Program Level (`batching10`)
*   **`Conf_Err_Id : INT`**
    *   *Status:* **Unused**. Declared in the `VAR` block but never read or written to in the implementation.
*   **`Duplicate_Found`, `Invalid_Material_Range`, `Zero_Target_Found : BOOL`**
    *   *Status:* **Redundant**. These can be declared as temporary variables (`VAR_TEMP`) or combined into a single transient check variable, as they are only used during the startup configuration checks on scan cycle 1.

### Function Block Level (`Auto_Batching_V10` & `Manual_Batching_V10`)
*   **`Discharge_Bin_Feedback : ARRAY[1..6] OF BOOL`** (`Auto_Batching_V10`)
    *   *Status:* **Unused**. Declared under `VAR_INPUT` but never referenced in the ST sequence code.
*   **`bin_set_value : REAL`** (Both FBs)
    *   *Status:* **Redundant**. Used to temporarily store `GVL.Recipe_Weights[Mat_Idx]`. The target weights can be directly accessed and offset:
        *   `target_act_bin := GVL.Recipe_Weights[Mat_Idx] - Auto_Bin_Tolerance[Step];`
*   **`Simulation_Mode : BOOL := TRUE`** (Both FBs)
    *   *Status:* **Design Constraint**. Declared inside the internal `VAR` block. This prevents HMI screens or external systems from toggling simulation mode on or off. It should ideally be a `VAR_INPUT`.

---

## 2. Potential Bugs & Logic Constraints

### Bug 1: Hard Halt on Target Weight = 0.0 kg (`Error 3`)
*   **The Issue:** If an operator maps a valid Material ID but that material happens to have a recipe weight set to `0.0` kg (e.g., optional ingredient not used in this specific batch), the program raises `Error 3` and halts the entire sequence.
*   **The Fix:** Instead of a hard halt, the sequence should automatically skip any bin step where the target weight is `0.0` kg (similar to mapping `0` to skip).

### Bug 2: Diagnostic Loop During E-Stop Reset
*   **The Issue:** In the FB error abort state (`Step 99`), if the start input goes `FALSE`, the FB resets `Step := 0` and clears `Error_Code := 0`. However, if `E_Stop_Active` remains physically pressed, the program level code `batching10` will immediately re-trigger the E-stop fault. This causes a toggle loop between `Error_Code := 0` and `Error_Code := 12` inside the FB until the physical E-Stop button is released.
*   **The Fix:** Step `99` inside the FBs should not reset until `NOT Start_Button AND NOT E_Stop_Active` are both met.
