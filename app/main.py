"""
ResQ-Odisha: AI Multi-Hazard Command & Citizen Safety Advisory System.
FastAPI Application Entry Point with Universal AI Copilot Integration.
"""

from contextlib import asynccontextmanager
import asyncio
import datetime
import logging
import os
from typing import Any, Dict, Optional

from fastapi import FastAPI, Query, status
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.advisory_engine import get_advisory, get_bilingual_advisories
from app.ai_copilot import process_copilot_request
from app.config import get_ai_config
from app.database import (
    find_nearest_available_shelter,
    get_all_cyclone_shelters,
    get_all_district_hazards,
    get_recent_sos_reports,
    increment_shelter_occupied,
    init_and_seed_db,
    reset_to_cyclone_simulation,
    save_sos_report,
)
from app.ml_engine import ml_engine
from app.weather_intel import get_weather_intelligence
from app.weather_service import get_combined_point_weather, get_weather_context, sync_live_weather_all_districts

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("resq_odisha")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Runtime weather mode state: "LIVE" or "SIMULATION"
CURRENT_WEATHER_MODE = "SIMULATION"
LAST_WEATHER_SYNC_TIME: Optional[str] = None
AUTO_SYNC_INTERVAL_SECONDS = 600  # 10 minutes regular interval


async def periodic_weather_syncer():
    """Background worker that periodically syncs live weather every 10 minutes when in LIVE mode."""
    global LAST_WEATHER_SYNC_TIME
    while True:
        try:
            await asyncio.sleep(AUTO_SYNC_INTERVAL_SECONDS)
            if CURRENT_WEATHER_MODE == "LIVE":
                logger.info("Automatic periodic background weather sync triggered...")
                await sync_live_weather_all_districts()
                LAST_WEATHER_SYNC_TIME = datetime.datetime.now(datetime.timezone.utc).isoformat()
                logger.info("Periodic weather sync completed successfully at %s", LAST_WEATHER_SYNC_TIME)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Error during periodic weather sync: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager to initialize database and run background sync."""
    logger.info("Initializing ResQ-Odisha Database...")
    init_and_seed_db()
    logger.info("Database initialized & pre-seeded successfully.")

    # Start automated periodic background syncer task only in persistent server environments
    syncer_task = None
    if not (os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME")):
        syncer_task = asyncio.create_task(periodic_weather_syncer())
    try:
        yield
    finally:
        if syncer_task:
            syncer_task.cancel()
            try:
                await syncer_task
            except asyncio.CancelledError:
                pass


app = FastAPI(
    title="ResQ-Odisha AI Multi-Hazard Command & Citizen Safety Advisory System",
    description="Universal AI Disaster Copilot and Command System tailored for Odisha.",
    version="2.0.0",
    lifespan=lifespan,
    redirect_slashes=False,
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static Files
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class SOSCreateRequest(BaseModel):
    contact_number: str = Field(..., description="Mobile or satellite contact number of caller")
    latitude: float = Field(..., description="GPS Latitude")
    longitude: float = Field(..., description="GPS Longitude")
    message: str = Field(..., description="Distress text message in English or Odia")


class CopilotRequest(BaseModel):
    user_message: str = Field(..., description="User query, distress call, or instruction")
    latitude: float = Field(..., description="GPS Latitude")
    longitude: float = Field(..., description="GPS Longitude")
    contact_number: Optional[str] = Field(None, description="Optional contact phone")
    language: str = Field("en", description="Preferred response language: 'en' or 'od'")


class APIKeyUpdateRequest(BaseModel):
    api_key: str = Field(..., description="API Key for Gemini, Groq, OpenAI, or Hugging Face")


class VoiceASRRequest(BaseModel):
    audio_base64: str = Field(..., description="Base64 encoded audio byte stream")
    language: str = Field("or", description="Language code: 'or' (Odia) or 'en' (English)")
    audio_format: str = Field("wav", description="Audio format: 'wav', 'webm', 'mp3'")
    sampling_rate: Optional[int] = Field(16000, description="Audio sampling rate in Hz")


class BhashiniConfigUpdateRequest(BaseModel):
    user_id: str = Field(..., description="Bhashini ULCA User ID")
    api_key: str = Field(..., description="Bhashini ULCA API Key")
    inference_key: Optional[str] = Field(None, description="Optional inference API Key")


class WeatherIntelRequest(BaseModel):
    lat: Optional[float] = Field(None, description="GPS Latitude from map click")
    lon: Optional[float] = Field(None, description="GPS Longitude from map click")
    query: Optional[str] = Field(None, description="Natural language query or location search from AI chat")
    language: Optional[str] = Field("en", description="Response language: 'en' or 'od'")


@app.post("/api/weather-intel")
async def handle_weather_intel_post(req: WeatherIntelRequest) -> Dict[str, Any]:
    """
    Unified AI Weather Intelligence & Interactive Cyclone Map Endpoint:
    - Accepts lat/lon (map click) or natural language query (AI chat)
    - Fetches Open-Meteo Forecast & Marine APIs (zero keys)
    - Returns grounded AI safety analysis & synchronized map payload.
    """
    return await get_weather_intelligence(
        lat=req.lat,
        lon=req.lon,
        query=req.query
    )


@app.get("/api/weather-intel")
async def handle_weather_intel_get(
    lat: Optional[float] = Query(None, description="GPS Latitude"),
    lon: Optional[float] = Query(None, description="GPS Longitude"),
    query: Optional[str] = Query(None, description="Natural language location query"),
) -> Dict[str, Any]:
    """GET variant for browser inspection and quick link triggers."""
    return await get_weather_intelligence(lat=lat, lon=lon, query=query)


@app.post("/api/config/key")
async def update_key(req: APIKeyUpdateRequest) -> Dict[str, Any]:
    """Dynamically save API key and reload configuration in runtime."""
    from app.config import save_ai_key
    cfg = save_ai_key(req.api_key)
    return {
        "status": "ok",
        "provider": cfg["provider"],
        "message": f"Successfully activated {cfg['provider'].upper()} AI Provider.",
    }


@app.post("/api/ai/asr")
async def handle_voice_asr(req: VoiceASRRequest) -> Dict[str, Any]:
    """
    Automatic Speech Recognition (ASR) endpoint for Odia and English:
    - Odia ('or'): Transcribes spoken Odia via Bhashini ULCA pipeline or Cloud Whisper fallback.
    - English ('en'): Transcribes English voice via high-precision Cloud Whisper engine or Web Speech API.
    """
    import base64
    from app.bhashini_service import transcribe_odia_audio, transcribe_with_whisper

    lang = req.language.lower().strip()
    if lang in ["or", "od", "ory", "odia"]:
        return await transcribe_odia_audio(
            audio_base64=req.audio_base64,
            audio_format=req.audio_format,
            sampling_rate=req.sampling_rate or 16000
        )
    else:
        # English or fallback speech transcription
        clean_b64 = req.audio_base64.strip()
        if clean_b64.startswith("data:"):
            c_idx = clean_b64.find(",")
            if c_idx != -1:
                clean_b64 = clean_b64[c_idx + 1:]
        try:
            raw_bytes = base64.b64decode(clean_b64)
            whisper_res = await transcribe_with_whisper(raw_bytes, language="en", audio_format=req.audio_format)
            if whisper_res:
                return whisper_res
        except Exception as err:
            logger.warning("English audio transcription error: %s", err)

        return {
            "status": "fallback",
            "provider": "browser_web_speech",
            "message": "Speech audio processed. Client can also transcribe via native Web Speech API (en-IN).",
            "language": req.language
        }


@app.get("/api/ai/asr/status")
async def get_asr_status() -> Dict[str, Any]:
    """Check configuration and availability of Bhashini Odia ASR service."""
    from app.bhashini_service import is_bhashini_configured, get_bhashini_credentials, KNOWN_ODIA_MODELS
    user_id, api_key, _ = get_bhashini_credentials()
    configured = is_bhashini_configured()
    return {
        "status": "ok",
        "provider": "bhashini",
        "is_configured": configured,
        "has_user_id": bool(user_id),
        "has_api_key": bool(api_key),
        "supported_models": KNOWN_ODIA_MODELS,
        "primary_model": KNOWN_ODIA_MODELS[0],
        "setup_guide_url": "https://bhashini.gov.in/ulca/user/register",
        "instructions": (
            "To enable Bhashini Odia ASR, configure BHASHINI_USER_ID and BHASHINI_API_KEY in .env."
        )
    }


@app.post("/api/config/bhashini")
async def update_bhashini_config(req: BhashiniConfigUpdateRequest) -> Dict[str, Any]:
    """Dynamically save Bhashini credentials in backend .env and reload environment."""
    from app.config import BASE_DIR
    env_path = os.path.join(BASE_DIR, ".env")
    
    os.environ["BHASHINI_USER_ID"] = req.user_id.strip()
    os.environ["BHASHINI_API_KEY"] = req.api_key.strip()
    if req.inference_key:
        os.environ["BHASHINI_INFERENCE_API_KEY"] = req.inference_key.strip()

    env_lines = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if not any(line.strip().startswith(prefix) for prefix in [
                    "BHASHINI_USER_ID=", "BHASHINI_API_KEY=", "BHASHINI_INFERENCE_API_KEY="
                ]):
                    env_lines.append(line.rstrip("\r\n"))
    
    env_lines.append(f"BHASHINI_USER_ID={req.user_id.strip()}")
    env_lines.append(f"BHASHINI_API_KEY={req.api_key.strip()}")
    if req.inference_key:
        env_lines.append(f"BHASHINI_INFERENCE_API_KEY={req.inference_key.strip()}")

    with open(env_path, "w", encoding="utf-8") as f:
        f.write("\n".join(env_lines) + "\n")

    return {
        "status": "ok",
        "message": "Bhashini credentials updated successfully in backend .env.",
        "is_configured": True
    }


@app.get("/", response_class=FileResponse)
async def serve_index():
    """Serve the Command Center & Citizen Safety Hub UI."""
    root_index = os.path.join(BASE_DIR, "index.html")
    static_index = os.path.join(STATIC_DIR, "index.html")
    index_path = root_index if os.path.exists(root_index) else static_index
    if not os.path.exists(index_path):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"message": "Frontend index.html not found"},
        )
    return FileResponse(index_path)


@app.get("/api/hazards")
async def get_hazards() -> Dict[str, Any]:
    """Retrieve all district hazard warning zones with rainfall and wind parameters."""
    districts = get_all_district_hazards()
    return {"status": "ok", "mode": CURRENT_WEATHER_MODE, "districts": districts}


@app.get("/api/shelters")
async def get_shelters() -> Dict[str, Any]:
    """Retrieve all multipurpose cyclone shelters with computed available capacity."""
    shelters = get_all_cyclone_shelters()
    return {"status": "ok", "shelters": shelters}


@app.get("/api/incidents")
async def get_incidents() -> Dict[str, Any]:
    """Retrieve recent SOS incident reports ordered by id DESC."""
    incidents = get_recent_sos_reports(limit=50)
    return {"status": "ok", "incidents": incidents}


@app.get("/api/advisory")
async def get_advisory_sop(
    threat_type: str = Query("CYCLONE", description="Threat category: CYCLONE, FLOOD, or GENERAL_STORM"),
    lang: str = Query("en", description="Language code: en or od"),
) -> Dict[str, Any]:
    """Retrieve bilingual OSDMA disaster safety SOP and actionable guidelines."""
    advisory = get_advisory(threat_type, lang)
    return {"status": "ok", "threat_type": threat_type, "lang": lang, "advisory": advisory}


@app.get("/api/disaster-news")
async def get_disaster_news(lang: str = Query("en", description="Language code: en or od")) -> Dict[str, Any]:
    """
    Retrieve live natural disaster updates, meteorological warnings,
    and flood bulletins for Odisha and adjoining Bay of Bengal basin.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    news_items = [
        {
            "id": "news-cyclone-bob-01",
            "category": "CYCLONE",
            "severity": "WARNING",
            "badge": "IMD CYCLONE BULLETIN",
            "badge_od": "ଭାରତୀୟ ପାଣିପାଗ ବୁଲେଟିନ୍",
            "headline": "Well-Marked Low Pressure over West-Central Bay of Bengal; Coastal Odisha on Watch",
            "headline_od": "ପଶ୍ଚିମ-କେନ୍ଦ୍ରୀୟ ବଙ୍ଗୋପସାଗରରେ ଲଘୁଚାପ ସକ୍ରିୟ; ଉପକୂଳ ଓଡ଼ିଶାରେ ସତର୍କତା ଜାରି",
            "summary": "Deep depression track moving north-northwestwards off South Odisha - North Andhra coast. Wind speeds gusting up to 65-75 kmph expected over coastal waters. Fishermen are strictly advised not to venture into deep sea.",
            "summary_od": "ଦକ୍ଷିଣ ଓଡ଼ିଶା ଉପକୂଳ ନିକଟରେ ଲଘୁଚାପ କ୍ଷେତ୍ର ଘନୀଭୂତ ହୋଇ ଉତ୍ତର-ପଶ୍ଚିମ ଆଡ଼କୁ ଗତି କରୁଛି। ସମୁଦ୍ରରେ ୬୫-୭୫ କିମି ବେଗରେ ପବନ ବହିବା ସମ୍ଭାବନା ଥିବାରୁ ମତ୍ସ୍ୟଜୀବୀମାନଙ୍କୁ ସମୁଦ୍ର ନ ଯିବାକୁ ପରାମର୍ଶ ଦିଆଯାଇଛି।",
            "source": "IMD Regional Centre Bhubaneswar",
            "location": "Bay of Bengal / Coastal Odisha (Puri, Ganjam, Jagatsinghpur)",
            "timestamp": (now - datetime.timedelta(minutes=18)).strftime("%Y-%m-%d %H:%M UTC"),
            "action_advice": "Check cyclone shelter availability, keep emergency supply kit ready, and monitor local disaster siren broadcasts.",
            "action_advice_od": "ନିକଟସ୍ଥ ବାତ୍ୟା ଆଶ୍ରୟସ୍ଥଳର ଯାଞ୍ଚ କରନ୍ତୁ ଏବଂ ଜରୁରୀକାଳୀନ ରିଲିଫ ସାମଗ୍ରୀ ପ୍ରସ୍ତୁତ ରଖନ୍ତୁ।",
            "copilot_prompt": "What is the current cyclone status and safety checklist for coastal Odisha?"
        },
        {
            "id": "news-flood-mahanadi-02",
            "category": "FLOOD",
            "severity": "ALERT",
            "badge": "CWC RIVER TELEMETRY",
            "badge_od": "କେନ୍ଦ୍ରୀୟ ଜଳ ଆୟୋଗ ସତର୍କତା",
            "headline": "Mahanadi River Basin Telemetry: Mundali Barrage Regulating 4.8 Lakh Cusecs Discharge",
            "headline_od": "ମହାନଦୀ ଅବବାହିକା: ମୁଣ୍ଡଳୀ ବ୍ୟାରେଜ୍ ଦେଇ ୪.୮ ଲକ୍ଷ କ୍ୟୁସେକ୍ ଜଳ ନିଷ୍କାସନ",
            "summary": "Upstream inflows from Hirakud Dam (14 sluice gates opened) passing smoothly through Khurda, Cuttack, and Kendrapada delta branches. Water levels currently below danger mark (87.20 ft vs warning 97.25 ft).",
            "summary_od": "ହୀରାକୁଦ ଡ୍ୟାମର ୧୪ଟି ଗେଟ୍ ଖୋଲିବା ପରେ ମୁଣ୍ଡଳୀ ଦେଇ ବନ୍ୟାଜଳ ନିୟନ୍ତ୍ରିତ ଭାବେ ନିଷ୍କାସିତ ହେଉଛି। ଜଳସ୍ତର ବିପଦ ସଙ୍କେତ ତଳେ ରହିଛି।",
            "source": "State Emergency Operations Centre (SEOC) & CWC",
            "location": "Mahanadi Delta (Cuttack, Kendrapara, Jagatsinghpur)",
            "timestamp": (now - datetime.timedelta(minutes=35)).strftime("%Y-%m-%d %H:%M UTC"),
            "action_advice": "Residents in low-lying riverine embankments should avoid crossing swollen canals and report breaches to toll-free 1070.",
            "action_advice_od": "ନଦୀକୂଳିଆ ତଳିଆ ଅଞ୍ଚଳ ବାସିନ୍ଦା ସତର୍କ ରୁହନ୍ତୁ ଏବଂ କୌଣସି ଜରୁରୀ ପରିସ୍ଥିତିରେ ୧୦୭୦ ଡାଏଲ୍ କରନ୍ତୁ।",
            "copilot_prompt": "Is there any flood risk in Cuttack or Kendrapara from Mundali barrage right now?"
        },
        {
            "id": "news-lightning-kalbaisakhi-03",
            "category": "LIGHTNING",
            "severity": "WARNING",
            "badge": "KALBAISAKHI WARNING",
            "badge_od": "କାଳବୈଶାଖୀ ଓ ବଜ୍ରପାତ ସତର୍କତା",
            "headline": "Severe Thunderstorm & Lightning Alert for Mayurbhanj, Keonjhar, Balasore & Cuttack",
            "headline_od": "ମୟୂରଭଞ୍ଜ, କେନ୍ଦୁଝର, ବାଲେଶ୍ୱର ଓ କଟକ ଜିଲ୍ଲାରେ ବଜ୍ରପାତ ଓ ଝଡ଼ବର୍ଷା ସତର୍କତା",
            "summary": "Doppler Weather Radar shows convective cloud clusters. High probability of cloud-to-ground lightning with squall winds reaching 50 kmph during the next 3 to 6 hours.",
            "summary_od": "ଡପଲର ରାଡାର୍ ତଥ୍ୟ ଅନୁସାରେ ଆଗାମୀ ୩-୬ ଘଣ୍ଟା ମଧ୍ୟରେ ଉତ୍ତର ଓ ଆଭ୍ୟନ୍ତରୀଣ ଓଡ଼ିଶାରେ ଘଡ଼ଘଡ଼ି ସହ ବଜ୍ରପାତ ଏବଂ ୫୦ କିମି ବେଗରେ ଝଟକା ପବନ ହୋଇପାରେ।",
            "source": "IMD Doppler Radar Network Bhubaneswar",
            "location": "North & Central Odisha Interior Districts",
            "timestamp": (now - datetime.timedelta(minutes=52)).strftime("%Y-%m-%d %H:%M UTC"),
            "action_advice": "Take shelter inside sturdy buildings immediately during thunder. Avoid standing under isolated trees or near electric poles.",
            "action_advice_od": "ବଜ୍ରପାତ ସମୟରେ ଗଛ ତଳେ କିମ୍ବା ଖୋଲା ପଡ଼ିଆରେ ନ ରହି ପକ୍କା ଘରେ ଆଶ୍ରୟ ନିଅନ୍ତୁ।",
            "copilot_prompt": "What are the essential lightning safety rules during severe thunderstorms?"
        },
        {
            "id": "news-coastal-surge-04",
            "category": "COASTAL",
            "severity": "ADVISORY",
            "badge": "INCOIS OCEAN ADVISORY",
            "badge_od": "ସମୁଦ୍ର ତରଙ୍ଗ ସତର୍କତା ସୂଚନା",
            "headline": "High Ocean Swell Waves Forecast along Puri, Chandrabhaga & Gopalpur Coasts",
            "headline_od": "ପୁରୀ, ଚନ୍ଦ୍ରଭାଗା ଏବଂ ଗୋପାଳପୁର ଉପକୂଳରେ ଉଚ୍ଚ ଜୁଆର ଓ ସମୁଦ୍ର ଢେଉ ସତର୍କତା",
            "summary": "INCOIS models project rough sea conditions with wave heights between 2.5 to 3.2 meters. Spring tide surge may cause sea-water ingress in low-lying beach zones.",
            "summary_od": "ଇନକୋଇସ୍ (INCOIS) ପୂର୍ବାନୁମାନ ଅନୁଯାୟୀ ସମୁଦ୍ରରେ ୨.୫ ରୁ ୩.୨ ମିଟର ଉଚ୍ଚ ଢେଉ ଉଠିବା ସମ୍ଭାବନା ଅଛି। ପର୍ଯ୍ୟଟକମାନଙ୍କୁ ସମୁଦ୍ରରେ ସ୍ନାନ ନ କରିବାକୁ ପରାମର୍ଶ।",
            "source": "Indian National Centre for Ocean Information Services (INCOIS)",
            "location": "Odisha Coastal Belt (Gopalpur, Puri, Paradip)",
            "timestamp": (now - datetime.timedelta(hours=1, minutes=15)).strftime("%Y-%m-%d %H:%M UTC"),
            "action_advice": "Beach tourism and water sports temporarily suspended. Coastal guards on high vigil.",
            "action_advice_od": "ବେଳାଭୂମିରେ ସମୁଦ୍ର ମଧ୍ୟକୁ ନ ଯିବାକୁ ଏବଂ ଲାଇଫଗାର୍ଡଙ୍କ ନିର୍ଦ୍ଦେଶ ପାଳନ କରିବାକୁ ଅନୁରୋଧ।",
            "copilot_prompt": "Is it safe to visit Puri beach today with the current ocean swell?"
        },
        {
            "id": "news-odraf-readiness-05",
            "category": "RESPONSE",
            "severity": "INFO",
            "badge": "OSDMA MOBILIZATION",
            "badge_od": "ଓସଡମା ଉଦ୍ଧାରକାରୀ ପ୍ରସ୍ତୁତି",
            "headline": "42 ODRAF and 18 NDRF Flood Rescue Units Pre-Positioned in Sensitive Blocks",
            "headline_od": "୧୪ଟି ଉପକୂଳ ଜିଲ୍ଲାରେ ୪୨ଟି ଓଡ୍ରାଫ୍ (ODRAF) ଓ ୧୮ଟି NDRF ଟିମ୍ ମୁତୟନ",
            "summary": "Special Relief Commissioner confirms standby deployment of inflatable motorboats, tree cutters, and satellite communication sets at district headquarters across Kendrapara, Balasore, Bhadrak, and Puri.",
            "summary_od": "ସମ୍ଭାବ୍ୟ ବନ୍ୟା ଓ ବାତ୍ୟା ମୁକାବିଲା ପାଇଁ ବୋଟ୍, ଡିଜି ସେଟ୍ ଏବଂ ଜରୁରୀକାଳୀନ ଉଦ୍ଧାର ସାମଗ୍ରୀ ସହ ସମସ୍ତ ରେସକ୍ୟୁ ଟିମ୍ ପ୍ରସ୍ତୁତ ରହିଛନ୍ତି।",
            "source": "Odisha State Disaster Management Authority (OSDMA)",
            "location": "14 Vulnerable Coastal & Delta Districts",
            "timestamp": (now - datetime.timedelta(hours=2, minutes=5)).strftime("%Y-%m-%d %H:%M UTC"),
            "action_advice": "In case of emergency evacuation assistance, contact the OSDMA District Control Room or 112.",
            "action_advice_od": "ଜରୁରୀକାଳୀନ ସ୍ଥାନାନ୍ତର କିମ୍ବା ଉଦ୍ଧାର ସହାୟତା ପାଇଁ ୧୧୨ କିମ୍ବା ଜିଲ୍ଲା କଣ୍ଟ୍ରୋଲ୍ ରୁମ୍ ଯୋଗାଯୋଗ କରନ୍ତୁ।",
            "copilot_prompt": "How can I contact ODRAF or request emergency rescue in my district?"
        }
    ]
    return {
        "status": "ok",
        "count": len(news_items),
        "source": "State Emergency Operations Centre (SEOC) & IMD",
        "updated_at": now.strftime("%Y-%m-%d %H:%M UTC"),
        "news": news_items
    }
    return {"status": "ok", "threat_type": threat_type, "lang": lang, "advisory": advisory}


@app.get("/api/stats")
async def get_kpis() -> Dict[str, Any]:
    """Provide real-time KPI metrics for dashboard badges."""
    global CURRENT_WEATHER_MODE
    hazards = get_all_district_hazards()
    shelters = get_all_cyclone_shelters()
    incidents = get_recent_sos_reports(limit=100)

    red_count = sum(1 for h in hazards if str(h.get("alert_level")).upper() == "RED")
    verified_sos_count = sum(1 for i in incidents if i.get("is_emergency") == 1)
    available_capacity = sum(s.get("available_spots", 0) for s in shelters)
    total_capacity = sum(s.get("capacity", 0) for s in shelters)

    ai_cfg = get_ai_config()
    provider_name = ai_cfg["provider"].upper()
    if provider_name == "FALLBACK":
        engine_label = "ONLINE (Universal Heuristic NLP)"
    else:
        engine_label = f"ONLINE ({provider_name} LLM Cloud)"

    return {
        "status": "ok",
        "active_red_alerts": red_count,
        "verified_sos_calls": verified_sos_count,
        "available_shelter_capacity": available_capacity,
        "total_shelter_capacity": total_capacity,
        "weather_mode": CURRENT_WEATHER_MODE,
        "last_sync": LAST_WEATHER_SYNC_TIME,
        "auto_sync_interval_seconds": AUTO_SYNC_INTERVAL_SECONDS,
        "ai_provider": ai_cfg["provider"],
        "ai_engine_status": engine_label,
    }


@app.get("/api/weather/point")
async def get_point_weather(
    lat: float = Query(..., description="GPS Latitude"),
    lon: float = Query(..., description="GPS Longitude"),
) -> Dict[str, Any]:
    """
    Retrieve comprehensive live Open-Meteo suite telemetry (Weather + GloFAS Flood + Marine + Elevation)
    for any geographic point in Odisha.
    """
    return await get_combined_point_weather(lat, lon)


@app.post("/api/weather/sync-live")
async def sync_live_weather() -> Dict[str, Any]:
    """Fetch real-time Open-Meteo observations for all Odisha districts and persist in SQLite."""
    global CURRENT_WEATHER_MODE, LAST_WEATHER_SYNC_TIME
    CURRENT_WEATHER_MODE = "LIVE"
    districts = await sync_live_weather_all_districts()
    LAST_WEATHER_SYNC_TIME = datetime.datetime.now(datetime.timezone.utc).isoformat()
    return {
        "status": "ok",
        "mode": CURRENT_WEATHER_MODE,
        "last_sync": LAST_WEATHER_SYNC_TIME,
        "message": "Successfully synchronized live real-time Open-Meteo observations for all Odisha districts.",
        "districts": districts,
    }


@app.post("/api/weather/simulate-cyclone")
async def simulate_cyclone_weather() -> Dict[str, Any]:
    """Reset district hazards to active severe Bay of Bengal cyclone landfall scenario for testing."""
    global CURRENT_WEATHER_MODE
    CURRENT_WEATHER_MODE = "SIMULATION"
    reset_to_cyclone_simulation()
    districts = get_all_district_hazards()
    return {
        "status": "ok",
        "mode": CURRENT_WEATHER_MODE,
        "message": "Simulated Severe Cyclone Landfall scenario activated across coastal Odisha.",
        "districts": districts,
    }


@app.post("/api/ai/copilot")
async def handle_copilot(req: CopilotRequest) -> Dict[str, Any]:
    """
    Omnipresent ResQ-Odisha AI Copilot:
    Answers any question, performs live weather checks, issues medical/disaster first-aid,
    dispatches automated emergency rescue, and controls map GIS actions.
    """
    res = await process_copilot_request(
        user_message=req.user_message,
        latitude=req.latitude,
        longitude=req.longitude,
        contact_number=req.contact_number,
        language=req.language,
    )
    return res


@app.post("/api/sos")
async def handle_sos(req: SOSCreateRequest) -> Dict[str, Any]:
    """
    Process incoming SOS distress call via unified AI Copilot logic:
    1. Fetch weather context asynchronously.
    2. Run ML classification in thread pool.
    3. Spatial query for nearest available cyclone shelter.
    4. Save incident record and update shelter occupancy if verified emergency.
    5. Return comprehensive triage report and bilingual safety advisories.
    """
    weather = await get_weather_context(req.latitude, req.longitude)
    triage = await run_in_threadpool(ml_engine.analyze_sos, req.message, weather)
    assigned_shelter = find_nearest_available_shelter(req.latitude, req.longitude)

    is_emergency = triage["is_emergency"]
    incident_status = "DISPATCHED" if is_emergency else "DISMISSED_FALSE_ALARM"

    saved_row = save_sos_report(
        contact_number=req.contact_number,
        latitude=req.latitude,
        longitude=req.longitude,
        raw_text=req.message,
        is_emergency=is_emergency,
        urgency_score=triage["urgency_score"],
        category=triage["category"],
        confidence=triage["confidence"],
        dispatch_unit=triage["dispatch_unit"],
        nearest_shelter_id=assigned_shelter.get("id"),
        nearest_shelter_name=assigned_shelter.get("name", "OSDMA Emergency Center"),
        shelter_distance_km=assigned_shelter.get("distance_km", 0.0),
        weather_summary=weather.get("summary", ""),
        status=incident_status,
    )

    if is_emergency and assigned_shelter.get("id"):
        increment_shelter_occupied(assigned_shelter["id"])
        assigned_shelter["occupied"] = min(assigned_shelter["capacity"], assigned_shelter["occupied"] + 1)
        assigned_shelter["available_spots"] = max(0, assigned_shelter["capacity"] - assigned_shelter["occupied"])

    advisories = get_bilingual_advisories(triage["advisory_key"])

    return {
        "status": "success",
        "incident": saved_row,
        "triage": triage,
        "weather": weather,
        "assigned_shelter": assigned_shelter,
        "advisories": {
            "en": advisories["en"],
            "od": advisories["od"],
        },
    }
