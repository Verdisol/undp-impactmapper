from fastapi import FastAPI, Form, UploadFile, File, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import uvicorn
import os
import json
import hashlib
import uuid
import asyncio
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import asyncpg
from contextlib import asynccontextmanager

# ============================================
# APP INITIALIZATION
# ============================================

# Use /tmp for writable storage on Vercel
PHOTOS_DIR = "/tmp/photos"
EXPORTS_DIR = "/tmp/exports"
os.makedirs(PHOTOS_DIR, exist_ok=True)
os.makedirs(EXPORTS_DIR, exist_ok=True)

security = HTTPBasic()

# Database connection pool
db_pool = None
DATABASE_URL = os.environ.get("DATABASE_URL")

async def init_db():
    global db_pool
    db_pool = await asyncpg.create_pool(DATABASE_URL)
    async with db_pool.acquire() as conn:
        # Reports table
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
        # Users table
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
        # Insert default users
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

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    if db_pool:
        await db_pool.close()

# Single FastAPI instance with lifespan, title, version
app = FastAPI(title="UNDP ImpactMapper", version="27.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# WEBSOCKET MANAGER (unchanged)
# ============================================

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[WebSocket, Dict] = {}
        self.user_locations: Dict[str, Dict] = {}
        self.chat_messages: List[Dict] = []
        
    async def connect(self, websocket: WebSocket, user_info: dict):
        await websocket.accept()
        self.active_connections[websocket] = user_info
        await self.broadcast_presence()
        await self.broadcast_live_contributors()
        
    def disconnect(self, websocket: WebSocket):
        username = self.active_connections.get(websocket, {}).get("username")
        if username and username in self.user_locations:
            del self.user_locations[username]
        if websocket in self.active_connections:
            del self.active_connections[websocket]
        asyncio.create_task(self.broadcast_presence())
        asyncio.create_task(self.broadcast_live_contributors())
        
    async def update_user_location(self, username: str, lat: float, lng: float):
        self.user_locations[username] = {"lat": lat, "lng": lng, "updated_at": datetime.now().isoformat()}
        await self.broadcast_live_contributors()
        
    async def broadcast_presence(self):
        presence_list = []
        for ws, info in self.active_connections.items():
            presence_list.append({
                "username": info.get("username", "Anonymous"),
                "role": info.get("role", "viewer"),
                "color": info.get("color", "#2ecc71"),
                "avatar": info.get("avatar", "🌍"),
                "badge": info.get("badge", "Citizen Reporter"),
                "points": info.get("points", 0)
            })
        await self.broadcast({"type": "presence", "users": presence_list, "count": len(presence_list)})
        
    async def broadcast_live_contributors(self):
        contributors = []
        for username, location in self.user_locations.items():
            user_info = None
            for ws, info in self.active_connections.items():
                if info.get("username") == username:
                    user_info = info
                    break
            if user_info and location:
                contributors.append({
                    "username": username, "role": user_info.get("role", "viewer"),
                    "color": user_info.get("color", "#2ecc71"), "avatar": user_info.get("avatar", "🌍"),
                    "badge": user_info.get("badge", "Citizen Reporter"), "points": user_info.get("points", 0),
                    "lat": location["lat"], "lng": location["lng"]
                })
        await self.broadcast({"type": "live_contributors", "contributors": contributors})
        
    async def broadcast_chat(self, message: str, sender_ws: WebSocket):
        if sender_ws in self.active_connections:
            chat_msg = {
                "username": self.active_connections[sender_ws].get("username", "Anonymous"),
                "role": self.active_connections[sender_ws].get("role", "viewer"),
                "message": message, "timestamp": datetime.now().isoformat(),
                "color": self.active_connections[sender_ws].get("color", "#2ecc71"),
                "badge": self.active_connections[sender_ws].get("badge", "Citizen Reporter")
            }
            self.chat_messages.append(chat_msg)
            if len(self.chat_messages) > 200:
                self.chat_messages = self.chat_messages[-200:]
            await self.broadcast({"type": "chat", "data": chat_msg})
            
    async def broadcast_report(self, report_data: dict):
        await self.broadcast({"type": "new_report", "data": report_data})
            
    async def broadcast(self, message: dict):
        for connection in list(self.active_connections.keys()):
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()

# ============================================
# OSM BUILDING LOOKUP (unchanged)
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
# ASYNC DATABASE FUNCTIONS
# ============================================

async def save_report(report_uuid: str, building_id: str, building_osm_id: str, building_name: str, building_address: str,
                damage_level: str, lat: float, lng: float, location_text: str, photo_path: str,
                infrastructure_type: str, crisis_nature: str, debris: str, notes: str, username: str, synced: int = 1, sms_number: str = ""):
    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO reports (report_uuid, building_id, building_osm_id, building_name, building_address,
                                damage_level, version, lat, lng, location_text, photo_path,
                                infrastructure_type, crisis_nature, debris, notes, username, timestamp, is_current, synced, sms_number)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20)
        """, report_uuid, building_id, building_osm_id, building_name, building_address,
           damage_level, 1, lat, lng, location_text, photo_path,
           infrastructure_type, crisis_nature, debris, notes, username, datetime.now().isoformat(), 1, synced, sms_number)

async def get_reports_db(limit: int = 200):
    async with db_pool.acquire() as conn:
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

async def get_leaderboard_db(limit: int = 15):
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("SELECT username, points, verified_reports, badge_level, avatar, color FROM users ORDER BY points DESC LIMIT $1", limit)
        return [{"username": r[0], "points": r[1], "verified_reports": r[2], "badge": r[3], "avatar": r[4], "color": r[5]} for r in rows]

async def update_user_points(username: str, points_increment: int = 10):
    async with db_pool.acquire() as conn:
        await conn.execute("UPDATE users SET points = points + $1, verified_reports = verified_reports + 1 WHERE username = $2", points_increment, username)

# ============================================
# AUTHENTICATION (unchanged)
# ============================================

async def verify_user(credentials: HTTPBasicCredentials = Depends(security)):
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("SELECT password_hash, role, avatar, color, points, badge_level FROM users WHERE username = $1", credentials.username)
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
# 6 LANGUAGES (unchanged – huge dict, omitted for brevity)
# ============================================

LANGUAGES = {
    "en": {"name": "English", "flag": "🇬🇧", "subtitle": "Unified Command Center | Analytics", "report_damage": "Report Damage", ...},
    # ... (keep your full LANGUAGES dict)
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
        # Save to /tmp/photos (writable on Vercel)
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
    
    await manager.broadcast_report({
        "report_uuid": report_uuid, "damage_level": damage_level, "lat": lat, "lng": lng,
        "infrastructure_type": infrastructure_type, "building_name": building_name,
        "timestamp": datetime.now().isoformat(), "username": current_user["username"]
    })
    
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
            await manager.broadcast_report({
                "report_uuid": report_uuid, "damage_level": damage_level, "lat": lat, "lng": lng,
                "infrastructure_type": "SMS Report", "building_name": "SMS Report",
                "timestamp": datetime.now().isoformat(), "username": "SMS User"
            })
            return {"status": "success", "message": "SMS report received", "lat": lat, "lng": lng}
        except ValueError:
            return {"status": "error", "message": "Invalid coordinates"}
    return {"status": "error", "message": "Invalid SMS format. Use: DAMAGE_TYPE LAT LNG"}

@app.post("/api/sync")
async def sync_offline_reports(reports_data: List[Dict], current_user: dict = Depends(require_reporter)):
    synced_count = 0
    for report in reports_data:
        try:
            async with db_pool.acquire() as conn:
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
        except Exception as e:
            print(f"Sync error: {e}")
    return {"synced": synced_count}

@app.post("/api/update_location")
async def update_user_location(lat: float, lng: float, current_user: dict = Depends(verify_user)):
    await manager.update_user_location(current_user["username"], lat, lng)
    return {"status": "success"}

@app.get("/api/reports")
async def get_reports(limit: int = 200, current_user: dict = Depends(verify_user)):
    return await get_reports_db(limit)

@app.get("/api/reports/geojson")
async def get_geojson(current_user: dict = Depends(require_admin)):
    async with db_pool.acquire() as conn:
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

@app.get("/api/reports/csv")
async def export_csv(current_user: dict = Depends(require_admin)):
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("SELECT damage_level, lat, lng, building_name, building_address, infrastructure_type, crisis_nature, debris, notes, timestamp, username FROM reports WHERE is_current = 1 ORDER BY timestamp DESC")
    csv = "Damage Level,Latitude,Longitude,Building Name,Building Address,Infrastructure Type,Crisis Nature,Debris,Notes,Timestamp,Username\n"
    for r in rows:
        lat_val = f"{r[1]:.6f}" if r[1] else ""
        lng_val = f"{r[2]:.6f}" if r[2] else ""
        csv += f"{r[0]},{lat_val},{lng_val},\"{r[3] or ''}\",\"{r[4] or ''}\",{r[5]},{r[6]},{r[7]},\"{r[8] or ''}\",{r[9]},{r[10]}\n"
    return HTMLResponse(csv, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=impact_reports.csv"})

@app.get("/api/stats")
async def get_stats():
    async with db_pool.acquire() as conn:
        total = await conn.fetchval("SELECT COUNT(*) FROM reports WHERE is_current = 1")
        today = datetime.now().date().isoformat()
        today_count = await conn.fetchval("SELECT COUNT(*) FROM reports WHERE DATE(timestamp) = $1 AND is_current = 1", today)
        pending = await conn.fetchval("SELECT COUNT(*) FROM reports WHERE synced = 0")
    return {"total_reports": total, "today_reports": today_count, "pending_sync": pending, "active_volunteers": 350, "rescue_teams": 12, "responders": 48}

@app.get("/photos/{filename}")
async def serve_photo(filename: str):
    # Serve from /tmp/photos (where uploaded files are stored)
    file_path = os.path.join(PHOTOS_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    # Fallback to old photos directory (not needed but kept for compatibility)
    old_path = f"photos/{filename}"
    if os.path.exists(old_path):
        return FileResponse(old_path)
    raise HTTPException(status_code=404, detail="Photo not found")

@app.websocket("/ws/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str):
    async with db_pool.acquire() as conn:
        user = await conn.fetchrow("SELECT role, avatar, color, points, badge_level FROM users WHERE username = $1", username)
        if not user:
            await websocket.close()
            return
    user_info = {"username": username, "role": user[0], "avatar": user[1], "color": user[2], "points": user[3], "badge": user[4]}
    await manager.connect(websocket, user_info)
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "chat":
                await manager.broadcast_chat(data.get("message", ""), websocket)
            elif data.get("type") == "location":
                await manager.update_user_location(username, data.get("lat"), data.get("lng"))
            elif data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# ============================================
# LOGIN HTML and DASHBOARD HTML (keep fully – omitted here for brevity)
# ============================================

LOGIN_HTML = """<!DOCTYPE html> ... """  # Keep your existing LOGIN_HTML exactly as before
UNIFIED_DASHBOARD_HTML = """<!DOCTYPE html> ... """  # Keep your existing dashboard HTML

# ============================================
# VERCEL SERVERLESS HANDLER (required)
# ============================================

from mangum import Mangum
handler = Mangum(app)

# ============================================
# LOCAL DEVELOPMENT SERVER
# ============================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
