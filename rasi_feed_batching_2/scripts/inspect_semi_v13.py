import sys
import os

project_path = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\Rasi_feeds_batching.project"
log_path = r"C:\Users\kabish\.gemini\antigravity-ide\brain\6bb09710-7f3e-4443-b187-ad04e16ca8dc\scratch\inspect_semi_v13.txt"

with open(log_path, "w") as f:
    try:
        proj = projects.open(project_path)
        for child in proj.get_children(True):
            if child.get_name().lower() == "semi_auto_batching_v13":
                f.write("=== SEMI_AUTO_BATCHING_V13 IMPLEMENTATION ===\n")
                f.write(child.textual_implementation.text)
                break
        proj.close()
    except Exception as e:
        f.write("Error: " + str(e) + "\n")
