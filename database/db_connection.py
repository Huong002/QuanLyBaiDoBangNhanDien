# database/db_connection.py
import psycopg2
from config.database import DB_CONFIG

def connectDB():
    try:
        con = psycopg2.connect(**DB_CONFIG)
        return con
    except Exception as e:
        print(f"Lỗi kết nối cơ sở dữ liệu: {e}")
        return None