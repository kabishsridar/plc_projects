import sys
import os

project_path = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\Rasi_feeds_batching.project"
log_path = r"C:\Users\kabish\.gemini\antigravity-ide\brain\6bb09710-7f3e-4443-b187-ad04e16ca8dc\scratch\check_libs.txt"

with open(log_path, "w") as f:
    try:
        proj = projects.open(project_path)
        libs = proj.find("Library Manager", True)
        if len(libs) == 0:
            libs = proj.find("LibraryManager", True)
        f.write("Found libs: " + str(len(libs)) + "\n")
        for lib in libs:
            f.write("Lib Manager: " + lib.get_name() + "\n")
            for c in lib.get_children():
                f.write("  Child: " + c.get_name() + "\n")
        pous = [c.get_name() for c in proj.get_children(True) if hasattr(c, "textual_declaration")]
        f.write("POUs in project: " + str(pous) + "\n")
        proj.close()
    except Exception as e:
        f.write("Error: " + str(e) + "\n")
