import sys
import os

project_path = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\Rasi_feeds_batching.project"
log_path = r"C:\Users\kabish\.gemini\antigravity-ide\brain\6bb09710-7f3e-4443-b187-ad04e16ca8dc\scratch\inspect_gvl.txt"

with open(log_path, "w") as f:
    try:
        proj = projects.open(project_path)
        gvl_node = None
        for child in proj.get_children(True):
            if child.get_name().lower() == "gvl":
                gvl_node = child
                break
        if gvl_node:
            f.write("Found GVL node.\n")
            decl = gvl_node.textual_declaration
            f.write("Has text property: " + str(hasattr(decl, 'text')) + "\n")
            if hasattr(decl, 'text'):
                f.write("Text value:\n" + str(decl.text) + "\n")
            
            # Let's inspect methods
            f.write("Dir of decl:\n" + "\\n".join(dir(decl)) + "\n")
        else:
            f.write("GVL node not found.\n")
        proj.close()
    except Exception as e:
        f.write("Error: " + str(e) + "\n")
