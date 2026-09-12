(* POU: batching14 *)

=== DECLARATION ===
PROGRAM batching14
VAR
	Auto_Ctrl: Auto_Batching_V15;
	Semi_Auto_Ctrl: Semi_Auto_Batching_V15;
	Auto_Complete: BOOL;
	Semi_Auto_Complete: BOOL;
	Auto_Err: INT;
	Auto_Msg: STRING;
	Semi_Auto_Err: INT;
	Semi_Auto_Msg: STRING;
	AutoBatchScale: MODRTUMAST;
	ModEnabler: BLINK;
	SamyakRaw: ARRAY[0..1] OF DINT;
	AutBatchRaw: ARRAY[0..1] OF DINT;
	SemAutoScale: MODRTUMAST;
	SemiAutoScaleRaw: ARRAY[0..1] OF DINT;
	AutoBatchSamyak: REAL;
	FB_Samyak_Multi_1: FB_Samyak_Multi;
	FB_Samyak_Control_1: FB_Samyak_Control;
	Run_PB_1: BOOL;
	Next_Cycle_Start: BOOL;
	TP_1: TP;
	TP_ON: BOOL;
	TP_Out: BOOL;
	TP_Et: TIME;
	arrTare_Cmds: ARRAY[1..4] OF BOOL;
END_VAR


=== IMPLEMENTATION ===
(* empty textual body - see batching14_fbd.xml for FBD *)
