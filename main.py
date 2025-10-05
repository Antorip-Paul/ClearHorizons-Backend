import os
import asyncio
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import aiohttp
import numpy as np
import pandas as pd

app = FastAPI(title="ClearHorizons Backend")

# Allow CORS to your frontend
FRONTEND_URL = os.getenv("FRONTEND_URL", "*")
allow_origins = ["*"] if FRONTEND_URL == "*" else [FRONTEND_URL]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Constants ---
BOUNDING_BOX = [90, -23.8, 90.5, -23.9]
LON_MIN, LAT_MIN, LON_MAX, LAT_MAX = BOUNDING_BOX
STEP_SIZE = 0.25
PARAMETER = "RH2M"

lats = np.arange(LAT_MIN, LAT_MAX + STEP_SIZE, STEP_SIZE)
lons = np.arange(LON_MIN, LON_MAX + STEP_SIZE, STEP_SIZE)
COORDINATE_GRID = [(lat, lon) for lat in lats for lon in lons]

base_url = "https://power.larc.nasa.gov/api/temporal/daily/point"
YEAR_RANGE = range(1995, 2025)
TOTAL_YEARS = len(YEAR_RANGE)


async def fetch_data(session, lat, lon, year, date_suffix):
    date_start = f"{year}{date_suffix}"
    params = {
        "parameters": PARAMETER,
        "community": "RE",
        "longitude": lon,
        "latitude": lat,
        "start": date_start,
        "end": date_start,
        "format": "JSON",
    }
    try:
        async with session.get(base_url, params=params, timeout=10) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
            rh_dict = data.get("properties", {}).get("parameter", {}).get(PARAMETER, {})
            rh_value = rh_dict.get(date_start, -999.00)
            return {"latitude": lat, "longitude": lon, "date": date_start, "rh2m": rh_value}
    except Exception:
        return None


async def process_data(date_suffix):
    connector = aiohttp.TCPConnector(limit=200)
    timeout = aiohttp.ClientTimeout(total=30)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        tasks = [
            asyncio.create_task(fetch_data(session, lat, lon, year, date_suffix))
            for year in YEAR_RANGE
            for lat, lon in COORDINATE_GRID
        ]
        results = await asyncio.gather(*tasks)

    valid_results = [r for r in results if r and r["rh2m"] != -999.00]
    df = pd.DataFrame(valid_results)
    humidity_levels = []

    if not df.empty:
        yearly_avg = df.groupby(df["date"].str[:4])["rh2m"].mean().reset_index()
        for _, row in yearly_avg.iterrows():
            avg_rh = row["rh2m"]
            if avg_rh <= 30:
                humidity_levels.append("LOW")
            elif 30 < avg_rh < 59:
                humidity_levels.append("MEDIUM")
            else:
                humidity_levels.append("HIGH")

    high_humidity = humidity_levels.count("HIGH")
    medium_humidity = humidity_levels.count("MEDIUM")
    low_humidity = humidity_levels.count("LOW")

    if not humidity_levels:
        highest_humidity_level = "NO DATA"
        humidity_formula = 0
    elif high_humidity == medium_humidity == low_humidity:
        highest_humidity_level = "TIE (ALL)"
        humidity_formula = high_humidity / TOTAL_YEARS
    elif max(high_humidity, medium_humidity, low_humidity) == high_humidity:
        highest_humidity_level = "HIGH"
        humidity_formula = high_humidity / TOTAL_YEARS
    elif max(high_humidity, medium_humidity, low_humidity) == medium_humidity:
        highest_humidity_level = "MEDIUM"
        humidity_formula = medium_humidity / TOTAL_YEARS
    else:
        highest_humidity_level = "LOW"
        humidity_formula = low_humidity / TOTAL_YEARS

    return {
        "humidity_levels": humidity_levels,
        "most_frequent_level": highest_humidity_level,
        "probability_percent": round(humidity_formula * 100, 2),
    }


@app.post("/humidity")
async def humidity_endpoint(request: Request):
    data = await request.json()
    month = data.get("month")
    day = data.get("day")
    if not month or not day:
        return {"error": "Provide month and day (zero-padded strings, e.g., '01', '05')"}
    date_suffix = f"{month}{day}"
    result = await process_data(date_suffix)
    return result


@app.get("/")
def root():
    return {"status": "ok", "note": "POST /humidity with {month, day}"}
