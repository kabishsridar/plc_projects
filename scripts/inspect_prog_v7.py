import sys
import os

project_path = r"D:\Git_repos\plc_projects\project1\Project1.project"
output_file = r"C:\Users\kabish\inspect_output.txt"

with open(output_file, "w") as f:
    f.write("Opening project...\n")
    try:
        proj = projects.open(project_path)
        f.write("Project opened successfully.\n")
        
        # Let's find batching7
        prog_v7 = None
        for child in proj.get_children(True):
            if child.get_name().lower() == "batching7":
                prog_v7 = child
                break
                
        if prog_v7:
            f.write("Found batching7.\n")
            f.write("--- DECLARATION ---\n")
            f.write(prog_v7.textual_declaration.text)
            f.write("\n--- IMPLEMENTATION ---\n")
            f.write(prog_v7.textual_implementation.text)
        else:
            f.write("batching7 not found.\n")
            
        proj.close()
    except Exception as e:
        f.write("Error: " + str(e) + "\n")
