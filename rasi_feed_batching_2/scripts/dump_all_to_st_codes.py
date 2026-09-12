import sys
import os

project_path = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\rasi_feed_batching_2\Rasi_feeds_batching2.project"
output_dir = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\St_Codes"

try:
    proj = projects.open(project_path)
    for obj in proj.get_children(True):
        name = obj.get_name()
        has_decl = hasattr(obj, "textual_declaration")
        has_impl = hasattr(obj, "textual_implementation")
        
        if has_decl or has_impl:
            decl = obj.textual_declaration.text if has_decl else ""
            impl = obj.textual_implementation.text if has_impl else ""
            
            # If it's a graphical POU (like FBD without textual implementation), export XML
            if hasattr(obj, "export_xml") and (not has_impl or len(impl.strip()) == 0):
                xml_file = os.path.join(output_dir, name + "_fbd.xml")
                obj.export_xml(xml_file)
                print("Exported XML: " + name)
            
            # If it has ST text, save as .st
            if len(decl.strip()) > 0 or len(impl.strip()) > 0:
                st_file = os.path.join(output_dir, name + ".st")
                with open(st_file, "w") as f:
                    f.write("(* ==========================================\n")
                    f.write("   POU: " + name + "\n")
                    f.write("   ========================================== *)\n\n")
                    f.write("=== DECLARATION ===\n")
                    f.write(decl + "\n\n")
                    if len(impl.strip()) > 0:
                        f.write("=== IMPLEMENTATION ===\n")
                        f.write(impl + "\n")
                print("Exported ST: " + name)
                
    proj.close()
    print("All POUs dumped successfully.")
except Exception as e:
    print("Error: " + str(e))
