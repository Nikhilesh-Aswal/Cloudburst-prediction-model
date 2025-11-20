from flask import Flask, render_template, jsonify, request
import traceback
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import os

from utils.feature_engineering import build_features
from utils.model_utils import predict_probs_df
from utils.api_fetcher import get_all_forecasts

app = Flask(__name__)

RISK_BINS_PERCENT = [-1, 5, 10, 30, 100]
RISK_LABELS = ["Low", "Moderate", "High", "Extreme"]
RISK_COLORS = {
    "Low": "#2ECC71",
    "Moderate": "#F1C40F",
    "High": "#E67E22",
    "Extreme": "#E74C3C",
}


def classify_risk(p):
    r = pd.cut([p], bins=RISK_BINS_PERCENT, labels=RISK_LABELS)[0]
    r = str(r) if pd.notna(r) else "Low"
    return r, RISK_COLORS.get(r, "#2ECC71")


def ensure_date(x):
    if isinstance(x, str):
        return datetime.strptime(x, "%Y-%m-%d").date()
    if isinstance(x, datetime):
        return x.date()
    return x


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/district/<name>")
def district_page(name):
    return render_template("district.html", district=name.title())


@app.route("/forecast", methods=["GET"])
def forecast():
    try:
        date_str = request.args.get("date")
        today = datetime.utcnow().date()

        if date_str:
            query_date = ensure_date(date_str)
        else:
            query_date = today

        target_dates = [(query_date + timedelta(days=i)) for i in range(6)]

        if query_date < today:

            hist_path = "historical/uttarakhand_all.csv"
            if not os.path.exists(hist_path):
                return jsonify({"error": "Historical dataset not found"}), 404

            df = pd.read_csv(hist_path)
            df.columns = [c.strip() for c in df.columns]

            df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
            df = df.dropna(subset=["date"])

            results = []

            for district, g in df.groupby("district"):

                g = g.sort_values("date").reset_index(drop=True).copy()

                rename_map = {}
                if "PRECTOT" in g.columns:
                    rename_map["PRECTOT"] = "rainfall"
                if "T2M" in g.columns:
                    rename_map["T2M"] = "temp"
                if "RH2M" in g.columns:
                    rename_map["RH2M"] = "humidity"
                if "PS" in g.columns:
                    rename_map["PS"] = "pressure"
                if "WS2M" in g.columns:
                    rename_map["WS2M"] = "wind"

                if rename_map:
                    g = g.rename(columns=rename_map)

                if "pressure" in g.columns and g["pressure"].max() < 200:
                    g["pressure"] *= 10.0

                try:
                    df_feat = build_features(g.copy())
                    probs, aligned = predict_probs_df(df_feat)
                except Exception:
                    continue

                pcts = [round(float(p) * 300.0, 2) for p in probs]

                aligned["date"] = pd.to_datetime(aligned["date"]).dt.date

                for td in target_dates:
                    if td in aligned["date"].values:
                        idx = aligned.index[aligned["date"] == td][0]

                        prob_pct = pcts[idx]
                        label, color = classify_risk(prob_pct)
                        row = aligned.loc[idx]

                        results.append({
                            "district": district,
                            "date": str(td),
                            "probability": prob_pct,
                            "risk_level": label,
                            "risk_color": color,
                            "temperature": float(row.get("temp", 0)),
                            "humidity": float(row.get("humidity", 0)),
                            "pressure": float(row.get("pressure", 0)),
                            "wind": float(row.get("wind", 0)),
                            "rainfall": float(row.get("rainfall", 0)),
                        })

            return jsonify(results)

        forecasts = get_all_forecasts()
        all_forecasts = []

        for district, raw_list in forecasts.items():
            if not raw_list:
                continue

            dfw = pd.DataFrame(raw_list)
            if dfw.empty or "date" not in dfw.columns:
                continue

            dfw["date"] = pd.to_datetime(dfw["date"]).dt.date

            if "wind_speed" in dfw.columns:
                dfw = dfw.rename(columns={"wind_speed": "wind"})
            if "rain" in dfw.columns:
                dfw = dfw.rename(columns={"rain": "rainfall"})

            daily = dfw.groupby("date").agg({
                "temp": "mean",
                "humidity": "mean",
                "pressure": "mean",
                "rainfall": "sum",
                "wind": "mean"
            }).reset_index()

            if daily.empty:
                continue

            try:
                df_feat = build_features(daily.copy())
                probs, aligned = predict_probs_df(df_feat)
            except Exception:
                continue

            aligned["date"] = pd.to_datetime(aligned["date"]).dt.date
            pcts = [round(float(p) * 100.0, 2) for p in probs]

            for td in target_dates:
                if td in aligned["date"].values:
                    idx = aligned.index[aligned["date"] == td][0]

                    prob_pct = pcts[idx]
                    label, color = classify_risk(prob_pct)
                    row = aligned.loc[idx]

                    all_forecasts.append({
                        "district": district,
                        "date": str(td),
                        "probability": prob_pct,
                        "risk_level": label,
                        "risk_color": color,
                        "temperature": float(row.get("temp", 0)),
                        "humidity": float(row.get("humidity", 0)),
                        "pressure": float(row.get("pressure", 0)),
                        "wind": float(row.get("wind", 0)),
                        "rainfall": float(row.get("rainfall", 0)),
                    })

        return jsonify(all_forecasts)

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(debug=True)
