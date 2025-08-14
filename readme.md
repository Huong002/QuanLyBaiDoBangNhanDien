set FLASK_APP=create_db.py
# Khởi tạo thư mục migration nếu chưa có
flask db init
# chạy migration
flask db migrate -m "Initial migration"