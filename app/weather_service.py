"""
Weather Context & Multi-Endpoint Open-Meteo Suite Service.
Queries Open-Meteo Forecast, GloFAS Flood, and Marine APIs for real-time
meteorological conditions, river discharge, wave heights, and elevation.
Supports single-point inspections, batch district updates, and cyclone simulation.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
import httpx
from app.database import find_nearest_district, get_all_district_hazards, update_district_hazard

logger = logging.getLogger("resq_odisha.weather")

DISTRICT_COORDINATES = [
    ("Puri", 19.8135, 85.8312),
    ("Jagatsinghpur (Paradip/Erasama)", 20.2648, 86.3820),
    ("Kendrapara", 20.5010, 86.4180),
    ("Cuttack", 20.4625, 85.8830),
    ("Khordha (Bhubaneswar)", 20.2961, 85.8245),
    ("Ganjam (Gopalpur)", 19.2647, 84.9120),
]


async def get_combined_point_weather(latitude: float, longitude: float) -> Dict[str, Any]:
    """
    Fetch comprehensive live telemetry for any geographic coordinate in Odisha:
    1. Open-Meteo Forecast: Temperature, Humidity, Rain, Wind, Wind Gusts, Pressure, Elevation
    2. Open-Meteo GloFAS: River Discharge (m³/s) for river basins (Mahanadi, Baitarani, etc.)
    3. Open-Meteo Marine: Significant Wave Height (m) & Wave Period (s) for coastal points
    """
    forecast_url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={latitude:.4f}&longitude={longitude:.4f}&"
        f"current=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,wind_gusts_10m,surface_pressure"
    )
    flood_url = (
        f"https://flood-api.open-meteo.com/v1/flood?"
        f"latitude={latitude:.4f}&longitude={longitude:.4f}&"
        f"daily=river_discharge&forecast_days=1"
    )
    marine_url = (
        f"https://marine-api.open-meteo.com/v1/marine?"
        f"latitude={latitude:.4f}&longitude={longitude:.4f}&"
        f"current=wave_height,wave_period"
    )

    nearest = find_nearest_district(latitude, longitude)
    district_name = nearest.get("district_name", "Odisha Coastal Zone")

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            responses = await asyncio.gather(
                client.get(forecast_url),
                client.get(flood_url),
                client.get(marine_url),
                return_exceptions=True
            )

        forecast_res, flood_res, marine_res = responses

        # 1. Parse Forecast Data
        if not isinstance(forecast_res, Exception) and forecast_res.status_code == 200:
            fdata = forecast_res.json()
            curr = fdata.get("current", {})
            temp_c = round(float(curr.get("temperature_2m", 28.0)), 1)
            humidity = int(curr.get("relative_humidity_2m", 70))
            precipitation = round(float(curr.get("precipitation", 0.0)), 1)
            wind_speed = round(float(curr.get("wind_speed_10m", 0.0)), 1)
            wind_gusts = round(float(curr.get("wind_gusts_10m", wind_speed * 1.25)), 1)
            pressure = round(float(curr.get("surface_pressure", 1010.0)), 1)
            elevation = round(float(fdata.get("elevation", 12.0)), 1)
        else:
            temp_c = 28.0
            humidity = 75
            precipitation = float(nearest.get("rainfall_mm", 0.0))
            wind_speed = float(nearest.get("wind_kmh", 15.0))
            wind_gusts = round(wind_speed * 1.25, 1)
            pressure = 1008.0
            elevation = 15.0

        # Determine Alert Level & Threat Category
        if precipitation >= 60.0 or wind_speed >= 75.0:
            alert_level = "RED"
            threat_type = "Severe Cyclone / Torrential Downpour"
        elif precipitation >= 30.0 or wind_speed >= 50.0:
            alert_level = "ORANGE"
            threat_type = "Gale Winds & High Flood Risk"
        elif precipitation >= 10.0 or wind_speed >= 25.0:
            alert_level = "YELLOW"
            threat_type = "Squally Weather & Waterlogging"
        else:
            alert_level = "GREEN"
            threat_type = "Normal / Calm Baseline"

        # 2. Parse GloFAS River Discharge
        river_discharge = None
        if not isinstance(flood_res, Exception) and flood_res.status_code == 200:
            try:
                gdata = flood_res.json()
                discharges = gdata.get("daily", {}).get("river_discharge", [])
                if discharges and discharges[0] is not None:
                    river_discharge = round(float(discharges[0]), 2)
            except Exception as e:
                logger.debug("GloFAS parse error: %s", e)

        # 3. Parse Marine Wave Height & Period
        wave_height = None
        wave_period = None
        is_coastal = False
        if not isinstance(marine_res, Exception) and marine_res.status_code == 200:
            try:
                mdata = marine_res.json()
                mcurr = mdata.get("current", {})
                wh = mcurr.get("wave_height")
                wp = mcurr.get("wave_period")
                if wh is not None:
                    wave_height = round(float(wh), 2)
                    is_coastal = True
                if wp is not None:
                    wave_period = round(float(wp), 1)
            except Exception as e:
                logger.debug("Marine parse error: %s", e)

        summary_parts = [
            f"Temp: {temp_c}°C",
            f"Rain: {precipitation} mm",
            f"Wind: {wind_speed} km/h (Gusts: {wind_gusts} km/h)",
            f"Pressure: {pressure} hPa",
            f"Elev: {elevation} m ASL",
        ]
        if river_discharge is not None:
            summary_parts.append(f"River Discharge: {river_discharge} m³/s")
        if wave_height is not None:
            summary_parts.append(f"Wave Height: {wave_height} m ({wave_period}s)")

        summary = (
            f"Live Telemetry ({district_name} [{alert_level}]): "
            + ", ".join(summary_parts)
            + "."
        )

        return {
            "status": "ok",
            "latitude": round(latitude, 4),
            "longitude": round(longitude, 4),
            "temperature_c": temp_c,
            "relative_humidity_pct": humidity,
            "precipitation_mm": precipitation,
            "rainfall_mm": precipitation,  # alias for backward-compatibility
            "wind_speed_kmh": wind_speed,
            "wind_kmh": wind_speed,        # alias for backward-compatibility
            "wind_gusts_kmh": wind_gusts,
            "surface_pressure_hpa": pressure,
            "elevation_m": elevation,
            "river_discharge_m3s": river_discharge,
            "wave_height_m": wave_height,
            "wave_period_s": wave_period,
            "is_coastal": is_coastal,
            "alert_level": alert_level,
            "threat_type": threat_type,
            "summary": summary,
            "nearest_district": district_name,
            "source": "open-meteo-suite",
        }

    except Exception as exc:
        logger.warning("Combined Open-Meteo suite query failed (%s). Using fallback.", exc)
        rainfall = float(nearest.get("rainfall_mm", 0.0))
        wind = float(nearest.get("wind_kmh", 15.0))
        alert_level = nearest.get("alert_level", "GREEN")
        threat = nearest.get("threat_type", "Calm Weather Baseline")

        summary = (
            f"District Hazard Fallback: {district_name} - "
            f"Rain {rainfall:.1f} mm, Wind {wind:.1f} km/h. "
            f"Alert: {alert_level} ({threat})."
        )

        return {
            "status": "ok",
            "latitude": round(latitude, 4),
            "longitude": round(longitude, 4),
            "temperature_c": 28.0,
            "relative_humidity_pct": 70,
            "precipitation_mm": round(rainfall, 1),
            "rainfall_mm": round(rainfall, 1),
            "wind_speed_kmh": round(wind, 1),
            "wind_kmh": round(wind, 1),
            "wind_gusts_kmh": round(wind * 1.25, 1),
            "surface_pressure_hpa": 1010.0,
            "elevation_m": 15.0,
            "river_discharge_m3s": None,
            "wave_height_m": None,
            "wave_period_s": None,
            "is_coastal": False,
            "alert_level": alert_level,
            "threat_type": threat,
            "summary": summary,
            "nearest_district": district_name,
            "source": "district-fallback",
        }


async def get_weather_context(latitude: float, longitude: float) -> Dict[str, Any]:
    """Retrieve weather context dict for triage & AI copilot inference."""
    return await get_combined_point_weather(latitude, longitude)


async def sync_live_weather_all_districts() -> List[Dict[str, Any]]:
    """
    Batch-fetch real-time weather from Open-Meteo Forecast API for all 6 pre-seeded
    Odisha districts in a single HTTP request using comma-separated coordinates,
    and persist live observations, elevations, and alert levels into SQLite.
    """
    lats_str = ",".join(f"{lat:.4f}" for _, lat, _ in DISTRICT_COORDINATES)
    lons_str = ",".join(f"{lon:.4f}" for _, _, lon in DISTRICT_COORDINATES)

    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lats_str}&longitude={lons_str}&"
        f"current=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,wind_gusts_10m,surface_pressure"
    )

    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            response = await client.get(url)

        if response.status_code == 200:
            results = response.json()
            # If multiple coordinates are requested, Open-Meteo returns a list of dicts
            if not isinstance(results, list):
                results = [results]

            for i, (name, lat, lon) in enumerate(DISTRICT_COORDINATES):
                if i < len(results):
                    data = results[i]
                    curr = data.get("current", {})
                    temp = round(float(curr.get("temperature_2m", 28.0)), 1)
                    humidity = int(curr.get("relative_humidity_2m", 70))
                    rain = round(float(curr.get("precipitation", 0.0)), 1)
                    wind = round(float(curr.get("wind_speed_10m", 0.0)), 1)
                    gusts = round(float(curr.get("wind_gusts_10m", wind * 1.25)), 1)
                    pressure = round(float(curr.get("surface_pressure", 1010.0)), 1)
                    elevation = round(float(data.get("elevation", 12.0)), 1)

                    if rain >= 60.0 or wind >= 75.0:
                        alert = "RED"
                        threat = "Severe Cyclone / Torrential Downpour"
                    elif rain >= 30.0 or wind >= 50.0:
                        alert = "ORANGE"
                        threat = "Gale Winds & River Swelling"
                    elif rain >= 10.0 or wind >= 25.0:
                        alert = "YELLOW"
                        threat = "Localized Squall & Showers"
                    else:
                        alert = "GREEN"
                        threat = "Normal Coastal Baseline"

                    summary = (
                        f"Live Open-Meteo: {temp}°C, {humidity}% humidity, "
                        f"Rain {rain}mm, Wind {wind}km/h (Gusts {gusts}km/h), "
                        f"Pres {pressure}hPa, Elev {elevation}m ASL. Alert: {alert}."
                    )
                    update_district_hazard(name, rain, wind, alert, threat, summary)
                    logger.info("Updated district %s -> Rain: %s mm, Wind: %s km/h [%s]", name, rain, wind, alert)
        else:
            logger.warning("Batch Open-Meteo forecast returned status %s: %s", response.status_code, response.text)
    except Exception as exc:
        logger.error("Failed to batch-sync live weather for districts: %s", exc)

    return get_all_district_hazards()
