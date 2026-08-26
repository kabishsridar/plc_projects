# Walkthrough - Closed-Loop Tolerance Verification, Auto-Reset & Excess Alarms (batching13)

I have implemented **`batching13`** (including Function Blocks **`Auto_Batching_V13`**, **`Semi_Auto_Batching_V13`**, and the **`batching13`** PROGRAM) inside `Rasi_feeds_batching.project` and verified it compiles cleanly with **0 errors**.

## Features Implemented in `batching13`

1. **Auto-Clearing Reset Trigger**:
   - `GVL.Reset` executes an immediate zeroing of all actual weights, outputs, and diagnostic registers, then automatically resets itself back to `FALSE` (`GVL.Reset := FALSE;`) within the same scan cycle, operating as a clean one-shot trigger.
2. **Tolerance Band Calculation**:
   - Calculates `Min_Tol_Weight = Target - Tolerance` and `Max_Tol_Weight = Target + Tolerance`.
3. **Global Inter-Bin Settling Delay**:
   - Settles the scale using `GVL.Inter_Bin_Delay` (`%MD190`) between bin closures and weight verifications.
4. **Closed-Loop Post-Settling Verification**:
   - **In Tolerance Range**: Snapshot baseline weight and advance to next silo.
   - **Underfilled**: Automatically re-engages fine feed feeder to top up until reaching the minimum tolerance threshold.
   - **Excess/Overfilled**:
     - If `GVL.Excess_Allowed = TRUE` (`%MX1.5`): logs bypass and proceeds to next silo.
     - If `GVL.Excess_Allowed = FALSE`: sets `GVL.Auto_Excess_Alarm` (`%MX1.6`) or `GVL.Semi_Auto_Excess_Alarm` (`%MX1.7`) and **holds execution** until the material is scooped/reduced into the valid tolerance window.
5. **Separate Alarms**:
   - `GVL.Auto_Excess_Alarm` for Auto system.
   - `GVL.Semi_Auto_Excess_Alarm` for Semi-Auto system.

---

### GVL Variables Mapping (`batching13`)

```pascal
{attribute 'qualified_only'}
VAR_GLOBAL
    Recipe_Weights AT %MD100 : ARRAY[1..20] OF REAL;
	Auto_Bin_Material_Mapping AT %MW50: ARRAY[1..6] OF INT;
	Semi_Auto_Bin_Material_Mapping AT %MW60: ARRAY[1..10] OF INT;
	Auto_Bin_Cutoff_Weights AT %MD120: ARRAY[1..6] OF REAL;
	Semi_Auto_Bin_Cutoff_Weights AT %MD130: ARRAY[1..10] OF REAL;
	Auto_Bin_Tolerance AT %MD150: ARRAY[1..6] OF REAL;
	Semi_Auto_Bin_Tolerance AT %MD160: ARRAY[1..10] OF REAL;
	Start_Button AT %MX1.0: BOOL;
	E_Stop_Active AT %MX1.1: BOOL;
	Reset AT %MX1.3: BOOL;
	Cycle_Hold_Active AT %MX1.2: BOOL;
	Auto_Active_Mat AT %MW70: INT;
	Auto_Active_Bin AT %MW71: INT;
	Semi_Auto_Active_Mat AT %MW72: INT;
	Semi_Auto_Active_Bin AT %MW73: INT;
	Target_Batch_Cycles AT %MW74: INT;
	Current_Batch_Cycle AT %MW75: INT;
	Error_Code AT %MW76: INT;
	Run AT %MX1.4 : BOOL;
	load_cell_auto AT %MD170 : REAL;
	load_cell_semi_auto AT %MD180 : REAL;
	Inter_Bin_Delay AT %MD190 : TIME;
	Excess_Allowed AT %MX1.5 : BOOL;
	Auto_Excess_Alarm AT %MX1.6 : BOOL;
	Semi_Auto_Excess_Alarm AT %MX1.7 : BOOL;
END_VAR
```
