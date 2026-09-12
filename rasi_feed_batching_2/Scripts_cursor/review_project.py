# Review Rasi_feeds_batching2.project via Automation Builder IronPython.
# Based on scripts/ inspect helpers + IronPython_Automation_Engine_Guide.md
#
# Run via Scripts_cursor/run_review.ps1 or:
#   AutomationBuilder.exe --profile="Automation Builder 2.7" --noUI --runscript=...review_project.py

import sys
import os

ROOT = r"c:\Users\DELL\Desktop\RASI FOODS PROJECT04Sep2026\rasi_feed_batching_2"
PROJECT_PATH = os.path.join(ROOT, "Rasi_feeds_batching2.project")
OUT_DIR = os.path.join(ROOT, "Scripts_cursor", "review_output")
LOG_PATH = os.path.join(OUT_DIR, "review_log.txt")
ST_DIR = os.path.join(OUT_DIR, "st_export")


def ensure_dirs():
    if not os.path.exists(OUT_DIR):
        os.makedirs(OUT_DIR)
    if not os.path.exists(ST_DIR):
        os.makedirs(ST_DIR)


def write(f, line):
    f.write(line + "\n")
    f.flush()


def dump_pou(obj, st_dir):
    name = obj.get_name()
    has_decl = hasattr(obj, "textual_declaration")
    has_impl = hasattr(obj, "textual_implementation")
    decl = ""
    impl = ""
    try:
        if has_decl:
            decl = obj.textual_declaration.text or ""
    except Exception:
        decl = ""
    try:
        if has_impl:
            impl = obj.textual_implementation.text or ""
    except Exception:
        impl = ""

    if len(decl.strip()) > 0 or len(impl.strip()) > 0:
        st_file = os.path.join(st_dir, name + ".st")
        sf = open(st_file, "w")
        sf.write("(* POU: " + name + " *)\n\n")
        sf.write("=== DECLARATION ===\n")
        sf.write(decl + "\n\n")
        if len(impl.strip()) > 0:
            sf.write("=== IMPLEMENTATION ===\n")
            sf.write(impl + "\n")
        sf.close()
        return "ST"
    if hasattr(obj, "export_xml"):
        try:
            xml_file = os.path.join(st_dir, name + "_fbd.xml")
            obj.export_xml(xml_file)
            return "XML"
        except Exception as ex:
            return "EXPORT_FAIL:" + str(ex)
    return "EMPTY"


def review():
    ensure_dirs()
    f = open(LOG_PATH, "w")
    write(f, "Rasi_feeds_batching2 - project review")
    write(f, "Project: " + PROJECT_PATH)
    write(f, "=" * 70)

    if not os.path.exists(PROJECT_PATH):
        write(f, "ERROR: project file not found.")
        f.close()
        return

    try:
        write(f, "Opening project...")
        try:
            proj = projects.open(PROJECT_PATH, allow_readonly=True)
        except TypeError:
            proj = projects.open(PROJECT_PATH)
        write(f, "Opened project OK")

        write(f, "")
        write(f, "--- PROJECT TREE (code objects) ---")
        pou_names = []
        for obj in proj.get_children(True):
            name = obj.get_name()
            is_code = hasattr(obj, "textual_declaration") or hasattr(obj, "textual_implementation")
            if is_code:
                pou_names.append(name)
                write(f, "[POU/Code] " + name + "  type=" + str(obj.type))
        write(f, "POU count: " + str(len(pou_names)))
        write(f, "POUs: " + str(pou_names))

        write(f, "")
        write(f, "--- TASK CONFIGURATION ---")
        try:
            tasks = proj.find("Task", True)
            write(f, "Task nodes found: " + str(len(tasks)))
            for t in tasks:
                kids = [c.get_name() for c in t.get_children()]
                write(f, "Task: " + t.get_name() + "  calls=" + str(kids))
        except Exception as ex:
            write(f, "Task inspect error: " + str(ex))

        write(f, "")
        write(f, "--- GVL ---")
        try:
            gvls = proj.find("GVL", True)
            if gvls:
                gvl = gvls[0]
                decl = gvl.textual_declaration.text
                gvl_path = os.path.join(OUT_DIR, "GVL.st")
                gf = open(gvl_path, "w")
                gf.write(decl)
                gf.close()
                write(f, "GVL exported -> " + gvl_path)
                write(f, "GVL length (chars): " + str(len(decl)))
                keys = [
                    "Start_Button", "E_Stop_Active", "Reset",
                    "load_cell_auto", "load_cell_semi_auto",
                    "Auto_Bin_Material_Mapping", "Semi_Auto_Bin_Material_Mapping",
                    "Recipe_Weights", "Auto_Excess_Allowed", "Semi_Auto_Excess_Allowed",
                ]
                for k in keys:
                    write(f, "  GVL has " + k + ": " + str(k in decl))
            else:
                write(f, "GVL not found")
        except Exception as ex:
            write(f, "GVL error: " + str(ex))

        write(f, "")
        write(f, "--- KEY POU PRESENCE ---")
        expected = [
            "batching14",
            "Auto_Batching_V14",
            "Semi_Auto_Batching_V14",
            "FB_Samyak_Multi",
            "FB_Samyak_Control",
            "GVL",
        ]
        for name in expected:
            found = proj.find(name, True)
            write(f, name + ": " + ("FOUND" if found else "MISSING"))

        write(f, "")
        write(f, "--- EXPORT POUs ---")
        for obj in proj.get_children(True):
            if hasattr(obj, "textual_declaration") or hasattr(obj, "textual_implementation"):
                kind = dump_pou(obj, ST_DIR)
                write(f, "  " + obj.get_name() + " -> " + kind)

        write(f, "")
        write(f, "--- BUILD ---")
        try:
            apps = proj.find("Application", True)
            if not apps:
                write(f, "Application node not found")
            else:
                app = apps[0]
                write(f, "Building: " + app.get_name())
                messages = app.build()
                err_n = 0
                warn_n = 0
                if messages:
                    for msg in messages:
                        sev = str(msg.Severity)
                        text = str(msg.Text)
                        low = sev.lower()
                        if "error" in low:
                            err_n = err_n + 1
                            write(f, "[ERROR] " + text)
                        elif "warning" in low:
                            warn_n = warn_n + 1
                            write(f, "[WARNING] " + text)
                        else:
                            write(f, "[" + sev + "] " + text)
                write(f, "Build result: " + str(err_n) + " Errors, " + str(warn_n) + " Warnings")
        except Exception as ex:
            write(f, "Build error: " + str(ex))

        proj.close()
        write(f, "")
        write(f, "Review complete. Project closed.")
    except Exception as e:
        write(f, "FATAL: " + str(e))
    f.close()


if __name__ == "__main__":
    review()