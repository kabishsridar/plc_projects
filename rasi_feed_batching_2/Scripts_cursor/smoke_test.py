# Minimal smoke test for Automation Builder IronPython
import sys
import os

ROOT = r"c:\Users\DELL\Desktop\RASI FOODS PROJECT04Sep2026\rasi_feed_batching_2"
OUT = os.path.join(ROOT, "Scripts_cursor", "review_output", "smoke_log.txt")

def main():
    d = os.path.dirname(OUT)
    if not os.path.exists(d):
        os.makedirs(d)
    f = open(OUT, "w")
    f.write("smoke ok\n")
    try:
        f.write("projects type: " + str(type(projects)) + "\n")
    except Exception as e:
        f.write("projects missing: " + str(e) + "\n")
    f.close()

if __name__ == "__main__":
    main()