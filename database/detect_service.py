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
        plates = Numberplate.query.filter_by(number_plate=number_plate).all()

        province = get_province(number_plate)

        if plates:
            latest = max(
                plates, key=lambda x: x.date_in
            )  
            for plate in plates:
                if plate.id != latest.id:
                    db.session.delete(plate)
            db.session.commit()

            if latest.status == 0:  
                latest.status = 1
                latest.date_in = datetime.utcnow()
                latest.date_out = None
                latest.user_id = latest.user_id or (
                    User.query.get(1).id if User.query.get(1) else None
                )
                db.session.commit()
                print("Xe vào bãi")
                return "in"
            elif latest.status == 1:
                print(
                    f"[DEBUG] insert_np: Gọi update_np cho plate_id={latest.id}, number_plate={latest.number_plate}, user_id={latest.user_id}"
                )
                success = update_np(latest.id)
                if success:
                    print("[DEBUG] insert_np: Xe ra bãi, update_np thành công")
                    user_email = None
                    if latest.user_id:
                        user = User.query.get(latest.user_id)
                        if user:
                            user_email = user.email
                            print(
                                f"[DEBUG] insert_np: User balance sau update_np: {user.balance}"
                            )
                    print(
                        "tai khoan cua nguoi dung vua ra khoi bai goi la:", user_email
                    )
                    if user_email:
                        send_fee_email(latest.id, 0, user_email)
                    return "out"
                else:
                    print(
                        f"[DEBUG] insert_np: Gọi update_np thất bại cho plate_id={latest.id}"
                    )
        else:
            new_plate = Numberplate(
                number_plate=number_plate,
                status=1,
                province=province,
                date_in=datetime.utcnow(),
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
        "15": "Hải Phòng",
        "16": "Hải Phòng",
        "17": "Thái Bình",
        "18": "Nam Định",
        "19": "Phú Thọ",
        "20": "Thái Nguyên",
        "21": "Yên Bái",
        "22": "Tuyên Quang",
        "23": "Hà Giang",
        "24": "Lào Cai",
        "25": "Lai Châu",
        "26": "Sơn La",
        "27": "Điện Biên",
        "28": "Hòa Bình",
        "29": "Hà Nội",
        "30": "Hà Nội",
        "31": "Hà Nội",
        "32": "Hà Nội",
        "33": "Hà Nội",
        "34": "Hải Dương",
        "35": "Ninh Bình",
        "36": "Thanh Hóa",
        "37": "Nghệ An",
        "38": "Hà Tĩnh",
        "40": "Hà Nội",
        "41": "TP.HCM",
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
        "62": "Long An",
        "63": "Tiền Giang",
        "64": "Vĩnh Long",
        "65": "Cần Thơ",
        "66": "Đồng Tháp",
        "67": "An Giang",
        "68": "Kiên Giang",
        "69": "Cà Mau",
        "70": "Tây Ninh",
        "71": "Bến Tre",
        "72": "Bà Rịa - Vũng Tàu",
        "73": "Quảng Bình",
        "74": "Quảng Trị",
        "75": "Thừa Thiên Huế",
        "76": "Quảng Ngãi",
        "77": "Bình Định",
        "78": "Phú Yên",
        "79": "Khánh Hòa",
        "80": "Cơ quan Trung ương",
        "81": "Gia Lai",
        "82": "Kon Tum",
        "83": "Sóc Trăng",
        "84": "Trà Vinh",
        "85": "Ninh Thuận",
        "86": "Bình Thuận",
        "88": "Vĩnh Phúc",
        "89": "Hưng Yên",
        "90": "Hà Nam",
        "92": "Quảng Nam",
        "93": "Bình Phước",
        "94": "Bạc Liêu",
        "95": "Hậu Giang",
        "97": "Bắc Cạn",
        "98": "Bắc Giang",
        "99": "Bắc Ninh",
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
        print(f"[DEBUG] update_np: Bắt đầu với plate_id={plate_id}")
        plate = Numberplate.query.get(plate_id)
        if plate:
            print(
                f"[DEBUG] update_np: Trước cập nhật: status={plate.status}, date_out={plate.date_out}, user_id={plate.user_id}"
            )
            plate.status = 0
            plate.date_out = datetime.utcnow()
            db.session.commit()
            print(
                f"[DEBUG] update_np: Đã commit thành công cho plate_id={plate_id}, status={plate.status}, date_out={plate.date_out}, user_id={plate.user_id}"
            )
            # Nếu có user, in thêm balance
            if plate.user_id:
                user = User.query.get(plate.user_id)
                if user:
                    print(f"[DEBUG] update_np: User balance sau commit: {user.balance}")
            return True
        print(f"[DEBUG] update_np: Không tìm thấy plate với id={plate_id}")
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
