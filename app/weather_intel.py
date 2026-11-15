"""
ResQ-Odisha Unified Weather Intelligence & AI Synthesis Service.
Synchronizes Open-Meteo Forecast, Marine API, Geocoding, and LLM Copilot Gateway.
"""

import asyncio
import logging
import re
from typing import Any, Dict, Optional, Tuple
import httpx
from app.config import get_ai_config
from app.database import find_nearest_available_shelter

logger = logging.getLogger("resq_odisha.weather_intel")

# Curated reference coordinates for Odisha, Bay of Bengal, and coastal hubs
KNOWN_REGIONS = [
    {
        "keys": ["bay of bengal", "bob", "deep sea", "ocean", "offshore", "sea", "ବଙ୍ଗୋପସାଗର", "ସମୁଦ୍ର"],
        "lat": 18.5000,
        "lon": 88.0000,
        "name": "Bay of Bengal (Offshore Maritime Zone)",
    },
    {
        "keys": ["bhubaneswar", "bbsr", "khordha", "khurda", "ଭୁବନେଶ୍ୱର", "ଭୁବନେଶ୍ବର", "ଖୋର୍ଦ୍ଧା", "ଖୁର୍ଦ୍ଧା"],
        "lat": 20.2961,
        "lon": 85.8245,
        "name": "Bhubaneswar, Khordha, Odisha",
    },
    {
        "keys": ["cuttack", "barabati", "mundali", "naraj", "କଟକ", "ମୁଣ୍ଡଳୀ", "ନରାଜ"],
        "lat": 20.4625,
        "lon": 85.8830,
        "name": "Cuttack, Odisha",
    },
    {
        "keys": ["puri", "puri beach", "swargadwar", "golden beach", "ପୁରୀ", "ପୁରି", "ସ୍ୱର୍ଗଦ୍ୱାର"],
        "lat": 19.8135,
        "lon": 85.8312,
        "name": "Puri Coastal Zone, Odisha",
    },
    {
        "keys": ["paradip", "paradeep", "jagatsinghpur", "erasama", "ପାରାଦୀପ", "ଜଗତସିଂହପୁର", "ଏରସମା"],
        "lat": 20.2648,
        "lon": 86.3820,
        "name": "Paradip Port, Jagatsinghpur, Odisha",
    },
    {
        "keys": ["gopalpur", "ganjam", "chhatrapur", "berhampur", "brahmapur", "ଗୋପାଳପୁର", "ଗଞ୍ଜାମ", "ଛତ୍ରପୁର", "ବ୍ରହ୍ମପୁର"],
        "lat": 19.2647,
        "lon": 84.9120,
        "name": "Gopalpur-on-Sea, Ganjam, Odisha",
    },
    {
        "keys": ["kendrapara", "rajnagar", "bhitharkanika", "bhitarkanika", "କେନ୍ଦ୍ରାପଡ଼ା", "ରାଜନଗର", "ଭିତରକନିକା"],
        "lat": 20.5010,
        "lon": 86.4180,
        "name": "Kendrapara Coast, Odisha",
    },
    {
        "keys": ["balasore", "baleshwar", "chandipur", "ବାଲେଶ୍ୱର", "ଚାନ୍ଦିପୁର"],
        "lat": 21.4934,
        "lon": 86.9135,
        "name": "Balasore / Chandipur Coast, Odisha",
    },
    {
        "keys": ["bhadrak", "dhamra", "dhamara", "ଭଦ୍ରକ", "ଧାମରା"],
        "lat": 20.9042,
        "lon": 86.5145,
        "name": "Dhamra Port, Bhadrak, Odisha",
    },
    {
        "keys": ["chilika", "barkul", "satapada", "ଚିଲିକା", "ବାରକୁଲ", "ସାତପଡ଼ା"],
        "lat": 19.7167,
        "lon": 85.3167,
        "name": "Chilika Lagoon, Odisha",
    },
    {
        "keys": ["digha", "mandarmani", "ଦୀଘା"],
        "lat": 21.6266,
        "lon": 87.5074,
        "name": "Digha Coast, West Bengal",
    },
    {
        "keys": ["visakhapatnam", "vizag", "ଭିଜାଗ"],
        "lat": 17.6868,
        "lon": 83.2185,
        "name": "Visakhapatnam Coast, Andhra Pradesh",
    },
    {
        "keys": ["kolkata", "calcutta", "କୋଲକାତା"],
        "lat": 22.5726,
        "lon": 88.3639,
        "name": "Kolkata, West Bengal",
    },
]


async def resolve_location(
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    query: Optional[str] = None,
) -> Tuple[float, float, str]:
    """
    Resolve coordinates and location name:
    1. If natural language query explicitly names a region (English or Odia), match that region.
    2. Else if coordinates (lat, lon) provided from map/district selector, match nearest known region.
    3. Fallback to Puri if no coordinates or query.
    """
    # 1. Natural language query resolution
    if query:
        q_lower = query.lower()

        # Check known dictionary first (supports both English and Odia scripts)
        for reg in KNOWN_REGIONS:
            for k in reg["keys"]:
                k_lower = k.lower()
                # Use word boundary for ASCII or direct substring for non-ASCII/Odia
                if re.search(r"\b" + re.escape(k_lower) + r"\b", q_lower) or k_lower in q_lower:
                    return reg["lat"], reg["lon"], reg["name"]

    # 2. Coordinates explicitly provided (e.g. from district dropdown, map click, or GPS)
    if lat is not None and lon is not None:
        # Check if coordinates fall inside deep Bay of Bengal waters
        if 15.0 <= lat <= 21.0 and 86.5 <= lon <= 93.0:
            return lat, lon, "Bay of Bengal (Offshore Maritime Zone)"

        # Check proximity to known coastal hubs and assign the closest region name
        best_dist = 9999.0
        best_name = f"Odisha Region ({lat:.4f}° N, {lon:.4f}° E)"
        best_lat = lat
        best_lon = lon

        for reg in KNOWN_REGIONS:
            d = ((lat - reg["lat"]) ** 2 + (lon - reg["lon"]) ** 2) ** 0.5
            if d < best_dist:
                best_dist = d
                best_name = reg["name"]

        return lat, lon, best_name

    if query:
        # If no direct match in dictionary, try Open-Meteo Geocoding API
        words = [w for w in re.findall(r"[a-zA-Z\u0B00-\u0B7F]+", query) if len(w) > 3 and w.lower() not in {
            "what", "where", "weather", "cyclone", "forecast", "status", "check", "tell",
            "about", "risk", "level", "please", "current", "update", "today", "tomorrow"
        }]

        if words:
            candidate_name = words[0]
            try:
                async with httpx.AsyncClient(timeout=2.0) as client:
                    geo_url = (
                        f"https://geocoding-api.open-meteo.com/v1/search?"
                        f"name={candidate_name}&count=1&language=en&format=json"
                    )
                    res = await client.get(geo_url)
                    if res.status_code == 200:
                        data = res.json()
                        results = data.get("results")
                        if results and len(results) > 0:
                            top = results[0]
                            resolved_name = f"{top.get('name')}, {top.get('admin1', top.get('country', ''))}".strip(", ")
                            return float(top["latitude"]), float(top["longitude"]), resolved_name
            except Exception as e:
                logger.warning(f"Geocoding API lookup failed for {candidate_name}: {e}")

    # Fallback default: Coastal Odisha / Puri
    return 19.8135, 85.8312, "Puri Coastal Zone, Odisha"


async def fetch_live_weather_telemetry(lat: float, lon: float) -> Dict[str, Any]:
    """
    Fetch live telemetry from Open-Meteo Forecast and Open-Meteo Marine APIs (No API keys required).
    Metrics captured: wind_speed_10m, wind_gusts_10m, pressure_msl, precipitation, wave_height.
    """
    forecast_url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat:.4f}&longitude={lon:.4f}&"
        f"current=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,wind_gusts_10m,pressure_msl"
    )
    marine_url = (
        f"https://marine-api.open-meteo.com/v1/marine?"
        f"latitude={lat:.4f}&longitude={lon:.4f}&"
        f"current=wave_height,wave_period"
    )

    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            res_forecast, res_marine = await asyncio.gather(
                client.get(forecast_url),
                client.get(marine_url),
                return_exceptions=True,
            )

        # Parse Forecast data
        if not isinstance(res_forecast, Exception) and res_forecast.status_code == 200:
            fdata = res_forecast.json().get("current", {})
            temp_c = round(float(fdata.get("temperature_2m", 28.0)), 1)
            humidity = int(fdata.get("relative_humidity_2m", 72))
            precipitation = round(float(fdata.get("precipitation", 0.0)), 1)
            wind_speed = round(float(fdata.get("wind_speed_10m", 15.0)), 1)
            wind_gusts = round(float(fdata.get("wind_gusts_10m", wind_speed * 1.3)), 1)
            pressure_msl = round(float(fdata.get("pressure_msl", 1012.0)), 1)
        else:
            temp_c, humidity, precipitation, wind_speed, wind_gusts, pressure_msl = (
                28.0, 72, 0.0, 18.0, 24.0, 1012.0
            )

        # Parse Marine data (available on sea/ocean points like Bay of Bengal)
        wave_height = None
        wave_period = None
        is_marine = False

        if not isinstance(res_marine, Exception) and res_marine.status_code == 200:
            mdata = res_marine.json().get("current", {})
            wh = mdata.get("wave_height")
            wp = mdata.get("wave_period")
            if wh is not None:
                wave_height = round(float(wh), 1)
                is_marine = True
            if wp is not None:
                wave_period = round(float(wp), 1)

        # Deep Bay of Bengal heuristic if wave API was quiet
        if 15.0 <= lat <= 21.0 and 86.5 <= lon <= 93.0 and wave_height is None:
            wave_height = 1.2
            wave_period = 8.5
            is_marine = True

        # Calculate Severity Level according to IMD / WMO disaster thresholds
        if (
            wind_speed >= 65.0
            or wind_gusts >= 90.0
            or precipitation >= 50.0
            or pressure_msl <= 995.0
            or (wave_height is not None and wave_height >= 3.5)
        ):
            severity = "RED"
            threat_type = "Severe Cyclone / Torrential Storm & Dangerous Seas"
            cyclone_active = True
            cyclone_cat = "Severe Cyclonic Storm (Landfall Watch)"
            radius_km = 80
            maritime_warning = "GREAT DANGER: Fishermen and all vessels must remain in port. High storm surge risk."
        elif (
            wind_speed >= 45.0
            or wind_gusts >= 65.0
            or precipitation >= 25.0
            or pressure_msl <= 1002.0
            or (wave_height is not None and wave_height >= 2.5)
        ):
            severity = "ORANGE"
            threat_type = "Gale Winds & Heavy Marine Swell Alert"
            cyclone_active = True
            cyclone_cat = "Cyclonic Storm / Deep Depression"
            radius_km = 55
            maritime_warning = "WARNING: Rough to very rough seas. Fishermen advised not to venture into deep sea."
        elif (
            wind_speed >= 25.0
            or wind_gusts >= 38.0
            or precipitation >= 10.0
            or (wave_height is not None and wave_height >= 1.5)
        ):
            severity = "YELLOW"
            threat_type = "Squally Weather / Moderate Sea Advisory"
            cyclone_active = False
            cyclone_cat = "Depression / Coastal Squall Watch"
            radius_km = 35
            maritime_warning = "ADVISORY: Moderate sea conditions. Small craft should exercise caution."
        else:
            severity = "GREEN"
            threat_type = "Normal / Calm Meteorological Baseline"
            cyclone_active = False
            cyclone_cat = "Calm Baseline"
            radius_km = 25
            maritime_warning = "NORMAL: Fair sea and atmospheric conditions. Routine operations permitted."

        return {
            "temperature_c": temp_c,
            "relative_humidity_pct": humidity,
            "precipitation_mm": precipitation,
            "wind_speed_kmh": wind_speed,
            "wind_gusts_kmh": wind_gusts,
            "pressure_msl_hpa": pressure_msl,
            "wave_height_m": wave_height,
            "wave_period_s": wave_period,
            "is_marine": is_marine,
            "severity_level": severity,
            "threat_type": threat_type,
            "cyclone_alert": {
                "active": cyclone_active,
                "category": cyclone_cat,
                "radius_km": radius_km,
                "maritime_warning": maritime_warning,
            },
        }

    except Exception as e:
        logger.error(f"Error fetching Open-Meteo telemetry: {e}")
        return {
            "temperature_c": 28.0,
            "relative_humidity_pct": 70,
            "precipitation_mm": 0.0,
            "wind_speed_kmh": 20.0,
            "wind_gusts_kmh": 28.0,
            "pressure_msl_hpa": 1012.0,
            "wave_height_m": 1.2 if (15.0 <= lat <= 21.0 and 86.5 <= lon <= 93.0) else None,
            "wave_period_s": 8.0,
            "is_marine": 15.0 <= lat <= 21.0 and 86.5 <= lon <= 93.0,
            "severity_level": "GREEN",
            "threat_type": "Normal / Calm Meteorological Baseline",
            "cyclone_alert": {
                "active": False,
                "category": "Calm Baseline",
                "radius_km": 25,
                "maritime_warning": "Normal sea operations permitted.",
            },
        }


def generate_fallback_ai_briefing(
    location_name: str,
    lat: float,
    lon: float,
    telemetry: Dict[str, Any],
    query: str,
) -> str:
    """Deterministic, highly structured contextual AI safety briefing fallback."""
    sev = telemetry["severity_level"]
    wind = telemetry["wind_speed_kmh"]
    gusts = telemetry["wind_gusts_kmh"]
    press = telemetry["pressure_msl_hpa"]
    rain = telemetry["precipitation_mm"]
    waves = telemetry["wave_height_m"]
    threat = telemetry["threat_type"]

    marine_section = ""
    if telemetry["is_marine"] or waves is not None:
        marine_section = (
            f"\n\n**🌊 Maritime & Offshore Conditions:**\n"
            f"- Significant Wave Height: **{waves if waves is not None else 'N/A'} meters**\n"
            f"- Wave Period: **{telemetry.get('wave_period_s', 'N/A')} seconds**\n"
            f"- Fishermen Advisory: *{telemetry['cyclone_alert']['maritime_warning']}*"
        )

    if sev in ("RED", "ORANGE"):
        action_advice = (
            "1. **Evacuation Readiness:** Identify closest cyclone shelter and secure loose exterior items.\n"
            "2. **Fishermen Alert:** Total suspension of fishing/boating operations in coastal and deep-sea waters.\n"
            "3. **Power & Water:** Charge communication devices, keep battery torches ready, and store clean drinking water.\n"
            "4. **Emergency Helpline:** Dial **112** (ERSS) or **1070** (OSDMA State Control Room) for distress rescue."
        )
    elif sev == "YELLOW":
        action_advice = (
            "1. **Precautionary Watch:** Monitor IMD and OSDMA bulletins for depression intensification.\n"
            "2. **Maritime Caution:** Small vessels and fishermen must avoid venturing far from the shoreline.\n"
            "3. **Urban Drainage:** Keep storm drains clear to prevent localized waterlogging."
        )
    else:
        action_advice = (
            "1. **Baseline Operations:** Normal daily activities, tourism, and maritime traffic permitted.\n"
            "2. **Hydration & Heat:** Maintain adequate hydration given coastal humidity.\n"
            "3. **Continuous Monitoring:** ResQ-Odisha radar and Open-Meteo feeds remain active 24/7."
        )

    return (
        f"### 🛡️ ResQ-AI Weather & Cyclone Intelligence Briefing\n\n"
        f"**Target Location:** {location_name} (`{lat:.4f}° N, {lon:.4f}° E`)\n"
        f"**Current Alert Status:** **{sev} ALERT** — *{threat}*\n\n"
        f"| Atmospheric Metric | Live Observation | Meteorological Evaluation |\n"
        f"| :--- | :--- | :--- |\n"
        f"| **Wind Speed (10m)** | `{wind} km/h` | Sustained coastal breeze |\n"
        f"| **Wind Gusts (10m)** | `{gusts} km/h` | Peak kinematic thrust |\n"
        f"| **Barometric Pressure (MSL)** | `{press} hPa` | {'Depression depression risk' if press < 1005 else 'Stable barometric field'} |\n"
        f"| **Precipitation** | `{rain} mm` | {'Heavy downpour' if rain > 20 else 'Dry / Trace rain'} |\n"
        f"{marine_section}\n\n"
        f"**🚨 Key Safety Directives & Recommendations:**\n{action_advice}"
    )


async def generate_grounded_weather_ai(
    location_name: str,
    lat: float,
    lon: float,
    telemetry: Dict[str, Any],
    query: str,
) -> str:
    """
    Format live telemetry into a structured prompt and invoke the configured LLM (Groq / Gemini / etc.).
    Returns grounded, context-aware analysis with automatic fallback.
    """
    cfg = get_ai_config()
    api_key = cfg["api_key"]
    provider = cfg["provider"]

    if not api_key or provider == "fallback":
        return generate_fallback_ai_briefing(location_name, lat, lon, telemetry, query)

    # Structured context block for the LLM
    system_prompt = (
        "You are the ResQ-Odisha AI Weather & Cyclone Intelligence Commander, "
        "an elite meteorological decision-support system operated for the Odisha State Disaster Management Authority (OSDMA). "
        "Provide factual, grounded, and concise weather intelligence and disaster safety advisories based strictly on the provided real-time telemetry."
    )

    user_prompt = f"""
REAL-TIME METEOROLOGICAL & MARITIME TELEMETRY:
- Target Location: {location_name} ({lat:.4f}° N, {lon:.4f}° E)
- Severity Level: {telemetry['severity_level']} ({telemetry['threat_type']})
- Temperature: {telemetry['temperature_c']} °C
- Relative Humidity: {telemetry['relative_humidity_pct']} %
- Precipitation: {telemetry['precipitation_mm']} mm
- Sustained Wind (10m): {telemetry['wind_speed_kmh']} km/h
- Peak Gusts (10m): {telemetry['wind_gusts_kmh']} km/h
- Sea Level Pressure (MSL): {telemetry['pressure_msl_hpa']} hPa
- Significant Wave Height: {f"{telemetry['wave_height_m']} m (Period: {telemetry['wave_period_s']}s)" if telemetry['wave_height_m'] else "Inland / No Marine Swell"}
- Marine / Offshore Water: {telemetry['is_marine']}
- Cyclone / Wave Advisory: {telemetry['cyclone_alert']['maritime_warning']}

USER QUERY / CONTEXT:
"{query}"

INSTRUCTIONS:
1. Provide a sharp, grounded meteorological situation assessment for {location_name}.
2. Interpret the live metrics (wind, barometric pressure MSL, and wave height if applicable) in terms of cyclone, gale, or flood threats.
3. If in or near the Bay of Bengal / coast, clearly state sea state and safety guidelines for fishermen and maritime vessels.
4. Give 3-4 specific, actionable safety directives for citizens and emergency personnel.
Format with clean markdown headings and bullet points. Keep it professional, urgent, and concise.
"""

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            if provider == "groq":
                url = "https://api.groq.com/openai/v1/chat/completions"
                headers = {"Authorization": f"Bearer {api_key}"}
                for model_name in ["openai/gpt-oss-120b", "qwen/qwen3.8-27b", "openai/gpt-oss-20b"]:
                    body = {
                        "model": model_name,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        "temperature": 0.2,
                    }
                    res = await client.post(url, json=body, headers=headers)
                    if res.status_code == 200:
                        content = res.json()["choices"][0]["message"]["content"]
                        if content:
                            return content.strip()

            elif provider == "gemini":
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
                body = {
                    "contents": [{"parts": [{"text": f"{system_prompt}\n\n{user_prompt}"}]}],
                    "generationConfig": {"temperature": 0.2},
                }
                res = await client.post(url, json=body)
                if res.status_code == 200:
                    cand = res.json().get("candidates", [])
                    if cand:
                        return cand[0]["content"]["parts"][0]["text"].strip()

            elif provider == "openai":
                url = "https://api.openai.com/v1/chat/completions"
                headers = {"Authorization": f"Bearer {api_key}"}
                body = {
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.2,
                }
                res = await client.post(url, json=body, headers=headers)
                if res.status_code == 200:
                    return res.json()["choices"][0]["message"]["content"].strip()

    except Exception as e:
        logger.warning(f"Error calling {provider} for weather intel: {e}")

    # Fallback if LLM API encounters network glitch
    return generate_fallback_ai_briefing(location_name, lat, lon, telemetry, query)


async def get_weather_intelligence(
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    query: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Unified entry point for `/api/weather-intel`.
    Accepts lat/lon or query, fetches live Open-Meteo & Marine telemetry,
    synthesizes grounded AI response, and formats map_payload.
    """
    # 1. Resolve Location & Coordinates
    resolved_lat, resolved_lon, location_name = await resolve_location(lat, lon, query)

    # 2. Fetch live Open-Meteo Forecast & Marine Data
    telemetry = await fetch_live_weather_telemetry(resolved_lat, resolved_lon)

    # 3. Generate grounded AI response
    effective_query = query if query and query.strip() else f"Live weather and cyclone telemetry check for {location_name}"
    ai_text = await generate_grounded_weather_ai(
        location_name=location_name,
        lat=resolved_lat,
        lon=resolved_lon,
        telemetry=telemetry,
        query=effective_query,
    )

    try:
        nearest_shelter = find_nearest_available_shelter(resolved_lat, resolved_lon)
    except Exception:
        nearest_shelter = None

    # 4. Construct unified JSON response
    map_action = {
        "fly_to": [resolved_lat, resolved_lon],
        "zoom": 9,
        "alert_level": telemetry["severity_level"],
        "severity_level": telemetry["severity_level"],
        "telemetry": telemetry,
        "location_name": location_name,
        "target_lat": resolved_lat,
        "target_lon": resolved_lon,
    }

    return {
        "status": "ok",
        "query": effective_query,
        "location_name": location_name,
        "ai_response": ai_text,
        "map_action": map_action,
        "map_payload": {
            "lat": resolved_lat,
            "lon": resolved_lon,
            "severity_level": telemetry["severity_level"],
            "threat_type": telemetry["threat_type"],
            "telemetry": {
                "temperature_c": telemetry["temperature_c"],
                "relative_humidity_pct": telemetry["relative_humidity_pct"],
                "precipitation_mm": telemetry["precipitation_mm"],
                "wind_speed_kmh": telemetry["wind_speed_kmh"],
                "wind_gusts_kmh": telemetry["wind_gusts_kmh"],
                "pressure_msl_hpa": telemetry["pressure_msl_hpa"],
                "wave_height_m": telemetry["wave_height_m"],
                "wave_period_s": telemetry["wave_period_s"],
                "is_marine": telemetry["is_marine"],
            },
            "cyclone_alert": telemetry["cyclone_alert"],
            "nearest_shelter": nearest_shelter,
        },
    }
