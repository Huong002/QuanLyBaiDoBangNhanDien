# database/number_plate_db.py
from database.db_connection import connectDB
import datetime

# Kiểm tra biển số xe đã tồn tại chưa
def check_np(number_plate):
    con = connectDB()
    if not con:
        return 0
    cursor = con.cursor()
    sql = "SELECT * FROM numberplate WHERE number_plate = %s"
    cursor.execute(sql, (number_plate,))
    cursor.fetchall()
    result = cursor.rowcount
    print("result: ",result)
    cursor.close()
    con.close()
    return result

# Kiểm tra trạng thái của biển số xe
def check_np_status(number_plate):
    con = connectDB()
    if not con:
        return None
    cursor = con.cursor()
    sql = "SELECT * FROM numberplate WHERE number_plate = %s ORDER BY date_in DESC LIMIT 1"
    cursor.execute(sql, (number_plate,))
    result = cursor.fetchone()
    cursor.close()
    con.close()
    return result

# Thêm biển số xe mới
def insert_np(number_plate):
    con = connectDB()
    if not con:
        return
    cursor = con.cursor()
    sql = "INSERT INTO numberplate (number_plate, status, date_in) VALUES (%s, %s, %s)"
    now = datetime.datetime.now()
    date_in = now.strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(sql, (number_plate, 0, date_in))
    con.commit()
    cursor.close()
    con.close()
    print("XE VÀO BÃI ĐỖ")
    print(f"Ngày giờ vào: {date_in}")

# Cập nhật trạng thái khi xe rời bãi
def update_np(id):
    con = connectDB()
    if not con:
        return
    cursor = con.cursor()
    sql = "UPDATE numberplate SET status = 1, date_out = %s WHERE id = %s"
    now = datetime.datetime.now()
    date_out = now.strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(sql, (date_out, id))
    con.commit()
    cursor.close()
    con.close()
    print("XE RA KHỎI BÃI ĐỖ")
    print(f"Ngày giờ ra: {date_out}")

# Nhận diện tỉnh thành từ mã số
def get_province(number_plate):
    con = connectDB()
    if not con:
        return "Không xác định"
    province_code = number_plate[:2]  # Lấy 2 ký tự đầu của biển số
    print(f"📌 Mã tỉnh thành: {province_code}")  # Debug
    try:
        cursor = con.cursor()
        sql = "SELECT province_name FROM provinces WHERE code = %s"
        cursor.execute(sql, (province_code,))
        result = cursor.fetchone()
        cursor.close()
        con.close()
        print(f"✅ Tên tỉnh thành tìm được: {result}")  # Debug kết quả SQL
        return result[0] if result else "Không xác định"
    except Exception as e:
        print(f"❌ Lỗi truy vấn SQL: {e}")
        return "Không xác định"
#Kiểm tra lịch sử ra vào
def get_history(number_plate):
    con = connectDB()
    if not con:
        return []
    cursor = con.cursor()
    sql = "SELECT number_plate, date_in, date_out, status FROM numberplate WHERE number_plate = %s ORDER BY date_in DESC"
    cursor.execute(sql, (number_plate,))
    result = cursor.fetchall()
    cursor.close()
    con.close()
    return result
#kiểm tra xe có trong bãi đổ không
def is_vehicle_in_parking(number_plate):
    con = connectDB()
    if not con:
        return []
    cursor = con.cursor()
    sql="select * from numberplate where numberplate.number_plate=%s ORDER by numberplate.date_in desc limit 1"
    cursor.execute(sql,(number_plate,))
    sql = "SELECT * FROM numberplate WHERE numberplate.number_plate = %s ORDER BY numberplate.date_in DESC LIMIT 1"
    cursor.execute(sql, (number_plate,))
    result = cursor.fetchone()

    if result is None:
        status = "Không có dữ liệu"
    else:
        if result[2] == 0:
            status = f"Xe có biển số {number_plate} hiện đang ở trong bãi. Thời gian vào: {result[3]}"
        else:
            status = f"Xe có biển số {number_plate} hiện đã rời khỏi bãi. Thời gian rời bãi: {result[4]}"
    cursor.close()
    con.close()
    return status