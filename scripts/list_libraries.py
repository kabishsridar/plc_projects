import sys
import os

project_path = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\Rasi_feeds_batching.project"
log_path = r"C:\Users\kabish\.gemini\antigravity-ide\brain\6bb09710-7f3e-4443-b187-ad04e16ca8dc\scratch\list_libraries.txt"

with open(log_path, "w") as f:
    try:
        proj = projects.open(project_path)
        app = proj.find("Application", True)[0]
        for obj in app.get_children():
            if "library" in obj.get_name().lower():
                f.write("Library manager obj: " + obj.get_name() + "\n")
                for m in obj.GetType().GetMembers():
                    f.write("  Member: " + m.Name + "\n")
        proj.close()
    except Exception as e:
        f.write("Error: " + str(e) + "\n")
