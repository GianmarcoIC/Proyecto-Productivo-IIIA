import os, base64, cv2, numpy as np, io, csv
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file
from ultralytics import YOLO
from datetime import datetime
import cloudinary, cloudinary.uploader
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

cloudinary.config(
    cloud_name=os.getenv("CLOUD_NAME"),
    api_key=os.getenv("API_KEY"),
    api_secret=os.getenv("API_SECRET")
)

FRUIT_IDS = {46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58}
COLOR_MAP = {
    "RIPEN": (0,255,0),
    "UNRIPEN": (0,0,255),
    "OVERRIPE": (0,255,255),
    "NO-FRUIT": (128,128,128)
}

detections_db = []
_model = None

def get_model():
    global _model
    if _model is None:
        _model = YOLO("yolov8n.pt")  # descarga automática 1ª vez
    return _model

def ripeness_class(crop):
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    s, v = hsv[:,:,1].mean(), hsv[:,:,2].mean()
    if s < 50 and v > 150: return "UNRIPEN"
    if s > 100 and v > 100: return "RIPEN"
    return "OVERRIPE"

@app.route("/")
def index():
    return render_template("index.html", library=detections_db)

@app.route("/ready")
def ready():
    try:
        get_model()
        return jsonify({"ready": True})
    except Exception as e:
        return jsonify({"ready": False, "error": str(e)}), 500

@app.route("/detect", methods=["POST"])
def detect():
    try:
        data = request.json.get("image", "")
        if not data: return jsonify({"error": "No image"}), 400
        im = cv2.imdecode(np.frombuffer(base64.b64decode(data.split(",")[1]), np.uint8), cv2.IMREAD_COLOR)
        if im is None: return jsonify({"error": "Imagen inválida"}), 400
        model = get_model()
        results = model(im, verbose=False)
        outs = []
        for r in results:
            for box in r.boxes:
                cls = int(box.cls[0])
                x1,y1,x2,y2 = map(int, box.xyxy[0])
                conf = float(box.conf[0])
                crop = im[y1:y2, x1:x2]
                label = model.names[cls]

                if cls in FRUIT_IDS:
                    ripeness = ripeness_class(crop)
                    folder = "frutas"
                    color = COLOR_MAP[ripeness]
                else:
                    ripeness = "NO-FRUIT"
                    folder = "no-frutas"
                    color = COLOR_MAP["NO-FRUIT"]

                cv2.rectangle(im, (x1,y1), (x2,y2), color, 3)
                cv2.putText(im, f"{label} ({ripeness})", (x1,y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                outs.append({
                    "class": label,
                    "ripeness": ripeness,
                    "confidence": round(conf,2),
                    "bbox": [x1,y1,x2,y2]
                })

        # Subir imagen **procesada** a Cloudinary
        _, buf = cv2.imencode(".jpg", im)
        upload = cloudinary.uploader.upload(buf.tobytes(), folder=folder, resource_type="image",
            context={"class": outs[0]["class"] if outs else "unknown", "ripeness": outs[0]["ripeness"] if outs else "unknown"})

        # Guardar en biblioteca local
        detections_db.append({
            "user_id": session.get("user","anon"),
            "timestamp": datetime.now().isoformat(),
            "label": outs[0]["class"] if outs else "unknown",
            "ripeness": outs[0]["ripeness"] if outs else "unknown",
            "confidence": outs[0]["confidence"] if outs else 0,
            "image_url": upload["secure_url"]
        })

        return jsonify({
            "detections": outs,
            "image": f"data:image/jpeg;base64,{base64.b64encode(buf).decode()}",
            "library": detections_db  # ← biblioteca actualizada
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/upload", methods=["POST"])
def upload():
    file = request.files["file"]
    if not file: return jsonify({"error": "No file"}), 400
    try:
        upload = cloudinary.uploader.upload(file, resource_type="auto")
        im = cv2.imdecode(np.frombuffer(file.read(), np.uint8), cv2.IMREAD_COLOR)
        if im is None: return jsonify({"error": "Formato no válido"}), 400
        model = get_model()
        results = model(im, verbose=False)
        outs = []
        for r in results:
            for box in r.boxes:
                cls = int(box.cls[0])
                x1,y1,x2,y2 = map(int, box.xyxy[0])
                conf = float(box.conf[0])
                label = model.names[cls]
                if cls in FRUIT_IDS:
                    ripeness = ripeness_class(im[y1:y2, x1:x2])
                    folder = "frutas"
                else:
                    ripeness = "NO-FRUIT"
                    folder = "no-frutas"
                outs.append({"class": label, "ripeness": ripeness, "confidence": round(conf,2)})
        detections_db.append({
            "user_id": session.get("user","anon"),
            "timestamp": datetime.now().isoformat(),
            "label": outs[0]["class"] if outs else "unknown",
            "ripeness": outs[0]["ripeness"] if outs else "unknown",
            "confidence": outs[0]["confidence"] if outs else 0,
            "image_url": upload["secure_url"]
        })
        return jsonify({"msg": "Procesado", "detections": outs})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ADMIN
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        user = request.form["user"]
        pwd = request.form["pass"]
        if user == os.getenv("ADMIN_USER") and pwd == os.getenv("ADMIN_PASS"):
            session["admin"] = True
            return redirect(url_for("admin_panel"))
        return "Credenciales inválidas", 403
    return render_template("login.html")

@app.route("/admin")
def admin_panel():
    if not session.get("admin"): return redirect(url_for("admin_login"))
    return render_template("admin.html", detections=detections_db)

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    return redirect(url_for("index"))

@app.route("/admin/export")
def admin_export():
    if not session.get("admin"): return redirect(url_for("admin_login"))
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(["user_id", "timestamp", "label", "ripeness", "confidence", "image_url"])
    for d in detections_db:
        cw.writerow([d["user_id"], d["timestamp"], d["label"], d["ripeness"], d["confidence"], d["image_url"]])
    output = io.BytesIO()
    output.write(si.getvalue().encode('utf-8'))
    output.seek(0)
    return send_file(output, mimetype="text/csv", download_name="detecciones.csv", as_attachment=True)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
