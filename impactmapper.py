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
# LANGUAGES (6 languages)
# ============================================
LANGUAGES = {
    "en": {
        "name": "English", "flag": "🇬🇧",
        "report_damage": "Report Damage", "damage_level": "Damage Level",
        "minimal": "Minimal/No Damage", "partial": "Partially Damaged", "complete": "Completely Damaged",
        "infrastructure": "Infrastructure Type", "residential": "Residential", "commercial": "Commercial",
        "government": "Government", "utility": "Utility", "transport": "Transport", "community": "Community",
        "public": "Public", "crisis": "Crisis Type", "earthquake": "Earthquake", "flood": "Flood",
        "tsunami": "Tsunami", "hurricane": "Hurricane", "wildfire": "Wildfire", "explosion": "Explosion",
        "conflict": "Conflict", "debris": "Debris?", "yes": "Yes", "no": "No", "submit": "Submit Report",
        "gps_location": "Use My GPS", "building_name": "Building Name", "photo": "Upload Photo",
        "notes": "Additional Notes", "recent_reports": "Recent Reports", "export_data": "Export Data",
        "export_csv": "Export CSV", "export_geojson": "Export GeoJSON", "active_volunteers": "Active Volunteers",
        "rescue_teams": "Rescue Teams", "online_users": "Online", "leaderboard": "Leaderboard",
        "chat": "Crisis Chat", "type_message": "Type a message...", "send": "Send",
        "click_building": "🏢 Click on any building on the map to select it!",
        "total_reports": "Total Reports", "today_reports": "Today", "pending_sync": "Pending Sync",
        "logout": "Logout", "sync_now": "Sync Now", "sms_report": "SMS Report",
        "sms_placeholder": "Format: DAMAGE LAT LNG", "sms_send": "Send SMS Report",
        "command_center": "Command Center", "analytics": "Analytics Dashboard"
    },
    "es": {
        "name": "Español", "flag": "🇪🇸",
        "report_damage": "Reportar daño", "damage_level": "Nivel de daño",
        "minimal": "Mínimo/Sin daño", "partial": "Parcialmente dañado", "complete": "Completamente dañado",
        "infrastructure": "Tipo de infraestructura", "residential": "Residencial", "commercial": "Comercial",
        "government": "Gubernamental", "utility": "Servicio público", "transport": "Transporte", "community": "Comunitario",
        "public": "Público", "crisis": "Tipo de crisis", "earthquake": "Terremoto", "flood": "Inundación",
        "tsunami": "Tsunami", "hurricane": "Huracán", "wildfire": "Incendio forestal", "explosion": "Explosión",
        "conflict": "Conflicto", "debris": "¿Escombros?", "yes": "Sí", "no": "No", "submit": "Enviar informe",
        "gps_location": "Usar mi GPS", "building_name": "Nombre del edificio", "photo": "Subir foto",
        "notes": "Notas adicionales", "recent_reports": "Informes recientes", "export_data": "Exportar datos",
        "export_csv": "Exportar CSV", "export_geojson": "Exportar GeoJSON", "active_volunteers": "Voluntarios activos",
        "rescue_teams": "Equipos de rescate", "online_users": "En línea", "leaderboard": "Clasificación",
        "chat": "Chat de crisis", "type_message": "Escribe un mensaje...", "send": "Enviar",
        "click_building": "🏢 ¡Haz clic en un edificio en el mapa para seleccionarlo!",
        "total_reports": "Total de informes", "today_reports": "Hoy", "pending_sync": "Pendientes de sincronización",
        "logout": "Cerrar sesión", "sync_now": "Sincronizar ahora", "sms_report": "Informe SMS",
        "sms_placeholder": "Formato: DAÑO LAT LNG", "sms_send": "Enviar informe SMS",
        "command_center": "Centro de mando", "analytics": "Panel de análisis"
    },
    "fr": {
        "name": "Français", "flag": "🇫🇷",
        "report_damage": "Signaler des dégâts", "damage_level": "Niveau de dégât",
        "minimal": "Minime/Aucun dégât", "partial": "Partiellement endommagé", "complete": "Complètement endommagé",
        "infrastructure": "Type d'infrastructure", "residential": "Résidentiel", "commercial": "Commercial",
        "government": "Gouvernement", "utility": "Service public", "transport": "Transport", "community": "Communautaire",
        "public": "Public", "crisis": "Type de crise", "earthquake": "Tremblement de terre", "flood": "Inondation",
        "tsunami": "Tsunami", "hurricane": "Ouragan", "wildfire": "Feu de forêt", "explosion": "Explosion",
        "conflict": "Conflit", "debris": "Débris?", "yes": "Oui", "no": "Non", "submit": "Soumettre le rapport",
        "gps_location": "Utiliser mon GPS", "building_name": "Nom du bâtiment", "photo": "Télécharger une photo",
        "notes": "Notes supplémentaires", "recent_reports": "Rapports récents", "export_data": "Exporter les données",
        "export_csv": "Exporter CSV", "export_geojson": "Exporter GeoJSON", "active_volunteers": "Volontaires actifs",
        "rescue_teams": "Équipes de secours", "online_users": "En ligne", "leaderboard": "Classement",
        "chat": "Chat de crise", "type_message": "Tapez un message...", "send": "Envoyer",
        "click_building": "🏢 Cliquez sur un bâtiment sur la carte pour le sélectionner !",
        "total_reports": "Total des rapports", "today_reports": "Aujourd'hui", "pending_sync": "En attente de synchronisation",
        "logout": "Déconnexion", "sync_now": "Synchroniser maintenant", "sms_report": "Rapport SMS",
        "sms_placeholder": "Format: DEGAT LAT LNG", "sms_send": "Envoyer rapport SMS",
        "command_center": "Centre de commandement", "analytics": "Tableau de bord analytique"
    },
    "pt": {
        "name": "Português", "flag": "🇵🇹",
        "report_damage": "Relatar danos", "damage_level": "Nível de dano",
        "minimal": "Mínimo/Sem danos", "partial": "Parcialmente danificado", "complete": "Completamente danificado",
        "infrastructure": "Tipo de infraestrutura", "residential": "Residencial", "commercial": "Comercial",
        "government": "Governamental", "utility": "Utilidade pública", "transport": "Transporte", "community": "Comunitário",
        "public": "Público", "crisis": "Tipo de crise", "earthquake": "Terremoto", "flood": "Inundação",
        "tsunami": "Tsunami", "hurricane": "Furacão", "wildfire": "Incêndio florestal", "explosion": "Explosão",
        "conflict": "Conflito", "debris": "Escombros?", "yes": "Sim", "no": "Não", "submit": "Enviar relatório",
        "gps_location": "Usar meu GPS", "building_name": "Nome do edifício", "photo": "Enviar foto",
        "notes": "Notas adicionais", "recent_reports": "Relatórios recentes", "export_data": "Exportar dados",
        "export_csv": "Exportar CSV", "export_geojson": "Exportar GeoJSON", "active_volunteers": "Voluntários ativos",
        "rescue_teams": "Equipes de resgate", "online_users": "Online", "leaderboard": "Classificação",
        "chat": "Chat de crise", "type_message": "Digite uma mensagem...", "send": "Enviar",
        "click_building": "🏢 Clique em qualquer edifício no mapa para selecioná-lo!",
        "total_reports": "Total de relatórios", "today_reports": "Hoje", "pending_sync": "Pendentes de sincronização",
        "logout": "Sair", "sync_now": "Sincronizar agora", "sms_report": "Relatório SMS",
        "sms_placeholder": "Formato: DANO LAT LNG", "sms_send": "Enviar relatório SMS",
        "command_center": "Centro de comando", "analytics": "Painel de análise"
    },
    "ar": {
        "name": "العربية", "flag": "🇸🇦",
        "report_damage": "الإبلاغ عن ضرر", "damage_level": "مستوى الضرر",
        "minimal": "الحد الأدنى/بدون ضرر", "partial": "متضرر جزئيًا", "complete": "متضرر بالكامل",
        "infrastructure": "نوع البنية التحتية", "residential": "سكني", "commercial": "تجاري",
        "government": "حكومي", "utility": "مرفق عام", "transport": "المواصلات", "community": "مجتمعي",
        "public": "عام", "crisis": "نوع الأزمة", "earthquake": "زلزال", "flood": "فيضان",
        "tsunami": "تسونامي", "hurricane": "إعصار", "wildfire": "حريق غابات", "explosion": "انفجار",
        "conflict": "نزاع", "debris": "حطام؟", "yes": "نعم", "no": "لا", "submit": "إرسال التقرير",
        "gps_location": "استخدم نظام تحديد المواقع", "building_name": "اسم المبنى", "photo": "تحميل صورة",
        "notes": "ملاحظات إضافية", "recent_reports": "التقارير الأخيرة", "export_data": "تصدير البيانات",
        "export_csv": "تصدير CSV", "export_geojson": "تصدير GeoJSON", "active_volunteers": "المتطوعين النشطين",
        "rescue_teams": "فرق الإنقاذ", "online_users": "متصل", "leaderboard": "لوحة الصدارة",
        "chat": "دردشة الأزمات", "type_message": "اكتب رسالة...", "send": "إرسال",
        "click_building": "🏢 انقر فوق أي مبنى على الخريطة لتحديده!",
        "total_reports": "إجمالي التقارير", "today_reports": "اليوم", "pending_sync": "مزامنة معلقة",
        "logout": "تسجيل الخروج", "sync_now": "مزامنة الآن", "sms_report": "تقرير SMS",
        "sms_placeholder": "التنسيق: الضرر خط العرض خط الطول", "sms_send": "إرسال تقرير SMS",
        "command_center": "مركز القيادة", "analytics": "لوحة التحليلات"
    },
    "zh": {
        "name": "中文", "flag": "🇨🇳",
        "report_damage": "报告损坏", "damage_level": "损坏程度",
        "minimal": "最小/无损坏", "partial": "部分损坏", "complete": "完全损坏",
        "infrastructure": "基础设施类型", "residential": "住宅", "commercial": "商业",
        "government": "政府", "utility": "公用事业", "transport": "交通", "community": "社区",
        "public": "公共", "crisis": "危机类型", "earthquake": "地震", "flood": "洪水",
        "tsunami": "海啸", "hurricane": "飓风", "wildfire": "野火", "explosion": "爆炸",
        "conflict": "冲突", "debris": "碎片？", "yes": "是", "no": "否", "submit": "提交报告",
        "gps_location": "使用我的GPS", "building_name": "建筑名称", "photo": "上传照片",
        "notes": "附加说明", "recent_reports": "最近的报告", "export_data": "导出数据",
        "export_csv": "导出CSV", "export_geojson": "导出GeoJSON", "active_volunteers": "活跃志愿者",
        "rescue_teams": "救援队", "online_users": "在线", "leaderboard": "排行榜",
        "chat": "危机聊天", "type_message": "输入消息...", "send": "发送",
        "click_building": "🏢 单击地图上的任何建筑物以选择它！",
        "total_reports": "总报告", "today_reports": "今天", "pending_sync": "待同步",
        "logout": "登出", "sync_now": "立即同步", "sms_report": "短信报告",
        "sms_placeholder": "格式：损害 纬度 经度", "sms_send": "发送短信报告",
        "command_center": "指挥中心", "analytics": "分析仪表板"
    }
}

# ============================================
# LOGIN HTML
# ============================================
LOGIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>UNDP ImpactMapper - Login</title>
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
# DASHBOARD HTML (with fixed auth helper & export)
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
        /* (All CSS remains identical to the previous version; omitted for brevity but must be included) */
        /* ... full CSS from the 50/50 map-charts version ... */
    </style>
</head>
<body>
<!-- HTML structure identical to the 50/50 map-charts version -->
<script>
// ========== GLOBAL AUTH HELPER ==========
const credentials = localStorage.getItem('credentials') || ':';
const authHeader = 'Basic ' + btoa(credentials);

async function fetchAPI(url, options = {}) {
    const res = await fetch(url, {
        ...options,
        headers: {
            ...options.headers,
            'Authorization': authHeader
        }
    });
    if (res.status === 401) {
        window.location.href = '/';
        throw new Error('Unauthorized');
    }
    return res;
}

// ========== VARIABLES ==========
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

// ========== ADMIN STATS ==========
async function loadAdminStats() {
    const days = document.getElementById('analyticsDays').value;
    try {
        const res = await fetchAPI(`/api/admin/stats?days=${days}`);
        const data = await res.json();

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
            data: { labels: trendLabels.length ? trendLabels : ['No Data'], datasets: [{ label: 'Reports', data: trendData.length ? trendData : [0], borderColor: '#2ecc71', fill: true, backgroundColor: 'rgba(46,204,113,0.1)', tension: 0.4 }] },
            options: { responsive: true, maintainAspectRatio: true, plugins: { legend: { labels: { color: '#e0e0e0' } } }, scales: { x: { ticks: { color: '#aaa' } }, y: { ticks: { color: '#aaa' }, beginAtZero: true } } }
        });

        safeDestroy(damageChart);
        const damageLabels = data.by_damage.map(d => d.level);
        const damageData = data.by_damage.map(d => d.count);
        damageChart = new Chart(document.getElementById('damageChart'), {
            type: 'doughnut',
            data: { labels: damageLabels.length ? damageLabels : ['No Data'], datasets: [{ data: damageData.length ? damageData : [1], backgroundColor: ['#e74c3c', '#f39c12', '#2ecc71', '#3498db'] }] },
            options: { responsive: true, plugins: { legend: { labels: { color: '#e0e0e0' } } } }
        });

        safeDestroy(infraChart);
        const infraLabels = data.by_infrastructure.map(d => d.type);
        const infraData = data.by_infrastructure.map(d => d.count);
        infraChart = new Chart(document.getElementById('infraChart'), {
            type: 'bar',
            data: { labels: infraLabels.length ? infraLabels : ['No Data'], datasets: [{ label: 'Reports', data: infraData.length ? infraData : [0], backgroundColor: '#2ecc71', borderRadius: 8 }] },
            options: { responsive: true, maintainAspectRatio: true, plugins: { legend: { labels: { color: '#e0e0e0' } } }, scales: { x: { ticks: { color: '#aaa' } }, y: { ticks: { color: '#aaa' }, beginAtZero: true } } }
        });

        safeDestroy(crisisChart);
        const crisisLabels = data.by_crisis.map(d => d.crisis);
        const crisisData = data.by_crisis.map(d => d.count);
        crisisChart = new Chart(document.getElementById('crisisChart'), {
            type: 'bar',
            data: { labels: crisisLabels.length ? crisisLabels : ['No Data'], datasets: [{ label: 'Reports', data: crisisData.length ? crisisData : [0], backgroundColor: '#3498db', borderRadius: 8 }] },
            options: { responsive: true, maintainAspectRatio: true, plugins: { legend: { labels: { color: '#e0e0e0' } } }, scales: { x: { ticks: { color: '#aaa' } }, y: { ticks: { color: '#aaa' }, beginAtZero: true } } }
        });

        document.getElementById('reportersTable').querySelector('tbody').innerHTML = data.top_reporters.map((r,i) => `<tr><td style="padding:8px;">${i+1}</td><td style="padding:8px;">${r.username}</td><td style="padding:8px;">${r.reports}</td></tr>`).join('') || '<tr><td colspan="3" style="text-align:center;color:#666;">No data</td></tr>';
        document.getElementById('rolesTable').querySelector('tbody').innerHTML = data.users_by_role.map(r => `<tr><td style="padding:8px;">${r.role}</td><td style="padding:8px;">${r.count}</td></tr>`).join('') || '<tr><td colspan="2" style="text-align:center;color:#666;">No data</td></tr>';
    } catch(e) { console.error('Error loading analytics:', e); document.getElementById('totalReports').innerHTML = '⚠️ Error'; }
}

// ========== COMMAND CHARTS ==========
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

// ========== LANGUAGE ==========
async function setLanguage(lang) {
    currentLang = lang; localStorage.setItem('language', lang);
    try {
        const res = await fetch(`/api/lang/${lang}`);
        translations = await res.json();
        updateUITexts();
    } catch(e) { console.error(e); }
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

// ========== MAP ==========
function initMap() {
    const container = document.getElementById('map');
    if (!container) return;
    if (container.offsetHeight === 0) container.style.height = '400px';
    map = L.map('map', { center: [20, 0], zoom: 2, zoomControl: true, fadeAnimation: true });
    map.attributionControl.setPrefix('');
    const osmLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>', maxZoom: 19 });
    osmLayer.addTo(map);
    osmLayer.on('tileerror', function() { map.removeLayer(osmLayer); L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '&copy; OSM', maxZoom: 19 }).addTo(map); });
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

// ========== SMS REPORT ==========
async function sendSMSReport() {
    let smsText = document.getElementById('smsText').value, smsNumber = document.getElementById('smsNumber').value;
    let statusDiv = document.getElementById('smsStatus');
    if(!smsText) { statusDiv.innerText = 'Please enter SMS text'; return; }
    try {
        let fd = new FormData(); fd.append('sms_text', smsText); fd.append('sms_number', smsNumber);
        let res = await fetchAPI('/api/sms_report', { method:'POST', body:fd });
        let data = await res.json();
        if(data.status==='success') { statusDiv.innerHTML = '✅ SMS report sent!'; document.getElementById('smsText').value = ''; loadReports(); }
        else { statusDiv.innerHTML = '❌ '+data.message; }
    } catch(e) { statusDiv.innerHTML = '❌ Failed to send SMS'; }
}

// ========== PHOTO PREVIEW ==========
document.getElementById('photo').addEventListener('change', function(e) {
    let preview = document.getElementById('photoPreview');
    if(e.target.files && e.target.files[0]) {
        let reader = new FileReader();
        reader.onload = function(ev) { preview.innerHTML = `<img src="${ev.target.result}" style="max-width:100%; max-height:80px; border-radius:8px;">`; };
        reader.readAsDataURL(e.target.files[0]);
    } else { preview.innerHTML = ''; }
});

// ========== SUBMIT REPORT (with auth) ==========
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
        let res = await fetchAPI('/api/report', { method:'POST', body:fd });
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

// ========== SYNC ==========
async function syncOfflineReports() {
    if(offlineQueue.length===0) return;
    try {
        let res = await fetchAPI('/api/sync', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(offlineQueue) });
        if(res.ok) { offlineQueue = []; saveOfflineQueue(); loadReports(); showToast('Synced offline reports','success'); }
    } catch(e) { console.error(e); }
}

async function forceSync() { await syncOfflineReports(); }

// ========== LOAD REPORTS (with auth) ==========
async function loadReports() {
    try {
        let res = await fetchAPI('/api/reports');
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

// ========== USER INFO (FIXED) ==========
async function loadCurrentUser() {
    try {
        let res = await fetchAPI('/api/current_user');
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

// ========== LEADERBOARD ==========
async function loadLeaderboard() {
    try {
        let res = await fetchAPI('/api/leaderboard');
        let leaders = await res.json();
        let container = document.getElementById('leaderboardList');
        if (!container) return;
        container.innerHTML = leaders.map((l,i) => 
            `<div class="leaderboard-item"><span class="rank">${i+1}</span><span>${l.username}</span><span>🏆 ${l.points}</span></div>`
        ).join('');
    } catch(e) { console.warn('Leaderboard unavailable:', e.message); }
}

async function loadStats() { try { let res = await fetchAPI('/api/stats'); let stats = await res.json(); /* not used */ } catch(e){} }

// ========== EXPORT (FIXED) ==========
async function exportCSV() {
    try {
        const res = await fetchAPI('/api/reports/csv');
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'impact_reports.csv';
        a.click();
        URL.revokeObjectURL(url);
    } catch(e) { alert('Export failed'); }
}

async function exportGeoJSON() {
    try {
        const res = await fetchAPI('/api/reports/geojson');
        const data = await res.json();
        const blob = new Blob([JSON.stringify(data)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'reports.geojson';
        a.click();
        URL.revokeObjectURL(url);
    } catch(e) { alert('Export failed'); }
}

// ========== EVENT LISTENERS ==========
document.getElementById('pendingTasksCard').addEventListener('click', function() {
    let pendingCount = offlineQueue.length;
    if(pendingCount === 0) { alert('No pending tasks.'); return; }
    let msg = 'Pending reports to sync:\n';
    offlineQueue.forEach((r,i) => { msg += `${i+1}. ${r.building_name || 'Unnamed'} - ${r.damage_level} (${new Date(r.timestamp).toLocaleString()})\n`; });
    msg += '\nClick OK to sync now.';
    if(confirm(msg)) forceSync();
});

// (rest of the event listeners for urgent tasks, online/offline, chat, drag, sidebar toggle remain unchanged)
// ... (include them exactly as in the previous version) ...

// ========== INIT ==========
document.addEventListener('DOMContentLoaded', function() {
    initMap();
    loadCurrentUser();
    // loadReports() is called inside loadCurrentUser
    loadLeaderboard();
    loadStats();
    setInterval(() => loadReports(), 30000);
    setInterval(() => updateKPIs(), 10000);
    setInterval(() => updateCommandCenterCharts(), 15000);
    setInterval(() => loadLeaderboard(), 10000);
});
</script>
</body>
</html>
"""

# ============================================
# API ENDPOINTS (all unchanged)
# ============================================
# (All endpoints remain exactly the same as before, including /api/lang/{lang})
# ...
# End of file with Vercel handler and local dev block
