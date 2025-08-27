import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import logging
from models.number_plated import Numberplate
import os
import pickle


def save_model(model, encoder, path="best_model.pkl"):
    with open(path, "wb") as f:
        pickle.dump({"model": model, "encoder": encoder}, f)


def load_model(path="best_model.pkl"):
    if not os.path.exists(path):
        return None, None
    with open(path, "rb") as f:
        data = pickle.load(f)
        return data["model"], data["encoder"]


def train_model(
    data_source="csv",
    csv_path="utils/dataset.csv",
    app=None,
    model_path="best_model.pkl",
):
    model, encoder = load_model(model_path)
    if model is not None and encoder is not None:
        model._encoder = encoder
        return model
    if data_source == "csv":
        df = pd.read_csv(csv_path)
        time_col = "LastUpdated"
        if time_col not in df.columns:
            raise Exception("Không tìm thấy cột LastUpdated trong dataset!")
        df[time_col] = pd.to_datetime(df[time_col])
    elif data_source == "database":
        if not app:
            raise Exception("Cần truyền app context khi lấy từ database!")
        with app.app_context():
            records = Numberplate.query.all()
            data = [
                {
                    "LastUpdated": record.date_in,
                    "Occupancy": 1 if record.status == 1 else 0,
                    "Capacity": getattr(record, "capacity", 0),
                    "SystemCodeNumber": getattr(record, "system_code", "A"),
                }
                for record in records
                if record.date_in
            ]
            df = pd.DataFrame(data)
            time_col = "LastUpdated"
            if df.empty:
                raise Exception("Không có dữ liệu trong bảng numberplate!")
    else:
        raise ValueError("data_source phải là 'csv' hoặc 'database'")

    df["hour"] = df[time_col].dt.hour
    df["dayofweek"] = df[time_col].dt.dayofweek
    df["month"] = df[time_col].dt.month
    df["is_weekend"] = df["dayofweek"].apply(lambda x: 1 if x >= 5 else 0)
    if "SystemCodeNumber" not in df.columns:
        df["SystemCodeNumber"] = "A"
    encoder = LabelEncoder()
    df["SystemCodeNumber_enc"] = encoder.fit_transform(df["SystemCodeNumber"])

    X = df[
        [
            "Capacity",
            "hour",
            "dayofweek",
            "month",
            "is_weekend",
            "SystemCodeNumber_enc",
        ]
    ]
    y = df["Occupancy"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    param_grid = {
        "n_estimators": [100, 200],
        "max_depth": [10, 20, None],
        "min_samples_split": [2, 5, 10],
        "min_samples_leaf": [1, 2, 4],
        "max_features": ["sqrt", "log2"],
    }
    rf = RandomForestRegressor(random_state=42, n_jobs=1)
    grid_search = GridSearchCV(rf, param_grid, cv=3, scoring="r2", n_jobs=1, verbose=0)
    grid_search.fit(X_train, y_train)
    best_model = grid_search.best_estimator_

    y_pred = best_model.predict(X_test)
    logging.basicConfig(level=logging.INFO)
    logging.info("\n📊 Kết quả mô hình Random Forest tối ưu:")
    logging.info(f"Best Params: {grid_search.best_params_}")
    logging.info(f"MAE: {mean_absolute_error(y_test, y_pred):.2f}")
    logging.info(f"MSE: {mean_squared_error(y_test, y_pred):.2f}")
    logging.info(f"R²: {r2_score(y_test, y_pred):.4f}")

    best_model._encoder = encoder
    save_model(best_model, encoder, model_path)
    return best_model


def du_doan_so_xe(thoi_gian, model, capacity=577, system_code=None):
    try:
        thoi_gian = pd.to_datetime(thoi_gian)
        hour = thoi_gian.hour
        dayofweek = thoi_gian.dayofweek
        month = thoi_gian.month
        is_weekend = 1 if dayofweek >= 5 else 0
        encoder = getattr(model, "_encoder", None)
        if encoder is None:
            return 0
        if system_code is None:
            system_code = encoder.classes_[0]
        system_code_enc = encoder.transform([system_code])[0]
        X_new = pd.DataFrame(
            {
                "Capacity": [capacity],
                "hour": [hour],
                "dayofweek": [dayofweek],
                "month": [month],
                "is_weekend": [is_weekend],
                "SystemCodeNumber_enc": [system_code_enc],
            }
        )
        so_xe = model.predict(X_new)[0]
        return max(0, round(so_xe))
    except Exception as e:
        logging.error(f"Lỗi dự đoán: {e}")
        return 0


# Hàm dự đoán số xe theo từng giờ trong ngày
def predict_hourly(date_str, model, capacity=577, system_code=None):
    date = pd.to_datetime(date_str)
    hourly_labels = [f"{h}:00" for h in range(24)]
    hourly_predictions = [
        du_doan_so_xe(f"{date_str}T{h}:00", model, capacity, system_code)
        for h in range(24)
    ]
    return {"labels": hourly_labels, "data": hourly_predictions}
