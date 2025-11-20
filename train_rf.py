import pandas as pd
import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
import datetime
import os

print("📥 Loading historical data")

data = pd.read_csv("historical/uttarakhand_all.csv")
labels = pd.read_csv("labels/cloudburst_labels.csv")

data.columns = [c.strip().lower() for c in data.columns]
labels["district"] = labels["district"].str.strip().str.title()

data["date"] = pd.to_datetime(data["date"])
labels["date"] = pd.to_datetime(labels["date"])

data = pd.merge(
    data,
    labels.assign(cloudburst=1),
    on=["district", "date"],
    how="left"
)
data["cloudburst"].fillna(0, inplace=True)

print(f"✅ Loaded {len(data)} records, positives: {data['cloudburst'].sum()}")

feature_cols = {
    "t2m": "temp",
    "rh2m": "humidity",
    "ps": "pressure",
    "prectot": "rainfall",
    "ws2m": "wind"
}
for old, new in feature_cols.items():
    if old in data.columns:
        data.rename(columns={old: new}, inplace=True)

data = data.dropna(subset=["temp", "humidity", "pressure", "rainfall"])

print("⚙️ Engineering features")

def add_features(df):
    df = df.sort_values("date")
    df["rain_3d"] = df["rainfall"].rolling(3, min_periods=1).sum()
    df["rain_7d"] = df["rainfall"].rolling(7, min_periods=1).sum()
    df["temp_diff"] = df["temp"].diff().fillna(0)
    df["humidity_diff"] = df["humidity"].diff().fillna(0)
    df["pressure_diff"] = df["pressure"].diff().fillna(0)
    df["monsoon"] = df["date"].dt.month.isin([6,7,8,9]).astype(int)
    return df

data = data.groupby("district", group_keys=False).apply(add_features)
data = data.fillna(0)

features = [
    "temp", "humidity", "pressure", "rainfall", "wind",
    "rain_3d", "rain_7d",
    "temp_diff", "humidity_diff", "pressure_diff",
    "monsoon"
]

X = data[features]
y = data["cloudburst"]
 
print(f"🧩 Features: {features}")
print(f"📊 Shape: {X.shape}, positives: {int(y.sum())}")

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print("🧠 Training Random Forest model (OpenWeather-compatible)")
rf = RandomForestClassifier(
    n_estimators=200,
    max_depth=10,
    min_samples_leaf=3,
    class_weight="balanced_subsample",
    random_state=42
)
rf.fit(X_train, y_train)

y_pred = rf.predict(X_test)
y_prob = rf.predict_proba(X_test)[:, 1]

print("\n📈 Model Performance:")
print(classification_report(y_test, y_pred, digits=3))
print("Confusion Matrix:")
print(confusion_matrix(y_test, y_pred))
print(f"ROC AUC: {roc_auc_score(y_test, y_prob):.3f}")

cv_scores = cross_val_score(rf, X, y, cv=5, scoring="roc_auc")
print(f"Mean CV AUC: {cv_scores.mean():.3f}")

os.makedirs("models", exist_ok=True)
joblib.dump(rf, "models/cloudburst_model.pkl")

print("\n✅ Model saved as models/cloudburst_model.pkl")
