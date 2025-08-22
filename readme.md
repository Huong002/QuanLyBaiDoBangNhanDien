set FLASK_APP=create_db.py
flask db migrate -m "add user table and user_id to numberplate"
flask db upgrade

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

- thư viện:
  pip install Flask-Mail

## HƯỚNG DẪN TẠO MODEL VA CHAY MIGRATION:

- tạo **init**.py cho thư mục model

```python
from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()

# các file khác thì gọi
from . import db # là đủ
# nhớ gọi cho app khi chạy
from models import db

db.init_app(app)
```


## hướng dẫn chạy seed cho flask
```python
$env:PYTHONPATH="."
# Biến môi trường PYTHONPATH giúp Python biết nơi để tìm các module (file .py) khi import. Nếu bạn đặt PYTHONPATH=".", Python sẽ tìm module bắt đầu từ thư mục hiện tại (thư mục gốc dự án).
python seed\seed.py
```