# IronPython Automation Engine Guide & Cheat Sheet

**Target Platform:** ABB Automation Builder 2.7+ / CODESYS V3 Automation Platform  
**Scope:** Headless CLI Automation, Code Generation, Batch Compilation, Project Migration & Verification

---

## 1. Overview & Architecture

The **IronPython Automation Engine** embeds a .NET-based Python runtime directly inside ABB Automation Builder. It exposes the complete internal Object Model of the PLC development environment, enabling you to automate:
* **Batch Compilation & Static Code Analysis** without opening the graphical UI.
* **Bi-Directional Code Synchronization** between VS Code / text editors (`.st`, `.xml`) and the binary `.project` container.
* **Automated POU, GVL, DUT & Task Creation**.
* **PLC Simulation & Online Deployment Pipelines (CI/CD)**.

```
┌─────────────────────────────────────────────────────────────┐
│             Automation Builder IronPython Engine            │
├─────────────────┬─────────────────┬─────────────────────────┤
│    projects     │     system      │         online          │
│ (Project & POUs)│ (IDE & Messages)│ (PLC Comm & Live State) │
├─────────────────┴─────────────────┴─────────────────────────┤
│            Device Tree / Task Configuration / GVL           │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Global Script Objects Injected at Runtime

When Automation Builder executes a script with `--runscript=<path.py>`, it automatically provides top-level global objects:

| Object | Methods / Properties | Purpose |
| :--- | :--- | :--- |
| **`projects`** | `projects.open(path)`<br>`projects.create(path)`<br>`projects.primary` | Master project manager for creating, opening, saving, archiving, and closing `.project` files. |
| **`system`** | `system.write_message(sev, text)`<br>`system.prompt(title, msg)` | IDE environment, diagnostics, and build message logging. |
| **`online`** | `online.create_online_application(app)` | Direct communication with simulated or physical PLCs (Login, Download, Start, Stop, Variable Read/Write). |

---

## 3. Headless CLI Invocation Syntax

Run scripts directly from **PowerShell**, **Windows Terminal**, or **VS Code Tasks**:

```powershell
# Standard Headless CLI Execution (No GUI)
& "C:\Program Files\ABB\AB2.7\AutomationBuilder\Common\AutomationBuilder.exe" `
    --profile="Automation Builder 2.7" `
    --noUI `
    --runscript="D:\Git_repos\plc_projects\Rasi_feeds_batching\scripts\my_script.py"
```

> [!IMPORTANT]
> **File Lock Rule**: Always ensure the `.project` file is closed in the Automation Builder desktop GUI before executing a headless script. The project file cannot be opened concurrently in write mode.

---

## 4. Production Automation Recipes

### Recipe 1: Project Tree Inspection & Bulk POU Discovery

Traverses all nodes in the project device tree to discover code blocks, GVLs, tasks, and hardware devices.

```python
# scripts/inspect_project.py
import sys

PROJECT_PATH = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\rasi_feed_batching_2\Rasi_feeds_batching2.project"

def inspect():
    proj = projects.open(PROJECT_PATH)
    print("=" * 60)
    print("PROJECT TREE: " + proj.get_name())
    print("=" * 60)
    
    for obj in proj.get_children(True):
        obj_name = obj.get_name()
        obj_type = str(obj.type)
        is_pou = hasattr(obj, "textual_implementation") or hasattr(obj, "textual_declaration")
        flag = "[POU/Code]" if is_pou else "[Tree Node]"
        print("{:<12} {:<30} (Type: {})".format(flag, obj_name, obj_type))
        
    proj.close()

if __name__ == "__main__":
    inspect()
```

---

### Recipe 2: Creating & Updating POUs and GVLs Programmatically

Creates or modifies a Global Variable List (GVL) and a Structured Text Function Block.

```python
# scripts/create_and_edit_pous.py
import sys

PROJECT_PATH = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\rasi_feed_batching_2\Rasi_feeds_batching2.project"

def setup_pous():
    proj = projects.open(PROJECT_PATH)
    app = proj.find("Application", True)[0]
    
    # 1. Create or Update GVL
    gvl_objs = proj.find("GVL_Sensors", True)
    gvl = gvl_objs[0] if gvl_objs else app.create_gvl("GVL_Sensors")
    gvl_code = "{attribute 'qualified_only'}\nVAR_GLOBAL\n    Scale_1_Live_Weight AT %MD500 : REAL;\n    Scale_2_Live_Weight AT %MD504 : REAL;\n    System_Healthy      AT %MX50.0: BOOL := TRUE;\nEND_VAR\n"
    gvl.textual_declaration.replace(gvl_code)
    print("GVL_Sensors updated.")

    # 2. Create or Update Function Block
    fb_objs = proj.find("FB_Moving_Average", True)
    fb = fb_objs[0] if fb_objs else app.create_pou("FB_Moving_Average", PouType.FunctionBlock)

    fb_decl = "FUNCTION_BLOCK FB_Moving_Average\nVAR_INPUT\n    Raw_Input : REAL;\n    Filter_Factor : REAL := 0.1; // Low-Pass Filter\nEND_VAR\nVAR_OUTPUT\n    Filtered_Output : REAL;\nEND_VAR\n"
    fb_impl = "IF Filtered_Output = 0.0 THEN\n    Filtered_Output := Raw_Input;\nELSE\n    Filtered_Output := (Filter_Factor * Raw_Input) + ((1.0 - Filter_Factor) * Filtered_Output);\nEND_IF;\n"
    
    fb.textual_declaration.replace(fb_decl)
    fb.textual_implementation.replace(fb_impl)
    print("FB_Moving_Average updated.")

    proj.save()
    proj.close()
    print("Project saved successfully.")

if __name__ == "__main__":
    setup_pous()
```

---

### Recipe 3: Two-Way Synchronization (VS Code Files $\leftrightarrow$ PLC `.project`)

Syncs all external `.st` text files and `.xml` PLCopen files directly into the compiled `.project` binary.

```python
# scripts/sync_ide_to_project.py
import sys
import os

PROJECT_PATH = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\rasi_feed_batching_2\Rasi_feeds_batching2.project"
SOURCE_DIR   = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\St_Codes"

def sync():
    proj = projects.open(PROJECT_PATH)
    app = proj.find("Application", True)[0]
    
    pous_to_sync = [
        "Auto_Batching_V14",
        "Semi_Auto_Batching_V14",
        "FB_Samyak_Multi",
        "FB_Samyak_Control"
    ]
    
    for pou_name in pous_to_sync:
        st_file = os.path.join(SOURCE_DIR, pou_name + ".st")
        if os.path.exists(st_file):
            with open(st_file, "r") as f:
                content = f.read()
            pou_obj = proj.find(pou_name, True)
            if pou_obj:
                pou_obj[0].textual_implementation.replace(content)
                print("[SYNCED] " + pou_name + " from " + st_file)
                
    fbd_xml = os.path.join(SOURCE_DIR, "batching14_fbd.xml")
    if os.path.exists(fbd_xml):
        for b in proj.find("batching14", True):
            b.remove()
        app.import_xml(fbd_xml)
        print("[SYNCED] batching14 (FBD) from XML")

    proj.save()
    proj.close()
    print("Sync complete.")

if __name__ == "__main__":
    sync()
```

---

### Recipe 4: Automated Build & Static Analysis Validation

Executes typify and build checks, reporting errors with severity levels and returning exit codes for CI/CD pipelines.

```python
# scripts/build_and_validate.py
import sys

PROJECT_PATH = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\rasi_feed_batching_2\Rasi_feeds_batching2.project"

def build():
    proj = projects.open(PROJECT_PATH)
    app = proj.find("Application", True)[0]
    
    print("Compiling Application: " + app.get_name() + "...")
    messages = app.build()
    
    error_count = 0
    warning_count = 0
    
    if messages:
        for msg in messages:
            sev = str(msg.Severity)
            text = str(msg.Text)
            if sev == "Error" or "error" in sev.lower():
                error_count += 1
                print(" [ERROR] " + text)
            elif sev == "Warning" or "warning" in sev.lower():
                warning_count += 1
                print(" [WARNING] " + text)

    print("-" * 50)
    print("Build Result: {} Errors, {} Warnings".format(error_count, warning_count))
    print("-" * 50)
    
    proj.close()
    if error_count > 0:
        sys.exit(1)

if __name__ == "__main__":
    build()
```

---

### Recipe 5: Online Deployment & Live Variable Inspection

Connects to physical or simulated AC500 PLCs, downloads the boot project, starts execution, and reads live GVL memory.

```python
# scripts/online_deploy.py
import sys

PROJECT_PATH = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\rasi_feed_batching_2\Rasi_feeds_batching2.project"

def deploy():
    proj = projects.open(PROJECT_PATH)
    app = proj.find("Application", True)[0]
    
    online_app = online.create_online_application(app)
    print("Connecting / Logging in to PLC...")
    online_app.login(OnlineChangeOption.Try, False)
    
    if online_app.is_logged_in:
        print("Logged in. Application State: " + str(online_app.application_state))
        print("Starting PLC...")
        online_app.start()
        
        val = online_app.read_value("GVL.Auto_Current_Step")
        print("Live GVL.Auto_Current_Step = " + str(val))
        
        online_app.logout()
        print("Logged out.")
    else:
        print("Failed to login to target.")

    proj.close()

if __name__ == "__main__":
    deploy()
```

---

## 5. VS Code One-Click Task Integration

Add this file to `.vscode/tasks.json` in your project to enable 1-click build (`Ctrl+Shift+B`) and export:

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "ABB: Compile & Build Project",
      "type": "shell",
      "command": "& 'C:\\Program Files\\ABB\\AB2.7\\AutomationBuilder\\Common\\AutomationBuilder.exe' --profile='Automation Builder 2.7' --noUI --runscript='${workspaceFolder}\\scripts\\build_and_validate.py'",
      "group": {
        "kind": "build",
        "isDefault": true
      },
      "problemMatcher": []
    },
    {
      "label": "ABB: Export All POUs to ST/XML",
      "type": "shell",
      "command": "& 'C:\\Program Files\\ABB\\AB2.7\\AutomationBuilder\\Common\\AutomationBuilder.exe' --profile='Automation Builder 2.7' --noUI --runscript='${workspaceFolder}\\scripts\\dump_all_to_st_codes.py'",
      "problemMatcher": []
    },
    {
      "label": "ABB: Sync IDE Code into .project",
      "type": "shell",
      "command": "& 'C:\\Program Files\\ABB\\AB2.7\\AutomationBuilder\\Common\\AutomationBuilder.exe' --profile='Automation Builder 2.7' --noUI --runscript='${workspaceFolder}\\scripts\\sync_ide_to_project.py'",
      "problemMatcher": []
    }
  ]
}
```

---

## 6. IronPython Quick Reference API Cheat Sheet

| Action | Python API Call |
| :--- | :--- |
| **Open Project** | `proj = projects.open(r"C:\path\to\proj.project")` |
| **Save Project** | `proj.save()` |
| **Save As** | `proj.save_as(r"C:\path\to\new_proj.project")` |
| **Close Project** | `proj.close()` |
| **Find Object by Name** | `items = proj.find("POU_Name", recursive=True)` |
| **Find Application** | `app = proj.find("Application", True)[0]` |
| **Create POU (Program)** | `pou = app.create_pou("MainProg", PouType.Program)` |
| **Create POU (Function Block)** | `fb = app.create_pou("MyFB", PouType.FunctionBlock)` |
| **Create POU (Function)** | `fn = app.create_pou("MyFunc", PouType.Function, "REAL")` |
| **Create GVL** | `gvl = app.create_gvl("GVL_Name")` |
| **Read ST Declaration** | `decl_text = pou.textual_declaration.text` |
| **Replace ST Declaration** | `pou.textual_declaration.replace("VAR...END_VAR")` |
| **Read ST Body** | `impl_text = pou.textual_implementation.text` |
| **Replace ST Body** | `pou.textual_implementation.replace("Step := 1;...")` |
| **Import PLCopen XML** | `app.import_xml(r"C:\path\to\file.xml")` |
| **Export PLCopen XML** | `pou.export_xml(r"C:\path\to\file.xml")` |
| **Export Project Archive** | `proj.save_archive(r"C:\path\to\archive.projectarchive")` |
| **Compile / Build** | `messages = app.build()` |
| **Clean All** | `app.clean()` |
| **Remove POU** | `pou.remove()` |
