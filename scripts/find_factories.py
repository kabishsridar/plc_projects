import sys
import os

project_path = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\Rasi_feeds_batching.project"
log_path = r"C:\Users\kabish\.gemini\antigravity-ide\brain\6bb09710-7f3e-4443-b187-ad04e16ca8dc\scratch\find_factories.txt"

with open(log_path, "w") as f:
    try:
        import System
        from System import Guid
        proj = projects.open(project_path)
        app = proj.find("Application", True)[0]
        
        # Let's inspect System.AppDomain to find IImplementationObjectFactory implementations
        for assem in System.AppDomain.CurrentDomain.GetAssemblies():
            try:
                for t in assem.GetTypes():
                    for iface in t.GetInterfaces():
                        if "IImplementationObjectFactory" in iface.Name or "Implementation" in iface.Name:
                            f.write("Class: " + t.FullName + " from " + assem.GetName().Name + "\n")
                            # Check attributes on class for GUID
                            attrs = t.GetCustomAttributes(True)
                            for attr in attrs:
                                if "Guid" in attr.GetType().Name:
                                    f.write("  GuidAttr: " + str(attr.Value) + "\n")
            except Exception as e_inner:
                pass
                
        proj.close()
    except Exception as e:
        f.write("Error: " + str(e) + "\n")
