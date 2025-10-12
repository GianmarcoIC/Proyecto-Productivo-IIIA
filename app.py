from flask import Flask, render_template, request, jsonify
import base64
import cv2
import numpy as np
from PIL import Image
from ultralytics import YOLO
import os

app = Flask(__name__)

# Descargar pesos la primera vez si no existen
if not os.path.exists("yolov8n.pt"):
    YOLO("yolov8n.pt")          # fuerza la descarga

model = YOLO("yolov8n.pt")      # nano para velocidad en Render

# Índices COCO de frutas
FRUIT_CLASSES = [46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58]

def classify_ripeness(crop):
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    saturation = np.mean(hsv[:, :, 1])
    value      = np.mean(hsv[:, :, 2])
    if saturation < 50 and value > 150:
        return "Inmaduro"
    elif saturation > 100 and value > 100:
        return "Maduro"
    return "Sobremaduro"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/detect', methods=['POST'])
def detect():
    try:
        img_bytes = base64.b64decode(request.json['image'].split(',')[1])
        img = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)

        results = model(img, verbose=False)
        detections = []

        for r in results:
            if r.boxes is not None:
                for box in r.boxes:
                    cls = int(box.cls[0])
                    if cls in FRUIT_CLASSES:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        conf = float(box.conf[0])
                        ripeness = classify_ripeness(img[y1:y2, x1:x2])
                        detections.append({
                            'class': model.names[cls],
                            'confidence': conf,
                            'ripeness': ripeness,
                            'bbox': [x1, y1, x2, y2]
                        })

        annotated = results[0].plot()
        _, buf = cv2.imencode('.jpg', annotated)
        b64 = base64.b64encode(buf).decode()
        return jsonify({'detections': detections, 'image': f'data:image/jpeg;base64,{b64}'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
