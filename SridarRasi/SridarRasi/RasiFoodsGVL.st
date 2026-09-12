(* Part 1 of main GVL — HMI / %M tags only. Part 2: scripts/st_v16/GVL_RETAIN_PASTE.st *)
(* Combined: scripts/st_v16/GVL_LIVE_PLANT.st *)
{attribute 'qualified_only'}
VAR_GLOBAL
    Recipe_Weights AT %MD100: ARRAY [1..20] OF REAL;
	Semi_Auto_Bin_Material_Mapping AT %MW60: ARRAY [1..10] OF INT;	
	Auto_Bin_Material_Mapping AT %MW50: ARRAY[1..6] OF INT;	
	Auto_Coarse_To_Fine_speed AT %MD120: ARRAY[1..6] OF REAL := [1.0,1.0,1.0,1.0,1.0,1.0];
	Auto_Bin_Tolerance AT %MD150: ARRAY[1..6] OF REAL;
	Semi_Auto_Bin_Tolerance AT %MD160: ARRAY[1..10] OF REAL :=[0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2];
	Start_Button AT %MX2.0: BOOL;
	///E_Stop_Active AT %MX2.1: BOOL;
	Next_Cycle_Ready AT %MX2.2: BOOL;
	Reset AT %MX2.3: BOOL;
	Next_Cycle_Start AT %MX2.4: BOOL;
	Auto_Active_Mat AT %MW70: INT;
	Auto_Active_Bin AT %MW71: INT;
	Semi_Auto_Active_Mat AT %MW72: INT;
	Semi_Auto_Active_Bin AT %MW73: INT;
	Target_Batch_Cycles AT %MW74: INT := 0;
	Current_Batch_Cycle AT %MW75: INT;
	Completed_Batch_Cycles AT %MW79: INT;
	Error_Code AT %MW76: INT;
	Run AT %MX2.5 : BOOL;
	load_cell_auto AT %MD174 : REAL;
	load_cell_semi_auto AT %MD175 : REAL;
	Auto_Initial_Tolerance AT %MD176 : REAL := 5.0;
	Semi_Auto_Initial_Tolerance AT %MD178 : REAL := 5.0;
	Empty_Weight_Limit AT %MD186 : REAL := 5.0;
	Ex_Weight_Allow_kg AT %MD188 : REAL := 0.2;
	Auto_Total_Target_Weight AT %MD170 : REAL;
	Semi_Auto_Total_Target_Weight AT %MD171 : REAL;
	Auto_Total_Actual_Weight AT %MD180 : REAL;
	Semi_Auto_Total_Actual_Weight AT %MD184 : REAL;
	Auto_Material_Count AT %MW77: INT;
	Semi_Auto_Material_Count AT %MW78 : INT;
	Auto_Current_Step AT %MW80 : INT;
	Semi_Auto_Current_Step AT %MW81 : INT;
	Auto_Active_Target_Weight AT %MD220 : REAL;
	Semi_Auto_Active_Target_Weight AT %MD224 : REAL;
	Auto_Active_Live_Weight AT %MD172 : REAL;
	Semi_Auto_Active_Live_Weight AT %MD173 : REAL;
	Auto_Excess_Alarm AT %MX2.7 : BOOL;
	Semi_Auto_Excess_Alarm AT %MX2.8 : BOOL;
	Auto_Inter_Bin_Delay AT %MD190 : TIME;
	Semi_Auto_Inter_Bin_Delay AT %MD194 : TIME;
	Auto_Sequence_Complete AT %MX8.2 : BOOL;
	Semi_Auto_Sequence_Complete AT %MX8.3 : BOOL;
	All_Cycles_Complete AT %MX3.2 : BOOL;
	Auto_Status_Message : STRING(80);
	Semi_Auto_Status_Message : STRING(80);	
	Auto_Bin : ARRAY[1..6] OF BOOL;
	auto_motor_slow_trigger : ARRAY[1..6] OF BOOL;
	auto_bin_motor : ARRAY[1..6] OF BOOL;
	Semi_Auto_Bin : ARRAY[1..10] OF BOOL;
	Auto_Weights AT %MD300: ARRAY [1..6] OF REAL;
	Semi_Auto_Weights AT %MD350: ARRAY [1..10] OF REAL;
	Auto_Target_Weights AT %MD400: ARRAY [1..6] OF REAL;
	Semi_Auto_Target_Weights AT %MD410: ARRAY [1..10] OF REAL;
	Waiting_Next_batch_HMI_HIDE AT %MX8.1: BOOL;
	All_Cycles_Seq_Completed AT %MX8.4: BOOL;
	Done_Batch_HMI: BOOL;
	Error_bit AT %MX8.5: BOOL;
	Fault_Reset AT %MX8.6: BOOL;
	samyak_weight AT %MD195 : ARRAY[1..4] OF REAL;

END_VAR
