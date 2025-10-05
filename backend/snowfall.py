import asyncio
import aiohttp
import pandas as pd

async def compute_probabilities(lat: float, lon: float, month: int, day: int):
    PARAMETER = "PRECSNO"  # Snowfall parameter
    COORDINATE_GRID = [(lat, lon)]

    precsno_values = {"NONE": 0, "LOW": 0, "MEDIUM": 0, "HIGH": 0}
    base_url = "https://power.larc.nasa.gov/api/temporal/daily/point"
    YEAR_RANGE = range(1995, 2025)

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
                precsno_value = data['properties']['parameter'][PARAMETER][date_start]
                return {'latitude': lat, 'longitude': lon, 'date': date_start, 'precsno': precsno_value}
        except asyncio.TimeoutError:
            return None
        except KeyError:
            return {'latitude': lat, 'longitude': lon, 'date': date_start, 'precsno': -999.00}
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

    valid_results = [r for r in results if r and r['precsno'] != -999.00]
    if not valid_results:
        return {"error": "No valid data retrieved."}
    df = pd.DataFrame(valid_results)
    for year in YEAR_RANGE:
        year_str = str(year)
        subset = df[df['date'].str.startswith(year_str)]
        if not subset.empty:
            avg_precsno = subset['precsno'].mean()
            if avg_precsno == 0:
                precsno_values["NONE"] += 1
            elif avg_precsno > 0 and avg_precsno <= 2.5:
                precsno_values["LOW"] += 1
            elif avg_precsno > 2.5 and avg_precsno <= 7.5:
                precsno_values["MEDIUM"] += 1
            else:
                precsno_values["HIGH"] += 1

    total_years = len(YEAR_RANGE)
    probs = {
        "HIGH": precsno_values["HIGH"] / total_years,
        "MEDIUM": precsno_values["MEDIUM"] / total_years,
        "LOW": precsno_values["LOW"] / total_years,
        "NONE": precsno_values["NONE"] / total_years
    }
    return probs