import sys
import os

project_path = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\rasi_feed_batching_2\Rasi_feeds_batching2.project"
log_path = r"C:\Users\kabish\.gemini\antigravity-ide\brain\6bb09710-7f3e-4443-b187-ad04e16ca8dc\scratch\apply_b14_alone_log.txt"
xml_path = r"C:\Users\kabish\.gemini\antigravity-ide\brain\6bb09710-7f3e-4443-b187-ad04e16ca8dc\scratch\b14_direct_fbd.xml"

b14_direct_xml = """<?xml version="1.0" encoding="utf-8"?>
<project xmlns="http://www.plcopen.org/xml/tc6_0200">
  <fileHeader companyName="" productName="Automation Builder 2.7 - Basic" productVersion="Automation Builder 2.7" creationDateTime="2026-09-01T08:00:00" />
  <contentHeader name="Rasi_feeds_batching2.project">
    <coordinateInfo>
      <fbd><scaling x="1" y="1" /></fbd>
      <ld><scaling x="1" y="1" /></ld>
      <sfc><scaling x="1" y="1" /></sfc>
    </coordinateInfo>
  </contentHeader>
  <types>
    <dataTypes />
    <pous>
      <pou name="batching14" pouType="program">
        <interface>
          <localVars>
            <variable name="Auto_Ctrl"><type><derived name="Auto_Batching_V14" /></type></variable>
            <variable name="Semi_Auto_Ctrl"><type><derived name="Semi_Auto_Batching_V14" /></type></variable>
            <variable name="Auto_Complete"><type><BOOL /></type></variable>
            <variable name="Semi_Auto_Complete"><type><BOOL /></type></variable>
            <variable name="Auto_Err"><type><INT /></type></variable>
            <variable name="Auto_Msg"><type><string /></type></variable>
            <variable name="Semi_Auto_Err"><type><INT /></type></variable>
            <variable name="Semi_Auto_Msg"><type><string /></type></variable>
            <variable name="FB_Samyak_Multi_1"><type><derived name="FB_Samyak_Multi" /></type></variable>
            <variable name="arrSlaveIDs"><type><array><dimension lower="1" upper="4" /><baseType><BYTE /></baseType></array></type><initialValue><arrayValue><value><simpleValue value="1" /></value><value><simpleValue value="2" /></value><value><simpleValue value="0" /></value><value><simpleValue value="0" /></value></arrayValue></initialValue></variable>
            <variable name="arrDivisor"><type><array><dimension lower="1" upper="4" /><baseType><REAL /></baseType></array></type><initialValue><arrayValue><value><simpleValue value="10.0" /></value><value><simpleValue value="10.0" /></value><value><simpleValue value="1.0" /></value><value><simpleValue value="1.0" /></value></arrayValue></initialValue></variable>
            <variable name="arrTare_In"><type><array><dimension lower="1" upper="4" /><baseType><BOOL /></baseType></array></type></variable>
            <variable name="Weight_Scaled_Array"><type><array><dimension lower="1" upper="4" /><baseType><REAL /></baseType></array></type></variable>
            <variable name="arrLine_Fault"><type><array><dimension lower="1" upper="4" /><baseType><BOOL /></baseType></array></type></variable>
          </localVars>
        </interface>
        <body>
          <FBD>
            <vendorElement localId="10000000000">
              <position x="0" y="0" />
              <alternativeText><xhtml xmlns="http://www.w3.org/1999/xhtml">FBD Implementation Attributes</xhtml></alternativeText>
              <addData>
                <data name="http://www.3s-software.com/plcopenxml/fbd/implementationattributes" handleUnknown="implementation">
                  <fbdattributes xmlns=""><attribute name="BoxInputFlagsSupported" value="true" /></fbdattributes>
                </data>
              </addData>
            </vendorElement>

            <!-- Network 1: FB_Samyak_Multi_1 (Method 3: Multi-Slave Polling List - No BLINK) -->
            <inVariable localId="1001"><position x="50" y="50" /><connectionPointOut /><expression>1</expression></inVariable>
            <inVariable localId="1002"><position x="50" y="70" /><connectionPointOut /><expression>2</expression></inVariable>
            <inVariable localId="1003"><position x="50" y="90" /><connectionPointOut /><expression>arrSlaveIDs</expression></inVariable>
            <inVariable localId="1004"><position x="50" y="110" /><connectionPointOut /><expression>arrDivisor</expression></inVariable>
            <inVariable localId="1005"><position x="50" y="130" /><connectionPointOut /><expression>arrTare_In</expression></inVariable>

            <block localId="1010" typeName="FB_Samyak_Multi" instanceName="FB_Samyak_Multi_1">
              <position x="250" y="50" />
              <inputVariables>
                <variable formalParameter="Com_Slot"><connectionPointIn><connection refLocalId="1001" /></connectionPointIn></variable>
                <variable formalParameter="iSlaveCount"><connectionPointIn><connection refLocalId="1002" /></connectionPointIn></variable>
                <variable formalParameter="arrSlaveIDs"><connectionPointIn><connection refLocalId="1003" /></connectionPointIn></variable>
                <variable formalParameter="arrDivisor"><connectionPointIn><connection refLocalId="1004" /></connectionPointIn></variable>
                <variable formalParameter="arrTare_In"><connectionPointIn><connection refLocalId="1005" /></connectionPointIn></variable>
              </inputVariables>
              <inOutVariables />
              <outputVariables>
                <variable formalParameter="arrWeight_Scaled" />
                <variable formalParameter="arrLine_Fault" />
                <variable formalParameter="arrErrCount" />
                <variable formalParameter="iCurrent_ID" />
                <variable formalParameter="xStatus_Busy" />
              </outputVariables>
            </block>

            <outVariable localId="1020"><position x="550" y="50" /><connectionPointIn><connection refLocalId="1010" formalParameter="arrWeight_Scaled" /></connectionPointIn><expression>Weight_Scaled_Array</expression></outVariable>
            <outVariable localId="1021"><position x="550" y="70" /><connectionPointIn><connection refLocalId="1010" formalParameter="arrLine_Fault" /></connectionPointIn><expression>arrLine_Fault</expression></outVariable>

            <!-- Network 2: Assign scaled weights to GVL.load_cell_auto and GVL.load_cell_semi_auto -->
            <inVariable localId="2001"><position x="50" y="180" /><connectionPointOut /><expression>Weight_Scaled_Array[1]</expression></inVariable>
            <outVariable localId="2002"><position x="350" y="180" /><connectionPointIn><connection refLocalId="2001" /></connectionPointIn><expression>GVL.load_cell_auto</expression></outVariable>

            <inVariable localId="2003"><position x="50" y="220" /><connectionPointOut /><expression>Weight_Scaled_Array[2]</expression></inVariable>
            <outVariable localId="2004"><position x="350" y="220" /><connectionPointIn><connection refLocalId="2003" /></connectionPointIn><expression>GVL.load_cell_semi_auto</expression></outVariable>

            <!-- Network 3: Auto_Ctrl (Auto_Batching_V14) -->
            <inVariable localId="70000000000"><position x="50" y="300" /><connectionPointOut /><expression>GVL.Start_Button</expression></inVariable>
            <inVariable localId="70000000001"><position x="50" y="320" /><connectionPointOut /><expression>GVL.E_Stop_Active</expression></inVariable>
            <inVariable localId="70000000002"><position x="50" y="340" /><connectionPointOut /><expression>GVL.Reset</expression></inVariable>
            <inVariable localId="70000000003"><position x="50" y="360" /><connectionPointOut /><expression>GVL.Auto_Bin_Material_Mapping</expression></inVariable>
            <inVariable localId="70000000004"><position x="50" y="380" /><connectionPointOut /><expression>GVL.Auto_Coarse_To_Fine_speed</expression></inVariable>
            <inVariable localId="70000000005"><position x="50" y="400" /><connectionPointOut /><expression>GVL.Auto_Bin_Tolerance</expression></inVariable>
            <inVariable localId="70000000006"><position x="50" y="420" /><connectionPointOut /><expression>GVL.Auto_Inter_Bin_Delay</expression></inVariable>
            <inVariable localId="70000000007"><position x="50" y="440" /><connectionPointOut /><expression>GVL.Auto_Excess_Allowed</expression></inVariable>
            <inVariable localId="70000000008"><position x="50" y="460" /><connectionPointOut /><expression>GVL.load_cell_auto</expression></inVariable>
            <inVariable localId="70000000009"><position x="50" y="480" /><connectionPointOut /><expression>GVL.Target_Batch_Cycles</expression></inVariable>
            <inVariable localId="70000000010"><position x="50" y="500" /><connectionPointOut /><expression>GVL.Next_Cycle_Start</expression></inVariable>
            <inVariable localId="70000000011"><position x="50" y="520" /><connectionPointOut /><expression>GVL.Empty_Weight_Limit</expression></inVariable>

            <block localId="70000000012" typeName="Auto_Batching_V14" instanceName="Auto_Ctrl">
              <position x="250" y="300" />
              <inputVariables>
                <variable formalParameter="Start_Button"><connectionPointIn><connection refLocalId="70000000000" /></connectionPointIn></variable>
                <variable formalParameter="E_Stop_Active"><connectionPointIn><connection refLocalId="70000000001" /></connectionPointIn></variable>
                <variable formalParameter="Reset"><connectionPointIn><connection refLocalId="70000000002" /></connectionPointIn></variable>
                <variable formalParameter="Auto_Bin_Material_Mapping"><connectionPointIn><connection refLocalId="70000000003" /></connectionPointIn></variable>
                <variable formalParameter="Auto_Coarse_To_Fine_Speed"><connectionPointIn><connection refLocalId="70000000004" /></connectionPointIn></variable>
                <variable formalParameter="Auto_Bin_Tolerance"><connectionPointIn><connection refLocalId="70000000005" /></connectionPointIn></variable>
                <variable formalParameter="Inter_Bin_Delay"><connectionPointIn><connection refLocalId="70000000006" /></connectionPointIn></variable>
                <variable formalParameter="Excess_Allowed"><connectionPointIn><connection refLocalId="70000000007" /></connectionPointIn></variable>
                <variable formalParameter="load_cell_value"><connectionPointIn><connection refLocalId="70000000008" /></connectionPointIn></variable>
                <variable formalParameter="Target_Batch_Cycles"><connectionPointIn><connection refLocalId="70000000009" /></connectionPointIn></variable>
                <variable formalParameter="Next_Cycle_Start"><connectionPointIn><connection refLocalId="70000000010" /></connectionPointIn></variable>
                <variable formalParameter="Empty_Weight_Limit"><connectionPointIn><connection refLocalId="70000000011" /></connectionPointIn></variable>
              </inputVariables>
              <inOutVariables />
              <outputVariables>
                <variable formalParameter="Auto_Bin" />
                <variable formalParameter="auto_bin_cutoff"><connectionPointOut><expression>GVL.auto_bin_cutoff</expression></connectionPointOut></variable>
                <variable formalParameter="auto_bin_motor"><connectionPointOut><expression>GVL.auto_bin_motor</expression></connectionPointOut></variable>
                <variable formalParameter="Actual_Weights"><connectionPointOut><expression>GVL.Auto_Weights</expression></connectionPointOut></variable>
                <variable formalParameter="Sequence_Complete"><connectionPointOut><expression>Auto_Complete</expression></connectionPointOut></variable>
                <variable formalParameter="Active_Material_ID"><connectionPointOut><expression>GVL.Auto_Active_Mat</expression></connectionPointOut></variable>
                <variable formalParameter="Active_Bin_ID"><connectionPointOut><expression>GVL.Auto_Active_Bin</expression></connectionPointOut></variable>
                <variable formalParameter="Active_Target_Weight"><connectionPointOut><expression>GVL.Auto_Active_Target_Weight</expression></connectionPointOut></variable>
                <variable formalParameter="Active_Live_Weight"><connectionPointOut><expression>GVL.Auto_Active_Live_Weight</expression></connectionPointOut></variable>
                <variable formalParameter="Current_Step"><connectionPointOut><expression>GVL.Auto_Current_Step</expression></connectionPointOut></variable>
                <variable formalParameter="Cycle_Manager_State" />
                <variable formalParameter="Excess_Alarm"><connectionPointOut><expression>GVL.Auto_Excess_Alarm</expression></connectionPointOut></variable>
                <variable formalParameter="Error_Code"><connectionPointOut><expression>Auto_Err</expression></connectionPointOut></variable>
                <variable formalParameter="Auto_Current_Batch_Cycle" />
                <variable formalParameter="Auto_Completed_Batch_Cycles" />
                <variable formalParameter="Auto_All_Cycles_Complete" />
                <variable formalParameter="Status_Message"><connectionPointOut><expression>Auto_Msg</expression></connectionPointOut></variable>
              </outputVariables>
            </block>
            <outVariable localId="70000000013"><position x="550" y="300" /><connectionPointIn><connection refLocalId="70000000012" formalParameter="Auto_Bin" /></connectionPointIn><expression>GVL.Auto_Bin</expression></outVariable>

            <!-- Network 4: Semi_Auto_Ctrl (Semi_Auto_Batching_V14) -->
            <inVariable localId="80000000000"><position x="50" y="650" /><connectionPointOut /><expression>GVL.Start_Button</expression></inVariable>
            <inVariable localId="80000000001"><position x="50" y="670" /><connectionPointOut /><expression>GVL.E_Stop_Active</expression></inVariable>
            <inVariable localId="80000000002"><position x="50" y="690" /><connectionPointOut /><expression>GVL.Reset</expression></inVariable>
            <inVariable localId="80000000003"><position x="50" y="710" /><connectionPointOut /><expression>GVL.Semi_Auto_Bin_Material_Mapping</expression></inVariable>
            <inVariable localId="80000000004"><position x="50" y="730" /><connectionPointOut /><expression>GVL.Semi_Auto_Coarse_To_Fine_speed</expression></inVariable>
            <inVariable localId="80000000005"><position x="50" y="750" /><connectionPointOut /><expression>GVL.Semi_Auto_Bin_Tolerance</expression></inVariable>
            <inVariable localId="80000000006"><position x="50" y="770" /><connectionPointOut /><expression>GVL.Semi_Auto_Inter_Bin_Delay</expression></inVariable>
            <inVariable localId="80000000007"><position x="50" y="790" /><connectionPointOut /><expression>GVL.Semi_Auto_Excess_Allowed</expression></inVariable>
            <inVariable localId="80000000008"><position x="50" y="810" /><connectionPointOut /><expression>GVL.load_cell_semi_auto</expression></inVariable>
            <inVariable localId="80000000009"><position x="50" y="830" /><connectionPointOut /><expression>GVL.Target_Batch_Cycles</expression></inVariable>
            <inVariable localId="80000000010"><position x="50" y="850" /><connectionPointOut /><expression>GVL.Next_Cycle_Start</expression></inVariable>
            <inVariable localId="80000000011"><position x="50" y="870" /><connectionPointOut /><expression>GVL.Empty_Weight_Limit</expression></inVariable>

            <block localId="80000000012" typeName="Semi_Auto_Batching_V14" instanceName="Semi_Auto_Ctrl">
              <position x="250" y="650" />
              <inputVariables>
                <variable formalParameter="Start_Button"><connectionPointIn><connection refLocalId="80000000000" /></connectionPointIn></variable>
                <variable formalParameter="E_Stop_Active"><connectionPointIn><connection refLocalId="80000000001" /></connectionPointIn></variable>
                <variable formalParameter="Reset"><connectionPointIn><connection refLocalId="80000000002" /></connectionPointIn></variable>
                <variable formalParameter="Semi_Auto_Bin_Material_Mapping"><connectionPointIn><connection refLocalId="80000000003" /></connectionPointIn></variable>
                <variable formalParameter="Semi_Auto_Coarse_To_Fine_Speed"><connectionPointIn><connection refLocalId="80000000004" /></connectionPointIn></variable>
                <variable formalParameter="Semi_Auto_Bin_Tolerance"><connectionPointIn><connection refLocalId="80000000005" /></connectionPointIn></variable>
                <variable formalParameter="Inter_Bin_Delay"><connectionPointIn><connection refLocalId="80000000006" /></connectionPointIn></variable>
                <variable formalParameter="Excess_Allowed"><connectionPointIn><connection refLocalId="80000000007" /></connectionPointIn></variable>
                <variable formalParameter="load_cell_value"><connectionPointIn><connection refLocalId="80000000008" /></connectionPointIn></variable>
                <variable formalParameter="Target_Batch_Cycles"><connectionPointIn><connection refLocalId="80000000009" /></connectionPointIn></variable>
                <variable formalParameter="Next_Cycle_Start"><connectionPointIn><connection refLocalId="80000000010" /></connectionPointIn></variable>
                <variable formalParameter="Empty_Weight_Limit"><connectionPointIn><connection refLocalId="80000000011" /></connectionPointIn></variable>
              </inputVariables>
              <inOutVariables />
              <outputVariables>
                <variable formalParameter="Semi_Auto_Bin" />
                <variable formalParameter="semi_auto_bin_cutoff"><connectionPointOut><expression>GVL.semi_auto_bin_cutoff</expression></connectionPointOut></variable>
                <variable formalParameter="semi_auto_bin_motor"><connectionPointOut><expression>GVL.semi_auto_bin_motor</expression></connectionPointOut></variable>
                <variable formalParameter="Actual_Weights"><connectionPointOut><expression>GVL.Semi_Auto_Weights</expression></connectionPointOut></variable>
                <variable formalParameter="Sequence_Complete"><connectionPointOut><expression>Semi_Auto_Complete</expression></connectionPointOut></variable>
                <variable formalParameter="Active_Material_ID"><connectionPointOut><expression>GVL.Semi_Auto_Active_Mat</expression></connectionPointOut></variable>
                <variable formalParameter="Active_Bin_ID"><connectionPointOut><expression>GVL.Semi_Auto_Active_Bin</expression></connectionPointOut></variable>
                <variable formalParameter="Active_Target_Weight"><connectionPointOut><expression>GVL.Semi_Auto_Active_Target_Weight</expression></connectionPointOut></variable>
                <variable formalParameter="Active_Live_Weight"><connectionPointOut><expression>GVL.Semi_Auto_Active_Live_Weight</expression></connectionPointOut></variable>
                <variable formalParameter="Current_Step"><connectionPointOut><expression>GVL.Semi_Auto_Current_Step</expression></connectionPointOut></variable>
                <variable formalParameter="Cycle_Manager_State" />
                <variable formalParameter="Excess_Alarm"><connectionPointOut><expression>GVL.Semi_Auto_Excess_Alarm</expression></connectionPointOut></variable>
                <variable formalParameter="Error_Code"><connectionPointOut><expression>Semi_Auto_Err</expression></connectionPointOut></variable>
                <variable formalParameter="Semi_Auto_Current_Batch_Cycle" />
                <variable formalParameter="Semi_Auto_Completed_Batch_Cycles" />
                <variable formalParameter="Semi_Auto_All_Cycles_Complete" />
                <variable formalParameter="Status_Message"><connectionPointOut><expression>Semi_Auto_Msg</expression></connectionPointOut></variable>
              </outputVariables>
            </block>
            <outVariable localId="80000000013"><position x="550" y="650" /><connectionPointIn><connection refLocalId="80000000012" formalParameter="Semi_Auto_Bin" /></connectionPointIn><expression>GVL.Semi_Auto_Bin</expression></outVariable>
          </FBD>
        </body>
      </pou>
    </pous>
  </types>
  <instances><configurations /></instances>
</project>
"""

with open(xml_path, "w") as f:
    f.write(b14_direct_xml)

with open(log_path, "w") as f:
    try:
        proj = projects.open(project_path)
        app = proj.find("Application", True)[0]
        
        # 1. Remove sample_read_two_weights if present
        s_pous = proj.find("sample_read_two_weights", True)
        for s in s_pous:
            s.remove()
        f.write("Removed sample_read_two_weights POU.\n")
        
        # 2. Re-import batching14 with direct FBD implementation
        b_pous = proj.find("batching14", True)
        for b in b_pous:
            b.remove()
        f.write("Removed old batching14.\n")
        
        app.import_xml(xml_path)
        f.write("Imported batching14 with direct FBD dual scale reading (Method 3).\n")
        
        proj.save()
        proj.close()
        f.write("Project saved successfully.\n")
    except Exception as e:
        f.write("Error: " + str(e) + "\n")
