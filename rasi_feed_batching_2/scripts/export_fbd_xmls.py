import sys
import os

project_path = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\rasi_feed_batching_2\Rasi_feeds_batching2.project"
export_path1 = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\St_Codes\sample_read_two_weights_fbd.xml"
export_path2 = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\St_Codes\batching14_fbd.xml"

try:
    proj = projects.open(project_path)
    s = proj.find("sample_read_two_weights", True)[0]
    s.export_xml(export_path1)
    b = proj.find("batching14", True)[0]
    b.export_xml(export_path2)
    proj.close()
    print("Exported FBD XMLs successfully.")
except Exception as e:
    print("Error: " + str(e))
