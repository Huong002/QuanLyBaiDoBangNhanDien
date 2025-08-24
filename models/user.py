
from . import db
class User(db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    email = db.Column(db.String(120), unique=True, nullable=False)
    bank_account = db.Column(db.String(50))
    balance = db.Column(db.Float, default=0)

    def __repr__(self):
        return f"<User {self.username}>"
