import sys
import os

project_path = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\Rasi_feeds_batching.project"
log_path = r"C:\Users\kabish\.gemini\antigravity-ide\brain\6bb09710-7f3e-4443-b187-ad04e16ca8dc\scratch\fix_all_remaining_log.txt"

# Updated GVL Declaration with Auto_Sequence_Complete & Semi_Auto_Sequence_Complete
gvl_content = """{attribute 'qualified_only'}
VAR_GLOBAL
    Recipe_Weights AT %MD100 : ARRAY[1..20] OF REAL;
	Auto_Bin_Material_Mapping AT %MW50: ARRAY[1..6] OF INT;
	Semi_Auto_Bin_Material_Mapping AT %MW60: ARRAY[1..10] OF INT;
	Auto_Bin_Cutoff_Weights AT %MD120: ARRAY[1..6] OF REAL;
	Semi_Auto_Bin_Cutoff_Weights AT %MD130: ARRAY[1..10] OF REAL;
	Auto_Bin_Tolerance AT %MD150: ARRAY[1..6] OF REAL;
	Semi_Auto_Bin_Tolerance AT %MD160: ARRAY[1..10] OF REAL;
	Start_Button AT %MX2.0: BOOL;
	E_Stop_Active AT %MX2.1: BOOL;
	Reset AT %MX2.3: BOOL;
	Cycle_Hold_Active AT %MX2.4: BOOL;
	Auto_Active_Mat AT %MW70: INT;
	Auto_Active_Bin AT %MW71: INT;
	Semi_Auto_Active_Mat AT %MW72: INT;
	Semi_Auto_Active_Bin AT %MW73: INT;
	Target_Batch_Cycles AT %MW74: INT;
	Current_Batch_Cycle AT %MW75: INT;
	Error_Code AT %MW76: INT;
	Run AT %MX2.5 : BOOL;
	load_cell_auto AT %MD174 : REAL;
	load_cell_semi_auto AT %MD175 : REAL;
	Auto_Initial_Tolerance AT %MD176 : REAL;
	Semi_Auto_Initial_Tolerance AT %MD178 : REAL;
	Auto_Total_Target_Weight AT %MD180 : REAL;
	Semi_Auto_Total_Target_Weight AT %MD184 : REAL;
	Auto_Material_Count AT %MW77 : INT;
	Semi_Auto_Material_Count AT %MW78 : INT;
	Auto_Active_Target_Weight AT %MD220 : REAL;
	Semi_Auto_Active_Target_Weight AT %MD224 : REAL;
	Auto_Active_Live_Weight AT %MD228 : REAL;
	Semi_Auto_Active_Live_Weight AT %MD232 : REAL;
	Auto_Excess_Allowed AT %MX2.6 : BOOL;
	Semi_Auto_Excess_Allowed AT %MX2.9 : BOOL;
	Auto_Excess_Alarm AT %MX2.7 : BOOL;
	Semi_Auto_Excess_Alarm AT %MX2.8 : BOOL;
	Auto_Inter_Bin_Delay AT %MD190 : TIME;
	Semi_Auto_Inter_Bin_Delay AT %MD194 : TIME;
	Auto_Sequence_Complete AT %MX3.0 : BOOL;
	Semi_Auto_Sequence_Complete AT %MX3.1 : BOOL;
	
	(* 8 Process Output and Weight Arrays *)
	Auto_Bin : ARRAY[1..6] OF BOOL;
	auto_bin_cutoff : ARRAY[1..6] OF BOOL;
	auto_bin_motor : ARRAY[1..6] OF BOOL;
	Semi_Auto_Bin : ARRAY[1..10] OF BOOL;
	semi_auto_bin_cutoff : ARRAY[1..10] OF BOOL;
	semi_auto_bin_motor : ARRAY[1..10] OF BOOL;
	Auto_Weights : ARRAY[1..6] OF REAL;
	Semi_Auto_Weights : ARRAY[1..10] OF REAL;
END_VAR
"""

# Updated Task Configuration XML mapping batching14
task_xml_path = r"C:\Users\kabish\.gemini\antigravity-ide\brain\6bb09710-7f3e-4443-b187-ad04e16ca8dc\scratch\task_batching14.xml"
task_xml = """<?xml version="1.0" encoding="utf-8"?>
<project xmlns="http://www.plcopen.org/xml/tc6_0200">
  <fileHeader companyName="" productName="Automation Builder 2.7 - Basic" productVersion="Automation Builder 2.7" creationDateTime="2026-08-29T13:26:29" />
  <contentHeader name="Rasi_feeds_batching.project">
    <coordinateInfo>
      <fbd><scaling x="1" y="1" /></fbd>
      <ld><scaling x="1" y="1" /></ld>
      <sfc><scaling x="1" y="1" /></sfc>
    </coordinateInfo>
  </contentHeader>
  <types><dataTypes /><pous /></types>
  <instances><configurations /></instances>
  <addData>
    <data name="http://www.3s-software.com/plcopenxml/application" handleUnknown="implementation">
      <resource name="Application">
        <task name="Task" interval="PT0.01S" priority="14">
          <pouInstance name="batching14" typeName="" />
          <addData>
            <data name="http://www.3s-software.com/plcopenxml/tasksettings" handleUnknown="implementation">
              <TaskSettings KindOfTask="Cyclic" Interval="t#10ms" IntervalUnit="ms" WithinSPSTimeSlicing="true">
                <Watchdog Enabled="true" Time="t#20ms" TimeUnit="ms" Sensitivity="1" />
              </TaskSettings>
            </data>
          </addData>
        </task>
      </resource>
    </data>
  </addData>
</project>
"""

with open(task_xml_path, "w") as f:
    f.write(task_xml)

with open(log_path, "w") as f:
    f.write("Starting comprehensive fixes...\n")
    try:
        proj = projects.open(project_path)
        app = proj.find("Application", True)[0]
        
        # 1. Update GVL
        gvl = proj.find("GVL", True)[0]
        gvl.textual_declaration.replace(gvl_content)
        f.write("GVL updated with Sequence_Complete flags.\n")
        
        # 2. Update Task to call batching14
        tasks = proj.find("Task", True)
        if len(tasks) > 0:
            for child in tasks[0].get_children():
                child.remove()
                f.write("Removed old task call: " + child.get_name() + "\n")
        app.import_xml(task_xml_path)
        f.write("Task updated to call batching14.\n")
        
        proj.save()
        proj.close()
        f.write("Comprehensive fixes completed successfully.\n")
    except Exception as e:
        f.write("Error: " + str(e) + "\n")
