from flask import Flask, render_template, request, jsonify, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import time
from datetime import datetime, timedelta
from database.detect_service import (
    insert_np,
    get_history,
    get_province,
    check_np_status,
    check_np,
)
from utils.image_processing import detect_plate_yolo
from models.user import db, User
from models import db
from models.number_plated import db, Numberplate
import config.database as db_config
from utils.prediction import train_model, du_doan_so_xe, predict_hourly
from flask_mail import Mail

import os

app = Flask(__name__)

# cấu hình cho migration:
app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"postgresql://{db_config.DB_CONFIG['user']}:{db_config.DB_CONFIG['password']}"
    f"@{db_config.DB_CONFIG['host']}:{db_config.DB_CONFIG['port']}/{db_config.DB_CONFIG['database']}"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
# cấu hình cho maikl
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = "0022410481@student.dthu.edu.vn"
app.config["MAIL_PASSWORD"] = "xdfd xhtm tdxn ibne"
app.config["MAIL_DEFAULT_SENDER"] = "psymint002@gmail.com"

mail = Mail(app)
db.init_app(app)
migrate = Migrate(app, db)


@app.route("/")
def index():
    try:
        # Thống kê cho dashboard
        total_cars = Numberplate.query.filter_by(status=1).count()  # Xe đang trong bãi
        total_records = Numberplate.query.count()  # Tổng số lượt

        # Xe vào hôm nay
        today = datetime.now().date()
        cars_in_today = Numberplate.query.filter(
            db.func.date(Numberplate.created_at) == today, Numberplate.status == 1
        ).count()

        # Xe ra hôm nay (dựa trên date_out nếu có)
        cars_out_today = Numberplate.query.filter(
            db.func.date(Numberplate.date_out) == today
        ).count()

        # Chỗ trống (giả sử tổng chỗ là 200)
        total_spots = 200
        available_spots = total_spots - total_cars

        # Lịch sử nhận diện gần đây
        recent_history = (
            Numberplate.query.order_by(Numberplate.created_at.desc()).limit(5).all()
        )

        # Dữ liệu tuần (7 ngày gần nhất)
        week_ago = today - timedelta(days=6)
        weekly_data = []
        for i in range(7):
            day = week_ago + timedelta(days=i)
            count = Numberplate.query.filter(
                db.func.date(Numberplate.created_at) == day
            ).count()
            weekly_data.append({"date": day.strftime("%d/%m"), "count": count})

        return render_template(
            "dashboard.html",
            total_cars=total_cars,
            cars_in_today=cars_in_today,
            cars_out_today=cars_out_today,
            available_spots=available_spots,
            total_records=total_records,
            recent_history=recent_history,
            weekly_data=weekly_data,
        )
    except Exception as e:
        return f"Lỗi: {e}", 500


@app.route("/detect")
def detect_page():
    """Hiển thị trang nhận diện biển số"""
    try:
        # Lấy lịch sử nhận diện gần đây
        recent_history = (
            Numberplate.query.order_by(Numberplate.created_at.desc()).limit(10).all()
        )
        history_data = [
            {
                "id": record.id,
                "plate_text": record.number_plate,
                "created_at": (
                    record.created_at.strftime("%H:%M:%S %d/%m/%Y")
                    if record.created_at
                    else None
                ),
                "plate_image": None,
                "confidence": None,
                "status": record.status,
            }
            for record in recent_history
        ]
        return render_template("detect.html", history=history_data)
    except Exception as e:
        return f"Lỗi: {e}", 500


@app.route("/test-insert")
def test_insert():
    try:
        timestamp = int(time.time())
        test_plate = f"30A-{timestamp % 10000:04d}"

        success = insert_np(test_plate)
        if success:
            return jsonify(
                {
                    "status": "success",
                    "message": f"Test record {test_plate} inserted successfully!",
                }
            )
        else:
            return jsonify(
                {"status": "error", "message": "Failed to insert test record"}
            )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


@app.route("/vehicles")
def vehicles():
    """Trang quản lý xe"""
    try:
        # Xe đang trong bãi
        vehicles_in_parking = (
            Numberplate.query.filter_by(status=1)
            .order_by(Numberplate.created_at.desc())
            .all()
        )
        return render_template("vehicles.html", vehicles=vehicles_in_parking)
    except Exception as e:
        return f"Lỗi: {e}", 500


@app.route("/history")
def history():
    """Trang lịch sử ra vào"""
    try:
        # Lấy tất cả lịch sử
        all_history = Numberplate.query.order_by(Numberplate.created_at.desc()).all()
        return render_template("history.html", history=all_history)
    except Exception as e:
        return f"Lỗi: {e}", 500


@app.route("/reports")
def reports():
    """Trang báo cáo"""
    try:
        # Thống kê cơ bản cho báo cáo
        today = datetime.now().date()

        # Báo cáo ngày
        daily_in = Numberplate.query.filter(
            db.func.date(Numberplate.created_at) == today
        ).count()

        # Báo cáo tuần (7 ngày gần đây)
        from datetime import timedelta

        week_ago = today - timedelta(days=7)
        weekly_data = []

        for i in range(7):
            day = week_ago + timedelta(days=i)
            count = Numberplate.query.filter(
                db.func.date(Numberplate.created_at) == day
            ).count()
            weekly_data.append({"date": day.strftime("%d/%m"), "count": count})

        return render_template(
            "reports.html", daily_in=daily_in, weekly_data=weekly_data
        )
    except Exception as e:
        return f"Lỗi: {e}", 500


@app.route("/settings")
def settings():
    """Trang cài đặt"""
    return render_template("settings.html")


@app.route("/api/dashboard-data")
def dashboard_data():
    """API để lấy dữ liệu dashboard (AJAX)"""
    try:
        total_cars = Numberplate.query.filter_by(status=1).count()
        today = datetime.now().date()
        cars_in_today = Numberplate.query.filter(
            db.func.date(Numberplate.created_at) == today, Numberplate.status == 1
        ).count()

        return jsonify(
            {
                "total_cars": total_cars,
                "cars_in_today": cars_in_today,
                "cars_out_today": 0,  # Implement logic xe ra
                "available_spots": 200 - total_cars,
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/system-info")
def system_info():
    """API để lấy thông tin hệ thống"""
    try:
        import sys
        import flask
        import psutil

        total_records = Numberplate.query.count()

        # Get system info
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent()
        disk = psutil.disk_usage("/")

        return jsonify(
            {
                "total_records": total_records,
                "db_size": "25.4 MB",  # Mock data - implement actual DB size check
                "stored_images": (
                    len(os.listdir("static/image"))
                    if os.path.exists("static/image")
                    else 0
                ),
                "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                "flask_version": flask.__version__,
                "uptime": "2 hours 30 minutes",  # Mock data - implement actual uptime
                "memory_usage": f"{memory.percent:.1f}%",
                "cpu_usage": f"{cpu_percent:.1f}%",
                "disk_space": f"{disk.percent:.1f}% used",
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/save-system-settings", methods=["POST"])
def save_system_settings():
    """API để lưu cài đặt hệ thống"""
    try:
        settings = request.json
        # TODO: Implement actual settings save to database or config file
        return jsonify({"success": True, "message": "Cài đặt đã được lưu"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/save-detection-settings", methods=["POST"])
def save_detection_settings():
    """API để lưu cài đặt nhận diện"""
    try:
        settings = request.json
        # TODO: Implement actual detection settings save
        return jsonify({"success": True, "message": "Cài đặt nhận diện đã được lưu"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/detect", methods=["POST"])
def detect_plate():
    """API endpoint để nhận diện biển số"""
    if "image" not in request.files:
        return jsonify({"success": False, "message": "Không có ảnh được tải lên"}), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify({"success": False, "message": "Không có file được chọn"}), 400

    try:
        import tempfile
        import uuid
        from PIL import Image

        # Lưu file ảnh tạm thời
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            file.save(tmp.name)
            image_path = tmp.name

        # Nhận diện biển số bằng YOLO và OCR
        number_plate, plate_crop = detect_plate_yolo(image_path)

        if number_plate:
            province = get_province(number_plate)
            result = insert_np(number_plate)
            if result == "in":
                status = "Xe vào bãi đỗ"
            elif result == "out":
                status = "Xe ra khỏi bãi"
            else:
                status = "Không xác định trạng thái"

            # Lưu ảnh crop biển số vào static để trả về giao diện
            plate_image_url = None
            if plate_crop:
                save_name = f"plate_{uuid.uuid4().hex}.jpg"
                save_path = os.path.join("static", "image", save_name)
                plate_crop.save(save_path)
                plate_image_url = url_for("static", filename=f"image/{save_name}")

            # Lấy lịch sử mới nhất
            recent_history = (
                Numberplate.query.order_by(Numberplate.created_at.desc()).limit(5).all()
            )
            history_data = [
                {
                    "id": record.id,
                    "plate_text": record.number_plate,
                    "created_at": (
                        record.created_at.strftime("%H:%M:%S %d/%m/%Y")
                        if record.created_at
                        else None
                    ),
                    "status": record.status,
                }
                for record in recent_history
            ]

            return jsonify(
                {
                    "success": True,
                    "number_plate": number_plate,
                    "plate_image": plate_image_url,
                    "province": province,
                    "status": status,
                    "confidence": 0.85,
                    "message": "Nhận diện thành công",
                    "history": history_data,
                }
            )
        else:
            return jsonify(
                {
                    "success": False,
                    "message": "Không nhận diện được biển số xe trong ảnh",
                }
            )

    except Exception as e:
        import traceback

        traceback.print_exc()
        return jsonify({"success": False, "message": f"Lỗi xử lý: {str(e)}"}), 500
    finally:
        # Xóa file tạm
        try:
            os.unlink(image_path)
        except:
            pass


# ham du doan so luong xe vao
# @app.route('/predict', methods=['GET', 'POST'])
# def predict():
#     prediction = None
#     if request.method == 'POST':
#         thoi_gian = request.form.get('datetime')
#         if thoi_gian:
#             prediction = du_doan_so_xe(thoi_gian)
#     return render_template('prediction.html', prediction=prediction)

model = train_model(data_source="csv", csv_path="utils/dataset.csv", app=app)


@app.route("/predict", methods=["GET", "POST"])
def predict():
    global model
    prediction = None
    error = None
    from datetime import datetime, timedelta

    data_source = (
        request.args.get("data_source") or request.form.get("data_source") or "csv"
    )

    # Huấn luyện lại model theo nguồn dữ liệu mỗi lần load trang hoặc submit
    try:
        model = train_model(
            data_source=data_source, csv_path="utils/dataset.csv", app=app
        )
    except Exception as e:
        error = f"Lỗi: {str(e)}"

    week_labels = [
        (datetime.now() + timedelta(days=i)).strftime("%d/%m") for i in range(7)
    ]
    week_predictions = [
        du_doan_so_xe(
            (datetime.now() + timedelta(days=i)).strftime("%Y-%m-%dT%H:%M"), model
        )
        for i in range(7)
    ]

    datetime_value = ""
    if request.method == "POST":
        thoi_gian = request.form.get("datetime")
        datetime_value = thoi_gian
        try:
            if thoi_gian:
                prediction = du_doan_so_xe(thoi_gian, model)
        except Exception as e:
            error = f"Lỗi: {str(e)}"

    # Nếu là GET và có query param datetime thì cũng giữ lại
    if request.method == "GET":
        datetime_value = request.args.get("datetime", "")

    return render_template(
        "prediction.html",
        prediction=prediction,
        week_labels=week_labels,
        week_predictions=week_predictions,
        data_source=data_source,
        error=error,
        datetime_value=datetime_value,
    )


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        print("Database tables created/verified!")
        print("App running in test mode (no YOLO)")
    app.run(debug=True, port=5001)
