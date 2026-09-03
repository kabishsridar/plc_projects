import sys
import os

project_path = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\Rasi_feeds_batching.project"
log_path = r"C:\Users\kabish\.gemini\antigravity-ide\brain\6bb09710-7f3e-4443-b187-ad04e16ca8dc\scratch\inspect_pous.txt"

with open(log_path, "w") as f:
    try:
        proj = projects.open(project_path)
        for child in proj.get_children(True):
            f.write("Node: {0}, Type: {1}, Guid: {2}\n".format(child.get_name(), str(child.type), str(child.guid)))
            if hasattr(child, "has_textual_implementation"):
                f.write("  has_textual_implementation: {0}\n".format(str(child.has_textual_implementation)))
        proj.close()
    except Exception as e:
        f.write("Error: {0}\n".format(str(e)))
