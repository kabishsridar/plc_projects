import json
import random
import time

filepath = r"D:\Git_repos\plc_projects\project1\workflow.excalidraw"

def generate_id():
    return "".join(random.choice("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-") for _ in range(21))

# Load Excalidraw JSON
with open(filepath, "r", encoding="utf-8") as f:
    data = json.load(f)

# Filter out previously added elements (anything added by us has x >= 750)
data["elements"] = [elem for elem in data["elements"] if elem.get("x", 0) < 750]

timestamp = int(time.time() * 1000)

def create_block(x, y, width, height, title, text, bg_color):
    rect_id = generate_id()
    text_id = generate_id()
    
    rect = {
        "id": rect_id,
        "type": "rectangle",
        "x": float(x),
        "y": float(y),
        "width": float(width),
        "height": float(height),
        "angle": 0,
        "strokeColor": "#1e1e1e",
        "backgroundColor": bg_color,
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
    
    full_text = f"**{title}**\n\n{text}"
    
    text_elem = {
        "id": text_id,
        "type": "text",
        "x": float(x + 20),
        "y": float(y + 20),
        "width": float(width - 40),
        "height": float(height - 40),
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
        "text": full_text,
        "fontSize": 14,
        "fontFamily": 3,
        "textAlign": "left",
        "verticalAlign": "top",
        "containerId": rect_id,
        "originalText": full_text,
        "autoResize": False,
        "lineHeight": 1.25
    }
    
    return [rect, text_elem]

# 1. Header Box (Teal Green)
header_title = "SYSTEM OVERVIEW: PARALLEL BATCHING CONTROL"
header_text = (
    "This architecture coordinates a 20-ingredient batching system.\n"
    "It processes automation (6 ingredients) and manual tasks (14 ingredients) "
    "in parallel, governed by a master Formula ID (21st float variable)."
)
elements_to_add = []
elements_to_add.extend(create_block(800, 70, 580, 130, header_title, header_text, "#e6fcf5"))

# 2. Formula ID & Routing Box (Soft Blue)
formula_title = "FORMULA ID & ROUTING PIPELINE"
formula_text = (
    "• Formula ID: Inputted as a 32-bit Float (21st element).\n"
    "• Loading Phase: Captures the selected batching configuration.\n"
    "• Branching: Forks system into two parallel paths: Auto and Manual.\n"
    "• Skipping Mechanism: Both branches evaluate their respective sequence\n"
    "  arrays (INT[1..20]). If any ingredient address resolves to 0,\n"
    "  the step is skipped instantly without valve or operator triggers."
)
elements_to_add.extend(create_block(800, 220, 580, 220, formula_title, formula_text, "#e8f4fd"))

# 3. Automation Sequence Box (Soft Yellow)
auto_title = "AUTOMATION FLOW (6 BINS) - GROUP 1"
auto_text = (
    "• 20 INT Sequence Array: Determines order (e.g. 1, 6, 4, 3, 7, 2).\n"
    "• Material ID Matching: Mapped to Group 1.\n"
    "• Weight Translation: Associates set weights (1 to 20) with physical\n"
    "  silos (Bin 1, Bin 2, Bin 3, etc.) by matching the material ID.\n"
    "• Loss-in-Weight execution:\n"
    "  - Opens selected bin valve output.\n"
    "  - Monitors weight reduction on load cell.\n"
    "  - Closes valve when weight reaches cutoff (Start - Target).\n"
    "  - Steps forward to next auto-ingredient."
)
elements_to_add.extend(create_block(1400, 70, 480, 370, auto_title, auto_text, "#fff9db"))

# 4. Manual Sequence Box (Soft Purple)
manual_title = "MANUAL FLOW (14 INGREDIENTS) - GROUP 2"
manual_text = (
    "• 20 INT Manual Sequence Array: Governs the sequence order.\n"
    "• Material ID Allocation: Linked to Group 2 (10 indices, except 0).\n"
    "• Strict Interlocking:\n"
    "  - Prevents operator from pouring multiple manual ingredients.\n"
    "  - Active manual ingredient must be fully confirmed (weight target met\n"
    "    or confirmed on HMI) before moving to next step.\n"
    "  - Standard interlocking shuts down manual paths if E-Stop is triggered."
)
elements_to_add.extend(create_block(1900, 70, 480, 370, manual_title, manual_text, "#f3e5f5"))

data["elements"].extend(elements_to_add)

# Write back to Excalidraw
with open(filepath, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)

print("Excalidraw updated with colorful blocks successfully.")
