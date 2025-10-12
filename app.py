import os, base64, cv2, numpy as np, json
from flask import Flask, render_template, request, jsonify
from ultralytics import YOLO
from datetime import datetime
from collections import defaultdict

app = Flask(__name__)

# ---------- modelo ----------
if not os.path.exists("yolov8n.pt"):
    YOLO("yolov8n.pt")
model = YOLO("yolov8n.pt")

# ---------- clases COCO frutas ----------
FRUIT_IDS = {46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58}

# ---------- estadísticas en RAM ----------
stats = defaultdict(int)          # {"RIPEN":12, "UNRIPEN":5, "OVERRIPE":3}

def classify_ripeness(crop):
    """Devuelve RIPEN / UNRIPEN / OVERRIPE"""
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    s, v = hsv[:, :, 1].mean(), hsv[:, :, 2].mean()
    if s < 50 and v > 150:
        return "UNRIPEN"
    if s > 100 and v > 100:
        return "RIPEN"
    return "OVERRIPE"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/detect", methods=["POST"])
def detect():
    try:
        # decodificar imagen
        im_b64 = request.json["image"].split(",")[1]
        im_data = base64.b64decode(im_b64)
        im = cv2.imdecode(np.frombuffer(im_data, np.uint8), cv2.IMREAD_COLOR)

        results = model(im, verbose=False)
        detections = []
        for r in results:
            for box in r.boxes:
                cls = int(box.cls[0])
                if cls in FRUIT_IDS:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    conf = float(box.conf[0])
                    ripeness = classify_ripeness(im[y1:y2, x1:x2])
                    detections.append({
                        "class": model.names[cls],
                        "ripeness": ripeness,
                        "confidence": round(conf, 2),
                        "bbox": [x1, y1, x2, y2]
                    })
                    stats[ripeness] += 1

        # imagen anotada
        annotated = results[0].plot()
        _, buf = cv2.imencode(".jpg", annotated)
        b64 = base64.b64encode(buf).decode()
        return jsonify({
            "detections": detections,
            "image": f"data:image/jpeg;base64,{b64}",
            "stats": dict(stats)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/stats")
def get_stats():
    return jsonify(dict(stats))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
