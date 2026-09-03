import sys
import os

project_path = r"D:\Git_repos\plc_projects\project1\Project1.project"
log_path = r"C:\Users\kabish\inspect_output.txt"

with open(log_path, "w") as f:
    f.write("Starting inspect script...\n")
    try:
        f.write("Opening project as read-only...\n")
        proj = projects.open(project_path, allow_readonly=True)
        f.write("Project opened successfully.\n")
        
        found = False
        # Let's iterate all objects in the project
        for child in proj.get_children(True):
            name = child.get_name()
            # If child has textual implementation or declaration, let's check it
            has_decl = getattr(child, "has_textual_declaration", False)
            has_impl = getattr(child, "has_textual_implementation", False)
            
            if name.lower() == "batching1" or "batching" in name.lower():
                found = True
                f.write("Found batching1 or similar: " + name + "\n")
                f.write("Type: " + str(child.type) + "\n")
                if has_decl:
                    f.write("--- DECLARATION ---\n")
                    f.write(child.textual_declaration.text + "\n")
                if has_impl:
                    f.write("--- IMPLEMENTATION ---\n")
                    f.write(child.textual_implementation.text + "\n")
                    
        if not found:
            f.write("batching1 not found specifically. Listing all textual objects:\n")
            for child in proj.get_children(True):
                has_decl = getattr(child, "has_textual_declaration", False)
                has_impl = getattr(child, "has_textual_implementation", False)
                if has_decl or has_impl:
                    f.write("- " + child.get_name() + " (Type: " + str(child.type) + ")\n")
                    
        proj.close()
        f.write("Done.\n")
    except Exception as e:
        f.write("Error: " + str(e) + "\n")
