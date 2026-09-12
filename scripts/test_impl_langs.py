import sys
import os

project_path = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\Rasi_feeds_batching.project"
log_path = r"C:\Users\kabish\.gemini\antigravity-ide\brain\6bb09710-7f3e-4443-b187-ad04e16ca8dc\scratch\test_impl_langs.txt"

with open(log_path, "w") as f:
    try:
        import clr
        from _3S.CoDeSys.ScriptEngine.BasicFunctionality import IScriptImplementationLanguages
        from _3S.CoDeSys.ScriptDriverProjects import ScriptImplementationLanguages
        
        f.write("ScriptImplementationLanguages members: " + str(dir(ScriptImplementationLanguages)) + "\n")
        
        proj = projects.open(project_path)
        app = proj.find("Application", True)[0]
        
        # Test creating POU with FBD language
        # Let's inspect properties on app or ScriptImplementationLanguages
        for p in dir(ScriptImplementationLanguages):
            if not p.startswith("_"):
                val = getattr(ScriptImplementationLanguages, p)
                f.write("  " + p + ": " + str(val) + "\n")
                
        proj.close()
    except Exception as e:
        f.write("Error: " + str(e) + "\n")
