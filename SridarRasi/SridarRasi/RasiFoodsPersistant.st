VAR_GLOBAL PERSISTENT RETAIN
	(* HMI recipe/mapping shadow — no %M address; restored to GVL after power *)
	Ret_Recipe_Weights: ARRAY [1..20] OF REAL;
	bin_last_weight: REAL;
	Ret_Current_Step: INT;
	Ret_Cycle_Manager_State: INT;
	Ret_Internal_FB_Start: BOOL;
	Ret_bin_last_weight: REAL;
	Ret_GVL_Run: BOOL;
	Ret_Current_Batch_Cycle: INT;
	Ret_Completed_Batch_Cycles: INT;
	Ret_Target_Batch_Cycles: INT;
	Ret_Process_Was_Active: BOOL;
	Ret_Actual_Weights: ARRAY [1..6] OF REAL;
	Ret_Active_Material_ID: INT;
	Ret_Active_Bin_ID: INT;
	Ret_Active_Target_Weight: REAL;
	Ret_Active_Live_Weight: REAL;
	Ret_Resume_Step: INT;
	Ret_Bin_Target_Weights: ARRAY [1..6] OF REAL;
	Ret_Bin_Material_Mapping: ARRAY [1..6] OF INT;
	// Semi-Auto power resume (10 bins; steps 1..10 dosing, 31 settle, 32 complete)
	Ret_Semi_bin_last_weight: REAL;
	Ret_Semi_Current_Step: INT;
	Ret_Semi_Cycle_Manager_State: INT;
	Ret_Semi_Between_Cycle_Hold: BOOL;
	Ret_Semi_Last_Batch_Cycle: INT;
	Ret_Semi_GVL_Run: BOOL;
	Ret_Semi_Current_Batch_Cycle: INT;
	Ret_Semi_Completed_Batch_Cycles: INT;
	Ret_Semi_Target_Batch_Cycles: INT;
	Ret_Semi_Process_Was_Active: BOOL;
	Ret_Semi_Actual_Weights: ARRAY [1..10] OF REAL;
	Ret_Semi_Active_Material_ID: INT;
	Ret_Semi_Active_Bin_ID: INT;
	Ret_Semi_Active_Target_Weight: REAL;
	Ret_Semi_Active_Live_Weight: REAL;
	Ret_Semi_Resume_Step: INT;
	Ret_Semi_Bin_Target_Weights: ARRAY [1..10] OF REAL;
	Ret_Semi_Bin_Material_Mapping: ARRAY [1..10] OF INT;
END_VAR
VAR_GLOBAL PERSISTENT

END_VAR
