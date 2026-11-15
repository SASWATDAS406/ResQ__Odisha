import math
import os
import sqlite3
from typing import Any, Dict, List, Optional

DB_PATH = os.environ.get(
    "RESQ_DB_PATH",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resq_odisha.db"),
)


def get_db_connection() -> sqlite3.Connection:
    """Connect to SQLite with sqlite3.Row row factory for dict-like access."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points on Earth in kilometers."""
    r = 6371.0  # Earth's radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


def init_and_seed_db() -> None:
    """Initialize database tables and seed required data if tables are empty."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # 1. District Hazards Table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS district_hazards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                district_name TEXT UNIQUE,
                lat REAL,
                lon REAL,
                radius_meters INTEGER,
                alert_level TEXT,
                threat_type TEXT,
                rainfall_mm REAL,
                wind_kmh REAL,
                summary TEXT
            )
            """
        )

        # 2. Cyclone Shelters Table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS cyclone_shelters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                district TEXT,
                latitude REAL,
                longitude REAL,
                capacity INTEGER,
                occupied INTEGER,
                contact_phone TEXT
            )
            """
        )

        # 3. SOS Reports Table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sos_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contact_number TEXT,
                latitude REAL,
                longitude REAL,
                raw_text TEXT,
                is_emergency INTEGER,
                urgency_score INTEGER,
                category TEXT,
                confidence REAL,
                dispatch_unit TEXT,
                nearest_shelter_id INTEGER,
                nearest_shelter_name TEXT,
                shelter_distance_km REAL,
                weather_summary TEXT,
                status TEXT DEFAULT 'DISPATCHED',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # Seed District Hazards if empty
        cursor.execute("SELECT COUNT(*) FROM district_hazards")
        if cursor.fetchone()[0] == 0:
            district_seeds = [
                (
                    "Puri",
                    19.8135,
                    85.8312,
                    28000,
                    "RED",
                    "Cyclone & Storm Surge",
                    115.0,
                    98.0,
                    "Severe storm surge of 1.5m expected along Puri coast. Immediate evacuation of low-lying wards.",
                ),
                (
                    "Jagatsinghpur (Paradip/Erasama)",
                    20.2648,
                    86.3820,
                    30000,
                    "RED",
                    "Severe Cyclone Landfall",
                    130.0,
                    110.0,
                    "Landfall proximity zone. High velocity gale winds and tidal inundation in Erasama & Paradip.",
                ),
                (
                    "Kendrapara",
                    20.5010,
                    86.4180,
                    26000,
                    "ORANGE",
                    "Tidal Inundation & Flood",
                    78.0,
                    82.0,
                    "Saline water ingression and Brahmani-Baitarani deltaic river swelling.",
                ),
                (
                    "Cuttack",
                    20.4625,
                    85.8830,
                    24000,
                    "ORANGE",
                    "Mahanadi Basin Flooding",
                    68.0,
                    55.0,
                    "Rising water levels at Mundali barrage. Low-lying riverbank villages on high alert.",
                ),
                (
                    "Khordha (Bhubaneswar)",
                    20.2961,
                    85.8245,
                    22000,
                    "YELLOW",
                    "Urban Waterlogging & Squalls",
                    48.0,
                    52.0,
                    "Intense rain spells causing urban waterlogging and localized tree uprooting.",
                ),
                (
                    "Ganjam (Gopalpur)",
                    19.2647,
                    84.9120,
                    25000,
                    "YELLOW",
                    "Rough Sea & High Swells",
                    35.0,
                    45.0,
                    "Fishermen advised not to venture into the Bay of Bengal.",
                ),
            ]
            cursor.executemany(
                """
                INSERT INTO district_hazards (
                    district_name, lat, lon, radius_meters, alert_level, threat_type, rainfall_mm, wind_kmh, summary
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                district_seeds,
            )

        # Seed Cyclone Shelters if empty
        cursor.execute("SELECT COUNT(*) FROM cyclone_shelters")
        if cursor.fetchone()[0] == 0:
            shelter_seeds = [
                (
                    "Puri Town Hall Multipurpose Cyclone Shelter",
                    "Puri",
                    19.8135,
                    85.8312,
                    800,
                    320,
                    "06752-222044",
                ),
                (
                    "Erasama Block OSDMA Cyclone Center",
                    "Jagatsinghpur",
                    20.1872,
                    86.4258,
                    1200,
                    850,
                    "06724-272231",
                ),
                (
                    "Paradip Port Trust Community Shelter",
                    "Jagatsinghpur",
                    20.3165,
                    86.6114,
                    1000,
                    410,
                    "06722-222004",
                ),
                (
                    "Kendrapara Autonomous High School MCS",
                    "Kendrapara",
                    20.5042,
                    86.4215,
                    600,
                    180,
                    "06727-232028",
                ),
                (
                    "SOA Campus 2 Emergency Shelter Hub",
                    "Khordha",
                    20.2520,
                    85.7760,
                    1500,
                    210,
                    "0674-2350635",
                ),
                (
                    "Gopalpur Coastal Marine Shelter",
                    "Ganjam",
                    19.2600,
                    84.9100,
                    500,
                    90,
                    "0680-2343211",
                ),
            ]
            cursor.executemany(
                """
                INSERT INTO cyclone_shelters (
                    name, district, latitude, longitude, capacity, occupied, contact_phone
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                shelter_seeds,
            )

        # Seed initial sample SOS reports if empty
        cursor.execute("SELECT COUNT(*) FROM sos_reports")
        if cursor.fetchone()[0] == 0:
            sos_seeds = [
                (
                    "+91-9437011223",
                    19.8050,
                    85.8250,
                    "Water level rising fast inside ground floor near Puri sea beach road, 4 elderly people trapped, need rescue boat urgently!",
                    1,
                    5,
                    "flood rescue",
                    0.96,
                    "ODRAF Inflatable Power Boat Unit",
                    1,
                    "Puri Town Hall Multipurpose Cyclone Shelter",
                    1.14,
                    "Precipitation: 115.0mm, Wind: 98.0 km/h [RED ALERT - Puri]",
                    "DISPATCHED",
                ),
                (
                    "+91-9861099887",
                    20.1920,
                    86.4180,
                    "Severe cyclone winds blew away tin roof in Erasama block, wall collapsed, one person has severe leg injury and bleeding.",
                    1,
                    5,
                    "structural collapse",
                    0.94,
                    "NDRF Heavy Cutting & Search Team",
                    2,
                    "Erasama Block OSDMA Cyclone Center",
                    0.96,
                    "Precipitation: 130.0mm, Wind: 110.0 km/h [RED ALERT - Jagatsinghpur]",
                    "DISPATCHED",
                ),
            ]
            cursor.executemany(
                """
                INSERT INTO sos_reports (
                    contact_number, latitude, longitude, raw_text, is_emergency, urgency_score,
                    category, confidence, dispatch_unit, nearest_shelter_id, nearest_shelter_name,
                    shelter_distance_km, weather_summary, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                sos_seeds,
            )

        conn.commit()


def get_all_district_hazards() -> List[Dict[str, Any]]:
    """Retrieve all district hazards."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM district_hazards ORDER BY alert_level ASC, district_name ASC")
        return [dict(row) for row in cursor.fetchall()]


def get_all_cyclone_shelters() -> List[Dict[str, Any]]:
    """Retrieve all cyclone shelters with computed available spots."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cyclone_shelters ORDER BY district ASC, name ASC")
        shelters = []
        for row in cursor.fetchall():
            s = dict(row)
            s["available_spots"] = max(0, s["capacity"] - s["occupied"])
            shelters.append(s)
        return shelters


def get_recent_sos_reports(limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieve recent SOS incident reports ordered by id DESC."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sos_reports ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(row) for row in cursor.fetchall()]


def find_nearest_available_shelter(lat: float, lon: float) -> Dict[str, Any]:
    """Find the nearest cyclone shelter with available capacity."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cyclone_shelters WHERE (capacity - occupied) > 0")
        rows = cursor.fetchall()

        if not rows:
            # Fallback to any shelter if all are full
            cursor.execute("SELECT * FROM cyclone_shelters")
            rows = cursor.fetchall()

        if not rows:
            return {
                "id": None,
                "name": "OSDMA Mobile Relief Hub",
                "district": "Unknown",
                "latitude": lat,
                "longitude": lon,
                "capacity": 1000,
                "occupied": 0,
                "available_spots": 1000,
                "contact_phone": "1070",
                "distance_km": 0.0,
            }

        best_shelter = None
        min_dist = float("inf")

        for r in rows:
            shelter_dict = dict(r)
            dist = haversine_km(lat, lon, shelter_dict["latitude"], shelter_dict["longitude"])
            if dist < min_dist:
                min_dist = dist
                shelter_dict["available_spots"] = max(0, shelter_dict["capacity"] - shelter_dict["occupied"])
                shelter_dict["distance_km"] = round(dist, 2)
                best_shelter = shelter_dict

        return best_shelter or {}


def find_top_available_shelters(lat: float, lon: float, top_n: int = 3) -> List[Dict[str, Any]]:
    """Find top N nearest cyclone shelters with available capacity."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cyclone_shelters WHERE (capacity - occupied) > 0")
        rows = cursor.fetchall()
        if not rows:
            cursor.execute("SELECT * FROM cyclone_shelters")
            rows = cursor.fetchall()

        results = []
        for r in rows:
            s = dict(r)
            dist = haversine_km(lat, lon, s["latitude"], s["longitude"])
            s["available_spots"] = max(0, s["capacity"] - s["occupied"])
            s["distance_km"] = round(dist, 2)
            results.append(s)

        results.sort(key=lambda x: x["distance_km"])
        return results[:top_n]


def update_district_hazard(
    district_name: str,
    rainfall_mm: float,
    wind_kmh: float,
    alert_level: str,
    threat_type: str,
    summary: str,
) -> None:
    """Update meteorological conditions and alert status for a district."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE district_hazards
            SET rainfall_mm = ?, wind_kmh = ?, alert_level = ?, threat_type = ?, summary = ?
            WHERE district_name = ?
            """,
            (rainfall_mm, wind_kmh, alert_level, threat_type, summary, district_name),
        )
        conn.commit()


def reset_to_cyclone_simulation() -> None:
    """Reset all district hazards to the high-severity simulated cyclone landfall state."""
    cyclone_seeds = [
        ("Puri", 115.0, 98.0, "RED", "Cyclone & Storm Surge", "Severe storm surge of 1.5m expected along Puri coast. Immediate evacuation of low-lying wards."),
        ("Jagatsinghpur (Paradip/Erasama)", 130.0, 110.0, "RED", "Severe Cyclone Landfall", "Landfall proximity zone. High velocity gale winds and tidal inundation in Erasama & Paradip."),
        ("Kendrapara", 78.0, 82.0, "ORANGE", "Tidal Inundation & Flood", "Saline water ingression and Brahmani-Baitarani deltaic river swelling."),
        ("Cuttack", 68.0, 55.0, "ORANGE", "Mahanadi Basin Flooding", "Rising water levels at Mundali barrage. Low-lying riverbank villages on high alert."),
        ("Khordha (Bhubaneswar)", 48.0, 52.0, "YELLOW", "Urban Waterlogging & Squalls", "Intense rain spells causing urban waterlogging and localized tree uprooting."),
        ("Ganjam (Gopalpur)", 35.0, 45.0, "YELLOW", "Rough Sea & High Swells", "Fishermen advised not to venture into the Bay of Bengal."),
    ]
    with get_db_connection() as conn:
        cursor = conn.cursor()
        for name, rain, wind, alert, threat, summ in cyclone_seeds:
            cursor.execute(
                """
                UPDATE district_hazards
                SET rainfall_mm = ?, wind_kmh = ?, alert_level = ?, threat_type = ?, summary = ?
                WHERE district_name = ?
                """,
                (rain, wind, alert, threat, summ, name),
            )
        conn.commit()


def find_nearest_district(lat: float, lon: float) -> Dict[str, Any]:
    """Find the nearest pre-seeded district hazard entry."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM district_hazards")
        rows = cursor.fetchall()
        if not rows:
            return {
                "district_name": "Odisha Coastal Zone",
                "rainfall_mm": 50.0,
                "wind_kmh": 60.0,
                "alert_level": "ORANGE",
                "threat_type": "Coastal Squall",
                "summary": "Coastal squall and rough seas along Bay of Bengal.",
                "distance_km": 0.0,
            }

        best_district = None
        min_dist = float("inf")
        for r in rows:
            d = dict(r)
            dist = haversine_km(lat, lon, d["lat"], d["lon"])
            if dist < min_dist:
                min_dist = dist
                d["distance_km"] = round(dist, 2)
                best_district = d

        return best_district or {}


def increment_shelter_occupied(shelter_id: int) -> None:
    """Safely increment shelter occupancy by 1 if capacity allows."""
    if not shelter_id:
        return
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE cyclone_shelters
            SET occupied = occupied + 1
            WHERE id = ? AND occupied < capacity
            """,
            (shelter_id,),
        )
        conn.commit()


def save_sos_report(
    contact_number: str,
    latitude: float,
    longitude: float,
    raw_text: str,
    is_emergency: bool,
    urgency_score: int,
    category: str,
    confidence: float,
    dispatch_unit: str,
    nearest_shelter_id: Optional[int],
    nearest_shelter_name: str,
    shelter_distance_km: float,
    weather_summary: str,
    status: str = "DISPATCHED",
) -> Dict[str, Any]:
    """Save an SOS incident report to SQLite and return the created record."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO sos_reports (
                contact_number, latitude, longitude, raw_text, is_emergency, urgency_score,
                category, confidence, dispatch_unit, nearest_shelter_id, nearest_shelter_name,
                shelter_distance_km, weather_summary, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                contact_number,
                latitude,
                longitude,
                raw_text,
                1 if is_emergency else 0,
                urgency_score,
                category,
                confidence,
                dispatch_unit,
                nearest_shelter_id,
                nearest_shelter_name,
                shelter_distance_km,
                weather_summary,
                status,
            ),
        )
        new_id = cursor.lastrowid
        conn.commit()

        cursor.execute("SELECT * FROM sos_reports WHERE id = ?", (new_id,))
        row = cursor.fetchone()
        return dict(row) if row else {}
