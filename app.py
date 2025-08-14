from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import time
from datetime import datetime
import os

app = Flask(__name__)

# cấu hình cho migration:
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:150600@localhost:5432/machine'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)

    def __repr__(self):
        return f'<User {self.username}>'

class Numberplate(db.Model):
    __tablename__ = 'numberplate'
    
    id = db.Column(db.Integer, primary_key=True)
    number_plate = db.Column(db.String(20), nullable=False)
    status = db.Column(db.Integer, nullable=False, default=1)
    province = db.Column(db.String(50), nullable=True)
    date_in = db.Column(db.DateTime, nullable=True, default=datetime.utcnow)
    date_out = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f'<Numberplate {self.number_plate}>'

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
        province = get_province(number_plate)
        new_plate = Numberplate(
            number_plate=number_plate,
            status=1,
            province=province,
            date_in=datetime.utcnow()
        )
        db.session.add(new_plate)
        db.session.commit()
        return True
    except Exception as e:
        print(f"Lỗi insert_np: {e}")
        db.session.rollback()
        return False

def get_province(number_plate):
    province_codes = {
        '11': 'Cao Bằng', '12': 'Lạng Sơn', '13': 'Quảng Ninh', '14': 'Hải Phòng',
        '15': 'Hải Dương', '16': 'Hưng Yên', '17': 'Thái Bình', '18': 'Hà Nam',
        '19': 'Nam Định', '20': 'Phú Thọ', '21': 'Thái Nguyên', '22': 'Yên Bái',
        '29': 'Hà Nội', '30': 'Hà Nội', '31': 'Hà Nội', '32': 'Hà Nội', '33': 'Hà Nội',
        '43': 'Đà Nẵng', '47': 'Đắk Lắk', '48': 'Đắk Nông', '49': 'Lâm Đồng',
        '50': 'TP.HCM', '51': 'TP.HCM', '52': 'TP.HCM', '53': 'TP.HCM',
        '54': 'TP.HCM', '55': 'TP.HCM', '56': 'TP.HCM', '57': 'TP.HCM',
        '58': 'TP.HCM', '59': 'TP.HCM', '60': 'Đồng Nai', '61': 'Bình Dương'
    }
    
    if len(number_plate) >= 2:
        code = number_plate[:2]
        return province_codes.get(code, 'Không xác định')
    return 'Không xác định'

def check_np_status(number_plate):
    try:
        result = Numberplate.query.filter_by(number_plate=number_plate)\
                                 .order_by(Numberplate.date_in.desc()).first()
        if result:
            return (result.id, result.number_plate, result.status)
        return None
    except Exception as e:
        print(f"Lỗi check_np_status: {e}")
        return None

def update_np(plate_id):
    try:
        plate = Numberplate.query.get(plate_id)
        if plate:
            plate.status = 0  # 0: xe ra bãi
            plate.date_out = datetime.utcnow()
            db.session.commit()
            return True
        return False
    except Exception as e:
        print(f"Lỗi update_np: {e}")
        db.session.rollback()
        return False

def get_history(number_plate):
    try:
        records = Numberplate.query.filter_by(number_plate=number_plate)\
                                  .order_by(Numberplate.date_in.desc()).all()
        result = []
        for record in records:
            result.append((
                record.number_plate,
                record.date_in,
                record.date_out,
                'Trong bãi' if record.status == 1 else 'Đã ra bãi'
            ))
        return result
    except Exception as e:
        print(f"Lỗi get_history: {e}")
        return []

def is_vehicle_in_parking(number_plate):
    try:
        latest_record = Numberplate.query.filter_by(number_plate=number_plate)\
                                        .order_by(Numberplate.date_in.desc()).first()
        if latest_record and latest_record.status == 1:
            return "Xe đang trong bãi"
        else:
            return "Xe không trong bãi"
    except Exception as e:
        print(f"Lỗi is_vehicle_in_parking: {e}")
        return "Lỗi kiểm tra"

@app.route('/')
def index():
    return render_template('templates/index.html')

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
    # Tạm thời simulate detect cho test
    test_plate = "30A-12345"
    
    status = "Xe vào bãi đổ"
    province = get_province(test_plate)
    check = check_np(test_plate)
    
    if check == 0:
        insert_np(test_plate)
    
    return jsonify({
        "plate": test_plate,
        "province": province,
        "status": status,
        "message": "Test mode - no actual image processing"
    })

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("Database tables created/verified!")
        print("App running in test mode (no YOLO)")
    app.run(debug=True, port=5001)
