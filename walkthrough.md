# Walkthrough - Real-World PLC Sensor Integration & Simulation Disable

I have successfully updated the project to map physical load cell sensors to GVL registers and disabled the internal software simulation mode across the state machines inside `Rasi_feeds_batching.project` and pushed it to GitHub.

## Changes Made

1. **GVL-Mapped Load Cell Sensors**:
   - Declared `load_cell_auto AT %MD170 : REAL;` and `load_cell_semi_auto AT %MD180 : REAL;` in the **`GVL`** variable list.
   - Cleared local declarations from the `batching12` program block, passing the `GVL.load_cell_auto` and `GVL.load_cell_semi_auto` memory variables to the FBs.
2. **Disabled Simulation Mode**:
   - Changed the internal parameter `Simulation_Mode : BOOL := FALSE;` in both `Auto_Batching_V12` and `Semi_Auto_Batching_V12`. This stops software weights simulation timers, allowing the FBs to read and write weights directly based on physical load cell scale sensors.
3. **Run Variable Overlap Resolve**:
   - Relocated the mapped memory address of `GVL.Run` to `%MX1.4` (from `%MX1.2`) to prevent overlap conflicts with `Cycle_Hold_Active AT %MX1.2 : BOOL;`.
4. **Compilation Verification**:
   - Verified that the project builds successfully with **0 errors**.

### Updated GVL Declarations

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
END_VAR
```
