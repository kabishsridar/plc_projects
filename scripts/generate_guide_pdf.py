import os
import subprocess
import shutil

html_content = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>IronPython Automation Engine Guide - ABB Automation Builder & CODESYS V3</title>
<style>
    @page {
        size: A4;
        margin: 18mm 14mm 18mm 14mm;
    }
    body {
        font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, Helvetica, Arial, sans-serif;
        color: #1e293b;
        line-height: 1.55;
        font-size: 10pt;
        background-color: #ffffff;
        margin: 0;
        padding: 0;
    }
    h1 {
        color: #0f172a;
        font-size: 18pt;
        border-bottom: 2px solid #3b82f6;
        padding-bottom: 6px;
        margin-top: 0;
        margin-bottom: 14px;
    }
    h2 {
        color: #1e3a8a;
        font-size: 13pt;
        border-bottom: 1px solid #e2e8f0;
        padding-bottom: 4px;
        margin-top: 20px;
        margin-bottom: 10px;
        page-break-after: avoid;
    }
    h3 {
        color: #2563eb;
        font-size: 11pt;
        margin-top: 16px;
        margin-bottom: 6px;
        page-break-after: avoid;
    }
    p {
        margin: 0 0 8px 0;
    }
    ul, ol {
        margin: 0 0 10px 0;
        padding-left: 20px;
    }
    li {
        margin-bottom: 3px;
    }
    table {
        width: 100%;
        border-collapse: collapse;
        margin: 12px 0;
        font-size: 9pt;
        page-break-inside: avoid;
    }
    th, td {
        border: 1px solid #cbd5e1;
        padding: 6px 9px;
        text-align: left;
    }
    th {
        background-color: #f1f5f9;
        color: #0f172a;
        font-weight: 600;
    }
    tr:nth-child(even) {
        background-color: #f8fafc;
    }
    code {
        font-family: 'Consolas', 'Courier New', monospace;
        font-size: 8.5pt;
        background-color: #f1f5f9;
        padding: 2px 4px;
        border-radius: 4px;
        color: #0f172a;
        border: 1px solid #e2e8f0;
    }
    pre {
        background-color: #0f172a;
        color: #f8fafc;
        padding: 10px 12px;
        border-radius: 6px;
        font-family: 'Consolas', 'Courier New', monospace;
        font-size: 8pt;
        line-height: 1.4;
        overflow-x: auto;
        margin: 8px 0 12px 0;
        page-break-inside: avoid;
        border: 1px solid #334155;
    }
    pre code {
        background-color: transparent;
        color: inherit;
        padding: 0;
        border: none;
        font-size: inherit;
    }
    .alert {
        background-color: #eff6ff;
        border-left: 4px solid #3b82f6;
        padding: 9px 12px;
        margin: 12px 0;
        border-radius: 0 6px 6px 0;
        font-size: 9pt;
    }
    .alert-title {
        font-weight: bold;
        color: #1d4ed8;
        margin-bottom: 3px;
    }
</style>
</head>
<body>

<h1>IronPython Automation Engine Guide</h1>
<p style="color: #64748b; font-size: 9.5pt; margin-top: -8px; margin-bottom: 16px;">
    <strong>Platform:</strong> ABB Automation Builder 2.7+ / CODESYS V3 Automation Platform &bull; 
    <strong>Reference Manual &amp; Automation Cookbook</strong>
</p>

<div class="alert">
    <div class="alert-title">OVERVIEW</div>
    The <strong>IronPython Automation Engine</strong> embeds a full .NET-based Python runtime directly inside Automation Builder. It exposes the complete internal Object Model of the PLC development environment, enabling headless compilation, bulk code migration, automated verification, and CI/CD pipelines.
</div>

<h2>1. Core Architecture &amp; Global Script Objects</h2>
<p>When Automation Builder executes a script with <code>--runscript=&lt;script.py&gt;</code>, it provides top-level global objects directly in the Python namespace:</p>

<table>
    <tr>
        <th style="width: 22%;">Global Object</th>
        <th style="width: 38%;">Primary Methods &amp; Properties</th>
        <th style="width: 40%;">Description</th>
    </tr>
    <tr>
        <td><code>projects</code></td>
        <td><code>.open(path)</code><br><code>.create(path)</code><br><code>.primary</code></td>
        <td>Master project controller. Manages opening, creating, saving, archiving, and closing <code>.project</code> files.</td>
    </tr>
    <tr>
        <td><code>system</code></td>
        <td><code>.write_message(sev, text)</code><br><code>.prompt(title, msg)</code></td>
        <td>IDE system environment, error logging, and diagnostic message dispatching.</td>
    </tr>
    <tr>
        <td><code>online</code></td>
        <td><code>.create_online_application(app)</code></td>
        <td>Manages direct communication with physical or simulated PLCs (Login, Start, Stop, Read/Write Variables).</td>
    </tr>
</table>

<h2>2. Headless CLI Invocation Syntax</h2>
<p>Execute scripts from PowerShell, Windows Terminal, or VS Code tasks:</p>
<pre><code># Standard Headless CLI Execution (No GUI)
&amp; "C:\Program Files\ABB\AB2.7\AutomationBuilder\Common\AutomationBuilder.exe" `
    --profile="Automation Builder 2.7" `
    --noUI `
    --runscript="D:\Git_repos\plc_projects\scripts\my_script.py"</code></pre>

<div class="alert">
    <div class="alert-title">IMPORTANT: FILE LOCK RULE</div>
    Always close the <code>.project</code> in the desktop Automation Builder GUI before running headless scripts. Two processes cannot open the same project simultaneously in write mode.
</div>

<h2>3. Production Automation Modules</h2>

<h3>Module 1: Project Inspection &amp; Bulk POU Discovery</h3>
<p>Recursively traverses all nodes in the project device tree to discover code blocks, GVLs, and configuration nodes.</p>
<pre><code># inspect_project.py
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
        print("{:&lt;12} {:&lt;30} (Type: {})".format(flag, obj_name, obj_type))
        
    proj.close()

if __name__ == "__main__":
    inspect()</code></pre>

<h3>Module 2: Programmatically Creating &amp; Updating POUs (ST)</h3>
<p>Creates a Global Variable List (GVL) and a Structured Text Function Block with custom logic.</p>
<pre><code># create_and_edit_pous.py
import sys

PROJECT_PATH = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\rasi_feed_batching_2\Rasi_feeds_batching2.project"

def setup_pous():
    proj = projects.open(PROJECT_PATH)
    app = proj.find("Application", True)[0]
    
    # 1. Create/Update GVL
    gvl_objs = proj.find("GVL_Sensors", True)
    gvl = gvl_objs[0] if gvl_objs else app.create_gvl("GVL_Sensors")
    gvl.textual_declaration.replace("""{attribute 'qualified_only'}
VAR_GLOBAL
    Scale_1_Live_Weight AT %MD500 : REAL;
    Scale_2_Live_Weight AT %MD504 : REAL;
    System_Healthy      AT %MX50.0: BOOL := TRUE;
END_VAR
""")
    print("GVL_Sensors updated.")

    # 2. Create/Update Function Block
    fb_objs = proj.find("FB_Moving_Average", True)
    fb = fb_objs[0] if fb_objs else app.create_pou("FB_Moving_Average", PouType.FunctionBlock)

    fb_decl = """FUNCTION_BLOCK FB_Moving_Average
VAR_INPUT
    Raw_Input : REAL;
    Filter_Factor : REAL := 0.1; // Low-Pass Filter
END_VAR
VAR_OUTPUT
    Filtered_Output : REAL;
END_VAR
"""
    fb_impl = """IF Filtered_Output = 0.0 THEN
    Filtered_Output := Raw_Input;
ELSE
    Filtered_Output := (Filter_Factor * Raw_Input) + ((1.0 - Filter_Factor) * Filtered_Output);
END_IF;
"""
    fb.textual_declaration.replace(fb_decl)
    fb.textual_implementation.replace(fb_impl)
    print("FB_Moving_Average updated.")

    proj.save()
    proj.close()
    print("Project saved successfully.")

if __name__ == "__main__":
    setup_pous()</code></pre>

<h3>Module 3: Two-Way Synchronization (IDE Files &harr; PLC Project)</h3>
<p>Imports source code files from your VS Code workspace into the compiled <code>.project</code> binary.</p>
<pre><code># sync_ide_to_project.py
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
    sync()</code></pre>

<h3>Module 4: Automated Build &amp; Compiler Error Reporting</h3>
<p>Executes typify and build checks, reporting errors with severity levels and return codes for CI/CD integration.</p>
<pre><code># build_and_validate.py
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
    build()</code></pre>

<h3>Module 5: Online Deployment &amp; Variable Monitoring</h3>
<p>Automates connecting to physical or simulated AC500 PLCs, downloading code, and inspecting live runtime variables.</p>
<pre><code># online_deploy.py
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
    deploy()</code></pre>

<h2>4. VS Code One-Click Task Integration</h2>
<p>Add the following configuration to <code>.vscode/tasks.json</code> in your workspace to trigger automated builds and exports via <code>Ctrl+Shift+B</code>:</p>
<pre><code>{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "ABB: Compile &amp; Build Project",
      "type": "shell",
      "command": "&amp; 'C:\\Program Files\\ABB\\AB2.7\\AutomationBuilder\\Common\\AutomationBuilder.exe' --profile='Automation Builder 2.7' --noUI --runscript='${workspaceFolder}\\scripts\\build_and_validate.py'",
      "group": { "kind": "build", "isDefault": true }
    },
    {
      "label": "ABB: Export All POUs to ST/XML",
      "type": "shell",
      "command": "&amp; 'C:\\Program Files\\ABB\\AB2.7\\AutomationBuilder\\Common\\AutomationBuilder.exe' --profile='Automation Builder 2.7' --noUI --runscript='${workspaceFolder}\\scripts\\dump_all_to_st_codes.py'"
    }
  ]
}</code></pre>

<h2>5. API Quick Reference Cheat Sheet</h2>
<table>
    <tr>
        <th>Operation</th>
        <th>IronPython Script Method</th>
    </tr>
    <tr>
        <td><strong>Open Project</strong></td>
        <td><code>proj = projects.open(r"path.project")</code></td>
    </tr>
    <tr>
        <td><strong>Save Project</strong></td>
        <td><code>proj.save()</code></td>
    </tr>
    <tr>
        <td><strong>Close Project</strong></td>
        <td><code>proj.close()</code></td>
    </tr>
    <tr>
        <td><strong>Find Application</strong></td>
        <td><code>app = proj.find("Application", True)[0]</code></td>
    </tr>
    <tr>
        <td><strong>Find POU</strong></td>
        <td><code>pou = proj.find("POU_Name", True)[0]</code></td>
    </tr>
    <tr>
        <td><strong>Read ST Declaration</strong></td>
        <td><code>text = pou.textual_declaration.text</code></td>
    </tr>
    <tr>
        <td><strong>Replace ST Declaration</strong></td>
        <td><code>pou.textual_declaration.replace("VAR...END_VAR")</code></td>
    </tr>
    <tr>
        <td><strong>Read ST Body</strong></td>
        <td><code>text = pou.textual_implementation.text</code></td>
    </tr>
    <tr>
        <td><strong>Replace ST Body</strong></td>
        <td><code>pou.textual_implementation.replace("Step := 1;...")</code></td>
    </tr>
    <tr>
        <td><strong>Import PLCopen XML</strong></td>
        <td><code>app.import_xml(r"path.xml")</code></td>
    </tr>
    <tr>
        <td><strong>Export PLCopen XML</strong></td>
        <td><code>pou.export_xml(r"path.xml")</code></td>
    </tr>
    <tr>
        <td><strong>Compile / Typify</strong></td>
        <td><code>messages = app.build()</code></td>
    </tr>
</table>

</body>
</html>
"""

html_path = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\scripts\IronPython_Automation_Engine_Guide.html"
pdf_path1 = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\St_Codes\IronPython_Automation_Engine_Guide.pdf"
pdf_path2 = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\ST_Code\IronPython_Automation_Engine_Guide.pdf"

os.makedirs(r"D:\Git_repos\plc_projects\Rasi_feeds_batching\scripts", exist_ok=True)
os.makedirs(r"D:\Git_repos\plc_projects\Rasi_feeds_batching\St_Codes", exist_ok=True)
os.makedirs(r"D:\Git_repos\plc_projects\Rasi_feeds_batching\ST_Code", exist_ok=True)

with open(html_path, "w", encoding="utf-8") as f:
    f.write(html_content)

print("HTML generated at: " + html_path)

# Convert to PDF via headless Microsoft Edge
edge_exe = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
if not os.path.exists(edge_exe):
    edge_exe = r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"

cmd = [
    edge_exe,
    "--headless",
    "--disable-gpu",
    "--no-pdf-header-footer",
    "--print-to-pdf=" + pdf_path1,
    html_path
]

print("Running Edge headless PDF conversion...")
subprocess.run(cmd, check=True)
print("PDF created at: " + pdf_path1)

shutil.copyfile(pdf_path1, pdf_path2)
print("PDF copied to: " + pdf_path2)
