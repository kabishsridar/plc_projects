import sys
import os

project_path = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\rasi_feed_batching_2\Rasi_feeds_batching2.project"
log_path = r"C:\Users\kabish\.gemini\antigravity-ide\brain\6bb09710-7f3e-4443-b187-ad04e16ca8dc\scratch\inspect_proj2.txt"

with open(log_path, "w") as f:
    try:
        proj = projects.open(project_path)
        pous = [c.get_name() for c in proj.get_children(True) if hasattr(c, "textual_declaration") or hasattr(c, "textual_implementation")]
        f.write("POUs in Rasi_feeds_batching2: " + str(pous) + "\n")
        for obj in proj.get_children(True):
            name = obj.get_name()
            if hasattr(obj, "textual_declaration"):
                decl = obj.textual_declaration.text
                if "modrtumast" in decl.lower() or "modbus" in decl.lower() or "blink" in decl.lower():
                    f.write("\nPOU with modbus/blink: " + name + "\n")
                    f.write("DECLARATION:\n" + decl + "\n")
            if hasattr(obj, "textual_implementation"):
                impl = obj.textual_implementation.text
                if "modrtumast" in impl.lower() or "modbus" in impl.lower() or "blink" in impl.lower():
                    f.write("\nPOU impl with modbus/blink: " + name + "\n")
                    f.write("IMPLEMENTATION:\n" + impl + "\n")
        proj.close()
    except Exception as e:
        f.write("Error: " + str(e) + "\n")
