import sys
import os

log_path = r"C:\Users\kabish\hello_output.txt"
try:
    with open(log_path, "w") as f:
        f.write("Hello from script! Python version: " + sys.version + "\n")
except Exception as e:
    # write to another place
    with open("C:\\Temp\\hello_output.txt", "w") as f:
        f.write("Error: " + str(e))
