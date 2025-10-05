from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import windspeed
import rainfall
import snowfall
import temperature
import airdensity
import humidity

app = FastAPI()

# Allow your frontend to call the backend (CORS setup)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://clearhorizons-app.onrender.com"],  # Add your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/windspeed")
async def get_windspeed(lat: float, lon: float, month: int, day: int):
    return await windspeed.compute_probabilities(lat, lon, month, day)

@app.get("/api/rainfall")
async def get_rainfall(lat: float, lon: float, month: int, day: int):
    return await rainfall.compute_probabilities(lat, lon, month, day)

@app.get("/api/snowfall")
async def get_snowfall(lat: float, lon: float, month: int, day: int):
    return await snowfall.compute_probabilities(lat, lon, month, day)

@app.get("/api/temperature")
async def get_temperature(lat: float, lon: float, month: int, day: int):
    return await temperature.compute_probabilities(lat, lon, month, day)

@app.get("/api/airdensity")
async def get_airdensity(lat: float, lon: float, month: int, day: int):
    return await airdensity.compute_probabilities(lat, lon, month, day)

@app.get("/api/humidity")
async def get_humidity(lat: float, lon: float, month: int, day: int):
    return await humidity.compute_probabilities(lat, lon, month, day)