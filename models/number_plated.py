

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Numberplate(db.Model):
    __tablename__ = 'numberplate'
    id = db.Column(db.Integer, primary_key=True)
    number_plate = db.Column(db.String(20), nullable=False)
    status = db.Column(db.Integer, nullable=False, default=1)
    province = db.Column(db.String(50), nullable=True)
    date_in = db.Column(db.DateTime, nullable=True, default=datetime.today)
    date_out = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=True, default=datetime.today)

    def __repr__(self):
        return f'<Numberplate {self.number_plate}>'