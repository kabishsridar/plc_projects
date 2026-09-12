import sys
import os

project_path = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\Rasi_feeds_batching.project"
log_path = r"C:\Users\kabish\.gemini\antigravity-ide\brain\6bb09710-7f3e-4443-b187-ad04e16ca8dc\scratch\test_pou_methods.txt"

with open(log_path, "w") as f:
    try:
        proj = projects.open(project_path)
        app = proj.find("Application", True)[0]
        f.write("app methods: " + str(dir(app)) + "\n")
        f.write("create_pou doc: " + str(getattr(app, "create_pou").__doc__) + "\n")
        proj.close()
    except Exception as e:
        f.write("Error: " + str(e) + "\n")
