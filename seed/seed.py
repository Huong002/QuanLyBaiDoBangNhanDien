from app import app, db
from models.user import User
from models.number_plated import Numberplate
from datetime import datetime


# Hàm seed dữ liệu mẫu cho database
def seed():
    with app.app_context():
        # Thêm 2 user mẫu
        user1 = User(
            name="Trần Phước Hưỡng",
            email="psymint002@gmail.com",
            bank_account="9704221234567",
            balance=10000,
        )
        user2 = User(
            name="Nguyễn Hoàng Tam",
            email="nguyenhoangtam12cb3@gmail.com",
            bank_account="9704221234568",
            balance=10000,
        )
        db.session.add_all([user1, user2])
        db.session.commit()

        # # Thêm 2 lượt gửi xe mẫu
        # np1 = Numberplate(
        #     number_plate="51H-086.86",
        #     status=1,
        #     province="TP.HCM",
        #     date_in=datetime(2025, 8, 21, 8, 0),
        #     date_out=None,
        #     created_at=datetime(2025, 8, 21, 8, 0),
        #     user_id=user1.id,
        # )
        # np2 = Numberplate(
        #     number_plate="18A-123.45",
        #     status=0,
        #     province="Hà Nam",
        #     date_in=datetime(2025, 8, 20, 7, 30),
        #     date_out=datetime(2025, 8, 20, 10, 0),
        #     created_at=datetime(2025, 8, 20, 7, 30),
        #     user_id=user2.id,
        # )
        # db.session.add_all([np1, np2])
        # db.session.commit()
        print("Seed data thành công!")


# Chạy seed khi chạy file này
if __name__ == "__main__":
    seed()
