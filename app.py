from flask import Flask, render_template, request, jsonify, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import time
from datetime import datetime
from database.detect_service import insert_np, get_history, get_province , check_np_status, check_np
from utils.image_processing import detect_plate_yolo
from models.user import db, User
from models.number_plated import db, Numberplate

import os
app = Flask(__name__)

# cấu hình cho migration:
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:150600@localhost:5432/machine'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
migrate = Migrate(app, db)



@app.route('/')
def index():
    try:
        count = Numberplate.query.count()
        return render_template('templates/index.html', record_count=count)
    except Exception as e:
        return f"Lỗi: {e}", 500

@app.route('/test-insert')
def test_insert():
    try:
        timestamp = int(time.time())
        test_plate = f"30A-{timestamp % 10000:04d}"
        
        success = insert_np(test_plate)
        if success:
            return jsonify({
                "status": "success",
                "message": f"Test record {test_plate} inserted successfully!"
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Failed to insert test record"
            })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        })

@app.route('/detect', methods=['POST'])
def detect_plate():
    if 'image' not in request.files:
        return jsonify({"error": "No image uploaded"}), 400
    file = request.files['image']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    import tempfile
    import uuid
    from PIL import Image
    # Lưu file ảnh tạm thời
    with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp:
        file.save(tmp.name)
        image_path = tmp.name

    # Nhận diện biển số bằng YOLO và OCR
    number_plate, plate_crop = detect_plate_yolo(image_path)
    if number_plate:
        province = get_province(number_plate)
        check = check_np(number_plate)
        if check == 0:
            insert_np(number_plate)
            status = "Xe vào bãi đỗ"
        else:
            check2 = check_np_status(number_plate)
            if check2 and check2[2] == 1:
                status = "Xe đang trong bãi"
            else:
                insert_np(number_plate)
                status = "Xe vào bãi đỗ"
        # Lưu ảnh crop biển số vào static để trả về giao diện
        image_url = None
        if plate_crop:
            save_name = f"plate_{uuid.uuid4().hex}.jpg"
            save_path = os.path.join('static', 'image', save_name)
            plate_crop.save(save_path)
            image_url = url_for('static', filename=f'image/{save_name}')
        return jsonify({
            "plate": number_plate,
            "province": province,
            "status": status,
            "image_url": image_url,
            "message": "Nhận diện thành công"
        })
    else:
        return jsonify({
            "plate": None,
            "province": None,
            "status": None,
            "image_url": None,
            "message": "Không nhận diện được biển số xe"
        })

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("Database tables created/verified!")
        print("App running in test mode (no YOLO)")
    app.run(debug=True, port=5001)
