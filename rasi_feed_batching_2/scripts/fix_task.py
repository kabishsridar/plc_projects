import sys
import os

project_path = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\Rasi_feeds_batching.project"
log_path = r"C:\Users\kabish\.gemini\antigravity-ide\brain\6bb09710-7f3e-4443-b187-ad04e16ca8dc\scratch\fix_task_log.txt"

with open(log_path, "w") as f:
    try:
        proj = projects.open(project_path)
        tasks = proj.find("Task", True)
        f.write("Found tasks: " + str(len(tasks)) + "\n")
        if len(tasks) > 0:
            task = tasks[0]
            f.write("Task children: " + str([c.get_name() for c in task.get_children()]) + "\n")
            # If no children or wrong name, add batching13
            found = False
            for c in task.get_children():
                if c.get_name() in ["batching13", "batching14"]:
                    c.rename("batching13")
                    found = True
                    f.write("Renamed child to batching13\n")
            if not found:
                # Add batching13 call
                task.create_child("batching13", Guid("{d8995a94-4f9e-4e4b-a25e-399e03d3c7d6}"))
                f.write("Created batching13 child under Task\n")
        proj.save()
        proj.close()
        f.write("Task fixed.\n")
    except Exception as e:
        f.write("Error: " + str(e) + "\n")
