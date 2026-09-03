import sys
import os

project_path = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\Rasi_feeds_batching.project"
log_path = r"C:\Users\kabish\.gemini\antigravity-ide\brain\6bb09710-7f3e-4443-b187-ad04e16ca8dc\scratch\create_sample_read_log.txt"

dut_xml_path = r"C:\Users\kabish\.gemini\antigravity-ide\brain\6bb09710-7f3e-4443-b187-ad04e16ca8dc\scratch\sample_dut.xml"
dut_xml = """<?xml version="1.0" encoding="utf-8"?>
<project xmlns="http://www.plcopen.org/xml/tc6_0200">
  <fileHeader companyName="" productName="Automation Builder 2.7 - Basic" productVersion="Automation Builder 2.7" creationDateTime="2026-08-31T23:45:00" />
  <contentHeader name="Rasi_feeds_batching.project">
    <coordinateInfo><fbd><scaling x="1" y="1" /></fbd><ld><scaling x="1" y="1" /></ld><sfc><scaling x="1" y="1" /></sfc></coordinateInfo>
  </contentHeader>
  <types>
    <dataTypes>
      <dataType name="Modbus_Poll_Request">
        <baseType>
          <struct>
            <variable name="Slave_ID"><type><BYTE /></type></variable>
            <variable name="Func_Code"><type><BYTE /></type></variable>
            <variable name="Start_Reg"><type><WORD /></type></variable>
            <variable name="Num_Regs"><type><WORD /></type></variable>
            <variable name="Raw_Data"><type><array><dimension lower="1" upper="4" /><baseType><WORD /></baseType></array></type></variable>
            <variable name="Done"><type><BOOL /></type></variable>
            <variable name="Error"><type><BOOL /></type></variable>
            <variable name="Error_Code"><type><WORD /></type></variable>
          </struct>
        </baseType>
      </dataType>
    </dataTypes>
    <pous />
  </types>
  <instances><configurations /></instances>
</project>
"""

decl_sample = """FUNCTION_BLOCK sample_read_two_weights
VAR_INPUT
    Enable : BOOL := TRUE;
    Auto_Node_ID : BYTE := 1;          // Modbus Address of Auto Weighing Indicator
    Auto_Reg_Addr : WORD := 0;         // Register offset for Auto Weight
    Semi_Node_ID : BYTE := 2;          // Modbus Address of Semi-Auto Weighing Indicator
    Semi_Reg_Addr : WORD := 0;         // Register offset for Semi-Auto Weight
    Timeout_Setting : TIME := T#150MS; // Max time to wait per node response
    Poll_Interval : TIME := T#10MS;    // Inter-request gap delay
    Simulated_Feed : BOOL := FALSE;    // Simulation mode for offline testing
END_VAR
VAR_OUTPUT
    Load_Cell_Auto_Weight : REAL;      // Live parsed weight for Auto scale
    Load_Cell_Semi_Weight : REAL;      // Live parsed weight for Semi-Auto scale
    Auto_Scale_Online : BOOL;          // Communication health indicator for Auto scale
    Semi_Scale_Online : BOOL;          // Communication health indicator for Semi-Auto scale
    Current_Poll_Node : BYTE;          // Active slave being queried
    Active_Table_Slot : INT;           // 1 = Auto, 2 = Semi-Auto
    Cycle_Counter : UDINT;             // Total completed round-robin polling loops
    Total_Comm_Errors : UDINT;         // Error counter
    Status_Text : STRING(80);          // Diagnostic status text
END_VAR
VAR
    State : INT;                       // State machine: 0=Init, 1=Dispatch, 2=Wait, 3=Parse, 4=Gap
    Table_Idx : INT := 1;              // 1 = Auto, 2 = Semi-Auto
    Poll_Table : ARRAY[1..2] OF Modbus_Poll_Request;
    
    Timeout_Timer : TON;
    Inter_Poll_Timer : TON;
    
    (* Raw word to float IEEE 754 converter *)
    dw_temp : DWORD;
    Sim_Val_1 : REAL;
    Sim_Val_2 : REAL;
    b_temp : ARRAY[0..3] OF BYTE;
END_VAR
"""

code_sample = """(* Method 3: Built-In Modbus Master Table / Continuous Polling List
   Cycles through Poll_Table[1..2] in continuous round-robin without any BLINK oscillator *)

IF NOT Enable THEN
    State := 0;
    Table_Idx := 1;
    Status_Text := 'Modbus Master Polling Disabled';
    Timeout_Timer(IN := FALSE);
    Inter_Poll_Timer(IN := FALSE);
    RETURN;
END_IF;

(* 1. Configure Hardware Polling Table Slots *)
Poll_Table[1].Slave_ID := Auto_Node_ID;
Poll_Table[1].Func_Code := 3; (* Read Holding Registers *)
Poll_Table[1].Start_Reg := Auto_Reg_Addr;
Poll_Table[1].Num_Regs := 2;  (* 2 Words = 32-bit Float Weight *)

Poll_Table[2].Slave_ID := Semi_Node_ID;
Poll_Table[2].Func_Code := 3;
Poll_Table[2].Start_Reg := Semi_Reg_Addr;
Poll_Table[2].Num_Regs := 2;

(* 2. Round-Robin Polling State Machine *)
CASE State OF
    0: (* Initialize Polling Table *)
        Table_Idx := 1;
        Current_Poll_Node := Poll_Table[Table_Idx].Slave_ID;
        Active_Table_Slot := Table_Idx;
        State := 1;
        Status_Text := 'Initializing Master Polling Table...';

    1: (* Dispatch Query for Current Table Slot *)
        Current_Poll_Node := Poll_Table[Table_Idx].Slave_ID;
        Active_Table_Slot := Table_Idx;
        Poll_Table[Table_Idx].Done := FALSE;
        Poll_Table[Table_Idx].Error := FALSE;
        
        (* In Simulation mode or driver stub, populate data *)
        IF Simulated_Feed THEN
            IF Table_Idx = 1 THEN
                Sim_Val_1 := GVL.load_cell_auto;
            ELSE
                Sim_Val_2 := GVL.load_cell_semi_auto;
            END_IF;
            Poll_Table[Table_Idx].Done := TRUE;
        END_IF;
        
        Timeout_Timer(IN := TRUE, PT := Timeout_Setting);
        State := 2;
        Status_Text := CONCAT('Polling Slot ', CONCAT(INT_TO_STRING(Table_Idx), CONCAT(' (Node ', CONCAT(BYTE_TO_STRING(Current_Poll_Node), ')...'))));

    2: (* Await Response with Hardware Timeout *)
        Timeout_Timer(IN := TRUE, PT := Timeout_Setting);
        
        IF Poll_Table[Table_Idx].Done THEN
            Timeout_Timer(IN := FALSE);
            State := 3; (* Response ready, advance to parser *)
        ELSIF Poll_Table[Table_Idx].Error OR Timeout_Timer.Q THEN
            Timeout_Timer(IN := FALSE);
            Total_Comm_Errors := Total_Comm_Errors + 1;
            IF Table_Idx = 1 THEN
                Auto_Scale_Online := FALSE;
            ELSE
                Semi_Scale_Online := FALSE;
            END_IF;
            Status_Text := CONCAT('Comm Timeout on Slot ', INT_TO_STRING(Table_Idx));
            State := 4; (* Advance to gap delay *)
        END_IF;

    3: (* Parse IEEE 754 Float Weight & Publish to GVL *)
        IF Simulated_Feed THEN
            IF Table_Idx = 1 THEN
                Load_Cell_Auto_Weight := Sim_Val_1;
                GVL.load_cell_auto := Load_Cell_Auto_Weight;
                Auto_Scale_Online := TRUE;
            ELSE
                Load_Cell_Semi_Weight := Sim_Val_2;
                GVL.load_cell_semi_auto := Load_Cell_Semi_Weight;
                Semi_Scale_Online := TRUE;
                Cycle_Counter := Cycle_Counter + 1;
            END_IF;
        ELSE
            (* Parse 2x 16-bit Modbus Registers into 32-bit Float *)
            dw_temp := SHL(WORD_TO_DWORD(Poll_Table[Table_Idx].Raw_Data[1]), 16) OR WORD_TO_DWORD(Poll_Table[Table_Idx].Raw_Data[2]);
            b_temp[0] := DWORD_TO_BYTE(SHR(dw_temp, 24));
            b_temp[1] := DWORD_TO_BYTE(SHR(dw_temp, 16));
            b_temp[2] := DWORD_TO_BYTE(SHR(dw_temp, 8));
            b_temp[3] := DWORD_TO_BYTE(dw_temp);
            
            IF Table_Idx = 1 THEN
                (* Assign to Auto Scale *)
                Load_Cell_Auto_Weight := DWORD_TO_REAL(dw_temp);
                GVL.load_cell_auto := Load_Cell_Auto_Weight;
                Auto_Scale_Online := TRUE;
            ELSE
                (* Assign to Semi-Auto Scale *)
                Load_Cell_Semi_Weight := DWORD_TO_REAL(dw_temp);
                GVL.load_cell_semi_auto := Load_Cell_Semi_Weight;
                Semi_Scale_Online := TRUE;
                Cycle_Counter := Cycle_Counter + 1;
            END_IF;
        END_IF;
        
        State := 4;

    4: (* Inter-Poll Gap Delay before Querying Next Node *)
        Inter_Poll_Timer(IN := TRUE, PT := Poll_Interval);
        IF Inter_Poll_Timer.Q THEN
            Inter_Poll_Timer(IN := FALSE);
            (* Advance to next slot in table *)
            IF Table_Idx = 1 THEN
                Table_Idx := 2;
            ELSE
                Table_Idx := 1;
            END_IF;
            State := 1; (* Query next slot *)
        END_IF;
END_CASE;
"""

with open(dut_xml_path, "w") as f:
    f.write(dut_xml)

with open(log_path, "w") as f:
    try:
        proj = projects.open(project_path)
        app = proj.find("Application", True)[0]
        
        # 1. Import DUT
        old_dut = proj.find("Modbus_Poll_Request", True)
        for d in old_dut:
            d.remove()
        app.import_xml(dut_xml_path)
        f.write("Modbus_Poll_Request DUT imported.\n")
        
        # 2. Create or Update sample_read_two_weights Function Block
        pou_list = proj.find("sample_read_two_weights", True)
        if len(pou_list) == 0:
            # Create POU
            pou = app.create_pou("sample_read_two_weights", PouType.FunctionBlock)
            f.write("Created sample_read_two_weights POU.\n")
        else:
            pou = pou_list[0]
            f.write("Found existing sample_read_two_weights POU.\n")
            
        pou.textual_declaration.replace(decl_sample)
        pou.textual_implementation.replace(code_sample)
        f.write("Updated sample_read_two_weights declaration and implementation.\n")
        
        proj.save()
        proj.close()
        f.write("Project saved successfully.\n")
    except Exception as e:
        f.write("Error: " + str(e) + "\n")
