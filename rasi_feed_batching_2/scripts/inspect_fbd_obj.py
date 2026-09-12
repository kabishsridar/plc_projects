import sys
import os

project_path = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\Rasi_feeds_batching.project"
log_path = r"C:\Users\kabish\.gemini\antigravity-ide\brain\6bb09710-7f3e-4443-b187-ad04e16ca8dc\scratch\inspect_fbd_obj.txt"

with open(log_path, "w") as f:
    try:
        import System
        from System import Guid
        proj = projects.open(project_path)
        app = proj.find("Application", True)[0]
        
        fbd_guid = Guid("c2e2244b-c806-41b4-8ad3-7a0e25ce1393")
        fbd_pou = app.create_pou("test_fbd_pou", PouType.Program, fbd_guid)
        
        f.write("fbd_pou members: " + str(dir(fbd_pou)) + "\n")
        f.write("has_textual_declaration: " + str(getattr(fbd_pou, "has_textual_declaration", False)) + "\n")
        f.write("has_textual_implementation: " + str(getattr(fbd_pou, "has_textual_implementation", False)) + "\n")
        
        # Test exporting the empty FBD POU to see its exact PLCopen XML structure
        exp_path = r"C:\Users\kabish\.gemini\antigravity-ide\brain\6bb09710-7f3e-4443-b187-ad04e16ca8dc\scratch\empty_fbd.xml"
        fbd_pou.export_xml(exp_path, False, False, False)
        f.write("Exported empty FBD POU to " + exp_path + "\n")
        
        fbd_pou.remove()
        proj.save()
        proj.close()
    except Exception as e:
        f.write("Error: " + str(e) + "\n")
