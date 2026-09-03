import sys
import os

project_path = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\Rasi_feeds_batching.project"
log_path = r"C:\Users\kabish\.gemini\antigravity-ide\brain\6bb09710-7f3e-4443-b187-ad04e16ca8dc\scratch\inspect_full_project.txt"

with open(log_path, "w") as f:
    try:
        proj = projects.open(project_path)
        app = proj.find("Application", True)[0]
        
        # 1. Inspect Task Configuration
        task_cfg = proj.find("Task Configuration", True)
        f.write("Task Configuration found: " + str(len(task_cfg)) + "\n")
        tasks = proj.find("Task", True)
        for t in tasks:
            f.write("Task: " + t.get_name() + ", children: " + str([c.get_name() for c in t.get_children()]) + "\n")
            
        # 2. Inspect GVL text
        gvl = proj.find("GVL", True)[0]
        f.write("--- GVL CONTENT ---\n")
        f.write(gvl.textual_declaration.text + "\n")
        
        proj.close()
    except Exception as e:
        f.write("Error: " + str(e) + "\n")
