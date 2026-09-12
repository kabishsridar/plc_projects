# Add TP pulse timer FBD network to batching14, then build + re-export.
# Vars: TP_ON (IN), TP_Out (Q), TP_Et (ET); PT wired to T#1S; instance TP_1.

import sys
import os
import re

ROOT = r"c:\Users\DELL\Desktop\RASI FOODS PROJECT04Sep2026\rasi_feed_batching_2"
PROJECT_PATH = os.path.join(ROOT, "Rasi_feeds_batching2.project")
XML_PATH = os.path.join(ROOT, "Scripts_cursor", "batching14_with_tp.xml")
OUT_DIR = os.path.join(ROOT, "Scripts_cursor", "review_output")
ST_DIR = os.path.join(OUT_DIR, "st_export")
LOG_PATH = os.path.join(OUT_DIR, "add_tp_log.txt")
B14_XML_OUT = os.path.join(ST_DIR, "batching14_fbd.xml")
B14_ST_OUT = os.path.join(ST_DIR, "batching14.st")
INDEX_PATH = os.path.join(OUT_DIR, "extracted_blocks_index.txt")


def write(f, line):
    f.write(line + "\n")
    f.flush()


def main():
    if not os.path.exists(OUT_DIR):
        os.makedirs(OUT_DIR)
    if not os.path.exists(ST_DIR):
        os.makedirs(ST_DIR)

    f = open(LOG_PATH, "w")
    write(f, "Add TP to batching14")
    write(f, "XML: " + XML_PATH)

    try:
        proj = projects.open(PROJECT_PATH)
        app = proj.find("Application", True)[0]
        write(f, "Opened project")

        existing = proj.find("batching14", True)
        write(f, "Existing batching14 count: " + str(len(existing)))
        for b in existing:
            b.remove()
        write(f, "Removed old batching14")

        app.import_xml(XML_PATH)
        write(f, "Imported batching14_with_tp.xml")

        # Verify
        b14s = proj.find("batching14", True)
        if not b14s:
            write(f, "ERROR: batching14 missing after import")
        else:
            b14 = b14s[0]
            decl = b14.textual_declaration.text
            write(f, "Decl has TP_ON: " + str("TP_ON" in decl))
            write(f, "Decl has TP_Out: " + str("TP_Out" in decl))
            write(f, "Decl has TP_Et: " + str("TP_Et" in decl))
            write(f, "Decl has TP_1: " + str(("TP_1" in decl) or ("TP :" in decl)))

            # Refresh ST + XML exports
            sf = open(B14_ST_OUT, "w")
            sf.write("(* POU: batching14 *)\n\n")
            sf.write("=== DECLARATION ===\n")
            sf.write(decl + "\n\n")
            sf.write("=== IMPLEMENTATION ===\n")
            sf.write("(* empty textual body - see batching14_fbd.xml for FBD *)\n")
            sf.close()
            b14.export_xml(B14_XML_OUT)
            write(f, "Re-exported ST/XML")

        # Ensure task still calls batching14
        try:
            tasks = proj.find("Task", True)
            for t in tasks:
                kids = [c.get_name() for c in t.get_children()]
                write(f, "Task " + t.get_name() + " calls=" + str(kids))
        except Exception as ex:
            write(f, "Task check: " + str(ex))

        # Build
        write(f, "Building...")
        msgs = app.build()
        err_n = 0
        warn_n = 0
        if msgs:
            for msg in msgs:
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
        write(f, "Build: " + str(err_n) + " errors, " + str(warn_n) + " warnings")

        proj.save()
        write(f, "Saved project")

        # Update index snippet
        idx = open(INDEX_PATH, "w")
        write(idx, "Final extracted blocks inventory (after TP add)")
        write(idx, "=" * 70)
        if os.path.exists(B14_XML_OUT):
            xf = open(B14_XML_OUT, "r")
            text = xf.read()
            xf.close()
            pairs = re.findall(r'typeName="([^"]+)"(?:\s+instanceName="([^"]*)")?', text)
            seen = {}
            write(idx, "=== FBD BLOCKS IN batching14_fbd.xml ===")
            for typ, inst in pairs:
                key = typ + "|" + (inst or "")
                if key not in seen:
                    seen[key] = True
                    if inst:
                        write(idx, "  FB type=" + typ + "  instance=" + inst)
                    else:
                        write(idx, "  FB type=" + typ)
            write(idx, "Unique FB instances: " + str(len(seen)))
        idx.close()

        proj.close()
        write(f, "Done.")
    except Exception as e:
        write(f, "FATAL: " + str(e))
    f.close()


if __name__ == "__main__":
    main()