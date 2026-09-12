import sys
import os

project_path = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\Rasi_feeds_batching.project"
xml_path = r"C:\Users\kabish\.gemini\antigravity-ide\brain\6bb09710-7f3e-4443-b187-ad04e16ca8dc\scratch\task_export.xml"
log_path = r"C:\Users\kabish\.gemini\antigravity-ide\brain\6bb09710-7f3e-4443-b187-ad04e16ca8dc\scratch\import_task13_log.txt"

with open(log_path, "w") as f:
    try:
        proj = projects.open(project_path)
        app = proj.find("Application", True)[0]
        # Remove existing Task if empty
        tasks = proj.find("Task", True)
        for t in tasks:
            t.remove()
            f.write("Removed old Task.\n")
        app.import_xml(xml_path)
        f.write("Imported task_export.xml successfully.\n")
        proj.save()
        proj.close()
        f.write("Project saved.\n")
    except Exception as e:
        f.write("Error: " + str(e) + "\n")
