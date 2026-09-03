import sys
import os

project_path = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\Rasi_feeds_batching.project"
log_path = r"C:\Users\kabish\.gemini\antigravity-ide\brain\6bb09710-7f3e-4443-b187-ad04e16ca8dc\scratch\test_xml.txt"

with open(log_path, "w") as f:
    try:
        proj = projects.open(project_path)
        app = proj.find("Application", True)[0]
        f.write("proj has import_xml: " + str(hasattr(proj, "import_xml")) + "\n")
        f.write("app has import_xml: " + str(hasattr(app, "import_xml")) + "\n")
        f.write("app has import_native: " + str(hasattr(app, "import_native")) + "\n")
        f.write("app has import_plcopenxml: " + str(hasattr(app, "import_plcopenxml")) + "\n")
        proj.close()
    except Exception as e:
        f.write("Error: " + str(e) + "\n")
