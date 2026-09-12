import sys
import os

project_path = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\rasi_feed_batching_2\Rasi_feeds_batching2.project"
log_path = r"C:\Users\kabish\.gemini\antigravity-ide\brain\6bb09710-7f3e-4443-b187-ad04e16ca8dc\scratch\inspect_samyak_multi.txt"

with open(log_path, "w") as f:
    try:
        proj = projects.open(project_path)
        p = proj.find("FB_Samyak_Multi", True)[0]
        f.write("=== DECLARATION ===\n")
        f.write(p.textual_declaration.text + "\n")
        f.write("=== IMPLEMENTATION ===\n")
        f.write(p.textual_implementation.text + "\n")
        proj.close()
    except Exception as e:
        f.write("Error: " + str(e) + "\n")
