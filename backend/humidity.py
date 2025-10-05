import asyncio
import aiohttp
import pandas as pd

async def compute_probabilities(lat: float, lon: float, month: int, day: int):
    PARAMETER = "RH2M"
    COORDINATE_GRID = [(lat, lon)]

    base_url = "https://power.larc.nasa.gov/api/temporal/daily/point"
    YEAR_RANGE = range(1995, 2025)
    TOTAL_YEARS = len(YEAR_RANGE)

    async def fetch_data(session, lat, lon, year):
        date_start = f"{year}{month:02d}{day:02d}"
        params = {
            'parameters': PARAMETER,
            'community': 'RE',
            'longitude': lon,
            'latitude': lat,
            'start': date_start,
            'end': date_start,
            'format': 'JSON'
        }
        try:
            async with session.get(base_url, params=params, timeout=10) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                rh_value = data['properties']['parameter'][PARAMETER][date_start]
                return {'latitude': lat, 'longitude': lon, 'date': date_start, 'rh2m': rh_value}
        except asyncio.TimeoutError:
            return None
        except KeyError:
            return {'latitude': lat, 'longitude': lon, 'date': date_start, 'rh2m': -999.00}
        except Exception:
            return None

    connector = aiohttp.TCPConnector(limit=200)
    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        tasks = [
            asyncio.create_task(fetch_data(session, lat, lon, year))
            for year in YEAR_RANGE
            for lat, lon in COORDINATE_GRID
        ]
        results = await asyncio.gather(*tasks)

    valid_results = [r for r in results if r and r['rh2m'] != -999.00]
    if not valid_results:
        return {"error": "No valid data retrieved."}
    df = pd.DataFrame(valid_results)
    humidity_levels = []
    if not df.empty:
        yearly_avg = df.groupby(df['date'].str[:4])['rh2m'].mean().reset_index()
        for _, row in yearly_avg.iterrows():
            avg_rh = row['rh2m']
            if avg_rh <= 30:
                humidity_levels.append("LOW")
            elif 30 < avg_rh < 59:
                humidity_levels.append("MEDIUM")
            else:
                humidity_levels.append("HIGH")

    high_humidity = humidity_levels.count("HIGH")
    medium_humidity = humidity_levels.count("MEDIUM")
    low_humidity = humidity_levels.count("LOW")
    probs = {
        "HIGH": high_humidity / TOTAL_YEARS,
        "MEDIUM": medium_humidity / TOTAL_YEARS,
        "LOW": low_humidity / TOTAL_YEARS
    }
    return probs