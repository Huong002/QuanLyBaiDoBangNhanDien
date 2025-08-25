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
    update_np,
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


@app.route("/checkout")
def checkout_page():
    """Trang cho xe ra bãi"""
    return render_template("checkout.html")


@app.route("/api/vehicles-in-parking")
def api_vehicles_in_parking():
    """API để lấy danh sách xe đang trong bãi"""
    try:
        vehicles_in_parking = (
            Numberplate.query.filter_by(status=1)
            .order_by(Numberplate.created_at.desc())
            .all()
        )
        
        vehicles_data = []
        for vehicle in vehicles_in_parking:
            # Tính thời gian đỗ xe
            if vehicle.created_at:
                duration = datetime.now() - vehicle.created_at
                duration_str = f"{duration.days} ngày, {duration.seconds // 3600} giờ, {(duration.seconds % 3600) // 60} phút"
            else:
                duration_str = "Không xác định"
                
            vehicles_data.append({
                "id": vehicle.id,
                "number_plate": vehicle.number_plate,
                "created_at": vehicle.created_at.strftime("%H:%M:%S %d/%m/%Y") if vehicle.created_at else "N/A",
                "duration": duration_str,
                "province": vehicle.province,
                "status": "Trong bãi"
            })
        
        return jsonify({
            "success": True,
            "vehicles": vehicles_data,
            "count": len(vehicles_data)
        })
        
    except Exception as e:
        return jsonify({"success": False, "message": f"Lỗi: {str(e)}"}), 500


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
    """Trang báo cáo động"""
    try:
        from datetime import timedelta
        from sqlalchemy import func, extract
        
        today = datetime.now().date()
        
        # Báo cáo ngày - Xe vào hôm nay
        daily_in = Numberplate.query.filter(
            db.func.date(Numberplate.created_at) == today
        ).count()

        # Báo cáo tuần (7 ngày gần đây)
        week_ago = today - timedelta(days=6)  # 7 ngày gần đây
        weekly_data = []
        total_week = 0

        for i in range(7):
            day = week_ago + timedelta(days=i)
            count = Numberplate.query.filter(
                db.func.date(Numberplate.created_at) == day
            ).count()
            weekly_data.append({"date": day.strftime("%d/%m"), "count": count})
            total_week += count

        # Tính toán thống kê tổng quan
        avg_daily = round(total_week / 7) if total_week > 0 else 0
        peak_day = max([day['count'] for day in weekly_data]) if weekly_data else 0

        # Top xe ra vào nhiều nhất (trong 30 ngày)
        month_ago = today - timedelta(days=30)
        top_vehicles_query = db.session.query(
            Numberplate.number_plate,
            func.count(Numberplate.id).label('visit_count'),
            func.max(Numberplate.created_at).label('last_visit')
        ).filter(
            Numberplate.created_at >= month_ago
        ).group_by(
            Numberplate.number_plate
        ).order_by(
            func.count(Numberplate.id).desc()
        ).limit(5).all()

        # Xử lý dữ liệu top vehicles với thông tin ngày
        top_vehicles = []
        for vehicle in top_vehicles_query:
            days_ago = (today - vehicle.last_visit.date()).days
            if days_ago == 0:
                last_visit_text = "Hôm nay"
            elif days_ago == 1:
                last_visit_text = "Hôm qua"
            else:
                last_visit_text = f"{days_ago} ngày trước"
            
            top_vehicles.append({
                'number_plate': vehicle.number_plate,
                'visit_count': vehicle.visit_count,
                'last_visit_text': last_visit_text
            })

        # Phân tích theo khung giờ
        hourly_stats = {
            'morning': 0,    # 6-12h
            'afternoon': 0,  # 12-18h
            'evening': 0,    # 18-24h
            'night': 0       # 0-6h
        }
        
        # Lấy dữ liệu tuần này để phân tích giờ
        week_start = today - timedelta(days=6)
        hourly_records = Numberplate.query.filter(
            Numberplate.created_at >= week_start
        ).all()

        total_hourly = len(hourly_records)
        if total_hourly > 0:
            for record in hourly_records:
                hour = record.created_at.hour
                if 6 <= hour < 12:
                    hourly_stats['morning'] += 1
                elif 12 <= hour < 18:
                    hourly_stats['afternoon'] += 1
                elif 18 <= hour < 24:
                    hourly_stats['evening'] += 1
                else:  # 0-6h
                    hourly_stats['night'] += 1

        # Tính phần trăm
        hourly_percentages = {}
        for period, count in hourly_stats.items():
            hourly_percentages[period] = round((count / total_hourly) * 100) if total_hourly > 0 else 0

        # Dữ liệu cho biểu đồ phân bố giờ
        hourly_chart_data = [
            hourly_percentages['morning'],
            hourly_percentages['afternoon'], 
            hourly_percentages['evening'],
            hourly_percentages['night']
        ]

        # Tổng số xe trong bãi hiện tại
        current_in_parking = Numberplate.query.filter(Numberplate.status == 1).count()

        return render_template(
            "reports.html", 
            daily_in=daily_in, 
            weekly_data=weekly_data,
            total_week=total_week,
            avg_daily=avg_daily,
            peak_day=peak_day,
            top_vehicles=top_vehicles,
            hourly_percentages=hourly_percentages,
            hourly_chart_data=hourly_chart_data,
            current_in_parking=current_in_parking
        )
    except Exception as e:
        print(f"Lỗi báo cáo: {e}")
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


@app.route("/api/checkout-vehicle", methods=["POST"])
def checkout_vehicle():
    """API để cho xe ra khỏi bãi đậu xe"""
    try:
        data = request.get_json()
        number_plate = data.get("number_plate")
        
        if not number_plate:
            return jsonify({"success": False, "message": "Thiếu thông tin biển số"}), 400
        
        # Tìm xe trong bãi
        vehicle = Numberplate.query.filter_by(
            number_plate=number_plate, 
            status=1
        ).order_by(Numberplate.created_at.desc()).first()
        
        if not vehicle:
            return jsonify({
                "success": False, 
                "message": f"Không tìm thấy xe {number_plate} trong bãi"
            }), 404
        
        # Cập nhật trạng thái xe ra bãi
        vehicle.status = 0
        vehicle.date_out = datetime.now()
        db.session.commit()
        
        # Tính thời gian đỗ xe
        if vehicle.created_at:
            duration = datetime.now() - vehicle.created_at
            duration_str = f"{duration.days} ngày, {duration.seconds // 3600} giờ, {(duration.seconds % 3600) // 60} phút"
        else:
            duration_str = "Không xác định"
        
        # Gửi email thông báo phí (nếu có user)
        user_email = None
        if vehicle.user_id:
            user = User.query.get(vehicle.user_id)
            if user:
                user_email = user.email
                # Gửi email thông báo phí
                from database.detect_service import send_fee_email
                send_fee_email(vehicle.id, 0, user_email)
        
        return jsonify({
            "success": True,
            "message": f"Xe {number_plate} đã ra khỏi bãi thành công",
            "duration": duration_str,
            "checkout_time": vehicle.date_out.strftime("%H:%M:%S %d/%m/%Y")
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Lỗi xử lý: {str(e)}"}), 500


@app.route("/api/search-vehicle", methods=["GET"])
def search_vehicle():
    """API để tìm kiếm thông tin xe trong bãi"""
    try:
        number_plate = request.args.get("number_plate")
        
        if not number_plate:
            return jsonify({"success": False, "message": "Thiếu thông tin biển số"}), 400
        
        # Tìm xe trong bãi
        vehicle = Numberplate.query.filter_by(
            number_plate=number_plate, 
            status=1
        ).order_by(Numberplate.created_at.desc()).first()
        
        if not vehicle:
            return jsonify({
                "success": False, 
                "message": f"Không tìm thấy xe {number_plate} trong bãi"
            })
        
        # Tính thời gian đỗ xe
        if vehicle.created_at:
            duration = datetime.now() - vehicle.created_at
            duration_str = f"{duration.days} ngày, {duration.seconds // 3600} giờ, {(duration.seconds % 3600) // 60} phút"
        else:
            duration_str = "Không xác định"
        
        return jsonify({
            "success": True,
            "vehicle": {
                "id": vehicle.id,
                "number_plate": vehicle.number_plate,
                "created_at": vehicle.created_at.strftime("%H:%M:%S %d/%m/%Y") if vehicle.created_at else "N/A",
                "duration": duration_str,
                "province": vehicle.province,
                "status": "Trong bãi"
            }
        })
        
    except Exception as e:
        return jsonify({"success": False, "message": f"Lỗi tìm kiếm: {str(e)}"}), 500


@app.route("/cleanup-temp-images", methods=["POST"])
def cleanup_temp_images():
    """API để dọn dẹp ảnh tạm thời cũ"""
    try:
        import glob
        from datetime import datetime, timedelta
        
        temp_dir = os.path.join("static", "images")
        if not os.path.exists(temp_dir):
            return jsonify({"success": True, "message": "Thư mục temp không tồn tại"})
        
        # Xóa file temp cũ hơn 1 giờ
        cutoff_time = time.time() - 3600  # 1 hour ago
        deleted_count = 0
        
        for file_path in glob.glob(os.path.join(temp_dir, "temp_plate_*.jpg")):
            if os.path.getctime(file_path) < cutoff_time:
                try:
                    os.remove(file_path)
                    deleted_count += 1
                except Exception as e:
                    print(f"Error deleting {file_path}: {e}")
        
        return jsonify({
            "success": True, 
            "message": f"Đã xóa {deleted_count} ảnh tạm thời cũ"
        })
        
    except Exception as e:
        return jsonify({"success": False, "message": f"Lỗi dọn dẹp: {str(e)}"}), 500


@app.route("/confirm-detection", methods=["POST"])
def confirm_detection():
    """API endpoint để xác nhận lưu kết quả nhận diện từ camera"""
    try:
        data = request.get_json()
        number_plate = data.get("number_plate")
        temp_image_path = data.get("temp_image_path")
        
        if not number_plate:
            return jsonify({"success": False, "message": "Thiếu thông tin biển số"}), 400
        
        # Lưu vào database
        result = insert_np(number_plate)
        if result == "in":
            status = "Xe vào bãi đỗ"
        elif result == "out":
            status = "Xe ra khỏi bãi"
        else:
            status = "Không xác định trạng thái"
        
        # Di chuyển ảnh từ temp sang permanent nếu có
        final_image_url = None
        if temp_image_path:
            try:
                import shutil
                # Tạo tên file mới cho ảnh vĩnh viễn
                import uuid
                save_name = f"plate_{uuid.uuid4().hex}.jpg"
                final_path = os.path.join("static", "image", save_name)
                
                # Di chuyển từ temp sang permanent
                temp_full_path = os.path.join("static", temp_image_path.replace("/static/", ""))
                if os.path.exists(temp_full_path):
                    shutil.move(temp_full_path, final_path)
                    final_image_url = url_for("static", filename=f"image/{save_name}")
            except Exception as e:
                print(f"Error moving temp image: {e}")
        
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
        
        return jsonify({
            "success": True,
            "message": f"Đã lưu biển số {number_plate}",
            "status": status,
            "final_image": final_image_url,
            "history": history_data
        })
        
    except Exception as e:
        return jsonify({"success": False, "message": f"Lỗi xác nhận: {str(e)}"}), 500


@app.route("/detect", methods=["POST"])
def detect_plate():
    """API endpoint để nhận diện biển số"""
    
    # Kiểm tra xem có phải request xác nhận ra bãi không (chỉ có biển số, không có ảnh)
    direct_plate = request.form.get("number_plate")
    if direct_plate and request.form.get("action") == "exit":
        # Xử lý trường hợp xác nhận ra bãi trực tiếp
        try:
            vehicle_status = check_np_status(direct_plate)
            if vehicle_status and vehicle_status[2] == 1:  # Xe đang trong bãi
                result = update_np(vehicle_status[0])
                if result:
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
                    
                    return jsonify({
                        "success": True,
                        "number_plate": direct_plate,
                        "status": "Xe ra khỏi bãi thành công",
                        "message": "Xe đã được cho ra bãi",
                        "history": history_data,
                        "vehicle_in_parking": False,
                    })
                else:
                    return jsonify({
                        "success": False,
                        "message": "Lỗi khi cho xe ra bãi"
                    }), 500
            else:
                return jsonify({
                    "success": False,
                    "message": "Xe không có trong bãi hoặc đã ra bãi"
                }), 400
        except Exception as e:
            return jsonify({
                "success": False,
                "message": f"Lỗi xử lý ra bãi: {str(e)}"
            }), 500
    
    # Logic cũ cho trường hợp có ảnh
    if "image" not in request.files:
        return jsonify({"success": False, "message": "Không có ảnh được tải lên"}), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify({"success": False, "message": "Không có file được chọn"}), 400

    try:
        import tempfile
        import uuid
        from PIL import Image

        # Lấy thông tin OCR engine từ form (mặc định là PaddleOCR)
        use_paddle_ocr = request.form.get("ocr_engine", "paddle") == "paddle"

        # Lưu file ảnh tạm thời
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            file.save(tmp.name)
            image_path = tmp.name

        # Nhận diện biển số bằng YOLO và OCR đã chọn
        number_plate, plate_crop = detect_plate_yolo(
            image_path, use_paddle_ocr=use_paddle_ocr
        )

        # Cleanup temporary file
        try:
            os.unlink(image_path)
        except:
            pass

        if number_plate:
            province = get_province(number_plate)
            
            # Kiểm tra xem có phải request từ camera không
            is_camera_request = request.form.get("source") == "camera"
            
            # Kiểm tra trạng thái xe trong database
            vehicle_status = check_np_status(number_plate)
            
            # Nếu xe đang trong bãi (status=1), hiển thị thông báo xác nhận ra bãi
            if vehicle_status and vehicle_status[2] == 1:  # status == 1 có nghĩa là xe đang trong bãi
                needs_exit_confirmation = True
                status = "Xe đang trong bãi - Xác nhận cho ra?"
                should_save_to_db = request.form.get("confirmed") == "true" and request.form.get("action") == "exit"
            else:
                needs_exit_confirmation = False
                # Logic cũ cho xe vào bãi
                should_save_to_db = not is_camera_request or request.form.get("confirmed") == "true"
                
            if should_save_to_db:
                if needs_exit_confirmation or (vehicle_status and vehicle_status[2] == 1):
                    # Cho xe ra bãi
                    result = update_np(vehicle_status[0])  # vehicle_status[0] là plate_id
                    if result:
                        status = "Xe ra khỏi bãi thành công"
                    else:
                        status = "Lỗi khi cho xe ra bãi"
                else:
                    # Logic cũ cho xe vào bãi
                    result = insert_np(number_plate)
                    if result == "in":
                        status = "Xe vào bãi đỗ"
                    elif result == "out":
                        status = "Xe ra khỏi bãi"
                    else:
                        status = "Không xác định trạng thái"
            elif needs_exit_confirmation:
                status = "Xe đang trong bãi - Xác nhận cho ra?"
            else:
                status = "Chờ xác nhận"

            # Lưu ảnh crop biển số - với prefix khác nhau cho camera và upload
            plate_image_url = None
            if plate_crop:
                if is_camera_request and not should_save_to_db:
                    # Lưu ảnh tạm thời cho camera preview
                    save_name = f"temp_plate_{uuid.uuid4().hex}.jpg"
                    save_path = os.path.join("static", "images", save_name)
                else:
                    # Lưu ảnh vĩnh viễn cho upload hoặc camera đã xác nhận
                    save_name = f"plate_{uuid.uuid4().hex}.jpg"
                    save_path = os.path.join("static", "image", save_name)
                
                # Tạo thư mục nếu chưa có
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                plate_crop.save(save_path)
                
                if is_camera_request and not should_save_to_db:
                    plate_image_url = url_for("static", filename=f"images/{save_name}")
                else:
                    plate_image_url = url_for("static", filename=f"image/{save_name}")

            # Lấy lịch sử mới nhất chỉ khi đã lưu vào database
            history_data = []
            if should_save_to_db:
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
                    "is_camera": is_camera_request,
                    "needs_confirmation": is_camera_request and not should_save_to_db,
                    "needs_exit_confirmation": needs_exit_confirmation if 'needs_exit_confirmation' in locals() else False,
                    "vehicle_in_parking": vehicle_status[2] == 1 if vehicle_status else False,
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
        
        # Log chi tiết lỗi
        print(f"Error in detect_plate: {str(e)}")
        traceback.print_exc()
        
        # Cleanup temporary file if exists
        try:
            if 'image_path' in locals():
                os.unlink(image_path)
        except:
            pass
            
        return jsonify({
            "success": False, 
            "message": f"Lỗi xử lý: {str(e)}",
            "error_type": type(e).__name__
        }), 500
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
        
        # Dọn dẹp ảnh temp cũ khi khởi động
        try:
            import glob
            temp_dir = os.path.join("static", "images")
            if os.path.exists(temp_dir):
                cutoff_time = time.time() - 3600  # 1 hour ago
                deleted_count = 0
                for file_path in glob.glob(os.path.join(temp_dir, "temp_plate_*.jpg")):
                    if os.path.getctime(file_path) < cutoff_time:
                        try:
                            os.remove(file_path)
                            deleted_count += 1
                        except:
                            pass
                print(f"Cleaned up {deleted_count} old temp images")
        except:
            pass
            
    app.run(debug=True, port=5001)
