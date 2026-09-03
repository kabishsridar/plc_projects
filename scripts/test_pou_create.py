import sys
import os

project_path = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\Rasi_feeds_batching.project"
log_path = r"C:\Users\kabish\.gemini\antigravity-ide\brain\6bb09710-7f3e-4443-b187-ad04e16ca8dc\scratch\test_pou_create.txt"

with open(log_path, "w") as f:
    try:
        import System
        from System import Guid
        
        proj = projects.open(project_path)
        app = proj.find("Application", True)[0]
        
        # Test creating with different known CODESYS language GUIDs
        # FBD: f1e03a9d-5226-4b89-a2b1-6a2e9b8915b8
        # LD: 670da4f5-a45e-4216-9179-69da7c57f61c
        # CFC: 7da02f85-24f4-4221-a49f-142918ca3810
        # SFC: 290151f8-08d4-469b-bc25-2efc0ea03a07
        
        guids_to_test = [
            ("FBD_1", "f1e03a9d-5226-4b89-a2b1-6a2e9b8915b8"),
            ("LD_1", "670da4f5-a45e-4216-9179-69da7c57f61c"),
            ("CFC_1", "7da02f85-24f4-4221-a49f-142918ca3810"),
            ("SFC_1", "290151f8-08d4-469b-bc25-2efc0ea03a07"),
            ("FBD_2", "b04fe134-7283-4b01-bf87-73799881dd49"),
            ("FBD_3", "738bea1e-99bb-4f04-90bb-a7a567e74e3a"),
        ]
        
        for name, g_str in guids_to_test:
            try:
                g = Guid(g_str)
                p = app.create_pou("test_" + name, PouType.Program, g)
                f.write("Successfully created " + name + " with guid " + g_str + " -> type: " + str(p.type) + "\n")
                p.remove()
            except Exception as ex:
                f.write("Failed " + name + " (" + g_str + "): " + str(ex) + "\n")
                
        proj.close()
    except Exception as e:
        f.write("Outer error: " + str(e) + "\n")
