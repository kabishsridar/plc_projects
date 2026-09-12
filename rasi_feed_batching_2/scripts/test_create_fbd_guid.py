import sys
import os

project_path = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\Rasi_feeds_batching.project"
log_path = r"C:\Users\kabish\.gemini\antigravity-ide\brain\6bb09710-7f3e-4443-b187-ad04e16ca8dc\scratch\test_create_fbd_guid.txt"

with open(log_path, "w") as f:
    try:
        import System
        from System import Guid
        proj = projects.open(project_path)
        app = proj.find("Application", True)[0]
        
        # Test creating FBD POU with NWL Factory Guid
        fbd_guid = Guid("c2e2244b-c806-41b4-8ad3-7a0e25ce1393")
        fbd_pou = app.create_pou("test_fbd_pou", PouType.Program, fbd_guid)
        f.write("Successfully created FBD POU! Name: " + fbd_pou.get_name() + ", type: " + str(fbd_pou.type) + "\n")
        fbd_pou.remove()
        
        proj.save()
        proj.close()
        f.write("Done!\n")
    except Exception as e:
        f.write("Error: " + str(e) + "\n")
