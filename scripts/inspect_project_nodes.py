import sys
import os

project_path = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\Rasi_feeds_batching.project"
log_path = r"C:\Users\kabish\inspect_output.txt"

with open(log_path, "w") as f:
    f.write("Starting inspect...\n")
    try:
        proj = projects.open(project_path)
        f.write("Project opened successfully.\n")
        
        for child in proj.get_children(True):
            f.write(child.get_name() + " (" + str(child.type) + ")\n")
            
        proj.close()
    except Exception as e:
        f.write("Error: " + str(e) + "\n")
