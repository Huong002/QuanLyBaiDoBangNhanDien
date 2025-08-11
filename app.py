from flask import Flask, render_template, request, jsonify
import cv2
import numpy as np
import pytesseract
from ultralytics import YOLO
import sqlite3
import os
import time
from database.number_plate_db import check_np, check_np_status, insert_np, update_np, get_province,get_history,is_vehicle_in_parking
app = Flask(__name__)

# Load model YOLO
model = YOLO("C:/Users/Laptop/Downloads/Demo/Demo/QuanLyBaiDoXe/runs/detect/train3-20250331T033458Z-001/train3/weights/best.pt")

# Cấu hình đường dẫn pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

@app.route('/')
def index():
    return render_template('index.html')

# nhận biển số xe vào và detect
@app.route('/detect', methods=['POST'])
def detect_plate():
    print("Received request:", request.files)  

    if 'image' not in request.files:
        return jsonify({"error": "No image file"}), 400

    file = request.files['image']
    if file.content_type not in ["image/jpeg", "image/png"]:
        return jsonify({"error": "File không hợp lệ"}), 400

    file_bytes = np.frombuffer(file.read(), np.uint8)
    if file_bytes.size == 0:
        return jsonify({"error": "Không thể đọc file"}), 400

    image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    if image is None:
        return jsonify({"error": "Lỗi khi đọc ảnh"}), 400

    print("Kích thước ảnh:", image.shape)
    image = cv2.resize(image, (640, 640))

    results = model(image)
    detected_plate = None

    for result in results:
        for box in result.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            plate_img = image[y1:y2, x1:x2]
            # Tạo thư mục nếu chưa có
            output_dir = "static/images"
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            # Tạo đường dẫn lưu ảnh (đặt tên theo timestamp hoặc biển số xe)
            timestamp = int(time.time())  # Lấy timestamp (giây)
            filename = f"{detected_plate.replace(' ', '_')}_{timestamp}.jpg" if detected_plate else f"unknown_{timestamp}.jpg"
            image_path = os.path.join(output_dir, filename)

            # Lưu ảnh đã cắt
            cv2.imwrite(image_path, plate_img)
            if plate_img.shape[0] < 20 or plate_img.shape[1] < 50:
                continue

            # Tiền xử lý ảnh
            gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)
            gray = cv2.fastNlMeansDenoising(gray, None, 30, 7, 21)  
            gray = cv2.equalizeHist(gray)  

            # CLAHE - tăng độ tương phản
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
            gray = clahe.apply(gray)

            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            # Lưu ảnh debug nếu cần
            cv2.imwrite("debug_plate.jpg", plate_img)
            cv2.imwrite("debug_thresh.jpg", thresh)

            # OCR với psm 7
            config = "--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
            text = pytesseract.image_to_string(thresh, lang='eng', config=config)
            detected_plate = text.strip()
            cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)

    if detected_plate:
        status="Xe vào bãi đổ"
        proviece=get_province(detected_plate)
        check = check_np(detected_plate)
        if check == 0:
            insert_np(detected_plate)
        else:
            check2 = check_np_status(detected_plate)
            print("Giá trị check2:", check2) 
            if check2[2] == 0: 
                status="Xe rời khỏi bãi đổ"
                update_np(check2[0])
            else:
                insert_np(detected_plate)
        return jsonify({
            "plate": detected_plate,
            "province":proviece,
            "image_url": f"/static/images/{filename}",
            "status":status
        })
    return jsonify({"error": "Không tìm thấy biển số"}), 400
#Hàm định dạng ngày giờ
def convert_datetime(dt):
    if dt is None:
        return "Chưa có dữ liệu"
    return dt.strftime("%Y-%m-%d %H:%M:%S")  # Định dạng ngày giờ
# Lấy lịch sử
@app.route('/history', methods=['POST'])
def def_get_history():
    data = request.get_json()
    plate=data.get("plate")
    print("plate:",plate)
    records=get_history(plate)
    # Chuyển đổi datetime thành string
    formatted_records = [
        {
            "plate": r[0],
            "start_time": convert_datetime(r[1]),
            "end_time": convert_datetime(r[2]),
            "status": r[3]
        }
        for r in records
    ]
    return jsonify({"history": formatted_records})
#Hàm trả về trạng thái
@app.route('/check',methods=['POST'])
def check_status():
    data=request.get_json()
    plate=data.get("plate")
    print("plate: ",plate)
    status=is_vehicle_in_parking(plate)
    print("status: ",status)
    return jsonify({"status": status})
if __name__ == '__main__':
    app.run(debug=True)
