import sys
import os

project_path = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\Rasi_feeds_batching.project"
log_path = r"C:\Users\kabish\.gemini\antigravity-ide\brain\6bb09710-7f3e-4443-b187-ad04e16ca8dc\scratch\b13_errors.txt"

with open(log_path, "w") as f:
    try:
        proj = projects.open(project_path)
        # Rename task call to batching13
        tasks = proj.find("Task", True)
        if len(tasks) > 0:
            for c in tasks[0].get_children():
                if c.get_name() == "batching14":
                    c.rename("batching13")
                    f.write("Renamed task call to batching13.\n")
        app = proj.find("Application", True)[0]
        f.write("Building application with batching13...\n")
        msgs = app.build()
        for m in msgs:
            f.write(str(m.Severity) + ": " + str(m.Text) + "\n")
        # Rename back to batching14
        for c in tasks[0].get_children():
            if c.get_name() == "batching13":
                c.rename("batching14")
        proj.close()
    except Exception as e:
        f.write("Error: " + str(e) + "\n")
