import sys
import os

project_path = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\Rasi_feeds_batching.project"
log_path = r"C:\Users\kabish\.gemini\antigravity-ide\brain\6bb09710-7f3e-4443-b187-ad04e16ca8dc\scratch\find_blink.txt"

with open(log_path, "w") as f:
    try:
        proj = projects.open(project_path)
        for obj in proj.get_children(True):
            if hasattr(obj, "textual_declaration"):
                decl = obj.textual_declaration.text
                impl = obj.textual_implementation.text if hasattr(obj, "textual_implementation") else ""
                name = obj.get_name()
                if "blink" in decl.lower() or "blink" in impl.lower():
                    f.write("Found BLINK in POU: " + name + "\n")
                    f.write("--- DECLARATION ---\n" + decl + "\n")
                    f.write("--- IMPLEMENTATION ---\n" + impl + "\n")
                if "load_cell" in decl.lower() or "load_cell" in impl.lower():
                    f.write("Found load_cell in: " + name + "\n")
        proj.close()
    except Exception as e:
        f.write("Error: " + str(e) + "\n")
