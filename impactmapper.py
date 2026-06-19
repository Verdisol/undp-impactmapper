import asyncio
import csv
import hashlib
import io
import json
import os
import urllib.parse
import urllib.request
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Dict, List

import asyncpg
import uvicorn
from fastapi import (Depends, FastAPI, File, Form, HTTPException, UploadFile,
                     WebSocket, WebSocketDisconnect)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

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

app = FastAPI(title="UNDP ImpactMapper", version="28.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# WEBSOCKET MANAGER (Chat + Online users)
# ============================================
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[WebSocket, str] = {}
        self.messages: List[dict] = []

    async def connect(self, websocket: WebSocket, username: str):
        await websocket.accept()
        self.active_connections[websocket] = username
        for msg in self.messages[-50:]:
            await websocket.send_text(json.dumps(msg))
        await self.broadcast_online_count()

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            del self.active_connections[websocket]
        asyncio.create_task(self.broadcast_online_count())

    async def broadcast(self, message: dict):
        self.messages.append(message)
        if len(self.messages) > 200:
            self.messages = self.messages[-200:]
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except:
                pass

    async def broadcast_online_count(self):
        count = len(self.active_connections)
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps({"type": "online", "count": count}))
            except:
                pass

manager = ConnectionManager()

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

async def get_analytics():
    conn = await get_db_conn()
    try:
        damage = await conn.fetch("SELECT damage_level, COUNT(*) as cnt FROM reports WHERE is_current = 1 GROUP BY damage_level")
        infra = await conn.fetch("SELECT infrastructure_type, COUNT(*) as cnt FROM reports WHERE is_current = 1 AND infrastructure_type IS NOT NULL AND infrastructure_type != '' GROUP BY infrastructure_type ORDER BY cnt DESC LIMIT 10")
        crisis = await conn.fetch("SELECT crisis_nature, COUNT(*) as cnt FROM reports WHERE is_current = 1 AND crisis_nature IS NOT NULL AND crisis_nature != '' GROUP BY crisis_nature ORDER BY cnt DESC LIMIT 10")
        trend = await conn.fetch("SELECT DATE(timestamp::timestamp) as date, COUNT(*) as cnt FROM reports WHERE is_current = 1 AND timestamp::timestamp >= (NOW() - INTERVAL '30 days') GROUP BY DATE(timestamp::timestamp) ORDER BY date ASC")
        return {
            "damage": [{"label": r["damage_level"] or "Unknown", "count": r["cnt"]} for r in damage],
            "infra": [{"label": r["infrastructure_type"], "count": r["cnt"]} for r in infra],
            "crisis": [{"label": r["crisis_nature"], "count": r["cnt"]} for r in crisis],
            "trend": [{"date": r["date"].isoformat(), "count": r["cnt"]} for r in trend]
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

def require_admin(current_user = Depends(verify_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

def require_reporter(current_user = Depends(verify_user)):
    if current_user["role"] not in ["admin", "reporter"]:
        raise HTTPException(status_code=403, detail="Reporter access required")
    return current_user

# ============================================
# LANGUAGES
# ============================================
LANGUAGES = {
    "en": {
        "name": "English", "flag": "🇬🇧",
        "report_damage": "Report Damage", "damage_level": "Damage Level",
        "minimal": "Minimal/No Damage", "partial": "Partially Damaged",
        "complete": "Completely Damaged", "infrastructure": "Infrastructure Type",
        "residential": "Residential", "commercial": "Commercial",
        "government": "Government", "utility": "Utility",
        "transport": "Transport", "community": "Community",
        "public": "Public", "crisis": "Crisis Type",
        "earthquake": "Earthquake", "flood": "Flood",
        "tsunami": "Tsunami", "hurricane": "Hurricane",
        "wildfire": "Wildfire", "explosion": "Explosion",
        "conflict": "Conflict", "debris": "Debris?",
        "yes": "Yes", "no": "No", "submit": "Submit Report",
        "gps_location": "Use My GPS", "building_name": "Building Name",
        "photo": "Upload Photo", "notes": "Additional Notes",
        "recent_reports": "Recent Reports", "export_data": "Export Data",
        "export_csv": "Export CSV", "export_geojson": "Export GeoJSON",
        "active_volunteers": "Active Volunteers", "rescue_teams": "Rescue Teams",
        "online_users": "Online", "leaderboard": "Leaderboard",
        "chat": "Crisis Chat", "type_message": "Type a message...",
        "send": "Send", "click_building": "🏢 Click on any building on the map to select it!",
        "total_reports": "Total Reports", "today_reports": "Today",
        "pending_sync": "Pending Sync", "logout": "Logout",
        "sync_now": "Sync Now", "sms_report": "SMS Report",
        "sms_placeholder": "Format: DAMAGE LAT LNG",
        "sms_send": "Send SMS Report", "command_center": "Command Center",
        "analytics": "Analytics Dashboard"
    },
    "fr": {
        "name": "Français", "flag": "🇫🇷",
        "report_damage": "Signaler des dégâts", "damage_level": "Niveau de dégât",
        "minimal": "Minime/Aucun dégât", "partial": "Partiellement endommagé",
        "complete": "Complètement endommagé", "infrastructure": "Type d'infrastructure",
        "residential": "Résidentiel", "commercial": "Commercial",
        "government": "Gouvernement", "utility": "Service public",
        "transport": "Transport", "community": "Communautaire",
        "public": "Public", "crisis": "Type de crise",
        "earthquake": "Tremblement de terre", "flood": "Inondation",
        "tsunami": "Tsunami", "hurricane": "Ouragan",
        "wildfire": "Feu de forêt", "explosion": "Explosion",
        "conflict": "Conflit", "debris": "Débris?",
        "yes": "Oui", "no": "Non", "submit": "Soumettre le rapport",
        "gps_location": "Utiliser mon GPS", "building_name": "Nom du bâtiment",
        "photo": "Télécharger une photo", "notes": "Notes supplémentaires",
        "recent_reports": "Rapports récents", "export_data": "Exporter les données",
        "export_csv": "Exporter CSV", "export_geojson": "Exporter GeoJSON",
        "active_volunteers": "Volontaires actifs", "rescue_teams": "Équipes de secours",
        "online_users": "En ligne", "leaderboard": "Classement",
        "chat": "Chat de crise", "type_message": "Tapez un message...",
        "send": "Envoyer", "click_building": "🏢 Cliquez sur un bâtiment sur la carte pour le sélectionner !",
        "total_reports": "Total des rapports", "today_reports": "Aujourd'hui",
        "pending_sync": "En attente de synchronisation", "logout": "Déconnexion",
        "sync_now": "Synchroniser maintenant", "sms_report": "Rapport SMS",
        "sms_placeholder": "Format: DEGAT LAT LNG", "sms_send": "Envoyer rapport SMS",
        "command_center": "Centre de commandement", "analytics": "Tableau de bord analytique"
    }
}

# ============================================
# LOGIN PAGE (YOUR ORIGINAL DESIGN)
# ============================================
LOGIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>UNDP ImpactMapper - Login</title>
<style>
  body { font-family: 'Segoe UI', Arial, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); margin: 0; padding: 0; display: flex; align-items: center; justify-content: center; height: 100vh; }
 .login-box { background: white; padding: 40px; border-radius: 12px; box-shadow: 0 10px 40px rgba(0,0,0,0.2); width: 100%; max-width: 400px; }
  h2 { color: #2c3e50; text-align: center; margin-bottom: 30px; }
  input { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; }
  button { width: 100%; padding: 12px; background: #27ae60; color: white; border: none; border-radius: 6px; font-size: 16px; font-weight: bold; cursor: pointer; margin-top: 10px; }
  button:hover { background: #219a52; }
 .demo { text-align: center; margin-top: 20px; color: #7f8c8d; font-size: 12px; }
</style>
</head>
<body>
<div class="login-box">
  <h2>UNDP ImpactMapper</h2>
  <p style="text-align:center; color:#7f8c8d;">Sign in to continue</p>
  <input type="text" id="username" placeholder="Username" value="admin">
  <input type="password" id="password" placeholder="Password" value="admin123">
  <button onclick="login()">Login</button>
  <div class="demo">
    Demo: admin/admin123<br>
    reporter/report123<br>
    viewer/view123
  </div>
</div>
<script>
async function login() {
  const username = document.getElementById('username').value;
  const password = document.getElementById('password').value;
  const credentials = btoa(username + ':' + password);

  try {
    const res = await fetch('/api/current_user', {
      headers: { 'Authorization': 'Basic ' + credentials }
    });
    if (res.ok) {
      window.location.href = '/dashboard';
    } else {
      alert('Invalid credentials');
    }
  } catch (e) {
    alert('Login failed');
  }
}
</script>
</body>
</html>
"""

# ============================================
# DASHBOARD HTML - WITH ROLE-BASED SPLIT VIEW
# ============================================
UNIFIED_DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>UNDP ImpactMapper - Command Center</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
    /* ========== ORIGINAL CSS (unchanged) ========== */
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'Segoe UI', Arial, sans-serif; background: #f4f6f8; padding: 15px; }

    .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px; flex-wrap: wrap; }
    .header h1 { color: #2c3e50; font-size: 24px; }
    .user-info { display: flex; align-items: center; gap: 12px; }
    .avatar { width: 40px; height: 40px; border-radius: 50%; background: #27ae60; display: flex; align-items: center; justify-content: center; color: white; font-size: 20px; }

    .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px; margin-bottom: 25px; }
    .stat-card { background: white; padding: 15px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
    .stat-card h4 { color: #7f8c8d; font-size: 12px; text-transform: uppercase; margin-bottom: 5px; }
    .stat-number { font-size: 28px; font-weight: bold; color: #2c3e50; }

    .panel {
        background: white;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
    .panel h3 {
        margin: 0 0 15px 0;
        color: #34495e;
        border-bottom: 3px solid #27ae60;
        padding-bottom: 10px;
        font-size: 18px;
    }

    /* SCROLLABLE DAMAGE PANEL */
    .damage-list {
        max-height: 500px;
        overflow-y: auto;
        padding-right: 8px;
    }
    .damage-list::-webkit-scrollbar { width: 8px; }
    .damage-list::-webkit-scrollbar-track { background: #f1f1f1; border-radius: 4px; }
    .damage-list::-webkit-scrollbar-thumb { background: #bdc3c7; border-radius: 4px; }
    .damage-list::-webkit-scrollbar-thumb:hover { background: #95a5a6; }

    .damage-item {
        padding: 14px;
        border-bottom: 1px solid #ecf0f1;
        display: flex;
        justify-content: space-between;
        align-items: center;
        transition: background 0.2s;
    }
    .damage-item:last-child { border-bottom: none; }
    .damage-item:hover { background: #f8f9fa; }

    .damage-info b { color: #2c3e50; font-size: 15px; display: block; margin-bottom: 4px; }
    .damage-info small { color: #7f8c8d; font-size: 12px; }
    .location { color: #95a5a6; font-size: 11px; margin-top: 2px; }

    .badge {
        padding: 6px 12px;
        border-radius: 15px;
        font-size: 11px;
        font-weight: bold;
        text-transform: uppercase;
        color: white;
        background: #95a5a6;
    }
    .badge.minimal { background: #f1c40f; color: #333; }
    .badge.partial { background: #e67e22; }
    .badge.complete { background: #e74c3c; }

    .photo-thumb { width: 50px; height: 50px; border-radius: 5px; object-fit: cover; }

    .leaderboard ol { padding-left: 20px; }
    .leaderboard li { margin-bottom: 8px; display: flex; align-items: center; gap: 8px; }
    .leaderboard .avatar { width: 24px; height: 24px; font-size: 14px; }

    .buttons { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 15px; }
    button { padding: 10px 20px; background: #27ae60; color: white; border: none; border-radius: 6px; font-size: 14px; cursor: pointer; }
    button:hover { background: #219a52; }
    button.danger { background: #e74c3c; }
    button.danger:hover { background: #c0392b; }

    /* ========== TOOLBAR & LAYOUT ========== */
    #toolbar {
        display: flex; justify-content: space-between; align-items: center;
        background: white; padding: 10px 20px; border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom: 15px;
    }
    .toolbar-left { display: flex; align-items: center; gap: 15px; }
    .toolbar-right { display: flex; align-items: center; gap: 15px; }
    .language-select { padding: 8px; border-radius: 6px; border: 1px solid #ddd; font-size: 14px; background: white; }
    .user-badge { display: flex; align-items: center; gap: 8px; }
    .export-dropdown { position: relative; display: inline-block; }
    .export-btn { background: #27ae60; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; }
    .export-btn:hover { background: #219a52; }
    .export-content {
        display: none; position: absolute; right: 0; background: white;
        box-shadow: 0 8px 16px rgba(0,0,0,0.2); border-radius: 5px; z-index: 1000; min-width: 160px;
    }
    .export-content a { color: #333; padding: 10px 16px; text-decoration: none; display: block; }
    .export-content a:hover { background: #f1f1f1; }
    .export-dropdown:hover .export-content { display: block; }
    .logout-btn { background: #e74c3c; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; }
    .new-report-btn { background: #27ae60; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; }

    /* Map & Charts container */
    #mainArea { margin-bottom: 15px; }
    #map { height: 400px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
    .charts-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 15px; }
    .chart-box { background: white; border-radius: 10px; padding: 15px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
    .chart-box canvas { max-height: 250px; }

    /* SPLIT VIEW FOR REPORTERS */
    #mainArea.split {
        display: flex;
        gap: 15px;
    }
    #mainArea.split #map {
        flex: 1;
        height: 500px;
    }
    #mainArea.split #chartsGrid {
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 15px;
    }
    #mainArea.split .chart-box {
        flex: 1;
    }
    #mainArea.split .chart-box canvas {
        max-height: 150px;
    }

    /* Panels row */
    .panels-row { display: flex; gap: 15px; margin-bottom: 15px; }
    .damage-panel { flex: 2; }
    .chat-panel { flex: 1; display: flex; flex-direction: column; }
    .toggle-arrow { cursor: pointer; font-size: 20px; color: #7f8c8d; transition: transform 0.3s; }
    .collapsed .damage-list { display: none; }
    .collapsed .toggle-arrow { transform: rotate(-90deg); }

    .chat-messages { flex: 1; overflow-y: auto; max-height: 350px; background: #f9f9f9; padding: 10px; border-radius: 5px; margin-bottom: 10px; }
    .chat-input { display: flex; gap: 5px; }
    .chat-input input { flex: 1; padding: 8px; border: 1px solid #ccc; border-radius: 6px; }
    .chat-input button { padding: 8px 16px; background: #3498db; color: white; border: none; border-radius: 6px; cursor: pointer; }
    .online-badge { background: #2ecc71; color: white; padding: 2px 8px; border-radius: 10px; font-size: 12px; margin-left: 10px; }

    .avatar-small { width: 24px; height: 24px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; color: white; font-size: 14px; margin-right: 5px; }
</style>
</head>
<body>
<!-- TOOLBAR -->
<div id="toolbar">
    <div class="toolbar-left">
        <h2 style="color:#2c3e50; font-size:24px;">🌍 UNDP ImpactMapper</h2>
        <select id="langSelect" class="language-select"></select>
        <button class="new-report-btn" id="newReportBtn" style="display:none;" onclick="window.location.href='/report'">➕ New Report</button>
    </div>
    <div class="toolbar-right">
        <div class="user-badge" id="userBadge"></div>
        <div class="export-dropdown">
            <button class="export-btn">📤 Export</button>
            <div class="export-content">
                <a href="#" onclick="window.open('/api/export/csv')">Export CSV</a>
                <a href="#" onclick="window.open('/api/export/geojson')">Export GeoJSON</a>
            </div>
        </div>
        <button class="logout-btn" onclick="logout()">🚪 Logout</button>
    </div>
</div>

<!-- STATS -->
<div class="stats-grid" id="statsRow"></div>

<!-- MAIN AREA (MAP + CHARTS) -->
<div id="mainArea">
    <div id="map"></div>
    <div class="charts-grid" id="chartsGrid">
        <div class="chart-box"><h4>Damage Levels</h4><canvas id="damageChart"></canvas></div>
        <div class="chart-box"><h4>Daily Reports (30 days)</h4><canvas id="trendChart"></canvas></div>
        <div class="chart-box"><h4>Crisis Types</h4><canvas id="crisisChart"></canvas></div>
    </div>
</div>

<!-- PANELS (Damage + Chat) -->
<div class="panels-row">
    <div class="panel damage-panel" id="damagePanel">
        <h3>
            <span>📋 Recent Damage Reports</span>
            <span class="toggle-arrow" onclick="togglePanel('damagePanel')">▼</span>
        </h3>
        <div class="damage-list" id="reportsList">Loading...</div>
    </div>
    <div class="panel chat-panel">
        <h3>💬 Crisis Chat <span class="online-badge" id="onlineCount">0 online</span></h3>
        <div class="chat-messages" id="chatMessages"></div>
        <div class="chat-input">
            <input type="text" id="chatInput" placeholder="Type a message..." onkeypress="if(event.key==='Enter') sendMessage()">
            <button onclick="sendMessage()">Send</button>
        </div>
    </div>
</div>

<!-- LEADERBOARD -->
<div class="panel leaderboard">
    <h3>🏆 Volunteer Leaderboard</h3>
    <ol id="leaderboardList"></ol>
</div>

<script>
// ========== GLOBALS ==========
let authHeader = 'Basic ' + btoa(localStorage.getItem('credentials') || ':');
let currentUser = null;
let currentLang = 'en';
let translations = {};
let map, markersLayer;
let damageChart, trendChart, crisisChart;
let ws;

// ========== API HELPER ==========
async function fetchAPI(url) {
    const res = await fetch(url, { headers: { 'Authorization': authHeader } });
    if (res.status === 401) { window.location.href = '/login'; return null; }
    return res.json();
}

// ========== TRANSLATIONS ==========
async function loadTranslations(lang) {
    try {
        const res = await fetch(`/api/lang/${lang}`);
        if (res.ok) translations = await res.json();
        else translations = {};
    } catch(e) { translations = {}; }
    applyTranslations();
}

function t(key) { return translations[key] || key; }

function applyTranslations() {
    document.querySelectorAll('[data-i18n]').forEach(el => {
        el.textContent = t(el.dataset.i18n);
    });
}

async function initLanguages() {
    const select = document.getElementById('langSelect');
    select.innerHTML = `<option value="en">🇬🇧 English</option><option value="fr">🇫🇷 Français</option>`;
    select.value = currentLang;
    select.addEventListener('change', async (e) => {
        currentLang = e.target.value;
        localStorage.setItem('lang', currentLang);
        await loadTranslations(currentLang);
    });
}

// ========== ROLE-BASED LAYOUT ==========
function applyRoleLayout() {
    if (currentUser.role !== 'admin') {
        // Reporter or viewer: split view (map left, charts right)
        document.getElementById('mainArea').classList.add('split');
        if (currentUser.role === 'reporter' || currentUser.role === 'admin') {
            document.getElementById('newReportBtn').style.display = 'inline-block';
        }
    } else {
        // Admin: keep default stacked layout
        document.getElementById('mainArea').classList.remove('split');
        document.getElementById('newReportBtn').style.display = 'inline-block';
    }
}

// ========== USER & WEBSOCKET ==========
async function loadUser() {
    currentUser = await fetchAPI('/api/current_user');
    if (!currentUser) return;
    document.getElementById('userBadge').innerHTML = `
        <span class="avatar-small" style="background:${currentUser.color}">${currentUser.avatar}</span>
        ${currentUser.username} · ${currentUser.points} pts · ${currentUser.badge}
    `;
    applyRoleLayout();
    connectWebSocket();
}

function connectWebSocket() {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${location.host}/ws/chat?username=${encodeURIComponent(currentUser.username)}`);
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'chat') {
            addChatMessage(data.username, data.message, data.timestamp);
        } else if (data.type === 'online') {
            document.getElementById('onlineCount').textContent = `${data.count} online`;
        }
    };
    ws.onclose = () => setTimeout(connectWebSocket, 3000);
}

function sendMessage() {
    const input = document.getElementById('chatInput');
    const message = input.value.trim();
    if (message && ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ message }));
        input.value = '';
    }
}

function addChatMessage(username, message, timestamp) {
    const div = document.getElementById('chatMessages');
    const time = new Date(timestamp).toLocaleTimeString();
    div.innerHTML += `<p><strong>${username}</strong>: ${message} <small>${time}</small></p>`;
    div.scrollTop = div.scrollHeight;
}

// ========== MAP ==========
function initMap() {
    map = L.map('map').setView([0, 0], 2);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);
    markersLayer = L.layerGroup().addTo(map);
    loadMapReports();
    map.on('click', function(e) {
        L.popup()
            .setLatLng(e.latlng)
            .setContent(`<b>${e.latlng.lat.toFixed(5)}, ${e.latlng.lng.toFixed(5)}</b><br><a href="/report?lat=${e.latlng.lat}&lng=${e.latlng.lng}">Report damage here</a>`)
            .openOn(map);
    });
}

async function loadMapReports() {
    const reports = await fetchAPI('/api/reports?limit=500');
    if (!reports) return;
    markersLayer.clearLayers();
    reports.forEach(r => {
        if (r.lat && r.lng) {
            const marker = L.marker([r.lat, r.lng]).addTo(markersLayer);
            marker.bindPopup(`<b>${r.damage_level}</b><br>${r.building_name || r.infrastructure_type || ''}<br>${r.location_text}`);
        }
    });
    if (reports.length > 0) map.fitBounds(markersLayer.getBounds().pad(0.1));
}

// ========== CHARTS ==========
async function loadCharts() {
    const data = await fetchAPI('/api/analytics');
    if (!data) return;

    // Damage bar
    const damageCtx = document.getElementById('damageChart').getContext('2d');
    if (damageChart) damageChart.destroy();
    damageChart = new Chart(damageCtx, {
        type: 'bar',
        data: {
            labels: data.damage.map(d => d.label),
            datasets: [{
                label: 'Reports',
                data: data.damage.map(d => d.count),
                backgroundColor: ['#f1c40f', '#e67e22', '#e74c3c', '#95a5a6']
            }]
        }
    });

    // Trend line
    const trendCtx = document.getElementById('trendChart').getContext('2d');
    if (trendChart) trendChart.destroy();
    trendChart = new Chart(trendCtx, {
        type: 'line',
        data: {
            labels: data.trend.map(d => d.date),
            datasets: [{
                label: 'Reports',
                data: data.trend.map(d => d.count),
                borderColor: '#3498db',
                fill: false
            }]
        }
    });

    // Crisis pie
    const crisisCtx = document.getElementById('crisisChart').getContext('2d');
    if (crisisChart) crisisChart.destroy();
    crisisChart = new Chart(crisisCtx, {
        type: 'pie',
        data: {
            labels: data.crisis.map(d => d.label),
            datasets: [{
                data: data.crisis.map(d => d.count),
                backgroundColor: ['#e74c3c', '#3498db', '#2ecc71', '#f1c40f', '#9b59b6', '#e67e22']
            }]
        }
    });
}

// ========== DAMAGE PANEL COLLAPSE ==========
function togglePanel(panelId) {
    document.getElementById(panelId).classList.toggle('collapsed');
}

// ========== REPORTS LIST ==========
async function loadReportsList() {
    const reports = await fetchAPI('/api/reports');
    const list = document.getElementById('reportsList');
    if (!reports) return;
    list.innerHTML = reports.map(r => `
        <div class="damage-item">
            <div class="damage-info">
                <b>${r.building_name || r.infrastructure_type || 'Unknown'}</b>
                <small>${r.location_text}</small>
                <div class="location">${r.damage_level} · ${r.crisis_nature} · ${r.timestamp}</div>
            </div>
            <span class="badge ${r.damage_level.toLowerCase().replace(/ /g,'')}">${r.damage_level}</span>
            ${r.photo_url ? `<img class="photo-thumb" src="${r.photo_url}">` : ''}
        </div>
    `).join('');
}

// ========== LEADERBOARD ==========
async function loadLeaderboard() {
    const lb = await fetchAPI('/api/leaderboard');
    const ol = document.getElementById('leaderboardList');
    ol.innerHTML = lb.map(u => `
        <li>
            <span class="avatar-small" style="background:${u.color}">${u.avatar}</span>
            ${u.username} - ${u.points} pts (${u.badge})
        </li>
    `).join('');
}

// ========== STATS ==========
async function loadStats() {
    const stats = await fetchAPI('/api/stats');
    document.getElementById('statsRow').innerHTML = `
        <div class="stat-card"><h4 data-i18n="total_reports">Total Reports</h4><div class="stat-number">${stats.total_reports}</div></div>
        <div class="stat-card"><h4 data-i18n="today_reports">Today</h4><div class="stat-number">${stats.today_reports}</div></div>
        <div class="stat-card"><h4 data-i18n="pending_sync">Pending Sync</h4><div class="stat-number">${stats.pending_sync}</div></div>
    `;
}

function logout() {
    localStorage.removeItem('credentials');
    window.location.href = '/login';
}

// ========== INIT ==========
(async () => {
    const storedLang = localStorage.getItem('lang') || 'en';
    currentLang = storedLang;
    await initLanguages();
    await loadTranslations(currentLang);
    await loadUser();         // role-based layout applied here
    initMap();
    loadCharts();
    loadReportsList();
    loadLeaderboard();
    loadStats();

    // Refresh every 60s
    setInterval(() => {
        loadCharts();
        loadReportsList();
        loadLeaderboard();
        loadStats();
        loadMapReports();
    }, 60000);
})();
</script>
</body>
</html>
"""

# ============================================
# ROUTES
# ============================================
@app.get("/", response_class=HTMLResponse)
async def login_page():
    return LOGIN_HTML

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    return UNIFIED_DASHBOARD_HTML

@app.get("/api/current_user")
async def get_current_user(current_user = Depends(verify_user)):
    return current_user

@app.get("/api/reports")
async def get_reports(limit: int = 200):
    return await get_reports_db(limit)

@app.get("/api/stats")
async def get_stats():
    return await get_stats_db()

@app.get("/api/leaderboard")
async def leaderboard():
    return await get_leaderboard_db()

@app.get("/api/analytics")
async def analytics():
    return await get_analytics()

@app.get("/api/export/csv")
async def export_csv():
    reports = await get_reports_db(1000)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["uuid","damage","lat","lng","location","infrastructure","crisis","debris","notes","timestamp","username"])
    for r in reports:
        writer.writerow([r["report_uuid"], r["damage_level"], r["lat"], r["lng"], r["location_text"],
                         r["infrastructure_type"], r["crisis_nature"], r["debris"], r["notes"],
                         r["timestamp"], r["username"]])
    return HTMLResponse(content=output.getvalue(), media_type="text/csv",
                        headers={"Content-Disposition": "attachment; filename=reports.csv"})

@app.get("/api/export/geojson")
async def export_geojson():
    reports = await get_reports_db(1000)
    features = [{
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [r["lng"], r["lat"]]},
        "properties": {
            "report_uuid": r["report_uuid"], "damage_level": r["damage_level"],
            "infrastructure_type": r["infrastructure_type"], "crisis_nature": r["crisis_nature"],
            "timestamp": r["timestamp"], "username": r["username"]
        }
    } for r in reports]
    geojson = {"type": "FeatureCollection", "features": features}
    return JSONResponse(content=geojson, media_type="application/geo+json",
                        headers={"Content-Disposition": "attachment; filename=reports.geojson"})

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

@app.websocket("/ws/chat")
async def chat_endpoint(websocket: WebSocket):
    username = websocket.query_params.get("username", "Anonymous")
    await manager.connect(websocket, username)
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            await manager.broadcast({
                "type": "chat",
                "username": username,
                "message": msg["message"],
                "timestamp": datetime.now().isoformat()
            })
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/api/lang/{lang}")
async def get_language(lang: str):
    return LANGUAGES.get(lang, LANGUAGES["en"])

@app.get("/photos/{filename}")
async def get_photo(filename: str):
    path = os.path.join(PHOTOS_DIR, filename)
    if os.path.exists(path):
        return FileResponse(path)
    raise HTTPException(status_code=404)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
