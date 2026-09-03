import json
import random
import time

filepath = r"D:\Git_repos\plc_projects\project1\workflow.excalidraw"

def generate_id():
    return "".join(random.choice("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-") for _ in range(21))

# Load Excalidraw JSON
with open(filepath, "r", encoding="utf-8") as f:
    data = json.load(f)

# Define our text element content
text_content = """=== RECIPE SEQUENCE DESIGN (PARALLEL AUTO & MANUAL) ===

1. INGREDIENTS DESIGN (1 to 20 IDs)
   - 6 Ingredients: Automated Feeding (Group 1)
   - 14 Ingredients: Manual Feeding (Group 2)
   - 21st Element: Formula ID (Float)

2. PARALLEL PROCESS FLOW
   [ Formula ID Loaded ]
            │
            ├─► AUTOMATION PATH (6 Bins)
            │   - Controlled by Sequence Array (20 INT addresses)
            │   - Target weights mapped to Bin 1, Bin 2, Bin 3, etc. by Material ID
            │   - If Sequence Address is 0: Skip
            │
            └─► MANUAL PATH (14 Ingredients)
                - Controlled by Manual Sequence Array (20 INT addresses)
                - If Sequence Address is 0: Skip
                - Strict Interlocking: One ingredient must complete (pour weight met) 
                  before the operator is permitted to start the next one.
                - Uses Manual Array (10 Indices) for Material IDs (except 0)"""

# Create a clean rectangle container
rect_id = generate_id()
text_id = generate_id()
timestamp = int(time.time() * 1000)

rect_element = {
    "id": rect_id,
    "type": "rectangle",
    "x": 800.0,
    "y": 200.0,
    "width": 620.0,
    "height": 450.0,
    "angle": 0,
    "strokeColor": "#1e1e1e",
    "backgroundColor": "#f8f9fa",
    "fillStyle": "solid",
    "strokeWidth": 2,
    "strokeStyle": "solid",
    "roughness": 0,
    "opacity": 100,
    "groupIds": [],
    "frameId": None,
    "roundness": {"type": 3},
    "seed": random.randint(1, 2000000000),
    "version": 1,
    "versionNonce": random.randint(1, 2000000000),
    "isDeleted": False,
    "boundElements": [{"type": "text", "id": text_id}],
    "updated": timestamp,
    "link": None,
    "locked": False
}

text_element = {
    "id": text_id,
    "type": "text",
    "x": 820.0,
    "y": 220.0,
    "width": 580.0,
    "height": 410.0,
    "angle": 0,
    "strokeColor": "#1e1e1e",
    "backgroundColor": "transparent",
    "fillStyle": "solid",
    "strokeWidth": 2,
    "strokeStyle": "solid",
    "roughness": 0,
    "opacity": 100,
    "groupIds": [],
    "frameId": None,
    "roundness": None,
    "seed": random.randint(1, 2000000000),
    "version": 1,
    "versionNonce": random.randint(1, 2000000000),
    "isDeleted": False,
    "boundElements": [],
    "updated": timestamp,
    "link": None,
    "locked": False,
    "text": text_content,
    "fontSize": 16,
    "fontFamily": 3,
    "textAlign": "left",
    "verticalAlign": "top",
    "containerId": rect_id,
    "originalText": text_content,
    "autoResize": False,
    "lineHeight": 1.25
}

# Append elements
data["elements"].append(rect_element)
data["elements"].append(text_element)

# Write back to Excalidraw
with open(filepath, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)

print("Excalidraw updated successfully.")
