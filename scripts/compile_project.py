import sys
import os

project_path = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\Rasi_feeds_batching.project"
log_path = r"C:\Users\kabish\modify_output.txt"

with open(log_path, "w") as f:
    f.write("Starting compile check script...\n")
    try:
        f.write("Opening project...\n")
        proj = projects.open(project_path)
        f.write("Project opened successfully. Compiling...\n")
        
        app = None
        for child in proj.get_children(True):
            if child.is_device:
                for dev_child in child.get_children(True):
                    if dev_child.get_name().lower() == "application":
                        app = dev_child
                        break
            if app:
                break
                
        if app:
            f.write("Found Application: " + app.get_name() + "\n")
            # Build application
            app.build()
            f.write("Build completed successfully.\n")
        else:
            f.write("Application node not found.\n")
            
        proj.close()
        f.write("Project closed.\n")
    except Exception as e:
        f.write("Error: " + str(e) + "\n")
