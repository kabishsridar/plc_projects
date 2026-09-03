import sys
import os

project_path = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\rasi_feed_batching_2\Rasi_feeds_batching2.project"
export_path = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\St_Codes\batching14_fbd.xml"

try:
    proj = projects.open(project_path)
    b = proj.find("batching14", True)[0]
    b.export_xml(export_path)
    proj.close()
    print("Exported batching14 FBD XML successfully.")
except Exception as e:
    print("Error: " + str(e))
