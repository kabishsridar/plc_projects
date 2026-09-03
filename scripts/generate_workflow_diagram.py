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
elements_to_add = []

def draw_rectangle(x, y, width, height, text, bg_color):
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
    
    text_elem = {
        "id": text_id,
        "type": "text",
        "x": float(x + 10),
        "y": float(y + 10),
        "width": float(width - 20),
        "height": float(height - 20),
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
        "text": text,
        "fontSize": 13,
        "fontFamily": 3,
        "textAlign": "center",
        "verticalAlign": "middle",
        "containerId": rect_id,
        "originalText": text,
        "autoResize": False,
        "lineHeight": 1.25
    }
    
    elements_to_add.append(rect)
    elements_to_add.append(text_elem)
    return rect_id

def draw_arrow(start_x, start_y, end_x, end_y, start_elem_id=None, end_elem_id=None):
    arrow_id = generate_id()
    
    arrow = {
        "id": arrow_id,
        "type": "arrow",
        "x": float(start_x),
        "y": float(start_y),
        "width": float(abs(end_x - start_x)),
        "height": float(abs(end_y - start_y)),
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
        "points": [
            [0.0, 0.0],
            [float(end_x - start_x), float(end_y - start_y)]
        ],
        "startBinding": {"elementId": start_elem_id, "focus": 0.0, "gap": 5} if start_elem_id else None,
        "endBinding": {"elementId": end_elem_id, "focus": 0.0, "gap": 5} if end_elem_id else None,
        "lastCommittedPoint": None,
        "startArrowhead": None,
        "endArrowhead": "arrow"
    }
    
    elements_to_add.append(arrow)
    return arrow_id

# --- LAYOUT DEFINITION ---

# 1. Start Node
start_id = draw_rectangle(1000, 50, 240, 60, "START TRIGGER\n(Start_Button pressed)", "#e6fcf5")

# 2. Initialization
init_id = draw_rectangle(1000, 150, 240, 60, "Initialize Step = 1\nbin_last_weight = load_cell_value", "#fff3cd")
draw_arrow(1120, 110, 1120, 150, start_id, init_id)

# 3. Read step
step_y = 250
r1_id = draw_rectangle(1000, step_y, 240, 60, "1. Read Target for Bin [Step]\ntarget_act_bin = bin_set_value", "#e8f4fd")
draw_arrow(1120, 210, 1120, 250, init_id, r1_id)

# 4. Open Silo Valve
step_y += 90
r2_id = draw_rectangle(1000, step_y, 240, 60, "2. Open Silo Valve Output\nDischarge_Bin[Step] = TRUE", "#e8f4fd")
draw_arrow(1120, 310, 1120, 340, r1_id, r2_id)

# 5. Measure added weight
step_y += 90
r3_id = draw_rectangle(1000, step_y, 240, 60, "3. Calculate Added Weight\nactual_bin = load_cell - bin_last_weight", "#e8f4fd")
draw_arrow(1120, 400, 1120, 430, r2_id, r3_id)

# 6. Condition Check
step_y += 90
r4_id = draw_rectangle(1000, step_y, 240, 60, "4. Is actual_bin >= target_act_bin?\n(Yes: Close Silo / No: Wait)", "#e8f4fd")
draw_arrow(1120, 490, 1120, 520, r3_id, r4_id)

# 7. Close Silo Valve & Update Last Weight
step_y += 90
r5_id = draw_rectangle(1000, step_y, 240, 60, "5. Close Silo Valve & Update\nbin_last_weight = load_cell_value", "#e8f4fd")
draw_arrow(1120, 580, 1120, 610, r4_id, r5_id)

# 8. Loop checks
step_y += 90
r6_id = draw_rectangle(1000, step_y, 240, 60, "6. Is Step = 6?\n(Yes: End Sequence / No: Step = Step + 1)", "#e8f4fd")
draw_arrow(1120, 670, 1120, 700, r5_id, r6_id)

# Loop back arrow for another bin
draw_arrow(1000, 730, 930, 730)
draw_arrow(930, 730, 930, 280)
draw_arrow(930, 280, 1000, 280, end_elem_id=r1_id)

# 9. Completion delay
step_y += 100
delay_id = draw_rectangle(1000, step_y, 240, 60, "7. Wait 2 Seconds\n(Post-batching delay)", "#fff3cd")
draw_arrow(1120, 760, 1120, 830, r6_id, delay_id)

# 10. Reset Last Weight
step_y += 90
reset_id = draw_rectangle(1000, step_y, 240, 60, "8. Reset Last Weight\nbin_last_weight = 0", "#e6fcf5")
draw_arrow(1120, 890, 1120, 920, delay_id, reset_id)

# 11. Final complete
step_y += 90
end_id = draw_rectangle(1000, step_y, 240, 60, "9. Sequence Complete\nSequence_Complete = TRUE", "#e6fcf5")
draw_arrow(1120, 980, 1120, 1010, reset_id, end_id)

data["elements"].extend(elements_to_add)

# Write back to Excalidraw
with open(filepath, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)

print("Excalidraw updated successfully.")
