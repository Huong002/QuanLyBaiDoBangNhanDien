import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from models.number_plated import Numberplate

def train_model(data_source='csv', csv_path='utils/dataset.csv', app=None):
    if data_source == 'csv':
        df = pd.read_csv(csv_path)
        time_col = 'LastUpdated'
        if time_col not in df.columns:
            raise Exception('Không tìm thấy cột LastUpdated trong dataset!')
        df[time_col] = pd.to_datetime(df[time_col])
    elif data_source == 'database':
        if not app:
            raise Exception('Cần truyền app context khi lấy từ database!')
        with app.app_context():
            records = Numberplate.query.all()
            data = [{
                'LastUpdated': record.date_in,
                'Occupancy': 1 if record.status == 1 else 0
            } for record in records if record.date_in]
            df = pd.DataFrame(data)
            time_col = 'LastUpdated'
            if df.empty:
                raise Exception('Không có dữ liệu trong bảng numberplate!')
    else:
        raise ValueError("data_source phải là 'csv' hoặc 'database'")

    df['hour'] = df[time_col].dt.hour
    df['day_of_week'] = df[time_col].dt.dayofweek
    df['is_weekend'] = df['day_of_week'].apply(lambda x: 1 if x >= 5 else 0)
    X = df[["hour", "day_of_week", "is_weekend"]]
    y = df["Occupancy"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    model = LinearRegression()
    model.fit(X_train, y_train)
    
    return model

def du_doan_so_xe(thoi_gian, model):
    try:
        thoi_gian = pd.to_datetime(thoi_gian)
        hour = thoi_gian.hour
        day_of_week = thoi_gian.dayofweek
        is_weekend = 1 if day_of_week >= 5 else 0
        X_new = pd.DataFrame([[hour, day_of_week, is_weekend]], columns=["hour", "day_of_week", "is_weekend"])
        so_xe = model.predict(X_new)[0]
        return max(0, round(so_xe))  
    except Exception as e:
        print(f"Lỗi dự đoán: {e}")
        return 0
        
# Hàm dự đoán số xe theo từng giờ trong ngày
def predict_hourly(date_str, model):
    date = pd.to_datetime(date_str)
    hourly_labels = [f"{h}:00" for h in range(24)]
    hourly_predictions = [du_doan_so_xe(f"{date_str}T{h}:00", model) for h in range(24)]
    return {"labels": hourly_labels, "data": hourly_predictions}