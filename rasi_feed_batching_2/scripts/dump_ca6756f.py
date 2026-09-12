import sys
import os

project_path = r"C:\Users\kabish\.gemini\antigravity-ide\brain\6bb09710-7f3e-4443-b187-ad04e16ca8dc\scratch\rasi_ca6756f.project"
dump_dir = r"C:\Users\kabish\.gemini\antigravity-ide\brain\6bb09710-7f3e-4443-b187-ad04e16ca8dc\scratch\ca6756f_dump"
if not os.path.exists(dump_dir):
    os.makedirs(dump_dir)

try:
    proj = projects.open(project_path)
    
    # Dump GVL
    gvl = proj.find("GVL", True)[0]
    with open(os.path.join(dump_dir, "GVL.txt"), "w") as f:
        f.write(gvl.textual_declaration.text)
        
    # Dump batching13
    b13 = proj.find("batching13", True)[0]
    with open(os.path.join(dump_dir, "batching13_decl.txt"), "w") as f:
        f.write(b13.textual_declaration.text)
    with open(os.path.join(dump_dir, "batching13_impl.txt"), "w") as f:
        f.write(b13.textual_implementation.text)
        
    # Dump Auto_Batching_V13
    a13 = proj.find("Auto_Batching_V13", True)[0]
    with open(os.path.join(dump_dir, "Auto_V13_decl.txt"), "w") as f:
        f.write(a13.textual_declaration.text)
    with open(os.path.join(dump_dir, "Auto_V13_impl.txt"), "w") as f:
        f.write(a13.textual_implementation.text)
        
    # Dump Semi_Auto_Batching_V13
    s13 = proj.find("Semi_Auto_Batching_V13", True)[0]
    with open(os.path.join(dump_dir, "Semi_V13_decl.txt"), "w") as f:
        f.write(s13.textual_declaration.text)
    with open(os.path.join(dump_dir, "Semi_V13_impl.txt"), "w") as f:
        f.write(s13.textual_implementation.text)
        
    proj.close()
    print("Successfully dumped all ca6756f files.")
except Exception as e:
    print("Error: " + str(e))
