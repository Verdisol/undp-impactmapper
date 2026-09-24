from fastapi import FastAPI, Form, UploadFile, File, HTTPException, Depends
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from contextlib import asynccontextmanager
import uvicorn
import os
import json
import hashlib
import uuid
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import asyncpg

# ============================================
# PHOTO STORAGE (Vercel uses /tmp)
# ============================================
PHOTOS_DIR = "/tmp/photos"
os.makedirs(PHOTOS_DIR, exist_ok=True)

security = HTTPBasic()

# ============================================
# DATABASE
# ============================================
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable not set")

async def get_db_conn():
    return await asyncpg.connect(DATABASE_URL)

async def ensure_tables():
    conn = await get_db_conn()
    try:
        await conn.execute("CREATE EXTENSION IF NOT EXISTS postgis")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id SERIAL PRIMARY KEY,
                report_uuid TEXT UNIQUE NOT NULL,
                building_id TEXT,
                building_osm_id TEXT,
                building_name TEXT,
                building_address TEXT,
                damage_level TEXT,
                version INTEGER DEFAULT 1,
                photo_path TEXT,
                lat REAL,
                lng REAL,
                geom geometry(Point, 4326),
                location_text TEXT,
                infrastructure_type TEXT,
                crisis_nature TEXT,
                debris TEXT,
                notes TEXT,
                username TEXT,
                timestamp TEXT,
                is_current INTEGER DEFAULT 1,
                synced INTEGER DEFAULT 1,
                sms_number TEXT
            )
        """)
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_reports_geom ON reports USING GIST (geom)")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'viewer',
                avatar TEXT DEFAULT '🌍',
                color TEXT DEFAULT '#2ecc71',
                points INTEGER DEFAULT 0,
                verified_reports INTEGER DEFAULT 0,
                badge_level TEXT DEFAULT 'Citizen Reporter',
                created_at TEXT,
                phone_number TEXT
            )
        """)
        default_users = [
            ("admin", hashlib.sha256("admin123".encode()).hexdigest(), "admin", "👑", "#e74c3c", 5000, 250, "🏆 Master Responder", "+1234567890"),
            ("reporter", hashlib.sha256("report123".encode()).hexdigest(), "reporter", "📸", "#2ecc71", 1250, 65, "⭐ Senior Responder", "+1234567891"),
            ("viewer", hashlib.sha256("view123".encode()).hexdigest(), "viewer", "👁️", "#3498db", 0, 0, "🆕 Citizen Reporter", ""),
        ]
        for user in default_users:
            await conn.execute("""
                INSERT INTO users (username, password_hash, role, avatar, color, points, verified_reports, badge_level, created_at, phone_number)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                ON CONFLICT (username) DO NOTHING
            """, *user + (datetime.now().isoformat(),))
    finally:
        await conn.close()

_db_initialized = False
async def init_db_once():
    global _db_initialized
    if not _db_initialized:
        await ensure_tables()
        _db_initialized = True

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await init_db_once()
        print("✅ Database connected and tables verified.")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
    yield

app = FastAPI(title="UNDP ImpactMapper", version="27.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# OSM BUILDING LOOKUP
# ============================================
def get_building_at_location(lat: float, lng: float):
    try:
        overpass_url = "https://overpass-api.de/api/interpreter"
        query = f"""
        [out:json];
        (
          way["building"](around:10,{lat},{lng});
          relation["building"](around:10,{lat},{lng});
        );
        out body;
        >;
        out skel qt;
        """
        params = urllib.parse.urlencode({'data': query}).encode()
        req = urllib.request.Request(overpass_url, data=params, headers={'User-Agent': 'UNDP-ImpactMapper/1.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            for element in data.get("elements", []):
                if element.get("type") in ["way", "relation"]:
                    tags = element.get("tags", {})
                    return {
                        "osm_id": f"{element['type']}/{element['id']}",
                        "name": tags.get("name", ""),
                        "building_type": tags.get("building", "yes"),
                        "address": f"{tags.get('addr:street', '')} {tags.get('addr:housenumber', '')}".strip()
                    }
    except Exception as e:
        print(f"OSM lookup error: {e}")
    return None

# ============================================
# DATABASE FUNCTIONS
# ============================================
async def save_report(report_uuid: str, building_id: str, building_osm_id: str, building_name: str, building_address: str,
                damage_level: str, lat: float, lng: float, location_text: str, photo_path: str,
                infrastructure_type: str, crisis_nature: str, debris: str, notes: str, username: str, synced: int = 1, sms_number: str = ""):
    await init_db_once()
    conn = await get_db_conn()
    try:
        await conn.execute("""
            INSERT INTO reports (
                report_uuid, building_id, building_osm_id, building_name, building_address,
                damage_level, version, lat, lng, geom, location_text, photo_path,
                infrastructure_type, crisis_nature, debris, notes, username,
                timestamp, is_current, synced, sms_number
            )
            VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9,
                CASE WHEN $9 IS NOT NULL AND $8 IS NOT NULL AND $9 != 0 AND $8 != 0
                     THEN ST_SetSRID(ST_MakePoint($9, $8), 4326)
                     ELSE NULL
                END,
                $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20
            )
        """, report_uuid, building_id, building_osm_id, building_name, building_address,
           damage_level, 1, lat, lng, location_text, photo_path,
           infrastructure_type, crisis_nature, debris, notes, username, datetime.now().isoformat(), 1, synced, sms_number)
    finally:
        await conn.close()

async def get_reports_db(limit: int = 200):
    await init_db_once()
    conn = await get_db_conn()
    try:
        rows = await conn.fetch("""
            SELECT report_uuid, damage_level, lat, lng, location_text, infrastructure_type,
                   building_name, building_address, crisis_nature, debris,
                   notes, timestamp, username, photo_path
            FROM reports WHERE is_current = 1 ORDER BY timestamp DESC LIMIT $1
        """, limit)
        return [{
            "report_uuid": r[0], "damage_level": r[1], "lat": r[2], "lng": r[3],
            "location_text": r[4] or "", "infrastructure_type": r[5],
            "building_name": r[6] or "", "building_address": r[7] or "",
            "crisis_nature": r[8], "debris": r[9],
            "notes": r[10] or "", "timestamp": r[11], "username": r[12],
            "photo_url": f"/photos/{os.path.basename(r[13])}" if r[13] else None
        } for r in rows]
    finally:
        await conn.close()

async def get_leaderboard_db(limit: int = 15):
    await init_db_once()
    conn = await get_db_conn()
    try:
        rows = await conn.fetch("SELECT username, points, verified_reports, badge_level, avatar, color FROM users ORDER BY points DESC LIMIT $1", limit)
        return [{"username": r[0], "points": r[1], "verified_reports": r[2], "badge": r[3], "avatar": r[4], "color": r[5]} for r in rows]
    finally:
        await conn.close()

async def update_user_points(username: str, points_increment: int = 10):
    conn = await get_db_conn()
    try:
        await conn.execute("UPDATE users SET points = points + $1, verified_reports = verified_reports + 1 WHERE username = $2", points_increment, username)
    finally:
        await conn.close()

async def get_user_by_username(username: str):
    conn = await get_db_conn()
    try:
        return await conn.fetchrow("SELECT password_hash, role, avatar, color, points, badge_level FROM users WHERE username = $1", username)
    finally:
        await conn.close()

async def get_stats_db():
    conn = await get_db_conn()
    try:
        total = await conn.fetchval("SELECT COUNT(*) FROM reports WHERE is_current = 1")
        today = datetime.now().date().isoformat()
        today_count = await conn.fetchval("SELECT COUNT(*) FROM reports WHERE DATE(timestamp) = $1 AND is_current = 1", today)
        pending = await conn.fetchval("SELECT COUNT(*) FROM reports WHERE synced = 0")
        return {"total_reports": total, "today_reports": today_count, "pending_sync": pending}
    finally:
        await conn.close()

async def get_admin_stats(days: int = 30):
    await init_db_once()
    conn = await get_db_conn()
    try:
        date_filter = ""
        if days > 0:
            date_filter = f"AND timestamp::timestamp >= (NOW() - INTERVAL '{days} days')"
        total_reports = await conn.fetchval(f"SELECT COUNT(*) FROM reports WHERE is_current = 1 {date_filter}")
        total_users = await conn.fetchval(f"SELECT COUNT(DISTINCT username) FROM reports WHERE is_current = 1 {date_filter}")
        top_reporters = await conn.fetch(f"SELECT username, COUNT(*) as reports FROM reports WHERE is_current = 1 {date_filter} GROUP BY username ORDER BY reports DESC LIMIT 10")
        days_limit = min(days, 30) if days > 0 else 30
        daily_trend = await conn.fetch(f"SELECT DATE(timestamp::timestamp) as date, COUNT(*) as count FROM reports WHERE is_current = 1 AND timestamp::timestamp >= (NOW() - INTERVAL '{days_limit} days') GROUP BY DATE(timestamp::timestamp) ORDER BY date ASC")
        by_damage = await conn.fetch(f"SELECT damage_level, COUNT(*) as count FROM reports WHERE is_current = 1 {date_filter} GROUP BY damage_level")
        by_infrastructure = await conn.fetch(f"SELECT infrastructure_type, COUNT(*) as count FROM reports WHERE is_current = 1 AND infrastructure_type IS NOT NULL AND infrastructure_type != '' {date_filter} GROUP BY infrastructure_type ORDER BY count DESC LIMIT 10")
        by_crisis = await conn.fetch(f"SELECT crisis_nature, COUNT(*) as count FROM reports WHERE is_current = 1 AND crisis_nature IS NOT NULL AND crisis_nature != '' {date_filter} GROUP BY crisis_nature ORDER BY count DESC LIMIT 10")
        users_by_role = await conn.fetch("SELECT role, COUNT(*) as count FROM users GROUP BY role")
        return {
            "total_reports": total_reports or 0,
            "total_users": total_users or 0,
            "avg_response_minutes": 0,
            "top_reporters": [{"username": r[0], "reports": r[1]} for r in top_reporters],
            "daily_trend": [{"date": r[0].isoformat(), "count": r[1]} for r in daily_trend],
            "by_damage": [{"level": r[0] or "unknown", "count": r[1]} for r in by_damage],
            "by_infrastructure": [{"type": r[0] or "unknown", "count": r[1]} for r in by_infrastructure],
            "by_crisis": [{"crisis": r[0] or "unknown", "count": r[1]} for r in by_crisis],
            "users_by_role": [{"role": r[0] or "viewer", "count": r[1]} for r in users_by_role],
        }
    finally:
        await conn.close()

# ============================================
# AUTH
# ============================================
async def verify_user(credentials: HTTPBasicCredentials = Depends(security)):
    await init_db_once()
    row = await get_user_by_username(credentials.username)
    if not row:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    password_hash = hashlib.sha256(credentials.password.encode()).hexdigest()
    if password_hash != row[0]:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"username": credentials.username, "role": row[1], "avatar": row[2], "color": row[3], "points": row[4], "badge": row[5]}

def require_admin(current_user: dict = Depends(verify_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

def require_reporter(current_user: dict = Depends(verify_user)):
    if current_user["role"] not in ["admin", "reporter"]:
        raise HTTPException(status_code=403, detail="Reporter access required")
    return current_user

# ============================================
# LANGUAGES
# ============================================
LANGUAGES = {
    "en": {"name": "English", "flag": "🇬🇧", "report_damage": "Report Damage", "damage_level": "Damage Level", "minimal": "Minimal/No Damage", "partial": "Partially Damaged", "complete": "Completely Damaged", "infrastructure": "Infrastructure Type", "residential": "Residential", "commercial": "Commercial", "government": "Government", "utility": "Utility", "transport": "Transport", "community": "Community", "public": "Public", "crisis": "Crisis Type", "earthquake": "Earthquake", "flood": "Flood", "tsunami": "Tsunami", "hurricane": "Hurricane", "wildfire": "Wildfire", "explosion": "Explosion", "conflict": "Conflict", "debris": "Debris?", "yes": "Yes", "no": "No", "submit": "Submit Report", "gps_location": "Use My GPS", "building_name": "Building Name", "photo": "Upload Photo", "notes": "Additional Notes", "recent_reports": "Recent Reports", "export_data": "Export Data", "export_csv": "Export CSV", "export_geojson": "Export GeoJSON", "active_volunteers": "Active Volunteers", "rescue_teams": "Rescue Teams", "online_users": "Online", "leaderboard": "Leaderboard", "chat": "Crisis Chat", "type_message": "Type a message...", "send": "Send", "click_building": "🏢 Click on any building on the map to select it!", "total_reports": "Total Reports", "today_reports": "Today", "pending_sync": "Pending Sync", "logout": "Logout", "sync_now": "Sync Now", "sms_report": "SMS Report", "sms_placeholder": "Format: DAMAGE LAT LNG", "sms_send": "Send SMS Report", "command_center": "Command Center", "analytics": "Analytics Dashboard"},
}

# ============================================
# API ENDPOINTS
# ============================================
@app.get("/")
async def login_page():
    return HTMLResponse(LOGIN_HTML)

@app.get("/dashboard")
async def unified_dashboard(current_user: dict = Depends(verify_user)):
    return HTMLResponse(UNIFIED_DASHBOARD_HTML)

@app.get("/api/lang/{lang}")
async def get_language(lang: str):
    return LANGUAGES.get(lang, LANGUAGES["en"])

@app.get("/api/current_user")
async def get_current_user(current_user: dict = Depends(verify_user)):
    return current_user

@app.get("/api/leaderboard")
async def get_leaderboard():
    return await get_leaderboard_db(15)

@app.get("/api/building/{lat}/{lng}")
async def get_building_info(lat: float, lng: float):
    building = get_building_at_location(lat, lng)
    return building if building else None

@app.post("/api/report")
async def create_report(
    damage_level: str = Form(...),
    infrastructure_type: str = Form(...),
    building_name: str = Form(""),
    building_address: str = Form(""),
    building_osm_id: str = Form(""),
    crisis_nature: str = Form(...),
    debris: str = Form(...),
    text_location: str = Form(""),
    lat: Optional[float] = Form(None),
    lng: Optional[float] = Form(None),
    notes: str = Form(""),
    sms_number: str = Form(""),
    photo: UploadFile = File(None),
    current_user: dict = Depends(require_reporter)
):
    photo_path = None
    if photo and photo.filename:
        ext = photo.filename.split('.')[-1] if '.' in photo.filename else 'jpg'
        photo_filename = f"{datetime.now().timestamp()}_{current_user['username']}_{uuid.uuid4().hex[:6]}.{ext}"
        photo_path = os.path.join(PHOTOS_DIR, photo_filename)
        content = await photo.read()
        with open(photo_path, "wb") as f:
            f.write(content)
    if lat is not None and lng is not None:
        building_id = f"bld_{lat}_{lng}"
    else:
        building_id = f"bld_txt_{hashlib.md5(text_location.encode()).hexdigest()[:10]}"
    report_uuid = str(uuid.uuid4())[:8]
    await save_report(
        report_uuid, building_id, building_osm_id, building_name, building_address,
        damage_level, lat or 0, lng or 0, text_location, photo_path,
        infrastructure_type, crisis_nature, debris, notes, current_user['username'], 1, sms_number
    )
    await update_user_points(current_user['username'], 10)
    return {"status": "success", "report_uuid": report_uuid, "lat": lat, "lng": lng}

@app.post("/api/sms_report")
async def sms_report(sms_text: str = Form(...), sms_number: str = Form("")):
    parts = sms_text.upper().split()
    if len(parts) >= 3:
        damage_level = parts[0].lower()
        try:
            lat = float(parts[1]); lng = float(parts[2])
            notes = " ".join(parts[3:]) if len(parts) > 3 else "SMS Report"
            report_uuid = str(uuid.uuid4())[:8]
            building_id = f"sms_{lat}_{lng}"
            await save_report(report_uuid, building_id, "", "", "", damage_level, lat, lng, "", None, "unknown", "earthquake", "no", notes, "sms_user", 1, sms_number)
            return {"status": "success", "message": "SMS report received", "lat": lat, "lng": lng}
        except ValueError:
            return {"status": "error", "message": "Invalid coordinates"}
    return {"status": "error", "message": "Invalid SMS format. Use: DAMAGE_TYPE LAT LNG"}

@app.post("/api/sync")
async def sync_offline_reports(reports_data: List[Dict], current_user: dict = Depends(require_reporter)):
    synced_count = 0
    for report in reports_data:
        try:
            conn = await get_db_conn()
            try:
                existing = await conn.fetchval("SELECT report_uuid FROM reports WHERE report_uuid = $1", report.get('report_uuid'))
                if not existing:
                    await conn.execute("""
                        INSERT INTO reports (
                            report_uuid, building_id, damage_level, lat, lng, geom,
                            location_text, infrastructure_type, building_name,
                            crisis_nature, debris, notes, username, timestamp,
                            synced, is_current
                        )
                        VALUES (
                            $1, $2, $3, $4, $5,
                            CASE WHEN $5 IS NOT NULL AND $4 IS NOT NULL AND $5 != 0 AND $4 != 0
                                 THEN ST_SetSRID(ST_MakePoint($5, $4), 4326)
                                 ELSE NULL
                            END,
                            $6, $7, $8, $9, $10, $11, $12, $13, $14, $15
                        )
                    """, report.get('report_uuid'), report.get('building_id'), report.get('damage_level'),
                        report.get('lat'), report.get('lng'),
                        report.get('location_text'), report.get('infrastructure_type'), report.get('building_name'),
                        report.get('crisis_nature'), report.get('debris'), report.get('notes'),
                        current_user['username'], report.get('timestamp'), 1, 1)
                    synced_count += 1
                    await update_user_points(current_user['username'], 10)
            finally:
                await conn.close()
        except Exception as e:
            print(f"Sync error: {e}")
    return {"synced": synced_count}

@app.get("/api/reports")
async def get_reports(limit: int = 200, current_user: dict = Depends(verify_user)):
    return await get_reports_db(limit)

@app.get("/api/spatial/nearest")
async def nearest_reports(lat: float, lng: float, k: int = 5, current_user: dict = Depends(verify_user)):
    conn = await get_db_conn()
    try:
        rows = await conn.fetch("""
            SELECT report_uuid, building_name, damage_level,
                   ST_Distance(geom::geography, ST_SetSRID(ST_MakePoint($1, $2), 4326)::geography) AS distance_m
            FROM reports WHERE is_current = 1 AND geom IS NOT NULL
            ORDER BY geom <-> ST_SetSRID(ST_MakePoint($1, $2), 4326) LIMIT $3
        """, lng, lat, k)
        return [dict(r) for r in rows]
    finally:
        await conn.close()

@app.get("/api/spatial/within")
async def reports_within(lat: float, lng: float, radius_m: int = 500, current_user: dict = Depends(verify_user)):
    conn = await get_db_conn()
    try:
        rows = await conn.fetch("""
            SELECT report_uuid, building_name, damage_level,
                   ST_Distance(geom::geography, ST_SetSRID(ST_MakePoint($1, $2), 4326)::geography) AS distance_m
            FROM reports WHERE is_current = 1 AND ST_DWithin(geom::geography, ST_SetSRID(ST_MakePoint($1, $2), 4326)::geography, $3)
            ORDER BY distance_m
        """, lng, lat, radius_m)
        return [dict(r) for r in rows]
    finally:
        await conn.close()

@app.get("/api/spatial/clusters")
async def damage_clusters(eps_m: int = 100, min_points: int = 3, current_user: dict = Depends(verify_user)):
    conn = await get_db_conn()
    try:
        rows = await conn.fetch("""
            WITH clustered AS (
                SELECT report_uuid, damage_level, geom,
                       ST_ClusterDBSCAN(geom, eps := $1 / 111320.0, minpoints := $2) OVER () AS cluster_id
                FROM reports WHERE is_current = 1 AND geom IS NOT NULL
            )
            SELECT cluster_id, COUNT(*) AS report_count,
                   ST_Y(ST_Centroid(ST_Collect(geom))) AS center_lat,
                   ST_X(ST_Centroid(ST_Collect(geom))) AS center_lng,
                   SUM(CASE WHEN damage_level = 'complete' THEN 1 ELSE 0 END) AS complete_damage
            FROM clustered WHERE cluster_id IS NOT NULL
            GROUP BY cluster_id ORDER BY report_count DESC
        """, eps_m, min_points)
        return [dict(r) for r in rows]
    finally:
        await conn.close()

@app.get("/api/spatial/bbox")
async def reports_in_bbox(min_lng: float, min_lat: float, max_lng: float, max_lat: float, current_user: dict = Depends(verify_user)):
    conn = await get_db_conn()
    try:
        rows = await conn.fetch("""
            SELECT report_uuid, building_name, damage_level, lat, lng
            FROM reports WHERE is_current = 1 AND geom && ST_MakeEnvelope($1, $2, $3, $4, 4326)
        """, min_lng, min_lat, max_lng, max_lat)
        return [dict(r) for r in rows]
    finally:
        await conn.close()

@app.get("/api/reports/geojson_spatial")
async def export_geojson_spatial(current_user: dict = Depends(require_reporter)):
    conn = await get_db_conn()
    try:
        rows = await conn.fetch("""
            SELECT jsonb_build_object(
                'type', 'Feature',
                'geometry', ST_AsGeoJSON(geom)::jsonb,
                'properties', jsonb_build_object(
                    'report_uuid', report_uuid, 'building_name', building_name,
                    'damage_level', damage_level, 'infrastructure_type', infrastructure_type,
                    'crisis_nature', crisis_nature, 'timestamp', timestamp, 'username', username
                )
            ) AS feature
            FROM reports WHERE is_current = 1 AND geom IS NOT NULL
        """)
        features = [r["feature"] for r in rows]
        return {"type": "FeatureCollection", "features": features}
    finally:
        await conn.close()

@app.get("/api/reports/geojson")
async def get_geojson(current_user: dict = Depends(require_reporter)):
    conn = await get_db_conn()
    try:
        rows = await conn.fetch("SELECT damage_level, lat, lng, infrastructure_type, crisis_nature, building_name, timestamp FROM reports WHERE lat != 0 AND is_current = 1")
        features = []
        for r in rows:
            if r[1] and r[2]:
                features.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [float(r[2]), float(r[1])]}, "properties": {"damage_level": r[0], "infrastructure_type": r[3], "crisis_nature": r[4], "building_name": r[5], "timestamp": r[6]}})
        return {"type": "FeatureCollection", "features": features}
    finally:
        await conn.close()

@app.get("/api/reports/csv")
async def export_csv(current_user: dict = Depends(require_reporter)):
    conn = await get_db_conn()
    try:
        rows = await conn.fetch("SELECT damage_level, lat, lng, building_name, building_address, infrastructure_type, crisis_nature, debris, notes, timestamp, username FROM reports WHERE is_current = 1 ORDER BY timestamp DESC")
        csv = "Damage Level,Latitude,Longitude,Building Name,Building Address,Infrastructure Type,Crisis Nature,Debris,Notes,Timestamp,Username\n"
        for r in rows:
            lat_val = f"{r[1]:.6f}" if r[1] else ""
            lng_val = f"{r[2]:.6f}" if r[2] else ""
            csv += f"{r[0]},{lat_val},{lng_val},\"{r[3] or ''}\",\"{r[4] or ''}\",{r[5]},{r[6]},{r[7]},\"{r[8] or ''}\",{r[9]},{r[10]}\n"
        return HTMLResponse(csv, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=impact_reports.csv"})
    finally:
        await conn.close()

@app.get("/api/stats")
async def get_stats():
    return await get_stats_db()

@app.get("/api/admin/stats")
async def admin_stats(days: int = 7, current_user: dict = Depends(require_admin)):
    return await get_admin_stats(days)

@app.get("/photos/{filename}")
async def serve_photo(filename: str):
    file_path = os.path.join(PHOTOS_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    old_path = f"photos/{filename}"
    if os.path.exists(old_path):
        return FileResponse(old_path)
    raise HTTPException(status_code=404, detail="Photo not found")

# ============================================
# LOGIN HTML
# ============================================
LOGIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>UNDP ImpactMapper - Unified Crisis Platform</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Inter', sans-serif; min-height: 100vh; background: linear-gradient(135deg, #0a2a1a 0%, #0a1a0f 100%); position: relative; overflow-x: hidden; }
        .hero-bg { position: fixed; inset: 0; background-image: url('https://images.unsplash.com/photo-1582213782179-e0d53f98f2ca?w=1600'); background-size: cover; background-position: center 30%; opacity: 0.12; z-index: 0; }
        .container { position: relative; z-index: 1; max-width: 1400px; margin: 0 auto; padding: 40px 60px; min-height: 100vh; display: flex; flex-direction: column; }
        .navbar { display: flex; justify-content: space-between; align-items: center; padding: 20px 0; margin-bottom: 80px; flex-wrap: wrap; gap: 20px; }
        .logo h1 { font-size: 28px; font-weight: 700; color: white; }
        .logo span { color: #2ecc71; }
        .logo p { font-size: 12px; color: #aaa; margin-top: 4px; }
        .nav-links { display: flex; gap: 30px; align-items: center; flex-wrap: wrap; }
        .nav-links a { color: #ccc; text-decoration: none; font-size: 14px; font-weight: 500; }
        .language-select { background: rgba(255,255,255,0.1); border: 1px solid rgba(46,204,113,0.3); padding: 8px 16px; border-radius: 30px; color: white; cursor: pointer; font-size: 13px; }
        .hero-section { display: flex; justify-content: space-between; align-items: center; gap: 60px; flex-wrap: wrap; margin-bottom: 80px; }
        .hero-left { flex: 1; min-width: 300px; }
        .hero-badge { display: inline-block; background: rgba(46,204,113,0.2); border: 1px solid rgba(46,204,113,0.4); padding: 6px 16px; border-radius: 30px; font-size: 12px; color: #2ecc71; margin-bottom: 24px; }
        .hero-left h1 { font-size: 56px; font-weight: 800; line-height: 1.2; margin-bottom: 20px; background: linear-gradient(135deg, #fff, #2ecc71); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
        .hero-left p { font-size: 18px; color: #ccc; line-height: 1.6; margin-bottom: 32px; max-width: 600px; }
        .stats { display: flex; gap: 40px; margin-top: 40px; flex-wrap: wrap; }
        .stat-item { text-align: left; }
        .stat-number { font-size: 32px; font-weight: 800; color: #2ecc71; }
        .stat-label { font-size: 12px; color: #888; margin-top: 4px; }
        .hero-right { flex: 0.8; min-width: 350px; }
        .login-card { background: rgba(17, 17, 17, 0.95); backdrop-filter: blur(15px); border-radius: 16px; padding: 40px; border: 1px solid rgba(46,204,113,0.3); box-shadow: 0 25px 50px rgba(0,0,0,0.3); }
        .login-card h2 { font-size: 24px; font-weight: 700; margin-bottom: 8px; }
        .login-card p { font-size: 13px; color: #888; margin-bottom: 24px; }
        .input-group { margin-bottom: 16px; }
        .input-group input { width: 100%; padding: 14px 16px; background: #2a2a2a; border: 1px solid #3a3a3a; border-radius: 12px; color: white; font-size: 14px; }
        .input-group input:focus { outline: none; border-color: #2ecc71; box-shadow: 0 0 0 3px rgba(46,204,113,0.2); }
        .login-btn { width: 100%; padding: 14px; background: linear-gradient(135deg, #2ecc71, #27ae60); color: white; font-weight: 700; border: none; border-radius: 12px; font-size: 16px; cursor: pointer; margin-top: 8px; }
        .demo-info { margin-top: 24px; padding-top: 20px; border-top: 1px solid #2a2a2a; text-align: center; }
        .demo-info p { font-size: 11px; color: #666; margin-bottom: 8px; }
        .demo-badge { display: inline-flex; gap: 12px; justify-content: center; flex-wrap: wrap; }
        .demo-role { background: rgba(46,204,113,0.1); padding: 4px 12px; border-radius: 20px; font-size: 11px; color: #2ecc71; }
        .footer { margin-top: auto; padding: 30px 0 20px; text-align: center; border-top: 1px solid rgba(255,255,255,0.05); }
        .footer p { font-size: 12px; color: #666; }
        .partner-logos { display: flex; justify-content: center; gap: 30px; margin-bottom: 20px; flex-wrap: wrap; }
        .partner { font-size: 14px; opacity: 0.6; }
        @media (max-width: 968px) { .container { padding: 20px 30px; } .hero-section { flex-direction: column; } .hero-left h1 { font-size: 40px; } .navbar { flex-direction: column; text-align: center; } }
        @media (max-width: 600px) { .container { padding: 15px 20px; } .hero-left h1 { font-size: 32px; } .login-card { padding: 25px; } }
    </style>
</head>
<body>
    <div class="hero-bg"></div>
    <div class="container">
        <div class="navbar">
            <div class="logo"><h1>🌍 UNDP <span>ImpactMapper</span></h1><p>Unified Crisis Intelligence Platform</p></div>
            <div class="nav-links">
                <a href="#">Explore</a><a href="#">Learn</a><a href="#">About</a><a href="#">Support</a>
                <select id="languageSelect" class="language-select">
                    <option value="en">🌍 English</option><option value="es">🇪🇸 Español</option><option value="fr">🇫🇷 Français</option>
                    <option value="pt">🇵🇹 Português</option><option value="ar">🇸🇦 العربية</option><option value="zh">🇨🇳 中文</option>
                </select>
            </div>
        </div>
        <div class="hero-section">
            <div class="hero-left">
                <div class="hero-badge">🌍 United Nations Development Programme</div>
                <h1>EMPOWERING<br>CRISIS RESPONSE</h1>
                <p>By leveraging artificial intelligence to create maps, coordinate rescue efforts, and provide vital information for sustainable development in communities facing disaster.</p>
                <div class="stats">
                    <div class="stat-item"><div class="stat-number">350+</div><div class="stat-label">Active Volunteers</div></div>
                    <div class="stat-item"><div class="stat-number">12+</div><div class="stat-label">Rescue Teams</div></div>
                    <div class="stat-item"><div class="stat-number">1,250+</div><div class="stat-label">Reports Submitted</div></div>
                </div>
            </div>
            <div class="hero-right">
                <div class="login-card">
                    <h2>Access Unified Dashboard</h2>
                    <p>Login to access Command Center & Analytics</p>
                    <div class="input-group"><input type="text" id="username" placeholder="Username"></div>
                    <div class="input-group"><input type="password" id="password" placeholder="Password"></div>
                    <button class="login-btn" onclick="login()">🔐 Login to ImpactMapper</button>
                    <div id="errorMsg" style="color:#e74c3c; font-size:12px; margin-top:12px; text-align:center;"></div>
                    <div class="demo-info">
                        <p>Demo Accounts:</p>
                        <div class="demo-badge">
                            <span class="demo-role">👑 admin / admin123</span>
                            <span class="demo-role">📸 reporter / report123</span>
                            <span class="demo-role">👁️ viewer / view123</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <div class="footer">
            <div class="partner-logos">
                <span class="partner">🔴 American Red Cross</span><span class="partner">🇺🇳 UN OCHA</span>
                <span class="partner">🌾 World Food Programme</span><span class="partner">🏥 WHO</span>
                <span class="partner">🚒 FEMA</span><span class="partner">🗺️ OpenStreetMap</span>
            </div>
            <p>© <span id="currentYear"></span> UNDP ImpactMapper</p>
        </div>
    </div>
    <script>
        document.getElementById('currentYear').innerText = new Date().getFullYear();
        const langSelect = document.getElementById('languageSelect');
        async function setLanguage(lang) { try { await fetch('/api/lang/' + encodeURIComponent(lang)); } catch(e) {} }
        langSelect.addEventListener('change', (e) => { setLanguage(e.target.value); });
        async function login() {
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            const errorDiv = document.getElementById('errorMsg');
            if (!username || !password) { errorDiv.innerText = 'Please enter username and password'; return; }
            try {
                const response = await fetch('/dashboard', { headers: { 'Authorization': 'Basic ' + btoa(username + ':' + password) } });
                if (response.ok) { window.location.href = '/dashboard'; }
                else { errorDiv.innerText = 'Invalid credentials (' + response.status + ')'; }
            } catch(e) { errorDiv.innerText = 'Login failed'; }
        }
        document.getElementById('password').addEventListener('keypress', function(e) { if (e.key === 'Enter') login(); });
    </script>
</body>
</html>
"""

# ============================================
# UNIFIED DASHBOARD HTML - BULLETPROOF MAP LAYOUT
# ============================================
UNIFIED_DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>UNDP ImpactMapper - Command Center</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        html, body { height: 100%; overflow: hidden; }
        body { font-family: 'Inter', sans-serif; background: #121212; color: #e0e0e0; }
        .leaflet-control-attribution { display: none !important; }
        .leaflet-bottom.leaflet-right { display: none !important; }

        .system-bar {
            background: #1a472a;
            padding: 8px 40px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 2px solid #2ecc71;
            height: 90px;
            flex-shrink: 0;
        }
        .brand-center { flex: 1; text-align: center; }
        .brand-center h1 { font-size: 1.6rem; font-weight: 700; color: white; margin: 0; line-height: 1.2; }
        .brand-center h1 span { color: #2ecc71; }
        .brand-center p { font-size: 0.9rem; color: rgba(255,255,255,0.75); margin-top: 2px; line-height: 1.2; }

        .controls-right {
            display: grid;
            grid-template-columns: repeat(4, auto);
            grid-template-rows: auto auto;
            gap: 4px 8px;
            align-items: center;
            justify-items: end;
        }
        .sync-btn, .logout-btn, .lang-dropdown, .status-badge, .role-badge {
            height: 32px;
            min-width: 70px;
            padding: 6px 14px;
            border-radius: 6px;
            font-size: 0.85rem;
            font-weight: 700;
            color: #000;
            background: rgba(255,255,255,0.85);
            border: 1px solid rgba(0,0,0,0.1);
            transition: 0.2s ease;
            white-space: nowrap;
            cursor: pointer;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
        }
        .sync-btn:hover, .logout-btn:hover { background: #fff; transform: scale(1.02); }
        .logout-btn { background: rgba(255, 200, 200, 0.9); color: #b00000; }
        .status-badge { background: rgba(200,255,200,0.85); color: #000; }
        .status-badge i { font-size: 8px; color: #2ecc71; }
        .lang-dropdown { background: rgba(255,255,255,0.85); color: #000; border: 1px solid #ccc; padding: 2px 10px; font-size: 0.8rem; min-width: 56px; }
        .role-badge { background: rgba(255,255,200,0.85); color: #000; }

        .tabs-container {
            background: #1a1a1a;
            padding: 0 16px 8px 16px;
            border-bottom: 1px solid #2a2d35;
            display: flex;
            gap: 6px;
            flex-shrink: 0;
            height: 52px;
        }
        .tab-btn { padding: 12px 28px; background: transparent; color: #a0a0a0; border: none; border-bottom: 2px solid transparent; font-size: 1.0rem; font-weight: 600; cursor: pointer; }
        .tab-btn.active { color: #2ecc71; border-bottom: 3px solid #2ecc71; background: rgba(46,204,113,0.15); box-shadow: 0 4px 20px rgba(46,204,113,0.6); }

        #commandTab { display: flex; flex-direction: column; height: calc(100vh - 142px); overflow: hidden; }
        .kpi-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; padding: 12px 20px; background: #121212; flex-shrink: 0; }
        .kpi-card { background: #1e1e1e; border-radius: 8px; padding: 12px 16px; border: 2px solid #2ecc71; cursor: pointer; }
        .kpi-card:hover { transform: translateY(-2px); box-shadow: 0 0 15px rgba(46,204,113,0.3); }
        .kpi-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
        .kpi-header span { font-size: 0.8rem; color: #a0a0a0; text-transform: uppercase; }
        .kpi-value { font-size: 1.6rem; font-weight: 700; margin-bottom: 4px; }
        .kpi-value.warning { color: #f39c12; }
        .progress-bar { height: 4px; background: #2a2a2a; border-radius: 2px; overflow: hidden; margin-top: 4px; }
        .progress-fill { height: 100%; background: #2ecc71; }
        .pill-group { display: flex; gap: 6px; margin-top: 4px; flex-wrap: wrap; }
        .pill { padding: 2px 8px; border-radius: 12px; font-size: 0.7rem; font-weight: 500; }
        .pill-red { background: rgba(231,76,60,0.12); color: #e74c3c; }
        .pill-yellow { background: rgba(243,156,18,0.12); color: #f39c12; }
        .pill-green { background: rgba(46,204,113,0.12); color: #2ecc71; }

        /* ===== CRITICAL: SIMPLE GRID LAYOUT WITH FIXED MAP HEIGHT ===== */
        .main-layout {
            display: grid;
            grid-template-columns: 1fr 1fr;
            flex: 1;
            overflow: hidden;
            min-height: 0;
        }
        .sidebar {
            background: #1a1d23;
            overflow-y: auto;
            padding: 20px;
            border-right: 1px solid #2a2d35;
            height: 100%;
            min-width: 0;
        }
        .sidebar::-webkit-scrollbar { width: 8px; }
        .sidebar::-webkit-scrollbar-thumb { background: #2ecc71; border-radius: 10px; }
        .sidebar.collapsed { display: none; }
        .right-panel {
            display: flex;
            flex-direction: column;
            overflow: hidden;
            height: 100%;
            min-width: 0;
        }
        /* === THE MAP NOW HAS A FORCED HEIGHT === */
        .map-container {
            height: 400px !important;
            min-height: 400px !important;
            position: relative;
            flex-shrink: 0;
        }
        #map {
            height: 400px !important;
            width: 100% !important;
            background: #1a1a1a;
            display: block;
        }
        .charts-section {
            flex: 1;
            min-height: 200px;
            background: rgba(255, 255, 255, 0.85);
            padding: 12px 18px 18px 18px;
            margin: 8px 10px;
            border-radius: 12px;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        .charts-title { font-size: 1.1rem; font-weight: 700; color: #1a1a1a; text-align: center; flex-shrink: 0; }
        .charts-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; flex: 1; min-height: 0; margin-top: 10px; }
        .chart-container { background: rgba(255, 255, 255, 0.9); border-radius: 8px; padding: 8px; display: flex; flex-direction: column; justify-content: center; min-height: 0; }
        .chart-container h4 { text-align: center; margin-bottom: 4px; color: #1a1a1a; font-size: 0.8rem; }
        canvas { width: 100% !important; height: auto !important; max-height: 120px; }

        .card { background: rgba(42, 42, 42, 0.9); border-radius: 10px; padding: 18px; margin-bottom: 14px; border: 1px solid rgba(255,255,255,0.08); }
        .card h3 { color: #2ecc71; margin-bottom: 10px; font-size: 1.3rem; display: flex; align-items: center; gap: 8px; }
        input, select, textarea { width: 100%; padding: 10px; margin: 6px 0; background: #1a1a1a; border: 1px solid #444; border-radius: 8px; color: white; font-size: 1.1rem; }
        button { background: linear-gradient(135deg, #1a472a, #0d2a1a); color: white; padding: 10px; font-weight: 600; border: none; border-radius: 8px; cursor: pointer; width: 100%; margin-top: 6px; font-size: 1.1rem; }
        .btn-location { background: linear-gradient(135deg, #3498db, #2980b9); }
        .reports-list { max-height: 220px; overflow-y: auto; }
        .report-item { background: #1a1a1a; padding: 10px 12px; margin: 8px 0; border-radius: 8px; border-left: 4px solid #2ecc71; cursor: pointer; font-size: 1.0rem; }
        .report-item.severity-critical { border-left-color: #e74c3c; }
        .report-item.severity-high { border-left-color: #f39c12; }
        .building-info { background: rgba(46,204,113,0.1); padding: 10px; border-radius: 8px; margin-top: 6px; font-size: 1.0rem; text-align: center; border: 1px solid rgba(46,204,113,0.3); color: #2ecc71; }
        .sms-card { background: rgba(46,204,113,0.08); padding: 10px; border-radius: 8px; margin-top: 6px; }
        .photo-preview { margin-top: 6px; text-align: center; }
        .photo-preview img { max-width: 100%; border-radius: 8px; max-height: 80px; }
        .scroll-hint { text-align: center; font-size: 1.0rem; color: #888; margin: 10px 0; animation: pulse-hint 1.5s ease-in-out infinite; }
        @keyframes pulse-hint { 0%,100% { opacity: 0.4; } 50% { opacity: 1; } }

        .leaderboard-panel { position: fixed; bottom: 15px; right: 15px; width: 240px; background: rgba(30,30,30,0.95); border-radius: 10px; border: 1px solid rgba(243,156,18,0.2); z-index: 1000; }
        .leaderboard-header { padding: 10px 14px; border-radius: 10px 10px 0 0; display: flex; justify-content: space-between; cursor: pointer; font-size: 0.9rem; font-weight: 600; background: rgba(243,156,18,0.08); }
        .leaderboard-list { max-height: 150px; overflow-y: auto; padding: 8px; }
        .leaderboard-item { display: flex; align-items: center; gap: 8px; padding: 6px 10px; border-radius: 6px; margin: 4px 0; background: rgba(255,255,255,0.02); font-size: 0.85rem; }
        .rank { width: 28px; font-weight: 700; color: #f39c12; }

        /* === CHAT BOTTOM-RIGHT GREEN GLOW === */
        .chat-panel {
            position: fixed !important;
            bottom: 20px !important;
            right: 20px !important;
            left: auto !important;
            width: 360px !important;
            min-width: 220px !important;
            max-width: 500px !important;
            max-height: 480px !important;
            min-height: 220px !important;
            background: rgba(18, 25, 40, 0.95) !important;
            backdrop-filter: blur(12px) !important;
            border-radius: 18px !important;
            border: 1px solid rgba(46, 204, 113, 0.3) !important;
            box-shadow: 0 0 25px rgba(46, 204, 113, 0.15), 0 0 50px rgba(46, 204, 113, 0.08) !important;
            animation: pulseGlowChat 2.8s ease-in-out infinite alternate !important;
            cursor: grab !important;
            z-index: 9999 !important;
            display: flex !important;
            flex-direction: column !important;
            overflow: hidden !important;
            resize: both !important;
        }
        @keyframes pulseGlowChat {
            0% { box-shadow: 0 0 15px rgba(46,204,113,0.1), 0 0 30px rgba(46,204,113,0.05); }
            100% { box-shadow: 0 0 35px rgba(46,204,113,0.3), 0 0 70px rgba(46,204,113,0.12); }
        }
        .chat-header { padding: 10px 18px !important; background: rgba(46,204,113,0.06) !important; border-bottom: 1px solid rgba(46,204,113,0.1) !important; border-radius: 18px 18px 0 0 !important; cursor: grab !important; display: flex !important; justify-content: space-between !important; align-items: center !important; }
        .chat-header h4 { color: #2ecc71 !important; font-size: 1.0rem !important; font-weight: 700 !important; display: flex; align-items: center; gap: 8px; }
        .chat-header .pulse-dot { display: inline-block; width: 10px; height: 10px; background: #2ecc71; border-radius: 50%; box-shadow: 0 0 12px #2ecc71; animation: blinkDotChat 1.2s infinite; }
        @keyframes blinkDotChat { 0%,100% { opacity: 1; } 50% { opacity: 0.15; } }
        .chat-header .status-badge { font-size: 0.8rem; background: rgba(46,204,113,0.1); padding: 2px 12px; border-radius: 30px; color: #aaffee; }
        .chat-messages { flex: 1; padding: 10px 14px; overflow-y: auto; max-height: 260px; min-height: 100px; display: flex; flex-direction: column; gap: 6px; }
        .chat-message { padding: 8px 14px; border-radius: 14px; max-width: 85%; font-size: 0.9rem; line-height: 1.4; }
        .chat-message.own { align-self: flex-end; background: rgba(46,204,113,0.15); border: 1px solid rgba(46,204,113,0.12); color: #e0faf5; }
        .chat-message.other { align-self: flex-start; background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.04); color: #cdd9e6; }
        .chat-message .msg-username { font-weight: 700; color: #2ecc71; font-size: 0.8rem; display: block; margin-bottom: 2px; }
        .chat-message .msg-time { font-size: 0.7rem; opacity: 0.4; margin-left: 8px; }
        .chat-input-area { padding: 8px 14px 14px 14px; border-top: 1px solid rgba(46,204,113,0.06); display: flex; gap: 8px; align-items: center; }
        .chat-input-area input { flex: 1; padding: 8px 14px; border-radius: 30px; border: 1px solid rgba(46,204,113,0.1); background: rgba(0,0,0,0.35); color: #fff; font-size: 0.85rem; outline: none; }
        .chat-input-area button { padding: 8px 20px; border-radius: 30px; border: none; background: #2ecc71; color: #0b0e14; font-weight: 700; font-size: 0.8rem; cursor: pointer; white-space: nowrap; width: auto; margin: 0; }

        #exportCard { padding: 8px 12px; margin-bottom: 8px; }
        #exportCard h3 { font-size: 1.0rem; margin-bottom: 6px; }
        #exportCard button { font-size: 0.95rem; padding: 8px 10px; margin-top: 4px; }

        .analytics-filter { display: flex; gap: 14px; align-items: center; margin-bottom: 14px; flex-wrap: wrap; }
        .analytics-filter select { background: #2a2a2a; color: white; padding: 8px 14px; border: 1px solid #3a3a3a; border-radius: 8px; font-size: 0.95rem; cursor: pointer; }
        .analytics-filter button { background: #2a2a2a; color: white; border: 1px solid #3a3a3a; padding: 8px 14px; border-radius: 8px; cursor: pointer; font-size: 0.95rem; width: auto; margin: 0; }

        #analyticsTab { padding: 14px 24px; overflow-y: auto; height: calc(100vh - 142px); }

        @media (max-width: 1000px) {
            .main-layout { grid-template-columns: 1fr; }
            .sidebar { max-height: 40vh; }
            .map-container, #map { height: 300px !important; min-height: 300px !important; }
            .charts-grid { grid-template-columns: 1fr; }
            .kpi-row { grid-template-columns: repeat(2, 1fr); }
        }
    </style>
</head>
<body>
<div class="system-bar">
    <div></div>
    <div class="brand-center">
        <h1>🌍 UNDP <span>ImpactMapper</span></h1>
        <p>Command Center | Live Intelligence</p>
    </div>
    <div class="controls-right">
        <select id="languageSelect" class="lang-dropdown">
            <option value="en">🇬🇧 EN</option><option value="es">🇪🇸 ES</option><option value="fr">🇫🇷 FR</option>
            <option value="pt">🇵🇹 PT</option><option value="ar">🇸🇦 AR</option><option value="zh">🇨🇳 中文</option>
        </select>
        <div id="connectionStatus" class="status-badge status-online"><i class="fas fa-circle"></i> Online</div>
        <button class="sync-btn" onclick="forceSync()"><i class="fas fa-sync-alt"></i> Sync</button>
        <span id="userRoleBadge" class="role-badge"></span>
        <button class="sync-btn" id="toggleSidebarBtn"><i class="fas fa-chevron-left"></i></button>
        <button id="exportCSVBtn" class="sync-btn" onclick="exportCSV()" style="display:none;">CSV</button>
        <button id="exportGeoJSONBtn" class="sync-btn" onclick="exportGeoJSON()" style="display:none;">GeoJSON</button>
        <a href="/" class="logout-btn"><i class="fas fa-sign-out-alt"></i> Logout</a>
    </div>
</div>
<div class="tabs-container">
    <button class="tab-btn active" onclick="switchTab('command')" id="tabCommandBtn"><i class="fas fa-map-marked-alt"></i> Command Center</button>
    <button class="tab-btn" onclick="switchTab('analytics')" id="tabAnalyticsBtn" style="display:none;"><i class="fas fa-chart-line"></i> Analytics</button>
</div>

<div id="commandTab" class="tab-content active">
    <div class="kpi-row">
        <div class="kpi-card"><div class="kpi-header"><span>Active Cases</span><i class="fas fa-chart-line"></i></div><div class="kpi-value" id="activeCases">0</div><div class="progress-bar"><div class="progress-fill" id="capacityBar" style="width:0%"></div></div><div class="pill-group"><span class="pill pill-red">Critical: <span id="criticalCount">0</span></span><span class="pill pill-yellow">High: <span id="highCount">0</span></span></div></div>
        <div class="kpi-card"><div class="kpi-header"><span>Resources</span><i class="fas fa-truck-medical"></i></div><div class="kpi-value" id="resourcesDeployed">0</div><div class="progress-bar"><div class="progress-fill" id="resourceBar" style="width:0%"></div></div><div class="pill-group"><span class="pill pill-green">Deployed: <span id="deployedCount">0</span></span><span class="pill">Standby: <span id="standbyCount">0</span></span></div></div>
        <div class="kpi-card"><div class="kpi-header"><span>Volunteers</span><i class="fas fa-users"></i></div><div class="kpi-value" id="totalVolunteers">0</div><div class="pill-group"><span class="pill pill-green">Active: <span id="activeVolunteersCount">0</span></span><span class="pill pill-yellow">Standby: <span id="standbyVolunteers">0</span></span><span class="pill">Offline: <span id="offlineVolunteers">0</span></span></div></div>
        <div class="kpi-card" id="pendingTasksCard"><div class="kpi-header"><span>Pending</span><i class="fas fa-tasks"></i></div><div class="kpi-value warning" id="pendingTasks">0</div><div class="pill-group"><span class="pill pill-red">Urgent: <span id="urgentTasks">0</span></span></div></div>
    </div>
    <div class="main-layout">
        <div class="sidebar" id="sidebarPanel">
            <div class="card">
                <h3><i class="fas fa-camera"></i> <span id="reportTitle">Report Damage</span></h3>
                <p id="clickHint" style="font-size:1.0rem; color:#2ecc71;">🏢 Click on any building on the map!</p>
                <div id="selectedBuildingInfo" class="building-info" style="display:none;"></div>
                <select id="damageLevel"><option value="minimal">🏠 Minimal/No Damage</option><option value="partial">⚠️ Partially Damaged</option><option value="complete">💀 Completely Damaged</option></select>
                <select id="infrastructureType"><option value="residential">🏘️ Residential</option><option value="commercial">🏪 Commercial</option><option value="government">🏛️ Government</option><option value="utility">💡 Utility</option><option value="transport">🛣️ Transport</option><option value="community">🏥 Community</option><option value="public">🏟️ Public</option></select>
                <input type="text" id="buildingName" placeholder="Building Name">
                <select id="crisisNature"><option value="earthquake">🌋 Earthquake</option><option value="flood">💧 Flood</option><option value="tsunami">🌊 Tsunami</option><option value="hurricane">🌀 Hurricane</option><option value="wildfire">🔥 Wildfire</option><option value="explosion">💥 Explosion</option><option value="conflict">⚔️ Conflict</option></select>
                <select id="debris"><option value="yes">Yes - Requires clearing</option><option value="no">No debris</option></select>
                <div style="display:flex; gap:8px;">
                    <input type="text" id="lat" placeholder="Latitude" readonly style="flex:1;">
                    <input type="text" id="lng" placeholder="Longitude" readonly style="flex:1;">
                </div>
                <button class="btn-location" onclick="shareLocation()" style="font-size:1.1rem; padding:12px;"><i class="fas fa-location-dot"></i> <span id="gpsLabel">Use My GPS</span></button>
                <input type="text" id="textLocation" placeholder="Describe location">
                <textarea id="notes" rows="2" placeholder="Additional notes"></textarea>
                <div style="margin-top:8px;">
                    <label style="color:#aaa; font-size:1.0rem;"><i class="fas fa-image"></i> Upload Photo:</label>
                    <input type="file" id="photo" accept="image/*" capture="environment" style="padding:8px; background:#2a2a2a; border:1px solid #444; border-radius:8px;">
                    <div id="photoPreview" class="photo-preview"></div>
                </div>
                <button id="submitBtn" onclick="submitReport()" style="font-size:1.1rem; padding:12px; background: linear-gradient(135deg, #2ecc71, #27ae60);"><i class="fas fa-paper-plane"></i> <span id="submitLabel">Submit Report</span></button>
                <div id="submitStatus" style="margin-top:8px; font-size:1.0rem;"></div>
                <div class="scroll-hint">↓ Scroll for more options ↓</div>
            </div>
            <div class="card"><h3><i class="fas fa-sms"></i> <span id="smsTitle">SMS Report</span></h3>
                <div class="sms-card">
                    <input type="text" id="smsText" placeholder="Format: DAMAGE LAT LNG">
                    <input type="text" id="smsNumber" placeholder="Phone (optional)">
                    <button onclick="sendSMSReport()"><i class="fas fa-envelope"></i> <span id="smsSendLabel">Send SMS</span></button>
                </div>
                <div id="smsStatus" style="margin-top:8px; font-size:1.0rem;"></div>
            </div>
            <div class="card"><h3><i class="fas fa-list"></i> <span id="recentTitle">Recent Reports</span></h3>
                <div id="reportsList" class="reports-list">Loading...</div>
            </div>
            <div class="card" id="exportCard"><h3><i class="fas fa-download"></i> <span id="exportTitle">Export Data</span></h3>
                <div style="display:flex; gap:8px;">
                    <button id="exportCSVCardBtn" onclick="exportCSV()" style="flex:1;">CSV</button>
                    <button id="exportGeoJSONCardBtn" onclick="exportGeoJSON()" style="flex:1;">GeoJSON</button>
                </div>
            </div>
        </div>
        <div class="right-panel">
            <div class="map-container"><div id="map"></div></div>
            <div class="charts-section" id="chartsSection">
                <div class="charts-title">📊 DAMAGE ANALYTICS</div>
                <div class="charts-grid">
                    <div class="chart-container"><h4>🥧 Distribution</h4><canvas id="pieChart"></canvas></div>
                    <div class="chart-container"><h4>📊 Infrastructure</h4><canvas id="barChart"></canvas></div>
                    <div class="chart-container"><h4>📈 Trend</h4><canvas id="lineChart"></canvas></div>
                </div>
            </div>
        </div>
    </div>
</div>

<div id="analyticsTab" class="tab-content" style="display:none;">
    <div style="padding:12px 20px;">
        <div class="analytics-filter">
            <label style="color:#aaa;"><i class="fas fa-calendar-alt"></i> Date Range:</label>
            <select id="analyticsDays" onchange="loadAdminStats()">
                <option value="7">Last 7 days</option>
                <option value="30" selected>Last 30 days</option>
                <option value="90">Last 90 days</option>
                <option value="0">All time</option>
            </select>
            <button onclick="loadAdminStats()">Refresh</button>
        </div>
        <div style="display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:14px; margin-bottom:14px;">
            <div style="background:#1e1e1e; border-radius:10px; padding:16px;"><div id="totalReports" style="font-size:1.8rem; font-weight:800; color:#2ecc71;">-</div><div style="font-size:0.85rem; color:#a0a0a0;">Total Reports</div></div>
            <div style="background:#1e1e1e; border-radius:10px; padding:16px;"><div id="totalUsers" style="font-size:1.8rem; font-weight:800; color:#2ecc71;">-</div><div style="font-size:0.85rem; color:#a0a0a0;">Active Users</div></div>
            <div style="background:#1e1e1e; border-radius:10px; padding:16px;"><div id="avgResponse" style="font-size:1.8rem; font-weight:800; color:#2ecc71;">-</div><div style="font-size:0.85rem; color:#a0a0a0;">Avg Response</div></div>
            <div style="background:#1e1e1e; border-radius:10px; padding:16px;"><div id="topReporter" style="font-size:1.8rem; font-weight:800; color:#2ecc71;">-</div><div style="font-size:0.85rem; color:#a0a0a0;">Top Reporter</div></div>
        </div>
        <div style="display:grid; grid-template-columns:repeat(auto-fit,minmax(300px,1fr)); gap:14px;">
            <div style="background:#1e1e1e; border-radius:10px; padding:16px;"><h3 style="color:#2ecc71;">📈 Daily Trend</h3><canvas id="trendChart"></canvas></div>
            <div style="background:#1e1e1e; border-radius:10px; padding:16px;"><h3 style="color:#2ecc71;">🏗️ Damage</h3><canvas id="damageChart"></canvas></div>
            <div style="background:#1e1e1e; border-radius:10px; padding:16px;"><h3 style="color:#2ecc71;">🏘️ Infrastructure</h3><canvas id="infraChart"></canvas></div>
            <div style="background:#1e1e1e; border-radius:10px; padding:16px;"><h3 style="color:#2ecc71;">🌋 Crisis</h3><canvas id="crisisChart"></canvas></div>
        </div>
    </div>
</div>

<div class="leaderboard-panel"><div class="leaderboard-header" onclick="toggleLeaderboard()"><span>🏆 Leaderboard</span><span>🏆</span></div><div id="leaderboardList" class="leaderboard-list">Loading...</div></div>

<div class="chat-panel" id="glowChat">
    <div class="chat-header" id="chatDragHandle">
        <h4><span class="pulse-dot"></span> CRISIS CHAT</h4>
        <div class="status-badge">● Local</div>
    </div>
    <div id="chatMessages" class="chat-messages"></div>
    <div class="chat-input-area">
        <input type="text" id="chatInput" placeholder="Type a message…" autocomplete="off">
        <button id="chatSendBtn">Send</button>
    </div>
</div>

<script>
let map, markers = [], reports = [];
let currentUser = { username: '', role: '', avatar: '', color: '#2ecc71', points: 0, badge: '' };
let currentLang = localStorage.getItem('language') || 'en';

function escapeHtml(value) {
    const text = value == null ? '' : String(value);
    return text.replace(/&/g, '&amp;')
               .replace(/</g, '&lt;')
               .replace(/>/g, '&gt;')
               .replace(/"/g, '&quot;')
               .replace(/'/g, '&#039;');
}
let translations = {};
let offlineQueue = [];
let isAdmin = false;
let pieChart, barChart, lineChart, damageChart, trendChart, infraChart, crisisChart;
let currentMarker = null;

function loadOfflineQueue() { const saved = localStorage.getItem('offline_reports'); if (saved) offlineQueue = JSON.parse(saved); updateOfflineUI(); }
function saveOfflineQueue() { localStorage.setItem('offline_reports', JSON.stringify(offlineQueue)); updateOfflineUI(); }
function updateOfflineUI() { const el = document.getElementById('pendingTasks'); if (el) el.innerHTML = offlineQueue.length; }
loadOfflineQueue();

function switchTab(tab) {
    if (tab === 'command') {
        document.getElementById('commandTab').classList.add('active');
        document.getElementById('commandTab').style.display = 'flex';
        document.getElementById('analyticsTab').classList.remove('active');
        document.getElementById('analyticsTab').style.display = 'none';
        document.getElementById('tabCommandBtn').classList.add('active');
        document.getElementById('tabAnalyticsBtn').classList.remove('active');
        setTimeout(() => { if (map) map.invalidateSize(); }, 150);
    } else {
        document.getElementById('commandTab').classList.remove('active');
        document.getElementById('commandTab').style.display = 'none';
        document.getElementById('analyticsTab').classList.add('active');
        document.getElementById('analyticsTab').style.display = 'block';
        document.getElementById('tabCommandBtn').classList.remove('active');
        document.getElementById('tabAnalyticsBtn').classList.add('active');
        loadAdminStats();
    }
}

async function loadAdminStats() {
    const days = document.getElementById('analyticsDays').value;
    try {
        const res = await fetch('/api/admin/stats?days=' + encodeURIComponent(days));
        const data = await res.json();
        document.getElementById('totalReports').innerHTML = data.total_reports || 0;
        document.getElementById('totalUsers').innerHTML = data.total_users || 0;
        document.getElementById('avgResponse').innerHTML = 'N/A';
        document.getElementById('topReporter').innerHTML = data.top_reporters[0]?.username || '-';
        if (trendChart) trendChart.destroy();
        trendChart = new Chart(document.getElementById('trendChart'), {
            type: 'line', data: { labels: data.daily_trend.map(d => d.date.slice(5)), datasets: [{ label: 'Reports', data: data.daily_trend.map(d => d.count), borderColor: '#2ecc71', fill: true, backgroundColor: 'rgba(46,204,113,0.1)', tension: 0.4 }] },
            options: { responsive: true, plugins: { legend: { labels: { color: '#e0e0e0' } } } }
        });
        if (damageChart) damageChart.destroy();
        damageChart = new Chart(document.getElementById('damageChart'), { type: 'doughnut', data: { labels: data.by_damage.map(d => d.level), datasets: [{ data: data.by_damage.map(d => d.count), backgroundColor: ['#e74c3c', '#f39c12', '#2ecc71'] }] }, options: { responsive: true, plugins: { legend: { labels: { color: '#e0e0e0' } } } } });
        if (infraChart) infraChart.destroy();
        infraChart = new Chart(document.getElementById('infraChart'), { type: 'bar', data: { labels: data.by_infrastructure.map(d => d.type), datasets: [{ label: 'Reports', data: data.by_infrastructure.map(d => d.count), backgroundColor: '#2ecc71' }] }, options: { responsive: true, plugins: { legend: { labels: { color: '#e0e0e0' } } } } });
        if (crisisChart) crisisChart.destroy();
        crisisChart = new Chart(document.getElementById('crisisChart'), { type: 'bar', data: { labels: data.by_crisis.map(d => d.crisis), datasets: [{ label: 'Reports', data: data.by_crisis.map(d => d.count), backgroundColor: '#3498db' }] }, options: { responsive: true, plugins: { legend: { labels: { color: '#e0e0e0' } } } } });
    } catch(e) { console.error(e); }
}

function updateCommandCenterCharts() {
    try {
        const dc = { minimal: 0, partial: 0, complete: 0 };
        reports.forEach(r => { if (r.damage_level === 'minimal') dc.minimal++; else if (r.damage_level === 'partial') dc.partial++; else if (r.damage_level === 'complete') dc.complete++; });
        if (pieChart) pieChart.destroy();
        pieChart = new Chart(document.getElementById('pieChart'), { type: 'pie', data: { labels: ['Minimal', 'Partial', 'Complete'], datasets: [{ data: [dc.minimal, dc.partial, dc.complete], backgroundColor: ['#2ecc71', '#f39c12', '#e74c3c'] }] }, options: { responsive: true, plugins: { legend: { position: 'bottom' } } } });
        const ic = {};
        reports.forEach(r => { const t = r.infrastructure_type || 'Unknown'; ic[t] = (ic[t] || 0) + 1; });
        const il = Object.keys(ic).slice(0, 6); const idata = il.map(l => ic[l]);
        if (barChart) barChart.destroy();
        barChart = new Chart(document.getElementById('barChart'), { type: 'bar', data: { labels: il.length ? il : ['None'], datasets: [{ label: 'Reports', data: il.length ? idata : [0], backgroundColor: '#3498db' }] }, options: { responsive: true } });
        const dc2 = {};
        reports.forEach(r => { const d = new Date(r.timestamp).toISOString().split('T')[0]; dc2[d] = (dc2[d] || 0) + 1; });
        const l7 = []; for (let i = 6; i >= 0; i--) { const d = new Date(); d.setDate(d.getDate() - i); l7.push(d.toISOString().split('T')[0]); }
        if (lineChart) lineChart.destroy();
        lineChart = new Chart(document.getElementById('lineChart'), { type: 'line', data: { labels: l7.map(d => d.slice(5)), datasets: [{ label: 'Reports', data: l7.map(d => dc2[d] || 0), borderColor: '#2ecc71', fill: true, backgroundColor: 'rgba(46,204,113,0.1)', tension: 0.4 }] }, options: { responsive: true } });
    } catch (e) { console.error(e); }
}

async function setLanguage(lang) {
    currentLang = lang; localStorage.setItem('language', lang);
    try { const res = await fetch('/api/lang/' + encodeURIComponent(lang)); const data = await res.json(); translations = data; updateUITexts(); } catch(e) { console.error(e); }
}
function updateUITexts() {
    const setTxt = (id, val) => { const el = document.getElementById(id); if (el) el.innerText = val; };
    setTxt('reportTitle', translations.report_damage || 'Report Damage');
    setTxt('gpsLabel', translations.gps_location || 'Use My GPS');
    setTxt('submitLabel', translations.submit || 'Submit Report');
    setTxt('chatInput', '');
    const ci = document.getElementById('chatInput'); if (ci) ci.placeholder = translations.type_message || 'Type a message...';
}
const ls = document.getElementById('languageSelect');
if (ls) { ls.value = currentLang; ls.addEventListener('change', (e) => setLanguage(e.target.value)); }

function initMap() {
    const container = document.getElementById('map');
    if (!container) { console.error('Map container not found'); return; }
    console.log('Initializing map, container size:', container.offsetWidth, 'x', container.offsetHeight);
    map = L.map('map', { center: [20, 0], zoom: 2, zoomControl: true });
    map.attributionControl.setPrefix('');
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '&copy; OpenStreetMap', maxZoom: 19 }).addTo(map);
    setTimeout(() => { map.invalidateSize(); console.log('Map size after invalidate:', map.getSize()); }, 100);
    setTimeout(() => { map.invalidateSize(); }, 500);
    setTimeout(() => { map.invalidateSize(); }, 1500);
    window.addEventListener('resize', () => map.invalidateSize());
    map.on('click', async function(e) {
        let lat = e.latlng.lat, lng = e.latlng.lng;
        document.getElementById('lat').value = lat.toFixed(6);
        document.getElementById('lng').value = lng.toFixed(6);
        try {
            let res = await fetch('/api/building/' + encodeURIComponent(lat) + '/' + encodeURIComponent(lng));
            let building = await res.json();
            if(building && building.name) {
                document.getElementById('buildingName').value = building.name;
                document.getElementById('selectedBuildingInfo').style.display = 'block';
                document.getElementById('selectedBuildingInfo').innerHTML = '🏢 ' + escapeHtml(building.name) + '<br>📍 ' + escapeHtml(building.address || 'Unknown');
            } else { document.getElementById('selectedBuildingInfo').style.display = 'none'; }
        } catch(err) { console.error(err); }
        if(currentMarker) map.removeLayer(currentMarker);
        currentMarker = L.marker([lat, lng]).addTo(map).bindPopup('Selected').openPopup();
    });
    window.map = map;
}

function shareLocation() {
    if(navigator.geolocation) navigator.geolocation.getCurrentPosition(pos => {
        let lat = pos.coords.latitude, lng = pos.coords.longitude;
        document.getElementById('lat').value = lat.toFixed(6); document.getElementById('lng').value = lng.toFixed(6);
        map.setView([lat,lng],16);
        if(currentMarker) map.removeLayer(currentMarker);
        currentMarker = L.marker([lat,lng]).addTo(map).bindPopup('Your location').openPopup();
    });
}

async function sendSMSReport() {
    let smsText = document.getElementById('smsText').value, smsNumber = document.getElementById('smsNumber').value;
    let statusDiv = document.getElementById('smsStatus');
    if(!smsText) { statusDiv.innerText = 'Please enter SMS text'; return; }
    try {
        let fd = new FormData(); fd.append('sms_text', smsText); fd.append('sms_number', smsNumber);
        let res = await fetch('/api/sms_report', { method:'POST', body:fd });
        let data = await res.json();
        if(data.status==='success') { statusDiv.innerHTML = '✅ Sent!'; document.getElementById('smsText').value = ''; loadReports(); }
        else { statusDiv.innerHTML = '❌ '+data.message; }
    } catch(e) { statusDiv.innerHTML = '❌ Failed'; }
}

const photoInput = document.getElementById('photo');
if (photoInput) photoInput.addEventListener('change', function(e) {
    let preview = document.getElementById('photoPreview');
    if(e.target.files && e.target.files[0]) {
        let reader = new FileReader();
        reader.onload = function(ev) { preview.innerHTML = '<img src="' + ev.target.result + '" style="max-width:100%; max-height:80px;">'; };
        reader.readAsDataURL(e.target.files[0]);
    } else { preview.innerHTML = ''; }
});

async function submitReport() {
    let fd = new FormData();
    fd.append('damage_level', document.getElementById('damageLevel').value);
    fd.append('infrastructure_type', document.getElementById('infrastructureType').value);
    fd.append('building_name', document.getElementById('buildingName').value);
    fd.append('crisis_nature', document.getElementById('crisisNature').value);
    fd.append('debris', document.getElementById('debris').value);
    fd.append('text_location', document.getElementById('textLocation').value);
    fd.append('lat', document.getElementById('lat').value);
    fd.append('lng', document.getElementById('lng').value);
    fd.append('notes', document.getElementById('notes').value);
    let photoFile = document.getElementById('photo').files[0];
    if(photoFile) fd.append('photo', photoFile);
    let statusDiv = document.getElementById('submitStatus');
    statusDiv.innerHTML = 'Submitting...';
    try {
        let res = await fetch('/api/report', { method:'POST', body:fd });
        let data = await res.json();
        if(data.status==='success') {
            statusDiv.innerHTML = '✅ Submitted!';
            document.getElementById('lat').value = ''; document.getElementById('lng').value = '';
            document.getElementById('buildingName').value = ''; document.getElementById('textLocation').value = '';
            document.getElementById('notes').value = ''; document.getElementById('photo').value = '';
            document.getElementById('photoPreview').innerHTML = '';
            if(currentMarker) map.removeLayer(currentMarker);
            loadReports();
        } else { statusDiv.innerHTML = '❌ Failed'; }
    } catch(e) {
        statusDiv.innerHTML = '❌ Offline – saved';
        offlineQueue.push({ report_uuid:Date.now().toString(), damage_level:document.getElementById('damageLevel').value, lat:document.getElementById('lat').value, lng:document.getElementById('lng').value, location_text:document.getElementById('textLocation').value, infrastructure_type:document.getElementById('infrastructureType').value, building_name:document.getElementById('buildingName').value, crisis_nature:document.getElementById('crisisNature').value, debris:document.getElementById('debris').value, notes:document.getElementById('notes').value, timestamp:new Date().toISOString(), is_offline:true });
        saveOfflineQueue(); loadReports();
    }
}

async function syncOfflineReports() {
    if(offlineQueue.length===0) return;
    try {
        let res = await fetch('/api/sync', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(offlineQueue) });
        if(res.ok) { offlineQueue = []; saveOfflineQueue(); loadReports(); }
    } catch(e) { console.error(e); }
}
async function forceSync() { await syncOfflineReports(); }
window.forceSync = forceSync;

async function loadReports() {
    try {
        let res = await fetch('/api/reports');
        let serverReports = await res.json();
        reports = [...serverReports, ...offlineQueue.map(r=>({...r,is_offline:true}))];
        reports.sort((a,b)=>new Date(b.timestamp)-new Date(a.timestamp));
        updateMapMarkers();
        updateReportsList();
        updateConnectionStatus(true);
        updateKPIs();
        updateCommandCenterCharts();
    } catch(e) {
        reports = offlineQueue.map(r=>({...r,is_offline:true}));
        updateReportsList();
        updateConnectionStatus(false);
        updateKPIs();
        updateCommandCenterCharts();
    }
}

function updateKPIs() {
    let total = reports.length;
    let critical = reports.filter(r=>r.damage_level==='complete').length;
    let high = reports.filter(r=>r.damage_level==='partial').length;
    const setTxt = (id, val) => { const el = document.getElementById(id); if (el) el.innerText = val; };
    setTxt('activeCases', total);
    setTxt('criticalCount', critical);
    setTxt('highCount', high);
    setTxt('pendingTasks', offlineQueue.length);
    setTxt('urgentTasks', critical);
    setTxt('resourcesDeployed', Math.floor(total*0.7));
    setTxt('deployedCount', Math.floor(total*0.4));
    setTxt('standbyCount', Math.floor(total*0.3));
    setTxt('totalVolunteers', 350 + Math.floor(total/2));
    setTxt('activeVolunteersCount', 200 + Math.floor(total/3));
    setTxt('standbyVolunteers', 100 + Math.floor(total/5));
    setTxt('offlineVolunteers', 50);
}

function updateMapMarkers() {
    if (!map) return;
    for(let m of markers) map.removeLayer(m);
    markers = [];
    for(let r of reports) {
        if(r.lat && r.lng) {
            let color = '#2ecc71';
            if(r.damage_level==='partial') color='#f39c12';
            if(r.damage_level==='complete') color='#e74c3c';
            let marker = L.circleMarker([r.lat,r.lng], { radius:8, fillColor:color, color:'#fff', weight:2, fillOpacity:0.8 }).addTo(map);
            marker.bindPopup('<b>' + escapeHtml(r.building_name || 'Building') + '</b><br>' + escapeHtml(r.damage_level || '') + '');
            markers.push(marker);
        }
    }
}

function updateReportsList() {
    let container = document.getElementById('reportsList');
    if(!container) return;
    container.innerHTML = '';
    reports.slice(0,15).forEach(r => {
        let div = document.createElement('div');
        div.className = 'report-item ' + (r.damage_level === 'complete' ? 'severity-critical' : (r.damage_level === 'partial' ? 'severity-high' : ''));
        div.innerHTML = '<strong>' + escapeHtml(r.building_name || 'Location') + '</strong><br>' + escapeHtml(r.infrastructure_type || '') + ' - ' + escapeHtml(r.damage_level || '');
        div.onclick = () => { if(r.lat && r.lng && map) map.setView([r.lat,r.lng],18); };
        container.appendChild(div);
    });
}

function updateConnectionStatus(isOnline) {
    let statusDiv = document.getElementById('connectionStatus');
    if(statusDiv) {
        if(isOnline) { statusDiv.innerHTML = '<i class="fas fa-circle"></i> Online'; statusDiv.className = 'status-badge status-online'; }
        else { statusDiv.innerHTML = '<i class="fas fa-circle"></i> Offline'; statusDiv.className = 'status-badge'; }
    }
}

async function loadCurrentUser() {
    try {
        let res = await fetch('/api/current_user');
        let user = await res.json();
        currentUser = user;
        document.getElementById('userRoleBadge').textContent = (user.role || '') + ' ' + (user.points || 0) + ' pts';
        if(user.role === 'admin') {
            document.getElementById('exportCard').style.display = 'block';
            document.getElementById('tabAnalyticsBtn').style.display = 'inline-block';
            document.getElementById('exportCSVBtn').style.display = 'inline-flex';
            document.getElementById('exportGeoJSONBtn').style.display = 'inline-flex';
            isAdmin=true;
        } else {
            document.getElementById('exportCard').style.display = 'none';
        }
        loadReports();
        loadLeaderboard();
        loadStats();
    } catch(e) { console.error('Auth error',e); }
}

async function loadLeaderboard() {
    try {
        let res = await fetch('/api/leaderboard');
        let leaders = await res.json();
        let container = document.getElementById('leaderboardList');
        if (!container) return;
        container.innerHTML = leaders.map((l,i) => '<div class="leaderboard-item"><span class="rank">' + (i + 1) + '</span><span>' + escapeHtml(l.username || '') + '</span><span>🏆 ' + (l.points || 0) + '</span></div>').join('');
    } catch(e) { console.warn(e); }
}

async function loadStats() { try { let res=await fetch('/api/stats'); let stats=await res.json(); } catch(e){} }

function exportCSV() { window.open('/api/reports/csv','_blank'); }
window.exportCSV = exportCSV;
async function exportGeoJSON() {
    try { let res=await fetch('/api/reports/geojson_spatial'); let data=await res.json(); let blob=new Blob([JSON.stringify(data)],{type:'application/json'}); let url=URL.createObjectURL(blob); let a=document.createElement('a'); a.href=url; a.download='reports.geojson'; a.click(); URL.revokeObjectURL(url); } catch(e){ alert('Export failed'); }
}

function toggleLeaderboard() { let el=document.querySelector('.leaderboard-list'); if(el) el.style.display=el.style.display==='none'?'block':'none'; }

document.getElementById('pendingTasksCard').addEventListener('click', function() {
    if(offlineQueue.length === 0) { alert('No pending tasks.'); return; }
    if(confirm('Sync ' + offlineQueue.length + ' pending reports?')) forceSync();
});

window.addEventListener('online', () => { updateConnectionStatus(true); syncOfflineReports(); loadReports(); });
window.addEventListener('offline', () => { updateConnectionStatus(false); });

function addChatMessage(username, message, isOwn = false) {
    const container = document.getElementById('chatMessages');
    if (!container) return;
    const div = document.createElement('div');
    div.className = 'chat-message ' + (isOwn ? 'own' : 'other');
    const time = new Date().toLocaleTimeString();
    div.innerHTML = '<span class="msg-username">' + escapeHtml(username) + ' <span class="msg-time">' + escapeHtml(time) + '</span></span>' + escapeHtml(message);
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}
function sendLocalChatMessage() {
    const input = document.getElementById('chatInput');
    const text = input.value.trim();
    if (!text) return;
    addChatMessage('You', text, true);
    input.value = '';
}
const chatSendBtn = document.getElementById('chatSendBtn');
const chatInput = document.getElementById('chatInput');
if (chatSendBtn) chatSendBtn.addEventListener('click', sendLocalChatMessage);
if (chatInput) chatInput.addEventListener('keydown', function(e) { if (e.key === 'Enter') sendLocalChatMessage(); });

(function initDragChat() {
    const container = document.getElementById('glowChat');
    const header = document.getElementById('chatDragHandle');
    if (!container || !header) return;
    let isDragging = false, offX = 0, offY = 0;
    header.addEventListener('mousedown', (e) => {
        if (e.target.closest('button') || e.target.closest('input')) return;
        isDragging = true;
        const rect = container.getBoundingClientRect();
        offX = e.clientX - rect.left;
        offY = e.clientY - rect.top;
        container.style.cursor = 'grabbing';
        header.style.cursor = 'grabbing';
        e.preventDefault();
    });
    document.addEventListener('mousemove', (e) => {
        if (!isDragging) return;
        let newX = e.clientX - offX;
        let newY = e.clientY - offY;
        const maxX = window.innerWidth - container.offsetWidth;
        const maxY = window.innerHeight - container.offsetHeight;
        newX = Math.max(0, Math.min(newX, maxX));
        newY = Math.max(0, Math.min(newY, maxY));
        container.style.left = newX + 'px';
        container.style.top = newY + 'px';
        container.style.bottom = 'auto';
        container.style.right = 'auto';
    });
    document.addEventListener('mouseup', () => {
        if (isDragging) { isDragging = false; container.style.cursor = 'grab'; header.style.cursor = 'grab'; }
    });
})();

document.addEventListener('DOMContentLoaded', function() {
    const toggleSidebarBtn = document.getElementById('toggleSidebarBtn');
    const sidebar = document.getElementById('sidebarPanel');
    let sidebarVisible = true;
    toggleSidebarBtn.addEventListener('click', function() {
        sidebarVisible = !sidebarVisible;
        sidebar.classList.toggle('collapsed', !sidebarVisible);
        toggleSidebarBtn.innerHTML = sidebarVisible ? '<i class="fas fa-chevron-left"></i>' : '<i class="fas fa-chevron-right"></i>';
        setTimeout(() => { if (map) map.invalidateSize(); }, 300);
    });
});

// ===== INIT =====
window.addEventListener('load', function() {
    console.log('Window loaded, initializing...');
    setTimeout(function() {
        initMap();
        loadCurrentUser();
        setInterval(() => loadReports(), 30000);
        setInterval(() => updateKPIs(), 10000);
        setInterval(() => updateCommandCenterCharts(), 15000);
        setInterval(() => loadLeaderboard(), 10000);
    }, 200);
});
</script>
</body>
</html>
"""

# ============================================
# VERCEL SERVERLESS HANDLER
# ============================================
from mangum import Mangum
handler = Mangum(app)

# ============================================
# LOCAL DEVELOPMENT
# ============================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
