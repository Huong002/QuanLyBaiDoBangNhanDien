set FLASK_APP=create_db.py
flask db migrate -m "Initial migration"


# config:
- cấu hình kết nối với csdl
# database/detect_service:
- định nghĩa các hàm logic như thêm bản ghi, lấy, cập nhập
# models:
- định nghia các lớp ( đối tượng) trong chương trinh
# runs:
- chứa mô hình
# template: 
- tổ chức ui
# utils
- định nghĩa hàm nhận dạng, đọc biển số và tiền xữ lí



# chức năng tính phí tự động:
mỗi lần cập nhập trạng thái xe từ 1 -> 0 thì trừ 1 ngàn vào tkhoan của người dừng
1. chuẩn bị:
s
