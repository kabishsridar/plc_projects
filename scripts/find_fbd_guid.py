import sys
import os

project_path = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\Rasi_feeds_batching.project"
log_path = r"C:\Users\kabish\.gemini\antigravity-ide\brain\6bb09710-7f3e-4443-b187-ad04e16ca8dc\scratch\find_fbd_guid.txt"

with open(log_path, "w") as f:
    try:
        import clr
        import System
        from System import Guid
        
        proj = projects.open(project_path)
        app = proj.find("Application", True)[0]
        
        # Test creating POU with different language GUIDs
        # Common CODESYS language GUIDs:
        # IL:   {225bfe47-7336-4dbc-9419-4105a7c831fa} / {6f9dac99-8de1-4efc-8465-68ac443b7d08}
        # ST:   {6f9dac99-8de1-4efc-8465-68ac443b7d08}
        # FBD:  {f1e03a9d-5226-4b89-a2b1-6a2e9b8915b8} or {adb5cb65-8e1d-4a00-b70a-375ea27582f3} or {b04fe134-7283-4b01-bf87-73799881dd49}
        # LD:   {670da4f5-a45e-4216-9179-69da7c57f61c}
        # CFC:  {7da02f85-24f4-4221-a49f-142918ca3810}
        
        # Let's inspect the types of language objects in system assemblies
        for assem in System.AppDomain.CurrentDomain.GetAssemblies():
            if "Language" in assem.FullName or "Fbd" in assem.FullName or "Script" in assem.FullName:
                f.write("Assembly: " + assem.FullName + "\n")
                for t in assem.GetTypes():
                    if "Language" in t.Name or "Fbd" in t.Name or "Pou" in t.Name:
                        f.write("  Type: " + t.FullName + "\n")
        
        proj.close()
    except Exception as e:
        f.write("Error: " + str(e) + "\n")
