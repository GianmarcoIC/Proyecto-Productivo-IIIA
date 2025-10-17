import os
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader
import cloudinary.api

load_dotenv()

cloudinary.config(
    cloud_name=os.getenv("CLOUD_NAME"),
    api_key=os.getenv("API_KEY"),
    api_secret=os.getenv("API_SECRET")
)

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload():
    file = request.files["file"]
    result = cloudinary.uploader.upload(file, folder="capturas")
    return jsonify(result)

@app.route("/list", methods=["GET"])
def list_images():
    resources = cloudinary.api.resources(
        type="upload",
        prefix="capturas",
        max_results=50
    )
    urls = [res["secure_url"] for res in resources["resources"]]
    return jsonify(urls)

if __name__ == "__main__":
    app.run(debug=True)
