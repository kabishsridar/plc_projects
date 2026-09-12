import sys
import os

project_path = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\rasi_feed_batching_2\Rasi_feeds_batching2.project"
export_path = r"C:\Users\kabish\.gemini\antigravity-ide\brain\6bb09710-7f3e-4443-b187-ad04e16ca8dc\scratch\b14_proj2_export.xml"

try:
    proj = projects.open(project_path)
    b14 = proj.find("batching14", True)[0]
    b14.export_xml(export_path)
    proj.close()
    print("Exported batching14 from proj2.")
except Exception as e:
    print("Error: " + str(e))
