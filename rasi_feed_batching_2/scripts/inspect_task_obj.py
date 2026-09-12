import sys
import os

project_path = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\Rasi_feeds_batching.project"
log_path = r"C:\Users\kabish\.gemini\antigravity-ide\brain\6bb09710-7f3e-4443-b187-ad04e16ca8dc\scratch\inspect_task_obj.txt"

with open(log_path, "w") as f:
    try:
        proj = projects.open(project_path)
        tasks = proj.find("Task", True)
        t = tasks[0]
        f.write("Task members: " + str(dir(t)) + "\n")
        for c in t.get_children():
            f.write("Child: " + c.get_name() + ", type: " + str(type(c)) + ", members: " + str(dir(c)) + "\n")
        proj.close()
    except Exception as e:
        f.write("Error: " + str(e) + "\n")
