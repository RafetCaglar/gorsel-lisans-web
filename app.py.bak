
import os
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify
from werkzeug.utils import secure_filename
from utils import analyze_image

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "heic", "tif", "tiff"}

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        if "file" not in request.files:
            return render_template("index.html", error="Dosya alınamadı.")
        file = request.files["file"]
        if file.filename == "":
            return render_template("index.html", error="Bir dosya seçin.")
        if file and allowed_file(file.filename):
            fname = secure_filename(file.filename)
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], fname)
            file.save(save_path)
            result = analyze_image(save_path)
            return render_template("result.html", result=result, image_url=url_for("uploaded_file", filename=fname))
        return render_template("index.html", error="Desteklenmeyen dosya türü.")
    return render_template("index.html")

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    # Optional: API endpoint for programmatic use
    if "file" not in request.files:
        return jsonify({"error": "Dosya alınamadı."}), 400
    file = request.files["file"]
    if file.filename == "" or not allowed_file(file.filename):
        return jsonify({"error": "Geçersiz dosya."}), 400
    fname = secure_filename(file.filename)
    save_path = os.path.join(app.config["UPLOAD_FOLDER"], fname)
    file.save(save_path)
    result = analyze_image(save_path)
    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
