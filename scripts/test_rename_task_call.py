import sys
import os

project_path = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\Rasi_feeds_batching.project"
log_path = r"C:\Users\kabish\.gemini\antigravity-ide\brain\6bb09710-7f3e-4443-b187-ad04e16ca8dc\scratch\test_rename_task_call.txt"

with open(log_path, "w") as f:
    try:
        proj = projects.open(project_path)
        tasks = proj.find("Task", True)
        t = tasks[0]
        children = t.get_children()
        f.write("Task children: " + str([c.get_name() for c in children]) + "\n")
        for c in children:
            if c.get_name() == "batching13":
                f.write("Renaming child batching13 to batching14...\n")
                c.rename("batching14")
                f.write("Renamed successfully!\n")
        proj.save()
        proj.close()
        f.write("Saved and closed.\n")
    except Exception as e:
        f.write("Error: " + str(e) + "\n")
