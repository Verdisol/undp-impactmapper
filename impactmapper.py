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
# DATABASE (lazy connections, no pool)
# ============================================
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable not set")

async def get_db_conn():
    return await asyncpg.connect(DATABASE_URL)

async def ensure_tables():
    conn = await get_db_conn()
    try:
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

# ============================================
# CREATE FASTAPI APP with lifespan
# ============================================
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
            INSERT INTO reports (report_uuid, building_id, building_osm_id, building_name, building_address,
                                damage_level, version, lat, lng, location_text, photo_path,
                                infrastructure_type, crisis_nature, debris, notes, username, timestamp, is_current, synced, sms_number)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20)
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

# ============================================
# ADMIN STATS (FIXED with timestamp casting)
# ============================================
async def get_admin_stats(days: int = 30):
    await init_db_once()
    conn = await get_db_conn()
    try:
        date_filter = ""
        if days > 0:
            date_filter = f"AND timestamp::timestamp >= (NOW() - INTERVAL '{days} days')"

        total_reports = await conn.fetchval(f"""
            SELECT COUNT(*) FROM reports WHERE is_current = 1 {date_filter}
        """)

        total_users = await conn.fetchval(f"""
            SELECT COUNT(DISTINCT username) FROM reports WHERE is_current = 1 {date_filter}
        """)

        top_reporters = await conn.fetch(f"""
            SELECT username, COUNT(*) as reports
            FROM reports
            WHERE is_current = 1 {date_filter}
            GROUP BY username
            ORDER BY reports DESC
            LIMIT 10
        """)

        days_limit = min(days, 30) if days > 0 else 30
        daily_trend = await conn.fetch(f"""
            SELECT DATE(timestamp::timestamp) as date, COUNT(*) as count
            FROM reports
            WHERE is_current = 1 AND timestamp::timestamp >= (NOW() - INTERVAL '{days_limit} days')
            GROUP BY DATE(timestamp::timestamp)
            ORDER BY date ASC
        """)

        by_damage = await conn.fetch(f"""
            SELECT damage_level, COUNT(*) as count
            FROM reports
            WHERE is_current = 1 {date_filter}
            GROUP BY damage_level
        """)

        by_infrastructure = await conn.fetch(f"""
            SELECT infrastructure_type, COUNT(*) as count
            FROM reports
            WHERE is_current = 1 AND infrastructure_type IS NOT NULL AND infrastructure_type != ''
            {date_filter}
            GROUP BY infrastructure_type
            ORDER BY count DESC
            LIMIT 10
        """)

        by_crisis = await conn.fetch(f"""
            SELECT crisis_nature, COUNT(*) as count
            FROM reports
            WHERE is_current = 1 AND crisis_nature IS NOT NULL AND crisis_nature != ''
            {date_filter}
            GROUP BY crisis_nature
            ORDER BY count DESC
            LIMIT 10
        """)

        users_by_role = await conn.fetch("""
            SELECT role, COUNT(*) as count
            FROM users
            GROUP BY role
        """)

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
# AUTHENTICATION
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
    
    if lat and lng:
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
async def sms_report(
    sms_text: str = Form(...),
    sms_number: str = Form("")
):
    parts = sms_text.upper().split()
    if len(parts) >= 3:
        damage_level = parts[0].lower()
        try:
            lat = float(parts[1])
            lng = float(parts[2])
            notes = " ".join(parts[3:]) if len(parts) > 3 else "SMS Report"
            report_uuid = str(uuid.uuid4())[:8]
            building_id = f"sms_{lat}_{lng}"
            await save_report(
                report_uuid, building_id, "", "", "",
                damage_level, lat, lng, "", None,
                "unknown", "earthquake", "no", notes, "sms_user", 1, sms_number
            )
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
                        INSERT INTO reports (report_uuid, building_id, damage_level, lat, lng, location_text,
                                            infrastructure_type, building_name, crisis_nature, debris,
                                            notes, username, timestamp, synced, is_current)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                    """, report.get('report_uuid'), report.get('building_id'), report.get('damage_level'),
                        report.get('lat'), report.get('lng'), report.get('location_text'),
                        report.get('infrastructure_type'), report.get('building_name'), report.get('crisis_nature'),
                        report.get('debris'), report.get('notes'), current_user['username'],
                        report.get('timestamp'), 1, 1)
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

@app.get("/api/reports/geojson")
async def get_geojson(current_user: dict = Depends(require_reporter)):
    conn = await get_db_conn()
    try:
        rows = await conn.fetch("SELECT damage_level, lat, lng, infrastructure_type, crisis_nature, building_name, timestamp FROM reports WHERE lat != 0 AND is_current = 1")
        features = []
        for r in rows:
            if r[1] and r[2]:
                features.append({
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [float(r[2]), float(r[1])]},
                    "properties": {
                        "damage_level": r[0], "infrastructure_type": r[3],
                        "crisis_nature": r[4], "building_name": r[5], "timestamp": r[6]
                    }
                })
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
        body {
            font-family: 'Inter', sans-serif;
            min-height: 100vh;
            background: linear-gradient(135deg, #0a2a1a 0%, #0a1a0f 100%);
            position: relative;
            overflow-x: hidden;
        }
        .hero-bg {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-image: url('https://images.unsplash.com/photo-1582213782179-e0d53f98f2ca?w=1600');
            background-size: cover;
            background-position: center 30%;
            opacity: 0.12;
            z-index: 0;
        }
        .container {
            position: relative;
            z-index: 1;
            max-width: 1400px;
            margin: 0 auto;
            padding: 40px 60px;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }
        .navbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px 0;
            margin-bottom: 80px;
            flex-wrap: wrap;
            gap: 20px;
        }
        .logo h1 { font-size: 28px; font-weight: 700; color: white; }
        .logo span { color: #2ecc71; }
        .logo p { font-size: 12px; color: #aaa; margin-top: 4px; }
        .nav-links { display: flex; gap: 30px; align-items: center; flex-wrap: wrap; }
        .nav-links a { color: #ccc; text-decoration: none; font-size: 14px; font-weight: 500; transition: all 0.3s ease; }
        .nav-links a:hover { color: #2ecc71; transform: scale(1.05); }
        .language-select {
            background: rgba(255,255,255,0.1);
            border: 1px solid rgba(46,204,113,0.3);
            padding: 8px 16px;
            border-radius: 30px;
            color: white;
            cursor: pointer;
            font-size: 13px;
            transition: all 0.3s ease;
        }
        .language-select:hover { border-color: #2ecc71; background: rgba(46,204,113,0.2); }
        .hero-section {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 60px;
            flex-wrap: wrap;
            margin-bottom: 80px;
        }
        .hero-left { flex: 1; min-width: 300px; }
        .hero-badge {
            display: inline-block;
            background: rgba(46,204,113,0.2);
            border: 1px solid rgba(46,204,113,0.4);
            padding: 6px 16px;
            border-radius: 30px;
            font-size: 12px;
            color: #2ecc71;
            margin-bottom: 24px;
        }
        .hero-left h1 {
            font-size: 56px;
            font-weight: 800;
            line-height: 1.2;
            margin-bottom: 20px;
            background: linear-gradient(135deg, #fff, #2ecc71);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .hero-left p { font-size: 18px; color: #ccc; line-height: 1.6; margin-bottom: 32px; max-width: 600px; }
        .stats { display: flex; gap: 40px; margin-top: 40px; flex-wrap: wrap; }
        .stat-item { text-align: left; transition: all 0.3s ease; cursor: pointer; }
        .stat-item:hover { transform: translateY(-5px); }
        .stat-item:hover .stat-number { text-shadow: 0 0 15px rgba(46,204,113,0.8); }
        .stat-number { font-size: 32px; font-weight: 800; color: #2ecc71; transition: all 0.3s ease; }
        .stat-label { font-size: 12px; color: #888; margin-top: 4px; }
        .hero-right { flex: 0.8; min-width: 350px; }
        .login-card {
            background: rgba(17, 17, 17, 0.95);
            backdrop-filter: blur(15px);
            border-radius: 16px;
            padding: 40px;
            border: 1px solid rgba(46,204,113,0.3);
            box-shadow: 0 25px 50px rgba(0,0,0,0.3);
            transition: all 0.3s ease;
        }
        .login-card:hover { border-color: rgba(46,204,113,0.6); transform: translateY(-5px); }
        .login-card h2 { font-size: 24px; font-weight: 700; margin-bottom: 8px; }
        .login-card p { font-size: 13px; color: #888; margin-bottom: 24px; }
        .input-group { margin-bottom: 16px; }
        .input-group input {
            width: 100%;
            padding: 14px 16px;
            background: #2a2a2a;
            border: 1px solid #3a3a3a;
            border-radius: 12px;
            color: white;
            font-size: 14px;
            transition: all 0.3s ease;
        }
        .input-group input:focus {
            outline: none;
            border-color: #2ecc71;
            box-shadow: 0 0 0 3px rgba(46,204,113,0.2);
            transform: scale(1.01);
        }
        .login-btn {
            width: 100%;
            padding: 14px;
            background: linear-gradient(135deg, #2ecc71, #27ae60);
            color: white;
            font-weight: 700;
            border: none;
            border-radius: 12px;
            font-size: 16px;
            cursor: pointer;
            margin-top: 8px;
            transition: all 0.3s ease;
        }
        .login-btn:hover { transform: translateY(-2px); box-shadow: 0 10px 25px rgba(46,204,113,0.5); }
        .demo-info { margin-top: 24px; padding-top: 20px; border-top: 1px solid #2a2a2a; text-align: center; }
        .demo-info p { font-size: 11px; color: #666; margin-bottom: 8px; }
        .demo-badge { display: inline-flex; gap: 12px; justify-content: center; flex-wrap: wrap; }
        .demo-role {
            background: rgba(46,204,113,0.1);
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 11px;
            color: #2ecc71;
            transition: all 0.3s ease;
            cursor: pointer;
        }
        .demo-role:hover { background: rgba(46,204,113,0.3); transform: scale(1.05); }
        .footer { margin-top: auto; padding: 30px 0 20px; text-align: center; border-top: 1px solid rgba(255,255,255,0.05); }
        .footer p { font-size: 12px; color: #666; }
        .partner-logos { display: flex; justify-content: center; gap: 30px; margin-bottom: 20px; flex-wrap: wrap; }
        .partner { font-size: 14px; opacity: 0.6; transition: all 0.3s ease; cursor: pointer; }
        .partner:hover { opacity: 1; transform: scale(1.1); }
        @media (max-width: 968px) {
            .container { padding: 20px 30px; }
            .hero-section { flex-direction: column; }
            .hero-left h1 { font-size: 40px; }
            .navbar { flex-direction: column; text-align: center; }
        }
        @media (max-width: 600px) {
            .container { padding: 15px 20px; }
            .hero-left h1 { font-size: 32px; }
            .login-card { padding: 25px; }
        }
    </style>
</head>
<body>
    <div class="hero-bg"></div>
    <div class="container">
        <div class="navbar">
            <div class="logo">
                <h1>🌍 UNDP <span>ImpactMapper</span></h1>
                <p>Unified Crisis Intelligence Platform</p>
            </div>
            <div class="nav-links">
                <a href="#">Explore</a>
                <a href="#">Learn</a>
                <a href="#">About</a>
                <a href="#">Support</a>
                <select id="languageSelect" class="language-select">
                    <option value="en">🌍 English</option>
                    <option value="es">🇪🇸 Español</option>
                    <option value="fr">🇫🇷 Français</option>
                    <option value="pt">🇵🇹 Português</option>
                    <option value="ar">🇸🇦 العربية</option>
                    <option value="zh">🇨🇳 中文</option>
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
                            <span class="demo-role">👑 admin / admin123 (Full Access + Analytics)</span>
                            <span class="demo-role">📸 reporter / report123 (Submit reports)</span>
                            <span class="demo-role">👁️ viewer / view123 (View only)</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <div class="footer">
            <div class="partner-logos">
                <span class="partner">🔴 American Red Cross</span>
                <span class="partner">🇺🇳 UN OCHA</span>
                <span class="partner">🌾 World Food Programme</span>
                <span class="partner">🏥 World Health Organization</span>
                <span class="partner">🚒 FEMA</span>
                <span class="partner">🗺️ OpenStreetMap</span>
            </div>
            <p>© <span id="currentYear"></span> UNDP ImpactMapper - Unified Crisis Intelligence Platform</p>
        </div>
    </div>
    <script>
        document.getElementById('currentYear').innerText = new Date().getFullYear();
        const langSelect = document.getElementById('languageSelect');
        async function setLanguage(lang) { try { const res = await fetch(`/api/lang/${lang}`); const data = await res.json(); } catch(e) {} }
        langSelect.addEventListener('change', (e) => { setLanguage(e.target.value); });
        async function login() {
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            const errorDiv = document.getElementById('errorMsg');
            if (!username || !password) { errorDiv.innerText = 'Please enter username and password'; return; }
            try {
                const response = await fetch('/dashboard', { headers: { 'Authorization': 'Basic ' + btoa(username + ':' + password) } });
                if (response.ok) {
                    window.location.href = '/dashboard';
                } else {
                    const text = await response.text();
                    console.error('Login failed:', response.status, text);
                    errorDiv.innerText = 'Invalid credentials (status ' + response.status + ')';
                }
            } catch(e) {
                errorDiv.innerText = 'Login failed: ' + e.message;
                console.error(e);
            }
        }
        document.getElementById('password').addEventListener('keypress', function(e) { if (e.key === 'Enter') login(); });
        setLanguage('en');
    </script>
</body>
</html>
"""

# ============================================
# UNIFIED DASHBOARD HTML – FULLY UPDATED
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
            padding: 8px 40px !important;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 2px solid #2ecc71;
            min-height: 90px !important;
            height: 90px !important;
            flex-shrink: 0;
        }
        .brand-center {
            flex: 1;
            text-align: center;
        }
        .brand-center h1 {
            font-size: 1.6rem !important;
            font-weight: 700;
            color: white;
            letter-spacing: 0.5px;
            margin: 0;
            line-height: 1.2;
        }
        .brand-center h1 span { color: #2ecc71; }
        .brand-center p {
            font-size: 0.9rem !important;
            color: rgba(255,255,255,0.75);
            margin-top: 2px;
            line-height: 1.2;
        }

        .controls-right {
            display: grid;
            grid-template-columns: repeat(5, auto);
            grid-template-rows: auto auto;
            gap: 4px 8px;
            align-items: center;
            justify-items: end;
        }

        .sync-btn, .logout-btn, .lang-dropdown, .status-badge, .role-badge {
            height: 32px !important;
            min-width: 70px !important;
            padding: 6px 14px !important;
            border-radius: 6px !important;
            font-size: 0.85rem !important;
            font-weight: 700 !important;
            color: #000 !important;
            background: rgba(255,255,255,0.85) !important;
            border: 1px solid rgba(0,0,0,0.1) !important;
            box-shadow: none !important;
            transition: 0.2s ease !important;
            white-space: nowrap !important;
            cursor: pointer !important;
            text-decoration: none !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            gap: 6px !important;
        }
        .sync-btn:hover, .logout-btn:hover, .lang-dropdown:hover, .status-badge:hover, .role-badge:hover {
            background: #fff !important;
            transform: scale(1.02);
            box-shadow: 0 2px 8px rgba(0,0,0,0.15) !important;
        }
        .logout-btn {
            background: rgba(255, 200, 200, 0.9) !important;
            color: #b00000 !important;
        }
        .logout-btn:hover {
            background: #fff !important;
            color: #d00 !important;
        }
        .status-badge {
            background: rgba(200,255,200,0.85) !important;
            color: #000 !important;
        }
        .status-badge i {
            font-size: 8px !important;
            color: #2ecc71 !important;
        }
        .lang-dropdown {
            background: rgba(255,255,255,0.85) !important;
            color: #000 !important;
            border: 1px solid #ccc !important;
            padding: 2px 10px !important;
            font-size: 0.8rem !important;
            min-width: 56px !important;
        }
        .role-badge {
            background: rgba(255,255,200,0.85) !important;
            color: #000 !important;
        }

        #exportCSVBtn, #exportGeoJSONBtn {
            height: 30px !important;
            min-width: 50px !important;
            padding: 4px 10px !important;
            font-size: 0.75rem !important;
            background: rgba(255,255,255,0.8) !important;
            border: 1px solid rgba(0,0,0,0.08) !important;
            border-radius: 4px !important;
            font-weight: 700 !important;
            color: #000 !important;
            justify-content: center !important;
            display: inline-flex !important;
            align-items: center !important;
            gap: 4px !important;
            cursor: pointer !important;
            transition: 0.2s ease !important;
        }
        #exportCSVBtn:hover, #exportGeoJSONBtn:hover {
            background: #fff !important;
            box-shadow: 0 1px 4px rgba(0,0,0,0.1) !important;
        }
        #exportCSVBtn i, #exportGeoJSONBtn i {
            font-size: 0.8em !important;
        }

        .sync-btn i, .logout-btn i, .status-badge i, .role-badge i {
            font-size: 0.9em !important;
        }

        .status-online {
            animation: none !important;
            box-shadow: none !important;
        }

        .tabs-container {
            background: var(--bg-card);
            padding: 0 16px 8px 16px;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            gap: 6px;
            overflow: visible;
            flex-shrink: 0;
        }
        .tab-btn {
            padding: 12px 28px;
            background: transparent;
            color: #a0a0a0;
            border: none;
            border-bottom: 2px solid transparent;
            font-size: 1.0rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        .tab-btn:hover {
            color: var(--primary);
            background: var(--primary-muted);
        }
        .tab-btn.active {
            color: #2ecc71;
            border-bottom: 3px solid #8B4513;
            background: rgba(139,69,19,0.15);
            box-shadow: 0 4px 20px rgba(46,204,113,0.6);
        }

        #commandTab {
            display: flex;
            flex-direction: column;
            flex: 1;
            overflow: hidden;
        }
        .kpi-row {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 12px;
            padding: 12px 20px;
            background: var(--bg-dark);
            flex-shrink: 0;
        }
        .kpi-card {
            background: var(--bg-card);
            border-radius: 8px;
            padding: 12px 16px;
            border: 2px solid #2ecc71;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        .kpi-card:hover {
            border-color: #27ae60;
            transform: translateY(-2px);
            box-shadow: 0 0 15px rgba(46,204,113,0.3);
        }
        .kpi-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
        .kpi-header span { font-size: 0.8rem; color: #a0a0a0; text-transform: uppercase; }
        .kpi-value { font-size: 1.6rem; font-weight: 700; margin-bottom: 4px; }
        .kpi-value.warning { color: #f39c12; }
        .progress-bar { height: 4px; background: #2a2a2a; border-radius: 2px; overflow: hidden; margin-top: 4px; }
        .progress-fill { height: 100%; background: var(--primary); border-radius: 2px; }
        .pill-group { display: flex; gap: 6px; margin-top: 4px; flex-wrap: wrap; }
        .pill { padding: 2px 8px; border-radius: 12px; font-size: 0.7rem; font-weight: 500; }
        .pill-red { background: rgba(231,76,60,0.12); color: #e74c3c; }
        .pill-yellow { background: rgba(243,156,18,0.12); color: #f39c12; }
        .pill-green { background: rgba(46,204,113,0.12); color: #2ecc71; }

        .main-layout {
            display: flex;
            flex: 1;
            overflow: hidden;
        }
        .sidebar {
            width: 420px;
            background: var(--bg-sidebar);
            overflow-y: auto !important;
            padding: 20px;
            border-right: 1px solid var(--border-color);
            transition: width 0.3s ease, padding 0.3s ease, opacity 0.3s ease;
            flex-shrink: 0;
            height: 100%;
            scrollbar-width: thin;
            scrollbar-color: #2ecc71 #1a1a1a;
        }
        .sidebar::-webkit-scrollbar {
            width: 8px;
        }
        .sidebar::-webkit-scrollbar-track {
            background: #1a1a1a;
        }
        .sidebar::-webkit-scrollbar-thumb {
            background: #2ecc71;
            border-radius: 10px;
        }
        .sidebar.collapsed {
            width: 0;
            padding: 0;
            overflow: hidden;
            border-right: none;
        }
        .right-panel {
            flex: 1;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        .map-container {
            flex: 1;
            min-height: 150px;
            position: relative;
        }
        #map {
            height: 100%;
            width: 100%;
            min-height: 300px;
            background: #1a1a1a;
        }

        /* ===== BIGGER FONTS (increased ~40%) ===== */
        .card {
            background: rgba(42, 42, 42, 0.9);
            backdrop-filter: blur(5px);
            border-radius: 10px;
            padding: 18px;
            margin-bottom: 14px;
            border: 1px solid rgba(255,255,255,0.08);
        }
        .card h3 {
            color: #2ecc71;
            margin-bottom: 10px;
            font-size: 1.3rem !important;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .card label, .card p, .card .building-info, .card .sms-card, .card .reports-list {
            font-size: 1.1rem !important;
        }
        input, select, textarea {
            width: 100%;
            padding: 10px;
            margin: 6px 0;
            background: #1a1a1a;
            border: 1px solid #444;
            border-radius: 8px;
            color: white;
            font-size: 1.1rem !important;
        }
        button {
            background: linear-gradient(135deg, #1a472a, #0d2a1a);
            color: white;
            padding: 10px;
            font-weight: 600;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            width: 100%;
            margin-top: 6px;
            font-size: 1.1rem !important;
        }
        .btn-location { background: linear-gradient(135deg, #3498db, #2980b9); }
        .btn-photo { background: linear-gradient(135deg, #8e44ad, #6c3483); }
        .reports-list { max-height: 220px; overflow-y: auto; }
        .report-item {
            background: #1a1a1a;
            padding: 10px 12px;
            margin: 8px 0;
            border-radius: 8px;
            border-left: 4px solid #2ecc71;
            cursor: pointer;
            font-size: 1.0rem !important;
        }
        .report-item.severity-critical { border-left-color: #e74c3c; }
        .report-item.severity-high { border-left-color: #f39c12; }
        .building-info {
            background: rgba(46,204,113,0.1);
            padding: 10px;
            border-radius: 8px;
            margin-top: 6px;
            font-size: 1.0rem !important;
            text-align: center;
            cursor: pointer;
            border: 1px solid rgba(46,204,113,0.3);
            color: #2ecc71;
        }
        .sms-card {
            background: rgba(46,204,113,0.08);
            padding: 10px;
            border-radius: 8px;
            margin-top: 6px;
        }
        .photo-preview { margin-top: 6px; text-align: center; }
        .photo-preview img { max-width: 100%; border-radius: 8px; max-height: 80px; }
        .scroll-hint {
            text-align: center;
            font-size: 1.0rem !important;
            color: #888;
            margin: 10px 0;
            animation: pulse-hint 1.5s ease-in-out infinite;
        }
        @keyframes pulse-hint {
            0%, 100% { opacity: 0.4; }
            50% { opacity: 1; }
        }

        .leaderboard-panel {
            position: fixed;
            bottom: 15px;
            right: 15px;
            width: 240px;
            background: rgba(30,30,30,0.95);
            backdrop-filter: blur(12px);
            border-radius: 10px;
            border: 1px solid rgba(243,156,18,0.2);
            z-index: 1000;
        }
        .leaderboard-header {
            padding: 10px 14px;
            border-radius: 10px 10px 0 0;
            display: flex;
            justify-content: space-between;
            cursor: pointer;
            font-size: 0.9rem;
            font-weight: 600;
            background: rgba(243,156,18,0.08);
        }
        .leaderboard-list { max-height: 150px; overflow-y: auto; padding: 8px; }
        .leaderboard-item {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 6px 10px;
            border-radius: 6px;
            margin: 4px 0;
            background: rgba(255,255,255,0.02);
            font-size: 0.85rem;
            cursor: pointer;
        }
        .leaderboard-item:hover { background: rgba(46,204,113,0.1); }
        .rank { width: 28px; font-weight: 700; color: #f39c12; }

        /* ===== CHARTS SECTION - ALWAYS VISIBLE, NO TOGGLE ===== */
        .charts-section {
            background: rgba(255, 255, 255, 0.85);
            backdrop-filter: blur(5px);
            padding: 12px 18px 18px 18px;
            margin: 8px 10px;
            border-radius: 12px;
            transition: none;
            flex-shrink: 0;
            height: 220px;
            overflow: hidden;
            display: block !important;
        }
        .charts-title {
            font-size: 1.1rem;
            font-weight: 700;
            color: #1a1a1a;
            text-align: center;
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 12px;
        }
        .charts-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px;
            margin-top: 10px;
        }
        .chart-container {
            background: rgba(255, 255, 255, 0.9);
            border-radius: 8px;
            padding: 12px;
            min-height: 130px;
        }
        .chart-container h4 { text-align: center; margin-bottom: 6px; color: #1a1a1a; font-size: 0.85rem; }
        canvas { max-height: 110px; width: 100% !important; height: auto !important; }

        .chat-panel {
            position: fixed !important;
            bottom: 20px !important;
            left: 20px !important;
            width: 360px !important;
            min-width: 220px !important;
            max-width: 500px !important;
            max-height: 480px !important;
            min-height: 220px !important;
            background: rgba(18, 25, 40, 0.95) !important;
            backdrop-filter: blur(12px) !important;
            border-radius: 18px !important;
            border: 1px solid rgba(0, 255, 200, 0.25) !important;
            box-shadow: 0 0 25px rgba(0, 255, 200, 0.12), 0 0 50px rgba(0, 255, 200, 0.06) !important;
            animation: pulseGlowChat 2.8s ease-in-out infinite alternate !important;
            cursor: grab !important;
            z-index: 9999 !important;
            display: flex !important;
            flex-direction: column !important;
            overflow: hidden !important;
            resize: both !important;
        }
        .chat-panel:hover { box-shadow: 0 0 35px rgba(0, 255, 200, 0.25), 0 0 70px rgba(0, 255, 200, 0.1) !important; }
        @keyframes pulseGlowChat {
            0% { box-shadow: 0 0 15px rgba(0,255,200,0.08), 0 0 30px rgba(0,255,200,0.04); }
            100% { box-shadow: 0 0 35px rgba(0,255,200,0.25), 0 0 70px rgba(0,255,200,0.1); }
        }
        .chat-header {
            padding: 10px 18px !important;
            background: rgba(0,255,200,0.06) !important;
            border-bottom: 1px solid rgba(0,255,200,0.08) !important;
            border-radius: 18px 18px 0 0 !important;
            cursor: grab !important;
            display: flex !important;
            justify-content: space-between !important;
            align-items: center !important;
            flex-shrink: 0 !important;
        }
        .chat-header:active { cursor: grabbing !important; }
        .chat-header h4 {
            color: #00ffcc !important;
            font-size: 1.0rem !important;
            font-weight: 700 !important;
            letter-spacing: 0.5px !important;
            display: flex !important;
            align-items: center !important;
            gap: 8px !important;
        }
        .chat-header .pulse-dot {
            display: inline-block !important;
            width: 10px !important;
            height: 10px !important;
            background: #00ffcc !important;
            border-radius: 50% !important;
            box-shadow: 0 0 12px #00ffcc !important;
            animation: blinkDotChat 1.2s infinite !important;
        }
        @keyframes blinkDotChat { 0%,100% { opacity: 1; } 50% { opacity: 0.15; } }
        .chat-header .status-badge {
            font-size: 0.8rem !important;
            background: rgba(0,255,200,0.1) !important;
            padding: 2px 12px !important;
            border-radius: 30px !important;
            color: #aaffee !important;
            border: 1px solid rgba(0,255,200,0.08) !important;
        }
        .chat-messages {
            flex: 1 !important;
            padding: 10px 14px !important;
            overflow-y: auto !important;
            max-height: 260px !important;
            min-height: 100px !important;
            display: flex !important;
            flex-direction: column !important;
            gap: 6px !important;
            background: transparent !important;
        }
        .chat-messages::-webkit-scrollbar { width: 6px; }
        .chat-messages::-webkit-scrollbar-thumb { background: #00ffcc; border-radius: 10px; }
        .chat-message {
            padding: 8px 14px !important;
            border-radius: 14px !important;
            max-width: 85% !important;
            font-size: 0.9rem !important;
            line-height: 1.4 !important;
        }
        .chat-message.own {
            align-self: flex-end !important;
            background: rgba(0,255,200,0.15) !important;
            border: 1px solid rgba(0,255,200,0.12) !important;
            color: #e0faf5 !important;
            border-bottom-right-radius: 3px !important;
        }
        .chat-message.other {
            align-self: flex-start !important;
            background: rgba(255,255,255,0.04) !important;
            border: 1px solid rgba(255,255,255,0.04) !important;
            color: #cdd9e6 !important;
            border-bottom-left-radius: 3px !important;
        }
        .chat-message .msg-username { font-weight: 700 !important; color: #00ffcc !important; font-size: 0.8rem !important; display: block !important; margin-bottom: 2px !important; }
        .chat-message .msg-time { font-size: 0.7rem !important; opacity: 0.4 !important; margin-left: 8px !important; }
        .chat-input-area {
            padding: 8px 14px 14px 14px !important;
            border-top: 1px solid rgba(0,255,200,0.06) !important;
            display: flex !important;
            gap: 8px !important;
            align-items: center !important;
            flex-shrink: 0 !important;
            background: transparent !important;
        }
        .chat-input-area input {
            flex: 1 !important;
            padding: 8px 14px !important;
            border-radius: 30px !important;
            border: 1px solid rgba(0,255,200,0.08) !important;
            background: rgba(0,0,0,0.35) !important;
            color: #fff !important;
            font-size: 0.85rem !important;
            outline: none !important;
        }
        .chat-input-area input:focus { border-color: #00ffcc !important; box-shadow: 0 0 15px rgba(0,255,200,0.06) !important; }
        .chat-input-area button {
            padding: 8px 20px !important;
            border-radius: 30px !important;
            border: none !important;
            background: #00ffcc !important;
            color: #0b0e14 !important;
            font-weight: 700 !important;
            font-size: 0.8rem !important;
            cursor: pointer !important;
            box-shadow: 0 0 15px rgba(0,255,200,0.08) !important;
            transition: 0.2s !important;
            white-space: nowrap !important;
            width: auto !important;
            margin: 0 !important;
        }
        .chat-input-area button:hover { transform: scale(1.05); box-shadow: 0 0 25px rgba(0,255,200,0.15); }
        .chat-panel::-webkit-resizer { background: #00ffcc; border-radius: 0 0 18px 0; opacity: 0.15; }

        #exportCard {
            padding: 8px 12px !important;
            margin-bottom: 8px !important;
        }
        #exportCard h3 {
            font-size: 1.0rem !important;
            margin-bottom: 6px !important;
        }
        #exportCard button {
            font-size: 0.95rem !important;
            padding: 8px 10px !important;
            margin-top: 4px !important;
        }

        .analytics-filter {
            display: flex;
            gap: 14px;
            align-items: center;
            margin-bottom: 14px;
            flex-wrap: wrap;
        }
        .analytics-filter select {
            background: #2a2a2a;
            color: white;
            padding: 8px 14px;
            border: 1px solid #3a3a3a;
            border-radius: 8px;
            font-size: 0.95rem;
            cursor: pointer;
        }
        .analytics-filter button {
            background: #2a2a2a;
            color: white;
            border: 1px solid #3a3a3a;
            padding: 8px 14px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.95rem;
            width: auto;
            margin: 0;
        }
        .analytics-filter button:hover {
            background: #3a3a3a;
        }

        #analyticsTab {
            padding: 14px 24px;
            overflow-y: auto;
            height: 100%;
        }
        #analyticsTab .stat-card .stat-value {
            font-size: 1.8rem !important;
        }

        @media (max-width: 1000px) {
            .sidebar {
                width: 100%;
                max-height: 70vh !important;
                height: auto !important;
                border-right: none;
                border-bottom: 1px solid var(--border-color);
            }
            .sidebar.collapsed {
                max-height: 0;
                padding: 0;
                border-bottom: none;
            }
            .right-panel { height: 70vh; }
            .charts-grid { grid-template-columns: 1fr; }
            .kpi-row { grid-template-columns: repeat(2,1fr); }
            .chat-panel { width: 300px !important; }
            .controls-right { flex-wrap: wrap; justify-content: flex-end; }
            .system-bar { height: auto !important; min-height: 56px !important; padding: 6px 16px !important; }
            .brand-center { order: 1; width: 100%; }
            .controls-right { order: 2; justify-content: center; flex-wrap: wrap; }
        }
        @media (max-width: 600px) {
            .sidebar { max-height: 60vh !important; }
            .right-panel { height: 60vh; }
            .chat-panel { width: 260px !important; left: 10px !important; bottom: 10px !important; }
            .controls-right { gap: 2px; }
            .sync-btn, .logout-btn, .lang-dropdown, .status-badge, .role-badge {
                font-size: 0.7rem !important;
                min-width: 40px !important;
                padding: 2px 8px !important;
                height: 28px !important;
            }
            .charts-section { height: 180px; }
            .charts-grid { grid-template-columns: 1fr; gap: 8px; }
            .chart-container { min-height: 100px; }
        }
    </style>
</head>
<body>
<div class="system-bar">
    <div class="brand-left"></div>
    <div class="brand-center">
        <h1>🌍 UNDP <span>ImpactMapper</span></h1>
        <p>Command Center | Live Intelligence</p>
    </div>
    <div class="controls-right">
        <select id="languageSelect" class="lang-dropdown">
            <option value="en">🇬🇧 EN</option>
            <option value="es">🇪🇸 ES</option>
            <option value="fr">🇫🇷 FR</option>
            <option value="pt">🇵🇹 PT</option>
            <option value="ar">🇸🇦 AR</option>
            <option value="zh">🇨🇳 中文</option>
        </select>
        <div id="connectionStatus" class="status-badge status-online"><i class="fas fa-circle"></i> Online</div>
        <button class="sync-btn" onclick="forceSync()"><i class="fas fa-sync-alt"></i> Sync</button>
        <span id="userRoleBadge" class="role-badge"></span>
        <button class="sync-btn" id="toggleSidebarBtn" title="Toggle Report Panel"><i class="fas fa-chevron-left"></i></button>
        <button id="exportCSVBtn" class="sync-btn" onclick="exportCSV()" style="display:none;" title="Export CSV"><i class="fas fa-file-csv"></i> CSV</button>
        <button id="exportGeoJSONBtn" class="sync-btn" onclick="exportGeoJSON()" style="display:none;" title="Export GeoJSON"><i class="fas fa-map"></i> GeoJSON</button>
        <a href="/" class="logout-btn"><i class="fas fa-sign-out-alt"></i> Logout</a>
    </div>
</div>
<div class="tabs-container">
    <button class="tab-btn active" onclick="switchTab('command')" id="tabCommandBtn"><i class="fas fa-map-marked-alt"></i> Command Center</button>
    <button class="tab-btn" onclick="switchTab('analytics')" id="tabAnalyticsBtn" style="display:none;"><i class="fas fa-chart-line"></i> Analytics Dashboard</button>
</div>

<div id="commandTab" class="tab-content active">
    <div class="kpi-row">
        <div class="kpi-card"><div class="kpi-header"><span>Active Cases</span><i class="fas fa-chart-line kpi-icon"></i></div><div class="kpi-value" id="activeCases">0</div><div class="progress-bar"><div class="progress-fill" id="capacityBar" style="width:0%"></div></div><div class="pill-group"><span class="pill pill-red">Critical: <span id="criticalCount">0</span></span><span class="pill pill-yellow">High: <span id="highCount">0</span></span></div></div>
        <div class="kpi-card"><div class="kpi-header"><span>Resources Deployed</span><i class="fas fa-truck-medical kpi-icon"></i></div><div class="kpi-value" id="resourcesDeployed">0</div><div class="progress-bar"><div class="progress-fill" id="resourceBar" style="width:0%"></div></div><div class="pill-group"><span class="pill pill-green">Deployed: <span id="deployedCount">0</span></span><span class="pill pill-grey">Standby: <span id="standbyCount">0</span></span></div></div>
        <div class="kpi-card"><div class="kpi-header"><span>Volunteers</span><i class="fas fa-users kpi-icon"></i></div><div class="kpi-value" id="totalVolunteers">0</div><div class="pill-group"><span class="pill pill-green">Active: <span id="activeVolunteersCount">0</span></span><span class="pill pill-yellow">Standby: <span id="standbyVolunteers">0</span></span><span class="pill pill-grey">Offline: <span id="offlineVolunteers">0</span></span></div></div>
        <div class="kpi-card" id="pendingTasksCard"><div class="kpi-header"><span>Pending Tasks</span><i class="fas fa-tasks kpi-icon"></i></div><div class="kpi-value warning" id="pendingTasks">0</div><div class="pill-group"><span class="pill pill-red">Urgent: <span id="urgentTasks">0</span></span></div></div>
    </div>
    <div class="main-layout">
        <div class="sidebar" id="sidebarPanel">
            <!-- ===== REPORT DAMAGE CARD ===== -->
            <div class="card">
                <h3><i class="fas fa-camera"></i> <span id="reportTitle">Report Damage</span></h3>
                <p id="clickHint" style="font-size:1.0rem; color:#2ecc71;">🏢 Click on any building on the map to select it!</p>
                <div id="selectedBuildingInfo" class="building-info" style="display:none;"></div>
                <select id="damageLevel">
                    <option value="minimal">🏠 Minimal/No Damage</option>
                    <option value="partial">⚠️ Partially Damaged</option>
                    <option value="complete">💀 Completely Damaged</option>
                </select>
                <select id="infrastructureType">
                    <option value="residential">🏘️ Residential</option>
                    <option value="commercial">🏪 Commercial</option>
                    <option value="government">🏛️ Government</option>
                    <option value="utility">💡 Utility</option>
                    <option value="transport">🛣️ Transport</option>
                    <option value="community">🏥 Community</option>
                    <option value="public">🏟️ Public</option>
                </select>
                <input type="text" id="buildingName" placeholder="Building Name">
                <select id="crisisNature">
                    <option value="earthquake">🌋 Earthquake</option>
                    <option value="flood">💧 Flood</option>
                    <option value="tsunami">🌊 Tsunami</option>
                    <option value="hurricane">🌀 Hurricane</option>
                    <option value="wildfire">🔥 Wildfire</option>
                    <option value="explosion">💥 Explosion</option>
                    <option value="conflict">⚔️ Conflict</option>
                </select>
                <select id="debris">
                    <option value="yes">Yes - Requires clearing</option>
                    <option value="no">No debris</option>
                </select>
                <div style="display:flex; gap:8px;">
                    <input type="text" id="lat" placeholder="Latitude" readonly style="flex:1;">
                    <input type="text" id="lng" placeholder="Longitude" readonly style="flex:1;">
                </div>
                <button class="btn-location" onclick="shareLocation()" style="font-size:1.1rem; padding:12px;">
                    <i class="fas fa-location-dot"></i> <span id="gpsLabel">Use My GPS</span>
                </button>
                <input type="text" id="textLocation" placeholder="Describe location (e.g., near school)">
                <textarea id="notes" rows="2" placeholder="Additional notes about damage"></textarea>

                <div style="margin-top:8px;">
                    <label style="color:#aaa; font-size:1.0rem;"><i class="fas fa-image"></i> Upload Photo:</label>
                    <input type="file" id="photo" accept="image/*" capture="environment" style="padding:8px; background:#2a2a2a; border:1px solid #444; border-radius:8px;">
                    <div id="photoPreview" class="photo-preview"></div>
                </div>

                <button id="submitBtn" onclick="submitReport()" style="font-size:1.1rem; padding:12px; background: linear-gradient(135deg, #2ecc71, #27ae60);">
                    <i class="fas fa-paper-plane"></i> <span id="submitLabel">Submit Report</span>
                </button>
                <div id="submitStatus" style="margin-top:8px; font-size:1.0rem;"></div>

                <div class="scroll-hint">↓ Scroll down for more options ↓</div>
            </div>

            <!-- ===== SMS REPORT CARD ===== -->
            <div class="card">
                <h3><i class="fas fa-sms"></i> <span id="smsTitle">SMS Report</span></h3>
                <div class="sms-card">
                    <input type="text" id="smsText" placeholder="Format: DAMAGE LAT LNG">
                    <input type="text" id="smsNumber" placeholder="Phone Number (optional)">
                    <button onclick="sendSMSReport()"><i class="fas fa-envelope"></i> <span id="smsSendLabel">Send SMS Report</span></button>
                </div>
                <div id="smsStatus" style="margin-top:8px; font-size:1.0rem;"></div>
            </div>

            <!-- ===== RECENT REPORTS ===== -->
            <div class="card">
                <h3><i class="fas fa-list"></i> <span id="recentTitle">Recent Reports</span></h3>
                <div id="reportsList" class="reports-list">Loading...</div>
            </div>

            <!-- ===== EXPORT DATA (ADMIN ONLY) ===== -->
            <div class="card" id="exportCard">
                <h3><i class="fas fa-download"></i> <span id="exportTitle">Export Data (Admin Only)</span></h3>
                <div style="display:flex; gap:8px;">
                    <button id="exportCSVCardBtn" onclick="exportCSV()" style="flex:1;"><i class="fas fa-file-excel"></i> <span id="csvLabel">CSV</span></button>
                    <button id="exportGeoJSONCardBtn" onclick="exportGeoJSON()" style="flex:1;"><i class="fas fa-map"></i> <span id="geojsonLabel">GeoJSON</span></button>
                </div>
            </div>
        </div>

        <div class="right-panel">
            <div class="map-container"><div id="map"></div></div>
            <!-- ===== CHARTS SECTION - ALWAYS VISIBLE ===== -->
            <div class="charts-section" id="chartsSection">
                <div class="charts-title">
                    📊 DAMAGE ANALYTICS DASHBOARD
                </div>
                <div class="charts-grid">
                    <div class="chart-container"><h4>🥧 Damage Distribution</h4><canvas id="pieChart"></canvas></div>
                    <div class="chart-container"><h4>📊 Damage by Infrastructure</h4><canvas id="barChart"></canvas></div>
                    <div class="chart-container"><h4>📈 Damage Trend</h4><canvas id="lineChart"></canvas></div>
                </div>
            </div>
        </div>
    </div>
</div>

<div id="analyticsTab" class="tab-content">
    <div style="padding:12px 20px; overflow-y:auto; height:100%;">
        <div class="analytics-filter">
            <label style="color:#aaa; font-size:0.95rem;"><i class="fas fa-calendar-alt"></i> Date Range:</label>
            <select id="analyticsDays" onchange="loadAdminStats()">
                <option value="7">Last 7 days</option>
                <option value="30" selected>Last 30 days</option>
                <option value="90">Last 90 days</option>
                <option value="0">All time</option>
            </select>
            <button onclick="loadAdminStats()"><i class="fas fa-sync-alt"></i> Refresh</button>
        </div>
        <div class="stats-grid" style="display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:14px; margin-bottom:14px;">
            <div class="stat-card" style="background:#1e1e1e; border-radius:10px; padding:16px;"><div class="stat-value" id="totalReports" style="font-size:1.8rem; font-weight:800; color:#2ecc71;">-</div><div style="font-size:0.85rem; color:#a0a0a0;">Total Reports</div></div>
            <div class="stat-card" style="background:#1e1e1e; border-radius:10px; padding:16px;"><div class="stat-value" id="totalUsers" style="font-size:1.8rem; font-weight:800; color:#2ecc71;">-</div><div style="font-size:0.85rem; color:#a0a0a0;">Active Users</div></div>
            <div class="stat-card" style="background:#1e1e1e; border-radius:10px; padding:16px;"><div class="stat-value" id="avgResponse" style="font-size:1.8rem; font-weight:800; color:#2ecc71;">-</div><div style="font-size:0.85rem; color:#a0a0a0;">Avg Response (min)</div></div>
            <div class="stat-card" style="background:#1e1e1e; border-radius:10px; padding:16px;"><div class="stat-value" id="topReporter" style="font-size:1.8rem; font-weight:800; color:#2ecc71;">-</div><div style="font-size:0.85rem; color:#a0a0a0;">Top Reporter</div></div>
        </div>
        <div style="display:grid; grid-template-columns:repeat(auto-fit,minmax(300px,1fr)); gap:14px;">
            <div style="background:#1e1e1e; border-radius:10px; padding:16px;"><h3 style="color:#2ecc71; font-size:1.0rem;">📈 Daily Report Trend</h3><canvas id="trendChart"></canvas></div>
            <div style="background:#1e1e1e; border-radius:10px; padding:16px;"><h3 style="color:#2ecc71; font-size:1.0rem;">🏗️ Damage Distribution</h3><canvas id="damageChart"></canvas></div>
            <div style="background:#1e1e1e; border-radius:10px; padding:16px;"><h3 style="color:#2ecc71; font-size:1.0rem;">🏘️ Reports by Infrastructure</h3><canvas id="infraChart"></canvas></div>
            <div style="background:#1e1e1e; border-radius:10px; padding:16px;"><h3 style="color:#2ecc71; font-size:1.0rem;">🌋 Reports by Crisis Type</h3><canvas id="crisisChart"></canvas></div>
            <div style="background:#1e1e1e; border-radius:10px; padding:16px; overflow-x:auto;"><h3 style="color:#2ecc71; font-size:1.0rem;">🏆 Top Reporters</h3><table id="reportersTable" style="width:100%; font-size:0.9rem;"><thead><tr><th>Rank</th><th>Username</th><th>Reports</th></tr></thead><tbody></tbody></table></div>
            <div style="background:#1e1e1e; border-radius:10px; padding:16px; overflow-x:auto;"><h3 style="color:#2ecc71; font-size:1.0rem;">👥 Users by Role</h3><table id="rolesTable" style="width:100%; font-size:0.9rem;"><thead><tr><th>Role</th><th>Count</th></tr></thead><tbody></tbody></table></div>
        </div>
    </div>
</div>

<div class="leaderboard-panel"><div class="leaderboard-header" onclick="toggleLeaderboard()"><span><i class="fas fa-trophy"></i> Leaderboard</span><span>🏆</span></div><div id="leaderboardList" class="leaderboard-list">Loading...</div></div>

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
let translations = {};
let offlineQueue = [];
let isAdmin = false;
let pieChart, barChart, lineChart, damageChart, trendChart, infraChart, crisisChart;
let currentMarker = null;

function loadOfflineQueue() { const saved = localStorage.getItem('offline_reports'); if (saved) offlineQueue = JSON.parse(saved); updateOfflineUI(); }
function saveOfflineQueue() { localStorage.setItem('offline_reports', JSON.stringify(offlineQueue)); updateOfflineUI(); }
function updateOfflineUI() { document.getElementById('pendingTasks').innerHTML = offlineQueue.length; }
loadOfflineQueue();

function switchTab(tab) {
    if (tab === 'command') {
        document.getElementById('commandTab').classList.add('active');
        document.getElementById('analyticsTab').classList.remove('active');
        document.getElementById('tabCommandBtn').classList.add('active');
        document.getElementById('tabAnalyticsBtn').classList.remove('active');
        setTimeout(() => { if (map) map.invalidateSize(); }, 100);
    } else {
        document.getElementById('commandTab').classList.remove('active');
        document.getElementById('analyticsTab').classList.add('active');
        document.getElementById('tabCommandBtn').classList.remove('active');
        document.getElementById('tabAnalyticsBtn').classList.add('active');
        loadAdminStats();
    }
}

async function loadAdminStats() {
    const days = document.getElementById('analyticsDays').value;
    try {
        const res = await fetch(`/api/admin/stats?days=${days}`);
        if (!res.ok) throw new Error('API error: ' + res.status);
        const data = await res.json();
        console.log('Analytics data:', data);

        document.getElementById('totalReports').innerHTML = data.total_reports || 0;
        document.getElementById('totalUsers').innerHTML = data.total_users || 0;
        document.getElementById('avgResponse').innerHTML = data.avg_response_minutes || 'N/A';
        document.getElementById('topReporter').innerHTML = data.top_reporters[0]?.username || '-';

        const safeDestroy = (chart) => { if (chart) { chart.destroy(); } };

        safeDestroy(trendChart);
        const trendLabels = data.daily_trend.map(d => d.date.slice(5));
        const trendData = data.daily_trend.map(d => d.count);
        trendChart = new Chart(document.getElementById('trendChart'), {
            type: 'line',
            data: {
                labels: trendLabels.length ? trendLabels : ['No Data'],
                datasets: [{
                    label: 'Reports',
                    data: trendData.length ? trendData : [0],
                    borderColor: '#2ecc71',
                    fill: true,
                    backgroundColor: 'rgba(46,204,113,0.1)',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: { legend: { labels: { color: '#e0e0e0' } } },
                scales: { x: { ticks: { color: '#aaa' } }, y: { ticks: { color: '#aaa' }, beginAtZero: true } }
            }
        });

        safeDestroy(damageChart);
        const damageLabels = data.by_damage.map(d => d.level);
        const damageData = data.by_damage.map(d => d.count);
        damageChart = new Chart(document.getElementById('damageChart'), {
            type: 'doughnut',
            data: {
                labels: damageLabels.length ? damageLabels : ['No Data'],
                datasets: [{
                    data: damageData.length ? damageData : [1],
                    backgroundColor: ['#e74c3c', '#f39c12', '#2ecc71', '#3498db']
                }]
            },
            options: {
                responsive: true,
                plugins: { legend: { labels: { color: '#e0e0e0' } } }
            }
        });

        safeDestroy(infraChart);
        const infraLabels = data.by_infrastructure.map(d => d.type);
        const infraData = data.by_infrastructure.map(d => d.count);
        infraChart = new Chart(document.getElementById('infraChart'), {
            type: 'bar',
            data: {
                labels: infraLabels.length ? infraLabels : ['No Data'],
                datasets: [{
                    label: 'Reports',
                    data: infraData.length ? infraData : [0],
                    backgroundColor: '#2ecc71',
                    borderRadius: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: { legend: { labels: { color: '#e0e0e0' } } },
                scales: { x: { ticks: { color: '#aaa' } }, y: { ticks: { color: '#aaa' }, beginAtZero: true } }
            }
        });

        safeDestroy(crisisChart);
        const crisisLabels = data.by_crisis.map(d => d.crisis);
        const crisisData = data.by_crisis.map(d => d.count);
        crisisChart = new Chart(document.getElementById('crisisChart'), {
            type: 'bar',
            data: {
                labels: crisisLabels.length ? crisisLabels : ['No Data'],
                datasets: [{
                    label: 'Reports',
                    data: crisisData.length ? crisisData : [0],
                    backgroundColor: '#3498db',
                    borderRadius: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: { legend: { labels: { color: '#e0e0e0' } } },
                scales: { x: { ticks: { color: '#aaa' } }, y: { ticks: { color: '#aaa' }, beginAtZero: true } }
            }
        });

        document.getElementById('reportersTable').querySelector('tbody').innerHTML =
            data.top_reporters.map((r,i) =>
                `<tr><td style="padding:8px;">${i+1}</td><td style="padding:8px;">${r.username}</td><td style="padding:8px;">${r.reports}</td></tr>`
            ).join('') || '<tr><td colspan="3" style="text-align:center;color:#666;">No data</td></tr>';
        document.getElementById('rolesTable').querySelector('tbody').innerHTML =
            data.users_by_role.map(r =>
                `<tr><td style="padding:8px;">${r.role}</td><td style="padding:8px;">${r.count}</td></tr>`
            ).join('') || '<tr><td colspan="2" style="text-align:center;color:#666;">No data</td></tr>';

    } catch(e) {
        console.error('Error loading analytics:', e);
        document.getElementById('totalReports').innerHTML = '⚠️ Error';
    }
}

function updateCommandCenterCharts() {
    const damageCounts = { minimal:0, partial:0, complete:0 };
    for(let r of reports) { if(r.damage_level==='minimal') damageCounts.minimal++; else if(r.damage_level==='partial') damageCounts.partial++; else if(r.damage_level==='complete') damageCounts.complete++; }
    if(pieChart) pieChart.destroy();
    pieChart = new Chart(document.getElementById('pieChart'), {
        type:'pie', data:{ labels:['Minimal','Partial','Complete'], datasets:[{ data:[damageCounts.minimal,damageCounts.partial,damageCounts.complete], backgroundColor:['#2ecc71','#f39c12','#e74c3c'] }] },
        options:{ responsive:true, maintainAspectRatio:true, plugins:{ legend:{ position:'bottom', labels:{ font:{ size:10, weight:'bold' }, color:'#000' } } } }
    });
    const infraCounts = {}; for(let r of reports) { let t=r.infrastructure_type||'Unknown'; infraCounts[t]=(infraCounts[t]||0)+1; }
    const infraLabels = Object.keys(infraCounts).slice(0,6);
    const infraData = infraLabels.map(l=>infraCounts[l]);
    if(barChart) barChart.destroy();
    barChart = new Chart(document.getElementById('barChart'), {
        type:'bar', data:{ labels:infraLabels, datasets:[{ label:'Reports', data:infraData, backgroundColor:'#3498db', borderRadius:6 }] },
        options:{ responsive:true, scales:{ y:{ beginAtZero:true, title:{ display:true, text:'Count', color:'#000', font:{size:10} }, ticks:{ color:'#000', font:{size:10} } }, x:{ ticks:{ color:'#000', font:{size:10} } } }, plugins:{ legend:{ labels:{ color:'#000', font:{size:10} } } } }
    });
    const dailyCounts = {}; for(let r of reports) { let d = new Date(r.timestamp).toISOString().split('T')[0]; dailyCounts[d]=(dailyCounts[d]||0)+1; }
    const last7Days = []; for(let i=6;i>=0;i--) { let d=new Date(); d.setDate(d.getDate()-i); last7Days.push(d.toISOString().split('T')[0]); }
    const lineData = last7Days.map(d=>dailyCounts[d]||0);
    if(lineChart) lineChart.destroy();
    lineChart = new Chart(document.getElementById('lineChart'), {
        type:'line', data:{ labels:last7Days.map(d=>d.slice(5)), datasets:[{ label:'Reports per Day', data:lineData, borderColor:'#2ecc71', backgroundColor:'rgba(46,204,113,0.1)', fill:true, tension:0.4 }] },
        options:{ responsive:true, scales:{ y:{ beginAtZero:true, title:{ display:true, text:'Count', color:'#000', font:{size:10} }, ticks:{ color:'#000', font:{size:10} } }, x:{ ticks:{ color:'#000', font:{size:10} } } }, plugins:{ legend:{ labels:{ color:'#000', font:{size:10} } } } }
    });

    setTimeout(() => {
        if (pieChart) pieChart.resize();
        if (barChart) barChart.resize();
        if (lineChart) lineChart.resize();
    }, 100);
}

async function setLanguage(lang) {
    currentLang = lang; localStorage.setItem('language', lang);
    try { const res = await fetch(`/api/lang/${lang}`); const data = await res.json(); translations = data; updateUITexts(); } catch(e) { console.error(e); }
}
function updateUITexts() {
    document.getElementById('reportTitle').innerText = translations.report_damage || 'Report Damage';
    document.getElementById('gpsLabel').innerText = translations.gps_location || 'Use My GPS';
    document.getElementById('submitLabel').innerText = translations.submit || 'Submit Report';
    document.getElementById('smsTitle').innerText = translations.sms_report || 'SMS Report';
    document.getElementById('smsSendLabel').innerText = translations.sms_send || 'Send SMS Report';
    document.getElementById('recentTitle').innerText = translations.recent_reports || 'Recent Reports';
    document.getElementById('exportTitle').innerText = translations.export_data || 'Export Data (Admin Only)';
    document.getElementById('csvLabel').innerText = translations.export_csv || 'Export CSV';
    document.getElementById('geojsonLabel').innerText = translations.export_geojson || 'Export GeoJSON';
    document.getElementById('clickHint').innerHTML = translations.click_building || '🏢 Click on any building on the map to select it!';
    document.getElementById('chatInput').placeholder = translations.type_message || 'Type a message...';
}
document.getElementById('languageSelect').value = currentLang;
document.getElementById('languageSelect').addEventListener('change', (e) => setLanguage(e.target.value));
setLanguage(currentLang);

function initMap() {
    const container = document.getElementById('map');
    if (!container) return;
    if (container.offsetHeight === 0) container.style.height = '400px';
    map = L.map('map', { center: [20, 0], zoom: 2, zoomControl: true, fadeAnimation: true });
    map.attributionControl.setPrefix('');
    const osmLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
        maxZoom: 19,
    });
    const osmFallback = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '&copy; OSM', maxZoom: 19 });
    const cycleLayer = L.tileLayer('https://{s}.tile-cyclosm.openstreetmap.fr/cyclosm/{z}/{x}/{y}.png', { attribution: '&copy; OSM | CycleOSM', maxZoom: 19 });
    const humanitarianLayer = L.tileLayer('https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png', { attribution: '&copy; OSM | Humanitarian', maxZoom: 19 });
    osmLayer.addTo(map);
    osmLayer.on('tileerror', function() { map.removeLayer(osmLayer); osmFallback.addTo(map); });
    L.control.layers({ "Standard": osmLayer, "Cycle": cycleLayer, "Humanitarian": humanitarianLayer }).addTo(map);
    setTimeout(() => map.invalidateSize(), 300);
    window.addEventListener('resize', () => map.invalidateSize());
    map.on('click', async function(e) {
        let lat = e.latlng.lat, lng = e.latlng.lng;
        document.getElementById('lat').value = lat.toFixed(6);
        document.getElementById('lng').value = lng.toFixed(6);
        try {
            let res = await fetch(`/api/building/${lat}/${lng}`);
            let building = await res.json();
            if(building && building.name) {
                document.getElementById('buildingName').value = building.name;
                document.getElementById('selectedBuildingInfo').style.display = 'block';
                document.getElementById('selectedBuildingInfo').innerHTML = `🏢 Selected: ${building.name}<br>📍 ${building.address || 'Address unknown'}`;
            } else {
                document.getElementById('selectedBuildingInfo').style.display = 'none';
            }
        } catch(err) { console.error(err); }
        if(currentMarker) map.removeLayer(currentMarker);
        currentMarker = L.marker([lat, lng]).addTo(map).bindPopup('Selected location').openPopup();
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
        if(data.status==='success') { statusDiv.innerHTML = '✅ SMS report sent!'; document.getElementById('smsText').value = ''; loadReports(); }
        else { statusDiv.innerHTML = '❌ '+data.message; }
    } catch(e) { statusDiv.innerHTML = '❌ Failed to send SMS'; }
}

document.getElementById('photo').addEventListener('change', function(e) {
    let preview = document.getElementById('photoPreview');
    if(e.target.files && e.target.files[0]) {
        let reader = new FileReader();
        reader.onload = function(ev) { preview.innerHTML = `<img src="${ev.target.result}" style="max-width:100%; max-height:80px; border-radius:8px;">`; };
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
            statusDiv.innerHTML = '✅ Report submitted!';
            document.getElementById('lat').value = ''; document.getElementById('lng').value = '';
            document.getElementById('buildingName').value = ''; document.getElementById('textLocation').value = '';
            document.getElementById('notes').value = ''; document.getElementById('photo').value = '';
            document.getElementById('photoPreview').innerHTML = '';
            if(currentMarker) map.removeLayer(currentMarker);
            loadReports();
        } else { statusDiv.innerHTML = '❌ Submission failed'; }
    } catch(e) {
        statusDiv.innerHTML = '❌ Offline – saved locally';
        offlineQueue.push({ report_uuid:Date.now().toString(), damage_level:document.getElementById('damageLevel').value, lat:document.getElementById('lat').value, lng:document.getElementById('lng').value, location_text:document.getElementById('textLocation').value, infrastructure_type:document.getElementById('infrastructureType').value, building_name:document.getElementById('buildingName').value, crisis_nature:document.getElementById('crisisNature').value, debris:document.getElementById('debris').value, notes:document.getElementById('notes').value, timestamp:new Date().toISOString(), is_offline:true });
        saveOfflineQueue(); loadReports();
    }
}

async function syncOfflineReports() {
    if(offlineQueue.length===0) return;
    try {
        let res = await fetch('/api/sync', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(offlineQueue) });
        if(res.ok) { offlineQueue = []; saveOfflineQueue(); loadReports(); showToast('Synced offline reports','success'); }
    } catch(e) { console.error(e); }
}

async function forceSync() { await syncOfflineReports(); }

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
    document.getElementById('activeCases').innerText = total;
    document.getElementById('criticalCount').innerText = critical;
    document.getElementById('highCount').innerText = high;
    document.getElementById('capacityBar').style.width = Math.min(100,(total/500)*100)+'%';
    document.getElementById('pendingTasks').innerText = offlineQueue.length;
    document.getElementById('urgentTasks').innerText = critical;
    document.getElementById('resourcesDeployed').innerText = Math.floor(total*0.7);
    document.getElementById('deployedCount').innerText = Math.floor(total*0.4);
    document.getElementById('standbyCount').innerText = Math.floor(total*0.3);
    document.getElementById('totalVolunteers').innerText = 350 + Math.floor(total/2);
    document.getElementById('activeVolunteersCount').innerText = 200 + Math.floor(total/3);
    document.getElementById('standbyVolunteers').innerText = 100 + Math.floor(total/5);
    document.getElementById('offlineVolunteers').innerText = 50;
}

function updateMapMarkers() {
    for(let m of markers) map.removeLayer(m);
    markers = [];
    for(let r of reports) {
        if(r.lat && r.lng) {
            let color = '#2ecc71';
            if(r.damage_level==='partial') color='#f39c12';
            if(r.damage_level==='complete') color='#e74c3c';
            let marker = L.circleMarker([r.lat,r.lng], { radius:8, fillColor:color, color:'#fff', weight:2, fillOpacity:0.8 }).addTo(map);
            marker.bindPopup(`<b>${r.building_name||'Building'}</b><br>Damage: ${r.damage_level}<br>${new Date(r.timestamp).toLocaleString()}`);
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
        div.className = `report-item ${r.damage_level==='complete'?'severity-critical':(r.damage_level==='partial'?'severity-high':'')}`;
        div.innerHTML = `<strong>${r.building_name||'Location'}</strong><br>${r.infrastructure_type||''} - ${r.damage_level}<br><small>${new Date(r.timestamp).toLocaleString()}</small>`;
        div.onclick = () => { if(r.lat && r.lng) map.setView([r.lat,r.lng],18); };
        container.appendChild(div);
    });
}

function updateConnectionStatus(isOnline) {
    let statusDiv = document.getElementById('connectionStatus');
    if(isOnline) { 
        statusDiv.innerHTML = '<i class="fas fa-circle"></i> Online'; 
        statusDiv.className = 'status-badge status-online'; 
    } else { 
        statusDiv.innerHTML = '<i class="fas fa-circle"></i> Offline'; 
        statusDiv.className = 'status-badge'; 
    }
}

async function loadCurrentUser() {
    try {
        let res = await fetch('/api/current_user');
        let user = await res.json();
        currentUser = user;
        document.getElementById('userRoleBadge').innerHTML = `${user.role} ${user.points} pts`;
        if(user.role === 'admin') { 
            document.getElementById('exportCard').style.display = 'block'; 
            document.getElementById('tabAnalyticsBtn').style.display = 'inline-block'; 
            document.getElementById('exportCSVBtn').style.display = 'inline-flex';
            document.getElementById('exportGeoJSONBtn').style.display = 'inline-flex';
            isAdmin=true; 
            setTimeout(() => loadAdminStats(), 500);
        } else { 
            document.getElementById('exportCard').style.display = 'none'; 
            document.getElementById('exportCSVBtn').style.display = 'none';
            document.getElementById('exportGeoJSONBtn').style.display = 'none';
            isAdmin=false; 
        }
        loadReports();
        loadLeaderboard();
        loadStats();
    } catch(e) { console.error('Auth error',e); }
}

// ============================================================
// FIXED: Leaderboard with try-catch (silences fetch error)
// ============================================================
async function loadLeaderboard() {
    try {
        let res = await fetch('/api/leaderboard');
        if (!res.ok) throw new Error('HTTP ' + res.status);
        let leaders = await res.json();
        let container = document.getElementById('leaderboardList');
        if (!container) return;
        container.innerHTML = leaders.map((l,i) => 
            `<div class="leaderboard-item"><span class="rank">${i+1}</span><span>${l.username}</span><span>🏆 ${l.points}</span></div>`
        ).join('');
    } catch(e) {
        console.warn('Leaderboard unavailable:', e.message);
        let container = document.getElementById('leaderboardList');
        if (container) container.innerHTML = '⚠️ Leaderboard unavailable';
    }
}

async function loadStats() { try { let res=await fetch('/api/stats'); let stats=await res.json(); document.getElementById('totalReports').innerText=stats.total_reports; document.getElementById('todayReports').innerText=stats.today_reports; document.getElementById('pendingSync').innerText=stats.pending_sync; } catch(e){} }

function exportCSV() { window.open('/api/reports/csv','_blank'); }

async function exportGeoJSON() {
    try { let res=await fetch('/api/reports/geojson'); let data=await res.json(); let blob=new Blob([JSON.stringify(data)],{type:'application/json'}); let url=URL.createObjectURL(blob); let a=document.createElement('a'); a.href=url; a.download='reports.geojson'; a.click(); URL.revokeObjectURL(url); } catch(e){ alert('Export failed'); }
}

function showToast(msg,type) { alert(msg); }

function toggleLeaderboard() { let el=document.querySelector('.leaderboard-list'); if(el) el.style.display=el.style.display==='none'?'block':'none'; }

document.getElementById('pendingTasksCard').addEventListener('click', function() {
    let pendingCount = offlineQueue.length;
    if(pendingCount === 0) { alert('No pending tasks.'); return; }
    let msg = 'Pending reports to sync:\n';
    offlineQueue.forEach((r,i) => { msg += `${i+1}. ${r.building_name || 'Unnamed'} - ${r.damage_level} (${new Date(r.timestamp).toLocaleString()})\n`; });
    msg += '\nClick OK to sync now.';
    if(confirm(msg)) forceSync();
});

let urgentElement = document.getElementById('urgentTasks');
if(urgentElement && urgentElement.parentElement && urgentElement.parentElement.parentElement) {
    urgentElement.parentElement.parentElement.addEventListener('click', function() {
        let criticalReports = reports.filter(r => r.damage_level === 'complete');
        if(criticalReports.length === 0) { alert('No urgent (complete damage) reports.'); return; }
        for(let m of markers) map.removeLayer(m);
        markers = [];
        for(let r of criticalReports) {
            if(r.lat && r.lng) {
                let marker = L.circleMarker([r.lat, r.lng], { radius:10, fillColor:'#e74c3c', color:'#fff', weight:2, fillOpacity:0.9 }).addTo(map);
                marker.bindPopup(`<b>URGENT</b><br>${r.building_name || 'Building'}<br>Damage: ${r.damage_level}`);
                markers.push(marker);
            }
        }
        if(criticalReports.length > 0) map.setView([criticalReports[0].lat, criticalReports[0].lng], 14);
    });
}

window.addEventListener('online', () => { updateConnectionStatus(true); syncOfflineReports(); loadReports(); showToast('Back online!'); updateKPIs(); updateCommandCenterCharts(); });
window.addEventListener('offline', () => { updateConnectionStatus(false); showToast('Offline – reports saved locally.'); });

document.addEventListener('DOMContentLoaded', function() {
    initMap();
    loadCurrentUser();
    loadReports();
    loadLeaderboard();
    loadStats();
    setInterval(() => loadReports(), 30000);
    setInterval(() => updateKPIs(), 10000);
    setInterval(() => updateCommandCenterCharts(), 15000);
    setInterval(() => loadLeaderboard(), 10000);
});

// ===== CHAT =====
function addChatMessage(username, message, isOwn = false) {
    const container = document.getElementById('chatMessages');
    if (!container) return;
    const div = document.createElement('div');
    div.className = `chat-message ${isOwn ? 'own' : 'other'}`;
    const time = new Date().toLocaleTimeString();
    div.innerHTML = `<span class="msg-username">${username} <span class="msg-time">${time}</span></span>${message}`;
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
if (chatInput) chatInput.addEventListener('keydown', function(e) {
    if (e.key === 'Enter') sendLocalChatMessage();
});

// ===== DRAG CHAT =====
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
        if (isDragging) {
            isDragging = false;
            container.style.cursor = 'grab';
            header.style.cursor = 'grab';
        }
    });
})();

// ===== TOGGLE SIDEBAR (KEPT, CHARTS TOGGLE REMOVED) =====
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
