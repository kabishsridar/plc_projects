import sys
import os

project_path = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\Rasi_feeds_batching.project"
log_path = r"C:\Users\kabish\.gemini\antigravity-ide\brain\6bb09710-7f3e-4443-b187-ad04e16ca8dc\scratch\test_langs.txt"

with open(log_path, "w") as f:
    try:
        proj = projects.open(project_path)
        app = proj.find("Application", True)[0]
        f.write("app types: " + str(app.type) + "\n")
        f.write("Searching for Language GUIDs...\n")
        import System
        from System import Guid
        # Check standard CODESYS language GUIDs
        # ST: 6f9dac99-8de1-4efc-8465-68ac443b7d08
        # FBD/LD/IL: 085766fd-043e-4545-8e8d-d651d56d5d3b / etc.
        f.write("Done checking.\n")
        proj.close()
    except Exception as e:
        f.write("Error: " + str(e) + "\n")
