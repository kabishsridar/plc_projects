import sys
import os

project_path = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\Rasi_feeds_batching.project"
log_path = r"C:\Users\kabish\.gemini\antigravity-ide\brain\6bb09710-7f3e-4443-b187-ad04e16ca8dc\scratch\test_nwl.txt"

with open(log_path, "w") as f:
    try:
        import System
        from System import Guid
        proj = projects.open(project_path)
        app = proj.find("Application", True)[0]
        
        # Look for Guid on NWLPOUImplementationObjectProvider
        for assem in System.AppDomain.CurrentDomain.GetAssemblies():
            if "NWL" in assem.FullName:
                for t in assem.GetTypes():
                    if "Provider" in t.Name or "Factory" in t.Name or "Object" in t.Name:
                        f.write("Type: " + t.FullName + "\n")
                        for attr in t.GetCustomAttributes(True):
                            f.write("  Attr: " + attr.GetType().Name + " = " + str(attr) + "\n")
                            if hasattr(attr, "Value"):
                                f.write("    Value: " + str(attr.Value) + "\n")
                            if hasattr(attr, "Guid"):
                                f.write("    Guid: " + str(attr.Guid) + "\n")
                                
        proj.close()
    except Exception as e:
        f.write("Error: " + str(e) + "\n")
