import json
import random
import time

filepath = r"D:\Git_repos\plc_projects\project1\workflow_5.excalidraw"

def generate_id():
    return "".join(random.choice("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-") for _ in range(21))

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
start_id = draw_rectangle(100, 50, 240, 60, "START TRIGGER\n(Start_Button pressed)", "#e6fcf5")

# 2. Initialization
init_id = draw_rectangle(100, 150, 240, 60, "Initialize Step = 1\nbin_last_weight = load_cell_value", "#fff3cd")
draw_arrow(220, 110, 220, 150, start_id, init_id)

# 3. Read step
step_y = 250
r1_id = draw_rectangle(100, step_y, 240, 60, "1. Read Target & Pct for Bin [Step]\ntarget = set_value\ntolerance_pct = 20%", "#e8f4fd")
draw_arrow(220, 210, 220, 250, init_id, r1_id)

# 4. Calculate threshold
step_y += 90
thresh_id = draw_rectangle(100, step_y, 240, 60, "2. Calculate Slow Cutoff\nslow_cutoff = target * (1 - pct/100)", "#e8f4fd")
draw_arrow(220, 310, 220, 340, r1_id, thresh_id)

# 5. Open Silo Valves (FAST and SLOW)
step_y += 90
valves_id = draw_rectangle(100, step_y, 240, 60, "3. Run Motor FAST\nDischarge_Fast = TRUE\nDischarge_Slow = TRUE", "#e8f4fd")
draw_arrow(220, 400, 220, 430, thresh_id, valves_id)

# 6. Check weight condition
step_y += 90
check_id = draw_rectangle(100, step_y, 240, 80, "4. Check Added Weight\nactual_bin = load_cell - bin_last_weight\nIs actual_bin >= slow_cutoff?", "#e8f4fd")
draw_arrow(220, 490, 220, 520, valves_id, check_id)

# 7. Slow down motor branch (Right side of check)
slow_id = draw_rectangle(400, step_y + 10, 260, 80, "5. SLOW DOWN MOTOR\nDischarge_Fast = FALSE\nDischarge_Slow = TRUE\nDisplay: 'Tolerance active, motor slow'\nSimRate = 2.0 kg/s", "#ffe3e3")
draw_arrow(340, step_y + 40, 400, step_y + 40, check_id, slow_id)

# 8. Check final target
step_y += 110
final_id = draw_rectangle(100, step_y, 240, 60, "6. Is actual_bin >= target_act_bin?", "#e8f4fd")
draw_arrow(220, step_y - 30, 220, step_y, check_id, final_id)
draw_arrow(530, step_y - 20, 340, step_y + 30, slow_id, final_id)

# 9. Close Silo Valve & Update Last Weight
step_y += 90
r5_id = draw_rectangle(100, step_y, 240, 60, "7. Close Slow Valve & Update\nbin_last_weight = load_cell_value", "#e8f4fd")
draw_arrow(220, step_y - 30, 220, step_y, final_id, r5_id)

# 10. Loop checks
step_y += 90
r6_id = draw_rectangle(100, step_y, 240, 60, "8. Is Step = 6?\n(Yes: End Sequence / No: Step = Step + 1)", "#e8f4fd")
draw_arrow(220, step_y - 30, 220, step_y, r5_id, r6_id)

# Loop back arrow for another bin
draw_arrow(100, step_y + 30, 40, step_y + 30)
draw_arrow(40, step_y + 30, 40, 280)
draw_arrow(40, 280, 100, 280, end_elem_id=r1_id)

# 11. Completion delay
step_y += 100
delay_id = draw_rectangle(100, step_y, 240, 60, "9. Wait 2 Seconds\n(Post-batching delay)", "#fff3cd")
draw_arrow(220, step_y - 40, 220, step_y, r6_id, delay_id)

# 12. Reset Last Weight
step_y += 90
reset_id = draw_rectangle(100, step_y, 240, 60, "10. Reset Last Weight\nbin_last_weight = 0", "#e6fcf5")
draw_arrow(220, step_y - 30, 220, step_y, delay_id, reset_id)

# 13. Final complete
step_y += 90
end_id = draw_rectangle(100, step_y, 240, 60, "11. Sequence Complete\nSequence_Complete = TRUE", "#e6fcf5")
draw_arrow(220, step_y - 30, 220, step_y, reset_id, end_id)

# Excalidraw base structure
excalidraw_data = {
    "type": "excalidraw",
    "version": 2,
    "source": "https://excalidraw.com",
    "elements": elements_to_add,
    "appState": {
        "gridSize": None,
        "viewBackgroundColor": "#ffffff"
    },
    "files": {}
}

# Write to workflow_5.excalidraw
with open(filepath, "w", encoding="utf-8") as f:
    json.dump(excalidraw_data, f, indent=2)

print("workflow_5.excalidraw created successfully.")
