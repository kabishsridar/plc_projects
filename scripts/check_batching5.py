import sys
import os

project_path = r"D:\Git_repos\plc_projects\project1\Project1.project"
log_path = r"C:\Users\kabish\.gemini\antigravity-ide\brain\6bb09710-7f3e-4443-b187-ad04e16ca8dc\scratch\inspect_batching5.txt"

with open(log_path, "w") as f:
    try:
        proj = projects.open(project_path)
        plc_prg_node = None
        for child in proj.get_children(True):
            if child.get_name().lower() == "plc_prg":
                plc_prg_node = child
                break
        
        if plc_prg_node:
            parent = plc_prg_node.parent
            batching5_node = None
            for child in parent.get_children(False):
                if child.get_name().lower() == "batching5":
                    batching5_node = child
                    break
            
            if batching5_node:
                f.write("batching5 POU found.\\n")
                f.write("Declaration:\\n")
                f.write(batching5_node.textual_declaration.text)
                f.write("\\nImplementation:\\n")
                f.write(batching5_node.textual_implementation.text)
            else:
                f.write("batching5 POU not found.\\n")
        else:
            f.write("PLC_PRG POU not found.\\n")
        proj.close()
    except Exception as e:
        f.write("Error: " + str(e) + "\\n")
