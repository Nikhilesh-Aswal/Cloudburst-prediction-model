# utils/feature_engineering.py
# Canonical feature engineering for both NASA POWER (historical) and OpenWeather (forecast).

import pandas as pd
import numpy as np

def build_features(df):
    """
    Input df must contain a date column and at least some of:
      - temp or temp_mean or temperature or T2M
      - humidity or RH2M
      - pressure or PS
      - rainfall or PRECTOT / PRECTOTCORR
      - wind or ws2m or wind_speed

    Output: df with canonical columns:
      date, temp, humidity, pressure, rainfall, wind,
      precip_1d, precip_3d, precip_7d,
      temp_diff, humidity_diff, pressure_diff,
      monsoon
    """

    df = df.copy()

    # Ensure date is datetime (keep as date in column but preserve datetime for month)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    else:
        raise ValueError("Input dataframe must contain a 'date' column")

    # Normalize possible alternative names to canonical
    # Temperature
    if "temp" not in df.columns:
        for alt in ("temp_mean", "temperature", "t2m", "T2M", "T2M_MEAN"):
            if alt in df.columns:
                df["temp"] = df[alt]
                break

    # Humidity
    if "humidity" not in df.columns:
        for alt in ("rh2m", "RH2M", "RH", "rel_humidity"):
            if alt in df.columns:
                df["humidity"] = df[alt]
                break

    # Pressure
    if "pressure" not in df.columns:
        for alt in ("ps", "PS", "surface_pressure"):
            if alt in df.columns:
                df["pressure"] = df[alt]
                break

    # Rainfall / Precip
    if "rainfall" not in df.columns:
        for alt in ("prectot", "PRECTOT", "prectotcorr", "PRECTOTCORR", "precip", "rain"):
            if alt in df.columns:
                df["rainfall"] = df[alt]
                break

    # Wind
    if "wind" not in df.columns:
        for alt in ("wind_speed", "ws2m", "WS2M", "windspd", "windSpeed"):
            if alt in df.columns:
                df["wind"] = df[alt]
                break

    # Fill missing numeric columns with zeros (defensive)
    for col in ("temp", "humidity", "pressure", "rainfall", "wind"):
        if col not in df.columns:
            df[col] = 0.0

    # Sort by date for rolling / diff
    df = df.sort_values("date").reset_index(drop=True)

    # Precip rolling sums (canonical names expected by model code)
    df["precip_1d"] = df["rainfall"].fillna(0)
    df["precip_3d"] = df["rainfall"].rolling(3, min_periods=1).sum()
    df["precip_7d"] = df["rainfall"].rolling(7, min_periods=1).sum()

    # Deltas
    # temp_diff: change from previous day (use temp mean if available)
    df["temp_diff"] = df["temp"].diff().fillna(0)

    # humidity_diff (aka humidity_change)
    df["humidity_diff"] = df["humidity"].diff().fillna(0)

    # pressure_diff
    df["pressure_diff"] = df["pressure"].diff().fillna(0)

    # monsoon flag
    df["month"] = df["date"].dt.month
    df["monsoon"] = df["month"].isin([6,7,8,9]).astype(int)

    # Ensure the expected canonical column names exist
    # (some parts of code expect 'temp' not temp_mean etc.)
    # Already ensured above

    # Return DataFrame with engineered columns (but keep originals too)
    return df
