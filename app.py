import os, base64, cv2, numpy as np
from flask import Flask, render_template, request, jsonify
from ultralytics import YOLO
from collections import defaultdict
from datetime import datetime
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Cloudinary config
cloudinary.config(
    cloud_name=os.getenv("CLOUD_NAME"),
    api_key=os.getenv("API_KEY"),
    api_secret=os.getenv("API_SECRET")
)

FRUIT_IDS = {46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58}
COLOR_MAP = {
    "RIPEN": (0, 255, 0),
    "UNRIPEN": (0, 0, 255),
    "OVERRIPE": (0, 255, 255)
}

stats = defaultdict(int)
library = []

_model = None
def get_model():
    global _model
    if _model is None:
        _model = YOLO("yolov8n.pt")
    return _model

def ripeness_class(crop):
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    s, v = hsv[:, :, 1].mean(), hsv[:, :, 2].mean()
    if s < 50 and v > 150:
        return "UNRIPEN"
    if s > 100 and v > 100:
        return "RIPEN"
    return "OVERRIPE"

@app.route("/")
def index():
    return render_template("index.html", library=library)

@app.route("/detect", methods=["POST"])
def detect():
    try:
        im_b64 = request.json["image"].split(",")[1]
        im_data = base64.b64decode(im_b64)
        im = cv2.imdecode(np.frombuffer(im_data, np.uint8), cv2.IMREAD_COLOR)

        model = get_model()
        results = model(im, verbose=False)
        detections = []

        for r in results:
            for box in r.boxes:
                cls = int(box.cls[0])
                if cls in FRUIT_IDS:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    conf = float(box.conf[0])
                    crop = im[y1:y2, x1:x2]
                    ripeness = ripeness_class(crop)
                    color = COLOR_MAP[ripeness]

                    # Dibujar sombra con color
                    cv2.rectangle(im, (x1, y1), (x2, y2), color, 3)
                    label = f"{model.names[cls]} ({ripeness})"
                    cv2.putText(im, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

                    detections.append({
                        "class": model.names[cls],
                        "ripeness": ripeness,
                        "confidence": round(conf, 2),
                        "bbox": [x1, y1, x2, y2]
                    })
                    stats[ripeness] += 1

        # Subir a Cloudinary
        _, buf = cv2.imencode(".jpg", im)
        img_bytes = buf.tobytes()
        upload_result = cloudinary.uploader.upload(
            img_bytes,
            folder="frutas",
            resource_type="image",
            context={
                "fruit": detections[0]["class"] if detections else "unknown",
                "ripeness": detections[0]["ripeness"] if detections else "unknown"
            }
        )

        library.append({
            "url": upload_result["secure_url"],
            "fruit": detections[0]["class"] if detections else "unknown",
            "ripeness": detections[0]["ripeness"] if detections else "unknown",
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

        b64 = base64.b64encode(buf).decode()
        return jsonify({
            "detections": detections,
            "image": f"data:image/jpeg;base64,{b64}",
            "stats": dict(stats),
            "library": library
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/stats")
def get_stats():
    return jsonify(dict(stats))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
