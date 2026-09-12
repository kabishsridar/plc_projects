import sys
import os

project_path = r"D:\Git_repos\plc_projects\Rasi_feeds_batching\Rasi_feeds_batching.project"
log_path = r"C:\Users\kabish\.gemini\antigravity-ide\brain\6bb09710-7f3e-4443-b187-ad04e16ca8dc\scratch\test_pou_types.txt"

with open(log_path, "w") as f:
    try:
        f.write("PouType: " + str(dir(PouType)) + "\n")
        f.write("LanguageType: " + str(dir(LanguageType)) + "\n")
    except Exception as e:
        f.write("Error: " + str(e) + "\n")
