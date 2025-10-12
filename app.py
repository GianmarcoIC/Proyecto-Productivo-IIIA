from flask import Flask, render_template, request, jsonify, Response
import base64
from io import BytesIO
from PIL import Image
import cv2
import numpy as np
from ultralytics import YOLO
import os

app = Flask(__name__)

# Cargar modelo YOLOv8 (pre-entrenado; reemplaza con custom si entrenas con Label Studio)
model = YOLO('yolov8n.pt')  # Nano para velocidad en Render

# Clases de frutas en COCO (filtramos solo frutas)
FRUIT_CLASSES = [46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58]  # apple, banana, orange, etc.

def classify_ripeness(image_crop):
    """Clasifica maduración basada en color HSV (avanzado: umbrales por fruta, pero simple aquí)"""
    hsv = cv2.cvtColor(image_crop, cv2.COLOR_BGR2HSV)
    # Ejemplo para frutas amarillas/rojas: alto en S/V para maduro
    saturation = np.mean(hsv[:,:,1])
    value = np.mean(hsv[:,:,2])
    if saturation < 50 and value > 150:  # Verde/inmaduro
        return "Inmaduro"
    elif saturation > 100 and value > 100:  # Amarillo/rojo/maduro
        return "Maduro"
    else:
        return "Sobremaduro"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/detect', methods=['POST'])
def detect():
    try:
        # Recibir imagen base64 de JS
        data = request.json['image']
        # Decodificar base64 a imagen
        img_data = base64.b64decode(data.split(',')[1])
        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Inferencia YOLOv8
        results = model(img, verbose=False)
        
        detections = []
        for r in results:
            boxes = r.boxes
            if boxes is not None:
                for box in boxes:
                    cls = int(box.cls[0])
                    if cls in FRUIT_CLASSES:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        conf = float(box.conf[0])
                        crop = img[y1:y2, x1:x2]
                        ripeness = classify_ripeness(crop)
                        detections.append({
                            'class': model.names[cls],
                            'confidence': conf,
                            'ripeness': ripeness,
                            'bbox': [x1, y1, x2, y2]
                        })
        
        # Dibujar resultados en imagen (opcional, para return)
        annotated = results[0].plot()
        
        # Codificar de vuelta a base64 para JS
        _, buffer = cv2.imencode('.jpg', annotated)
        img_str = base64.b64encode(buffer).decode('utf-8')
        
        return jsonify({'detections': detections, 'image': f'data:image/jpeg;base64,{img_str}'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
