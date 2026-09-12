import sys
import os

project_path = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\Rasi_feeds_batching.project"
log_path = r"C:\Users\kabish\.gemini\antigravity-ide\brain\6bb09710-7f3e-4443-b187-ad04e16ca8dc\scratch\update_step_plus_6.txt"

with open(log_path, "w") as f:
    f.write("Opening project...\n")
    try:
        proj = projects.open(project_path)
        f.write("Project opened successfully.\n")
        
        for child in proj.get_children(True):
            name = child.get_name().lower()
            if "semi_auto" in name or "manual" in name:
                f.write("Checking " + child.get_name() + "...\n")
                if hasattr(child, "textual_implementation"):
                    decl_obj = child.textual_implementation
                    impl = decl_obj.text
                    if "Step + 6" in impl or "(Step - 20) + 6" in impl or "Step+6" in impl:
                        f.write("Found Step + 6 in " + child.get_name() + ", replacing...\n")
                        impl = impl.replace("Step + 6", "Step")
                        impl = impl.replace("Step+6", "Step")
                        impl = impl.replace("(Step - 20) + 6", "Step - 20")
                        decl_obj.replace(impl)
                        f.write("Replaced in " + child.get_name() + ".\n")
                    else:
                        f.write("No Step + 6 found in " + child.get_name() + " (already clean).\n")
                        
        proj.save()
        proj.close()
        f.write("Project saved and closed.\n")
    except Exception as e:
        f.write("Error: " + str(e) + "\n")
