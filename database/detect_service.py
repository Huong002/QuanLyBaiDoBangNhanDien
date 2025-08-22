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


# chèn bien so vao csdl
def insert_np(number_plate):
    count = Numberplate.query.filter_by(number_plate=number_plate).count()
    province = get_province(number_plate)
    if count % 2 == 0:
        # Chẵn: cho vào bãi (status=1)
        new_plate = Numberplate(
            number_plate=number_plate,
            status=1,
            province=province,
            date_in=datetime.utcnow(),
        )
        db.session.add(new_plate)
        print("Xe vào bãi")
        db.session.commit()
        return "in"
    else:
        # Lẻ: cập nhật bản ghi mới nhất status=0, date_out=now
        latest = (
            Numberplate.query.filter_by(number_plate=number_plate)
            .order_by(Numberplate.date_in.desc())
            .first()
        )
        if latest:
            latest.status = 0
            latest.date_out = datetime.utcnow()
            print("Xe ra bãi")
            db.session.commit()
            # Gửi email và trừ tiền nếu có user
            user_email = None
            if latest.user_id:
                user = User.query.get(latest.user_id)
                if user:
                    user_email = user.email
            if user_email:
                send_fee_email(latest.id, 0, [user_email])
            return "out"
        else:
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
    if np and np.status == 1 and new_status == 0:
        # Mỗi lượt ra bãi tính phí cố định 1.000đ
        total_fee = 1000
        user = None
        # Trừ tiền user nếu có user_id
        if np.user_id:
            user = User.query.get(np.user_id)
            if user:
                user.balance = max(0, user.balance - total_fee)
                db.session.commit()

        # Gửi email thông báo (giả lập)
        try:
            from flask_mail import Message
            from app import app

            with app.app_context():
                msg = Message(
                    subject="Thông báo phí gửi xe",
                    recipients=[user_email],
                    body=f"Xe {np.number_plate} đã ra bãi. Phí: {total_fee:,}đ. Số dư còn lại: {user.balance if np.user_id and user else 'N/A'}đ.",
                )
                # mail.send(msg)  # Bỏ comment nếu đã cấu hình Flask-Mail
                print(f"Đã gửi email tới {user_email}")
        except Exception as e:
            print(f"Lỗi gửi email: {e}")
        return True
    return False
