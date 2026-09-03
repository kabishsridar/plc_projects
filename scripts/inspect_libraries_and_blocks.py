import sys
import os

project_path = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\Rasi_feeds_batching.project"
log_path = r"C:\Users\kabish\.gemini\antigravity-ide\brain\6bb09710-7f3e-4443-b187-ad04e16ca8dc\scratch\libraries_and_pous.txt"

with open(log_path, "w") as f:
    try:
        proj = projects.open(project_path)
        f.write("=== POUS AND OBJECTS ===\n")
        for obj in proj.get_children(True):
            f.write(obj.get_name() + " (" + str(obj.get_type()) + ")\n")
            if hasattr(obj, "textual_declaration"):
                decl = obj.textual_declaration.text
                if "blink" in decl.lower():
                    f.write("  [BLINK in decl]\n")
            if hasattr(obj, "textual_implementation"):
                impl = obj.textual_implementation.text
                if "blink" in impl.lower():
                    f.write("  [BLINK in impl]\n")
                    
        # Check libraries under Application
        app = proj.find("Application", True)[0]
        f.write("\n=== APPLICATION CHILDREN ===\n")
        for c in app.get_children():
            f.write("Child: " + c.get_name() + " (" + str(c.get_type()) + ")\n")
            
        proj.close()
    except Exception as e:
        f.write("Error: " + str(e) + "\n")
