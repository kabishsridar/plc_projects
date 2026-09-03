import sys
import os

project_path = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\Rasi_feeds_batching.project"
log_path = r"C:\Users\kabish\.gemini\antigravity-ide\brain\6bb09710-7f3e-4443-b187-ad04e16ca8dc\scratch\test_fbd_import.txt"
xml_path = r"C:\Users\kabish\.gemini\antigravity-ide\brain\6bb09710-7f3e-4443-b187-ad04e16ca8dc\scratch\batching14_fbd.xml"

# PLCopen XML for batching14 (FBD) with strict schema ordering
plcopen_xml = """<?xml version="1.0" encoding="utf-8"?>
<project xmlns="http://www.plcopen.org/xml/tc6_0200">
  <fileHeader companyName="" productName="Automation Builder 2.7 - Basic" productVersion="Automation Builder 2.7" creationDateTime="2026-08-27T17:40:00" />
  <contentHeader name="Rasi_feeds_batching.project">
    <coordinateInfo>
      <fbd>
        <scaling x="1" y="1" />
      </fbd>
      <ld>
        <scaling x="1" y="1" />
      </ld>
      <sfc>
        <scaling x="1" y="1" />
      </sfc>
    </coordinateInfo>
  </contentHeader>
  <types>
    <dataTypes />
    <pous>
      <pou name="batching14" pouType="program">
        <interface>
          <localVars>
            <variable name="Supervisor_Inst">
              <type>
                <derived name="Batch_Supervisor_V14" />
              </type>
            </variable>
            <variable name="Auto_Ctrl_Inst">
              <type>
                <derived name="Auto_Batching_V14" />
              </type>
            </variable>
            <variable name="Semi_Auto_Ctrl_Inst">
              <type>
                <derived name="Semi_Auto_Batching_V14" />
              </type>
            </variable>
            <variable name="Auto_Complete">
              <type>
                <BOOL />
              </type>
            </variable>
            <variable name="Semi_Auto_Complete">
              <type>
                <BOOL />
              </type>
            </variable>
            <variable name="Auto_Err">
              <type>
                <INT />
              </type>
            </variable>
            <variable name="Auto_Msg">
              <type>
                <string />
              </type>
            </variable>
            <variable name="Semi_Auto_Err">
              <type>
                <INT />
              </type>
            </variable>
            <variable name="Semi_Auto_Msg">
              <type>
                <string />
              </type>
            </variable>
          </localVars>
        </interface>
        <body>
          <FBD>
            <!-- Network 1: Supervisor -->
            <block localId="1" typeName="Batch_Supervisor_V14" instanceName="Supervisor_Inst" executionOrderId="1">
              <position x="10" y="10" />
              <inputVariables>
                <variable formalParameter="Start_Button"><connectionPointIn><connection refLocalId="10" /></connectionPointIn></variable>
                <variable formalParameter="E_Stop_Active"><connectionPointIn><connection refLocalId="11" /></connectionPointIn></variable>
                <variable formalParameter="Reset"><connectionPointIn><connection refLocalId="12" /></connectionPointIn></variable>
                <variable formalParameter="Cycle_Hold_Active"><connectionPointIn><connection refLocalId="13" /></connectionPointIn></variable>
                <variable formalParameter="Target_Batch_Cycles"><connectionPointIn><connection refLocalId="14" /></connectionPointIn></variable>
                <variable formalParameter="Auto_Complete"><connectionPointIn><connection refLocalId="15" /></connectionPointIn></variable>
                <variable formalParameter="Semi_Auto_Complete"><connectionPointIn><connection refLocalId="16" /></connectionPointIn></variable>
                <variable formalParameter="Auto_Err"><connectionPointIn><connection refLocalId="17" /></connectionPointIn></variable>
                <variable formalParameter="Auto_Msg"><connectionPointIn><connection refLocalId="18" /></connectionPointIn></variable>
                <variable formalParameter="Semi_Auto_Err"><connectionPointIn><connection refLocalId="19" /></connectionPointIn></variable>
                <variable formalParameter="Semi_Auto_Msg"><connectionPointIn><connection refLocalId="20" /></connectionPointIn></variable>
                <variable formalParameter="load_cell_auto"><connectionPointIn><connection refLocalId="21" /></connectionPointIn></variable>
                <variable formalParameter="load_cell_semi_auto"><connectionPointIn><connection refLocalId="22" /></connectionPointIn></variable>
                <variable formalParameter="Auto_Initial_Tolerance"><connectionPointIn><connection refLocalId="23" /></connectionPointIn></variable>
                <variable formalParameter="Semi_Auto_Initial_Tolerance"><connectionPointIn><connection refLocalId="24" /></connectionPointIn></variable>
              </inputVariables>
              <inOutVariables />
              <outputVariables>
                <variable formalParameter="Internal_FB_Start" />
                <variable formalParameter="Run" />
                <variable formalParameter="Current_Batch_Cycle" />
                <variable formalParameter="Completed_Batch_Cycles" />
                <variable formalParameter="All_Cycles_Complete" />
                <variable formalParameter="Error_Code" />
                <variable formalParameter="Status_Message" />
                <variable formalParameter="Auto_Total_Target_Weight" />
                <variable formalParameter="Semi_Auto_Total_Target_Weight" />
                <variable formalParameter="Auto_Material_Count" />
                <variable formalParameter="Semi_Auto_Material_Count" />
              </outputVariables>
            </block>
            <inVariable localId="10"><position x="0" y="10" /><expression>GVL.Start_Button</expression></inVariable>
            <inVariable localId="11"><position x="0" y="20" /><expression>GVL.E_Stop_Active</expression></inVariable>
            <inVariable localId="12"><position x="0" y="30" /><expression>GVL.Reset</expression></inVariable>
            <inVariable localId="13"><position x="0" y="40" /><expression>GVL.Cycle_Hold_Active</expression></inVariable>
            <inVariable localId="14"><position x="0" y="50" /><expression>GVL.Target_Batch_Cycles</expression></inVariable>
            <inVariable localId="15"><position x="0" y="60" /><expression>Auto_Complete</expression></inVariable>
            <inVariable localId="16"><position x="0" y="70" /><expression>Semi_Auto_Complete</expression></inVariable>
            <inVariable localId="17"><position x="0" y="80" /><expression>Auto_Err</expression></inVariable>
            <inVariable localId="18"><position x="0" y="90" /><expression>Auto_Msg</expression></inVariable>
            <inVariable localId="19"><position x="0" y="100" /><expression>Semi_Auto_Err</expression></inVariable>
            <inVariable localId="20"><position x="0" y="110" /><expression>Semi_Auto_Msg</expression></inVariable>
            <inVariable localId="21"><position x="0" y="120" /><expression>GVL.load_cell_auto</expression></inVariable>
            <inVariable localId="22"><position x="0" y="130" /><expression>GVL.load_cell_semi_auto</expression></inVariable>
            <inVariable localId="23"><position x="0" y="140" /><expression>GVL.Auto_Initial_Tolerance</expression></inVariable>
            <inVariable localId="24"><position x="0" y="150" /><expression>GVL.Semi_Auto_Initial_Tolerance</expression></inVariable>
            <outVariable localId="25"><position x="20" y="10" /><connectionPointIn><connection refLocalId="1" formalParameter="Run" /></connectionPointIn><expression>GVL.Run</expression></outVariable>
            <outVariable localId="26"><position x="20" y="20" /><connectionPointIn><connection refLocalId="1" formalParameter="Error_Code" /></connectionPointIn><expression>GVL.Error_Code</expression></outVariable>
            <outVariable localId="27"><position x="20" y="30" /><connectionPointIn><connection refLocalId="1" formalParameter="Auto_Total_Target_Weight" /></connectionPointIn><expression>GVL.Auto_Total_Target_Weight</expression></outVariable>
            <outVariable localId="28"><position x="20" y="40" /><connectionPointIn><connection refLocalId="1" formalParameter="Semi_Auto_Total_Target_Weight" /></connectionPointIn><expression>GVL.Semi_Auto_Total_Target_Weight</expression></outVariable>
            <outVariable localId="29"><position x="20" y="50" /><connectionPointIn><connection refLocalId="1" formalParameter="Auto_Material_Count" /></connectionPointIn><expression>GVL.Auto_Material_Count</expression></outVariable>
            <outVariable localId="30"><position x="20" y="60" /><connectionPointIn><connection refLocalId="1" formalParameter="Semi_Auto_Material_Count" /></connectionPointIn><expression>GVL.Semi_Auto_Material_Count</expression></outVariable>

            <!-- Network 2: Auto Batching -->
            <block localId="2" typeName="Auto_Batching_V14" instanceName="Auto_Ctrl_Inst" executionOrderId="2">
              <position x="10" y="200" />
              <inputVariables>
                <variable formalParameter="Start_Button"><connectionPointIn><connection refLocalId="1" formalParameter="Internal_FB_Start" /></connectionPointIn></variable>
                <variable formalParameter="E_Stop_Active"><connectionPointIn><connection refLocalId="31" /></connectionPointIn></variable>
                <variable formalParameter="Reset"><connectionPointIn><connection refLocalId="32" /></connectionPointIn></variable>
                <variable formalParameter="Auto_Bin_Material_Mapping"><connectionPointIn><connection refLocalId="33" /></connectionPointIn></variable>
                <variable formalParameter="Auto_Bin_Cutoff_Weights"><connectionPointIn><connection refLocalId="34" /></connectionPointIn></variable>
                <variable formalParameter="Auto_Bin_Tolerance"><connectionPointIn><connection refLocalId="35" /></connectionPointIn></variable>
                <variable formalParameter="Inter_Bin_Delay"><connectionPointIn><connection refLocalId="36" /></connectionPointIn></variable>
                <variable formalParameter="Excess_Allowed"><connectionPointIn><connection refLocalId="37" /></connectionPointIn></variable>
              </inputVariables>
              <inOutVariables>
                <variable formalParameter="load_cell_value"><connectionPointIn><connection refLocalId="38" /></connectionPointIn></variable>
              </inOutVariables>
              <outputVariables>
                <variable formalParameter="Auto_Bin" />
                <variable formalParameter="auto_bin_cutoff" />
                <variable formalParameter="auto_bin_motor" />
                <variable formalParameter="Actual_Weights" />
                <variable formalParameter="Sequence_Complete" />
                <variable formalParameter="Active_Material_ID" />
                <variable formalParameter="Active_Bin_ID" />
                <variable formalParameter="Active_Target_Weight" />
                <variable formalParameter="Active_Live_Weight" />
                <variable formalParameter="Excess_Alarm" />
                <variable formalParameter="Error_Code" />
                <variable formalParameter="Status_Message" />
              </outputVariables>
            </block>
            <inVariable localId="31"><position x="0" y="210" /><expression>GVL.E_Stop_Active</expression></inVariable>
            <inVariable localId="32"><position x="0" y="220" /><expression>GVL.Reset</expression></inVariable>
            <inVariable localId="33"><position x="0" y="230" /><expression>GVL.Auto_Bin_Material_Mapping</expression></inVariable>
            <inVariable localId="34"><position x="0" y="240" /><expression>GVL.Auto_Bin_Cutoff_Weights</expression></inVariable>
            <inVariable localId="35"><position x="0" y="250" /><expression>GVL.Auto_Bin_Tolerance</expression></inVariable>
            <inVariable localId="36"><position x="0" y="260" /><expression>GVL.Auto_Inter_Bin_Delay</expression></inVariable>
            <inVariable localId="37"><position x="0" y="270" /><expression>GVL.Auto_Excess_Allowed</expression></inVariable>
            <inVariable localId="38"><position x="0" y="280" /><expression>GVL.load_cell_auto</expression></inVariable>
            <outVariable localId="39"><position x="20" y="200" /><connectionPointIn><connection refLocalId="2" formalParameter="Auto_Bin" /></connectionPointIn><expression>GVL.Auto_Bin</expression></outVariable>
            <outVariable localId="40"><position x="20" y="210" /><connectionPointIn><connection refLocalId="2" formalParameter="auto_bin_cutoff" /></connectionPointIn><expression>GVL.auto_bin_cutoff</expression></outVariable>
            <outVariable localId="41"><position x="20" y="220" /><connectionPointIn><connection refLocalId="2" formalParameter="auto_bin_motor" /></connectionPointIn><expression>GVL.auto_bin_motor</expression></outVariable>
            <outVariable localId="42"><position x="20" y="230" /><connectionPointIn><connection refLocalId="2" formalParameter="Actual_Weights" /></connectionPointIn><expression>GVL.Auto_Weights</expression></outVariable>
            <outVariable localId="43"><position x="20" y="240" /><connectionPointIn><connection refLocalId="2" formalParameter="Sequence_Complete" /></connectionPointIn><expression>Auto_Complete</expression></outVariable>
            <outVariable localId="44"><position x="20" y="250" /><connectionPointIn><connection refLocalId="2" formalParameter="Active_Material_ID" /></connectionPointIn><expression>GVL.Auto_Active_Mat</expression></outVariable>
            <outVariable localId="45"><position x="20" y="260" /><connectionPointIn><connection refLocalId="2" formalParameter="Active_Bin_ID" /></connectionPointIn><expression>GVL.Auto_Active_Bin</expression></outVariable>
            <outVariable localId="46"><position x="20" y="270" /><connectionPointIn><connection refLocalId="2" formalParameter="Active_Target_Weight" /></connectionPointIn><expression>GVL.Auto_Active_Target_Weight</expression></outVariable>
            <outVariable localId="47"><position x="20" y="280" /><connectionPointIn><connection refLocalId="2" formalParameter="Active_Live_Weight" /></connectionPointIn><expression>GVL.Auto_Active_Live_Weight</expression></outVariable>
            <outVariable localId="48"><position x="20" y="290" /><connectionPointIn><connection refLocalId="2" formalParameter="Excess_Alarm" /></connectionPointIn><expression>GVL.Auto_Excess_Alarm</expression></outVariable>
            <outVariable localId="49"><position x="20" y="300" /><connectionPointIn><connection refLocalId="2" formalParameter="Error_Code" /></connectionPointIn><expression>Auto_Err</expression></outVariable>
            <outVariable localId="50"><position x="20" y="310" /><connectionPointIn><connection refLocalId="2" formalParameter="Status_Message" /></connectionPointIn><expression>Auto_Msg</expression></outVariable>

            <!-- Network 3: Semi-Auto Batching -->
            <block localId="3" typeName="Semi_Auto_Batching_V14" instanceName="Semi_Auto_Ctrl_Inst" executionOrderId="3">
              <position x="10" y="400" />
              <inputVariables>
                <variable formalParameter="Start_Button"><connectionPointIn><connection refLocalId="1" formalParameter="Internal_FB_Start" /></connectionPointIn></variable>
                <variable formalParameter="E_Stop_Active"><connectionPointIn><connection refLocalId="51" /></connectionPointIn></variable>
                <variable formalParameter="Reset"><connectionPointIn><connection refLocalId="52" /></connectionPointIn></variable>
                <variable formalParameter="Semi_Auto_Bin_Material_Mapping"><connectionPointIn><connection refLocalId="53" /></connectionPointIn></variable>
                <variable formalParameter="Semi_Auto_Bin_Cutoff_Weights"><connectionPointIn><connection refLocalId="54" /></connectionPointIn></variable>
                <variable formalParameter="Semi_Auto_Bin_Tolerance"><connectionPointIn><connection refLocalId="55" /></connectionPointIn></variable>
                <variable formalParameter="Inter_Bin_Delay"><connectionPointIn><connection refLocalId="56" /></connectionPointIn></variable>
                <variable formalParameter="Excess_Allowed"><connectionPointIn><connection refLocalId="57" /></connectionPointIn></variable>
              </inputVariables>
              <inOutVariables>
                <variable formalParameter="load_cell_value"><connectionPointIn><connection refLocalId="58" /></connectionPointIn></variable>
              </inOutVariables>
              <outputVariables>
                <variable formalParameter="Semi_Auto_Bin" />
                <variable formalParameter="semi_auto_bin_cutoff" />
                <variable formalParameter="semi_auto_bin_motor" />
                <variable formalParameter="Actual_Weights" />
                <variable formalParameter="Sequence_Complete" />
                <variable formalParameter="Active_Material_ID" />
                <variable formalParameter="Active_Bin_ID" />
                <variable formalParameter="Active_Target_Weight" />
                <variable formalParameter="Active_Live_Weight" />
                <variable formalParameter="Excess_Alarm" />
                <variable formalParameter="Error_Code" />
                <variable formalParameter="Status_Message" />
              </outputVariables>
            </block>
            <inVariable localId="51"><position x="0" y="410" /><expression>GVL.E_Stop_Active</expression></inVariable>
            <inVariable localId="52"><position x="0" y="420" /><expression>GVL.Reset</expression></inVariable>
            <inVariable localId="53"><position x="0" y="430" /><expression>GVL.Semi_Auto_Bin_Material_Mapping</expression></inVariable>
            <inVariable localId="54"><position x="0" y="440" /><expression>GVL.Semi_Auto_Bin_Cutoff_Weights</expression></inVariable>
            <inVariable localId="55"><position x="0" y="450" /><expression>GVL.Semi_Auto_Bin_Tolerance</expression></inVariable>
            <inVariable localId="56"><position x="0" y="460" /><expression>GVL.Semi_Auto_Inter_Bin_Delay</expression></inVariable>
            <inVariable localId="57"><position x="0" y="470" /><expression>GVL.Semi_Auto_Excess_Allowed</expression></inVariable>
            <inVariable localId="58"><position x="0" y="480" /><expression>GVL.load_cell_semi_auto</expression></inVariable>
            <outVariable localId="59"><position x="20" y="400" /><connectionPointIn><connection refLocalId="3" formalParameter="Semi_Auto_Bin" /></connectionPointIn><expression>GVL.Semi_Auto_Bin</expression></outVariable>
            <outVariable localId="60"><position x="20" y="410" /><connectionPointIn><connection refLocalId="3" formalParameter="semi_auto_bin_cutoff" /></connectionPointIn><expression>GVL.semi_auto_bin_cutoff</expression></outVariable>
            <outVariable localId="61"><position x="20" y="420" /><connectionPointIn><connection refLocalId="3" formalParameter="semi_auto_bin_motor" /></connectionPointIn><expression>GVL.semi_auto_bin_motor</expression></outVariable>
            <outVariable localId="62"><position x="20" y="430" /><connectionPointIn><connection refLocalId="3" formalParameter="Actual_Weights" /></connectionPointIn><expression>GVL.Semi_Auto_Weights</expression></outVariable>
            <outVariable localId="63"><position x="20" y="440" /><connectionPointIn><connection refLocalId="3" formalParameter="Sequence_Complete" /></connectionPointIn><expression>Semi_Auto_Complete</expression></outVariable>
            <outVariable localId="64"><position x="20" y="450" /><connectionPointIn><connection refLocalId="3" formalParameter="Active_Material_ID" /></connectionPointIn><expression>GVL.Semi_Auto_Active_Mat</expression></outVariable>
            <outVariable localId="65"><position x="20" y="460" /><connectionPointIn><connection refLocalId="3" formalParameter="Active_Bin_ID" /></connectionPointIn><expression>GVL.Semi_Auto_Active_Bin</expression></outVariable>
            <outVariable localId="66"><position x="20" y="470" /><connectionPointIn><connection refLocalId="3" formalParameter="Active_Target_Weight" /></connectionPointIn><expression>GVL.Semi_Auto_Active_Target_Weight</expression></outVariable>
            <outVariable localId="67"><position x="20" y="480" /><connectionPointIn><connection refLocalId="3" formalParameter="Active_Live_Weight" /></connectionPointIn><expression>GVL.Semi_Auto_Active_Live_Weight</expression></outVariable>
            <outVariable localId="68"><position x="20" y="490" /><connectionPointIn><connection refLocalId="3" formalParameter="Excess_Alarm" /></connectionPointIn><expression>GVL.Semi_Auto_Excess_Alarm</expression></outVariable>
            <outVariable localId="69"><position x="20" y="500" /><connectionPointIn><connection refLocalId="3" formalParameter="Error_Code" /></connectionPointIn><expression>Semi_Auto_Err</expression></outVariable>
            <outVariable localId="70"><position x="20" y="510" /><connectionPointIn><connection refLocalId="3" formalParameter="Status_Message" /></connectionPointIn><expression>Semi_Auto_Msg</expression></outVariable>
          </FBD>
        </body>
      </pou>
    </pous>
  </types>
  <instances>
    <configurations />
  </instances>
</project>
"""

with open(xml_path, "w") as f:
    f.write(plcopen_xml)

with open(log_path, "w") as f:
    f.write("Starting import of batching14 (FBD)...\n")
    try:
        proj = projects.open(project_path)
        app = proj.find("Application", True)[0]
        
        old = proj.find("batching14", True)
        if len(old) > 0:
            old[0].remove()
            f.write("Removed existing batching14.\n")
            
        f.write("Importing batching14 PLCopen XML...\n")
        app.import_xml(xml_path)
        f.write("Import successful!\n")
        
        proj.save()
        proj.close()
        f.write("Project saved successfully.\n")
    except Exception as e:
        f.write("Error: " + str(e) + "\n")
