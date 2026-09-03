import sys
import os

project_path = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\Rasi_feeds_batching.project"
export_path = r"C:\Users\kabish\.gemini\antigravity-ide\brain\6bb09710-7f3e-4443-b187-ad04e16ca8dc\scratch\batching13_exported.xml"
log_path = r"C:\Users\kabish\.gemini\antigravity-ide\brain\6bb09710-7f3e-4443-b187-ad04e16ca8dc\scratch\test_export2.txt"

with open(log_path, "w") as f:
    try:
        proj = projects.open(project_path)
        batching13 = proj.find("batching13", True)[0]
        batching13.export_xml(export_path, False, False, False)
        f.write("Exported successfully to " + export_path + "\n")
        proj.close()
    except Exception as e:
        f.write("Error: " + str(e) + "\n")
