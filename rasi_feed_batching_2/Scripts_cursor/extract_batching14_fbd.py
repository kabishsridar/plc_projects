# Export batching14 FBD (PLCopen XML) + refresh all extracted POU blocks.
# Also builds an inventory of FBD function-block instances from the XML.
# Based on scripts/export_b14_proj2.py and dump_all_to_st_codes.py

import sys
import os
import re

ROOT = r"c:\Users\DELL\Desktop\RASI FOODS PROJECT04Sep2026\rasi_feed_batching_2"
PROJECT_PATH = os.path.join(ROOT, "Rasi_feeds_batching2.project")
OUT_DIR = os.path.join(ROOT, "Scripts_cursor", "review_output")
ST_DIR = os.path.join(OUT_DIR, "st_export")
LOG_PATH = os.path.join(OUT_DIR, "extract_blocks_log.txt")
INDEX_PATH = os.path.join(OUT_DIR, "extracted_blocks_index.txt")
B14_XML = os.path.join(ST_DIR, "batching14_fbd.xml")


def ensure_dirs():
    if not os.path.exists(OUT_DIR):
        os.makedirs(OUT_DIR)
    if not os.path.exists(ST_DIR):
        os.makedirs(ST_DIR)


def write(f, line):
    f.write(line + "\n")
    f.flush()


def dump_pou(obj, st_dir, logf):
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

    kinds = []
    if len(decl.strip()) > 0 or len(impl.strip()) > 0:
        st_file = os.path.join(st_dir, name + ".st")
        sf = open(st_file, "w")
        sf.write("(* POU: " + name + " *)\n\n")
        sf.write("=== DECLARATION ===\n")
        sf.write(decl + "\n\n")
        if len(impl.strip()) > 0:
            sf.write("=== IMPLEMENTATION ===\n")
            sf.write(impl + "\n")
        else:
            sf.write("=== IMPLEMENTATION ===\n")
            sf.write("(* empty textual body - see " + name + "_fbd.xml for FBD *)\n")
        sf.close()
        kinds.append("ST")

    if hasattr(obj, "export_xml") and len(impl.strip()) == 0:
        try:
            xml_file = os.path.join(st_dir, name + "_fbd.xml")
            obj.export_xml(xml_file)
            kinds.append("XML")
        except Exception as ex:
            kinds.append("XML_FAIL:" + str(ex))

    write(logf, "  " + name + " -> " + ",".join(kinds))
    return kinds


def inventory_fbd_blocks(xml_path, indexf):
    write(indexf, "")
    write(indexf, "=== FBD BLOCKS IN " + os.path.basename(xml_path) + " ===")
    if not os.path.exists(xml_path):
        write(indexf, "XML missing: " + xml_path)
        return
    xf = open(xml_path, "r")
    text = xf.read()
    xf.close()
    pairs = re.findall(r'typeName="([^"]+)"(?:\s+instanceName="([^"]*)")?', text)
    if not pairs:
        write(indexf, "(no block typeName found)")
        return
    seen = {}
    for typ, inst in pairs:
        key = typ + "|" + (inst or "")
        if key not in seen:
            seen[key] = True
            if inst:
                write(indexf, "  FB type=" + typ + "  instance=" + inst)
            else:
                write(indexf, "  FB type=" + typ)
    write(indexf, "Unique FB instances: " + str(len(seen)))


def main():
    ensure_dirs()
    logf = open(LOG_PATH, "w")
    indexf = open(INDEX_PATH, "w")
    write(logf, "Extract / refresh POU blocks")
    write(logf, "Project: " + PROJECT_PATH)
    write(indexf, "Final extracted blocks inventory")
    write(indexf, "Project: " + PROJECT_PATH)
    write(indexf, "=" * 70)

    try:
        try:
            proj = projects.open(PROJECT_PATH, allow_readonly=True)
        except TypeError:
            proj = projects.open(PROJECT_PATH)
        write(logf, "Opened project OK")

        write(logf, "")
        write(logf, "--- Targeted batching14.export_xml ---")
        b14s = proj.find("batching14", True)
        if not b14s:
            write(logf, "ERROR: batching14 not found")
        else:
            b14 = b14s[0]
            b14.export_xml(B14_XML)
            write(logf, "Exported: " + B14_XML)
            dump_pou(b14, ST_DIR, logf)

        write(logf, "")
        write(logf, "--- Refresh all code POUs (ST + FBD XML when needed) ---")
        write(indexf, "")
        write(indexf, "=== APPLICATION / USER POUs ===")
        for obj in proj.get_children(True):
            if hasattr(obj, "textual_declaration") or hasattr(obj, "textual_implementation"):
                name = obj.get_name()
                if name == "batching14":
                    continue
                kinds = dump_pou(obj, ST_DIR, logf)
                write(indexf, name + ": " + ",".join(kinds))

        write(indexf, "batching14: ST,XML")
        inventory_fbd_blocks(B14_XML, indexf)

        write(indexf, "")
        write(indexf, "=== FILES IN st_export ===")
        for fn in sorted(os.listdir(ST_DIR)):
            fp = os.path.join(ST_DIR, fn)
            write(indexf, "  " + fn + "  (" + str(os.path.getsize(fp)) + " bytes)")

        proj.close()
        write(logf, "Done. Project closed.")
        write(indexf, "")
        write(indexf, "Done.")
    except Exception as e:
        write(logf, "FATAL: " + str(e))
        write(indexf, "FATAL: " + str(e))
    logf.close()
    indexf.close()


if __name__ == "__main__":
    main()