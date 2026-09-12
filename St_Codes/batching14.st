(* ==========================================
   POU: batching14
   ========================================== *)

=== DECLARATION ===
PROGRAM batching14
VAR
	Auto_Ctrl: Auto_Batching_V14;
	Semi_Auto_Ctrl: Semi_Auto_Batching_V14;
	Auto_Complete: BOOL;
	Semi_Auto_Complete: BOOL;
	Auto_Err: INT;
	Auto_Msg: STRING;
	Semi_Auto_Err: INT;
	Semi_Auto_Msg: STRING;
	FB_Samyak_Multi_1: FB_Samyak_Multi;
	arrSlaveIDs: ARRAY[1..4] OF BYTE := [1, 2, 0, 0];
	arrDivisor: ARRAY[1..4] OF REAL := [10.0, 10.0, 1.0, 1.0];
	arrTare_In: ARRAY[1..4] OF BOOL;
	Weight_Scaled_Array: ARRAY[1..4] OF REAL;
	arrLine_Fault: ARRAY[1..4] OF BOOL;
END_VAR


