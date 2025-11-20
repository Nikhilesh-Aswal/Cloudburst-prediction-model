# utils/model_utils.py
# Loads model, defines canonical features, and provides a robust predict function for DataFrames.

import joblib
import numpy as np
import pandas as pd
import os
from utils.feature_engineering import build_features

# Try common model paths (training script saved as cloudburst_model_openweather.pkl)
MODEL_CANDIDATES = [
    "models/cloudburst_model_openweather.pkl",
    "models/cloudburst_model.pkl",
    "models/cloudburst_model_openweather.joblib",
    "models/cloudburst_model.joblib"
]

_model = None
for p in MODEL_CANDIDATES:
    if os.path.exists(p):
        try:
            _model = joblib.load(p)
            MODEL_PATH = p
            break
        except Exception:
            _model = None

if _model is None:
    # Attempt to load default path (might throw)
    try:
        _model = joblib.load("models/cloudburst_model_openweather.pkl")
        MODEL_PATH = "models/cloudburst_model_openweather.pkl"
    except Exception:
        raise FileNotFoundError("No valid model found in models/*.pkl - check training output and filenames")

model = _model

# Canonical features expected by the model (must match training)
FEATURES = [
    "temp", "humidity", "pressure", "rainfall", "wind",
    "precip_3d", "precip_7d",
    "temp_diff", "humidity_diff", "pressure_diff",
    "monsoon"
]

def _align_and_fill(df_feat):
    """
    Ensure df_feat contains all FEATURES (in this order), fill missing with 0,
    and return X (numpy array) and the aligned dataframe subset.
    """
    df = df_feat.copy()
    # If model expects precip_1d but training used precip_3d/7d, ensure we provide precip_3d/7d
    # We included precip_3d/7d in FEATURES above.

    # ensure date remains, so consumer can pick row metadata
    # Create missing columns with zeros
    for c in FEATURES:
        if c not in df.columns:
            # For precip_3d/7d try to derive from rainfall
            if c == "precip_3d":
                df[c] = df.get("precip_3d", df.get("rainfall", 0)).fillna(0)
            elif c == "precip_7d":
                df[c] = df.get("precip_7d", df.get("rainfall", 0)).fillna(0)
            else:
                df[c] = df.get(c, 0).fillna(0)

    X = df[FEATURES].astype(float).values
    return X, df[["date"] + [c for c in df.columns if c in FEATURES]]

def predict_probs_df(raw_df):
    """
    raw_df: DataFrame with at least columns convertible by build_features (date + raw inputs)
    Returns: (probs, df_aligned)
      probs: list/np.array of probabilities (0..1)
      df_aligned: DataFrame with date + FEATURE columns aligned (one row per input row)
    """
    if raw_df is None or raw_df.empty:
        return np.array([]), pd.DataFrame()

    # Build features (this normalizes names and computes rolling/deltas)
    df_feat = build_features(raw_df.copy())

    # Align to FEATURES and fill missing
    X, df_aligned = _align_and_fill(df_feat)

    # predict_proba expects 2D array of shape (n_samples, n_features)
    probs = model.predict_proba(X)[:, 1]  # probability for class 1
    return probs, df_aligned.reset_index(drop=True)
