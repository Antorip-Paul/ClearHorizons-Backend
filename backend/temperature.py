import asyncio
import aiohttp
import pandas as pd

async def compute_probabilities(lat: float, lon: float, month: int, day: int):
    PARAMETER = "T2M"  # temperature parameter
    COORDINATE_GRID = [(lat, lon)]

    t2m_values = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
    base_url = "https://power.larc.nasa.gov/api/temporal/daily/point"
    YEAR_RANGE = range(2010, 2025)

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
                t2m_value = data['properties']['parameter'][PARAMETER][date_start]
                return {'latitude': lat, 'longitude': lon, 'date': date_start, 't2m': t2m_value}
        except asyncio.TimeoutError:
            return None
        except KeyError:
            return {'latitude': lat, 'longitude': lon, 'date': date_start, 't2m': -999.00}
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

    valid_results = [r for r in results if r and r['t2m'] != -999.00]
    if not valid_results:
        return {"error": "No valid data retrieved."}
    df = pd.DataFrame(valid_results)
    for year in YEAR_RANGE:
        year_str = str(year)
        subset = df[df['date'].str.startswith(year_str)]
        if not subset.empty:
            avg_t2m = subset['t2m'].mean()
            if round(avg_t2m) < 15:
                t2m_values["LOW"] += 1
            elif 15 <= round(avg_t2m) <= 25:
                t2m_values["MEDIUM"] += 1
            else:
                t2m_values["HIGH"] += 1

    total_years = len(YEAR_RANGE)
    probs = {
        "HIGH": t2m_values["HIGH"] / total_years,
        "MEDIUM": t2m_values["MEDIUM"] / total_years,
        "LOW": t2m_values["LOW"] / total_years
    }
    return probs