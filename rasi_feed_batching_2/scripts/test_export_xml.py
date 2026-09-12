import sys
import os

project_path = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\Rasi_feeds_batching.project"
export_path = r"C:\Users\kabish\.gemini\antigravity-ide\brain\6bb09710-7f3e-4443-b187-ad04e16ca8dc\scratch\sample_export.xml"
log_path = r"C:\Users\kabish\.gemini\antigravity-ide\brain\6bb09710-7f3e-4443-b187-ad04e16ca8dc\scratch\test_export.txt"

with open(log_path, "w") as f:
    try:
        proj = projects.open(project_path)
        app = proj.find("Application", True)[0]
        f.write("app has export_xml: " + str(hasattr(app, "export_xml")) + "\n")
        f.write("export_xml doc: " + str(getattr(app, "export_xml").__doc__) + "\n")
        batching13 = proj.find("batching13", True)[0]
        app.export_xml([batching13], export_path)
        f.write("Exported successfully to " + export_path + "\n")
        proj.close()
    except Exception as e:
        f.write("Error: " + str(e) + "\n")
