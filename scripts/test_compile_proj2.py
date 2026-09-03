import sys
import os

project_path = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\rasi_feed_batching_2\Rasi_feeds_batching2.project"
log_path = r"C:\Users\kabish\.gemini\antigravity-ide\brain\6bb09710-7f3e-4443-b187-ad04e16ca8dc\scratch\compile_proj2_log.txt"

with open(log_path, "w") as f:
    try:
        proj = projects.open(project_path)
        app = proj.find("Application", True)[0]
        f.write("Building Rasi_feeds_batching2...\n")
        msgs = app.build()
        for m in msgs:
            f.write(str(m.Severity) + ": " + str(m.Text) + "\n")
        proj.close()
    except Exception as e:
        f.write("Error: " + str(e) + "\n")
