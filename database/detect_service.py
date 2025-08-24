from models.user import db, User
from models.number_plated import db, Numberplate
from datetime import datetime


# Database service functions
def check_np(number_plate):
    try:
        count = Numberplate.query.filter_by(number_plate=number_plate).count()
        return count
    except Exception as e:
        print(f"Lỗi check_np: {e}")
        return 0



def insert_np(number_plate):
    try:
        # Lấy tất cả bản ghi của biển số này
        plates = Numberplate.query.filter_by(number_plate=number_plate).all()

        province = get_province(number_plate)

        # Nếu có bản ghi, giữ bản ghi mới nhất và xóa các bản ghi khác
        if plates:
            latest = max(
                plates, key=lambda x: x.date_in
            )  # Lấy bản ghi có date_in mới nhất
            # Xóa tất cả bản ghi trừ bản ghi mới nhất
            for plate in plates:
                if plate.id != latest.id:
                    db.session.delete(plate)
            db.session.commit()

            # Cập nhật trạng thái dựa trên tình trạng hiện tại
            if latest.status == 0:  # Xe đã ra bãi, giờ vào lại
                latest.status = 1
                latest.date_in = datetime.utcnow()
                latest.date_out = None
                latest.user_id = latest.user_id or (
                    User.query.get(1).id if User.query.get(1) else None
                )  # Kế thừa user_id
                db.session.commit()
                print("Xe vào bãi")
                return "in"
            elif latest.status == 1:  # Xe đang trong bãi, giờ ra
                success = update_np(latest.id)
                if success:
                    print("Xe ra bãi")
                    user_email = None
                    if latest.user_id:
                        user = User.query.get(latest.user_id)
                        if user:
                            user_email = user.email
                    print(
                        "tai khoan cua nguoi dung vua ra khoi bai goi la:", user_email
                    )
                    if user_email:
                        send_fee_email(
                            latest.id, 0, user_email
                        )  # Truyền trực tiếp user_email
                    return "out"
        else:  # Nếu không có bản ghi nào, tạo mới
            new_plate = Numberplate(
                number_plate=number_plate,
                status=1,
                province=province,
                date_in=datetime.utcnow(),
                user_id=(
                    User.query.get(1).id if User.query.get(1) else None
                ),  # Gán user_id mặc định nếu có
            )
            db.session.add(new_plate)
            db.session.commit()
            print("Xe vào bãi (bản ghi mới)")
            return "in"

    except Exception as e:
        print(f"Lỗi insert_np: {e}")
        db.session.rollback()
        return False


# lấy tình thành
def get_province(number_plate):
    province_codes = {
        "11": "Cao Bằng",
        "12": "Lạng Sơn",
        "13": "Quảng Ninh",
        "14": "Hải Phòng",
        "15": "Hải Dương",
        "16": "Hưng Yên",
        "17": "Thái Bình",
        "18": "Hà Nam",
        "19": "Nam Định",
        "20": "Phú Thọ",
        "21": "Thái Nguyên",
        "22": "Yên Bái",
        "29": "Hà Nội",
        "30": "Hà Nội",
        "31": "Hà Nội",
        "32": "Hà Nội",
        "33": "Hà Nội",
        "43": "Đà Nẵng",
        "47": "Đắk Lắk",
        "48": "Đắk Nông",
        "49": "Lâm Đồng",
        "50": "TP.HCM",
        "51": "TP.HCM",
        "52": "TP.HCM",
        "53": "TP.HCM",
        "54": "TP.HCM",
        "55": "TP.HCM",
        "56": "TP.HCM",
        "57": "TP.HCM",
        "58": "TP.HCM",
        "59": "TP.HCM",
        "60": "Đồng Nai",
        "61": "Bình Dương",
    }

    if len(number_plate) >= 2:
        code = number_plate[:2]
        return province_codes.get(code, "Không xác định")
    return "Không xác định"


# check trang thai
def check_np_status(number_plate):
    try:
        result = (
            Numberplate.query.filter_by(number_plate=number_plate)
            .order_by(Numberplate.date_in.desc())
            .first()
        )
        if result:
            return (result.id, result.number_plate, result.status)
        return None
    except Exception as e:
        print(f"Lỗi check_np_status: {e}")
        return None


# cap nhap
def update_np(plate_id):
    try:
        plate = Numberplate.query.get(plate_id)
        if plate:
            plate.status = 0
            plate.date_out = datetime.utcnow()
            db.session.commit()
            return True
        return False
    except Exception as e:
        print(f"Lỗi update_np: {e}")
        db.session.rollback()
        return False


# lấy lich su
def get_history(number_plate):
    try:
        records = (
            Numberplate.query.filter_by(number_plate=number_plate)
            .order_by(Numberplate.date_in.desc())
            .all()
        )
        result = []
        for record in records:
            result.append(
                (
                    record.number_plate,
                    record.date_in,
                    record.date_out,
                    "Trong bãi" if record.status == 1 else "Đã ra bãi",
                )
            )
        return result
    except Exception as e:
        print(f"Lỗi get_history: {e}")
        return []


# kiem tra trong bai
def is_vehicle_in_parking(number_plate):
    try:
        latest_record = (
            Numberplate.query.filter_by(number_plate=number_plate)
            .order_by(Numberplate.date_in.desc())
            .first()
        )
        if latest_record and latest_record.status == 1:
            return "Xe đang trong bãi"
        else:
            return "Xe không trong bãi"
    except Exception as e:
        print(f"Lỗi is_vehicle_in_parking: {e}")
        return "Lỗi kiểm tra"


def send_fee_email(id, new_status, user_email):
    np = Numberplate.query.get(id)
    if np and new_status == 0:  # Chỉ kiểm tra new_status
        total_fee = 1000
        user = None
        if np.user_id:
            user = User.query.get(np.user_id)
            if user:
                user.balance = max(0, user.balance - total_fee)
                db.session.commit()

        try:
            from flask_mail import Message
            from app import app, mail  # Đảm bảo mail được import từ app

            with app.app_context():
                msg = Message(
                    subject="Thông báo phí gửi xe",
                    recipients=[
                        user_email
                    ],  # Đảm bảo recipients là danh sách chứa chuỗi
                    body=f"Xe {np.number_plate} đã ra bãi. Phí: {total_fee:,}đ. Số dư còn lại: {user.balance if np.user_id and user else 'N/A'}đ.",
                )
                mail.send(msg)  # Gửi email
                print(f"Đã gửi email tới {user_email} tại {datetime.utcnow()}")
        except Exception as e:
            print(f"Lỗi gửi email tại {datetime.utcnow()}: {str(e)}")
            import traceback

            traceback.print_exc()
        return True
    return False
