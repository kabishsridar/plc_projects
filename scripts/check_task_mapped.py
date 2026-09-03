import sys
import os

project_path = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\Rasi_feeds_batching.project"
log_path = r"C:\Users\kabish\.gemini\antigravity-ide\brain\6bb09710-7f3e-4443-b187-ad04e16ca8dc\scratch\check_task_mapped.txt"

with open(log_path, "w") as f:
    try:
        proj = projects.open(project_path)
        tasks = proj.find("Task", True)
        for t in tasks:
            f.write("Task: " + t.get_name() + "\n")
            for c in t.get_children():
                f.write("  Child: " + c.get_name() + "\n")
        proj.close()
    except Exception as e:
        f.write("Error: " + str(e) + "\n")
