import sys
import os

project_path = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\rasi_feed_batching_2\Rasi_feeds_batching2.project"
log_path = r"C:\Users\kabish\.gemini\antigravity-ide\brain\6bb09710-7f3e-4443-b187-ad04e16ca8dc\scratch\list_final_pous.txt"

with open(log_path, "w") as f:
    try:
        proj = projects.open(project_path)
        pous = [c.get_name() for c in proj.get_children(True) if hasattr(c, "textual_declaration") or hasattr(c, "textual_implementation")]
        f.write("Final POUs in Rasi_feeds_batching2: " + str(pous) + "\n")
        proj.close()
    except Exception as e:
        f.write("Error: " + str(e) + "\n")
