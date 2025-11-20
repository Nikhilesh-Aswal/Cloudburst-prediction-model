# utils/api_fetcher.py
"""
Ultra-fast OpenWeather API fetcher with parallel async requests and caching.
Handles 13 districts of Uttarakhand simultaneously.
"""

import aiohttp
import asyncio
import time
import json
import os
import sys

# 🧩 Fix for Windows event loop issues
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

API_KEY = "dbd281892ba36f06f1abe34f87951589"
BASE_URL = "https://api.openweathermap.org/data/2.5/forecast"
CACHE_FILE = "cache/openweather_cache.json"
CACHE_EXPIRY = 3600  # 1 hour

# Coordinates for Uttarakhand's 13 districts
DISTRICT_COORDS = {
    "Dehradun": (30.3165, 78.0322),
    "Haridwar": (29.9457, 78.1642),
    "Pauri Garhwal": (30.1527, 78.7724),
    "Tehri Garhwal": (30.3897, 78.4800),
    "Rudraprayag": (30.2844, 78.9800),
    "Chamoli": (30.4100, 79.3200),
    "Uttarkashi": (30.7299, 78.4437),
    "Almora": (29.5970, 79.6590),
    "Bageshwar": (29.8373, 79.7708),
    "Pithoragarh": (29.5830, 80.2170),
    "Nainital": (29.3803, 79.4636),
    "Champawat": (29.3366, 80.0982),
    "Udham Singh Nagar": (28.9845, 79.3964),
}

# ---------------------------
# 💾 Simple in-memory + file cache
# ---------------------------
_cache = {}

def _load_cache():
    global _cache
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                _cache = json.load(f)
        except Exception:
            _cache = {}

def _save_cache():
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump(_cache, f)

def _get_cached(key):
    now = time.time()
    if key in _cache:
        entry = _cache[key]
        if now - entry["time"] < CACHE_EXPIRY:
            return entry["data"]
    return None

def _set_cached(key, data):
    _cache[key] = {"time": time.time(), "data": data}
    _save_cache()

# ---------------------------
# 🌦️ Async Fetch Function
# ---------------------------
async def fetch_district_forecast(session, district, lat, lon):
    key = f"{district}_forecast"
    cached = _get_cached(key)
    if cached:
        return district, cached

    url = f"{BASE_URL}?lat={lat}&lon={lon}&appid={API_KEY}&units=metric"

    try:
        async with session.get(url, timeout=12) as resp:
            if resp.status != 200:
                print(f"⚠️ {district}: API status {resp.status}")
                return district, []
            data = await resp.json()
            result = []
            for entry in data.get("list", []):
                dt_txt = entry.get("dt_txt", "")
                main = entry.get("main", {})
                rain = entry.get("rain", {}).get("3h", 0)
                wind = entry.get("wind", {}).get("speed", 0)
                result.append({
                    "date": dt_txt.split(" ")[0],
                    "temp": main.get("temp", 0),
                    "humidity": main.get("humidity", 0),
                    "pressure": main.get("pressure", 0),
                    "wind_speed": wind,
                    "rain": rain,
                })
            _set_cached(key, result)
            return district, result
    except Exception as e:
        print(f"❌ {district}: {e}")
        return district, []

# ---------------------------
# 🚀 Public Function
# ---------------------------
async def get_all_forecasts_async():
    async with aiohttp.ClientSession() as session:
        tasks = [
            fetch_district_forecast(session, d, lat, lon)
            for d, (lat, lon) in DISTRICT_COORDS.items()
        ]
        results = await asyncio.gather(*tasks)
        return {district: data for district, data in results}

def get_forecast_weather(district):
    """Synchronous wrapper for single district"""
    lat, lon = DISTRICT_COORDS.get(district, (None, None))
    if lat is None:
        print(f"⚠️ Unknown district: {district}")
        return []

    cached = _get_cached(f"{district}_forecast")
    if cached:
        return cached

    async def run_single():
        async with aiohttp.ClientSession() as session:
            _, data = await fetch_district_forecast(session, district, lat, lon)
            return data

    result = asyncio.run(run_single())
    return result

def get_all_forecasts():
    """Fetch all districts concurrently (safe for Windows & Linux)."""
    try:
        _load_cache()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(get_all_forecasts_async())
        loop.close()
        return result
    except Exception as e:
        print(f"❌ Parallel forecast error: {e}")
        return {}
