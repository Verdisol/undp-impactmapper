"""
GeoReport-DR: GIS-Based Crowdsourced Reporting Tool for Disaster Response
v1.0.0-dissertation
"""
from fastapi import FastAPI, Form, UploadFile, File, HTTPException, Depends
from fastapi.responses import HTMLResponse, FileResponse
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

from templates import LOGIN_HTML, DASHBOARD_HTML

PHOTOS_DIR = "/tmp/photos"
os.makedirs(PHOTOS_DIR, exist_ok=True)

APP_TITLE = "GeoReport-DR"
APP_VERSION = "1.0.0-dissertation"

security = HTTPBasic()

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
                report_type TEXT DEFAULT 'damage',
                severity TEXT DEFAULT 'medium',
                verification_status TEXT DEFAULT 'pending',
                verified_by TEXT,
                verified_at TEXT,
                assigned_to TEXT,
                resolved_at TEXT,
                report_source TEXT DEFAULT 'web',
                gps_accuracy_m REAL,
                duplicate_of TEXT,
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
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_reports_status ON reports (verification_status)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_reports_type ON reports (report_type)")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'viewer',
                created_at TEXT,
                phone_number TEXT
            )
        """)
        default_users = [
            ("admin",    hashlib.sha256("admin123".encode()).hexdigest(),  "admin",    "+1234567890"),
            ("reporter", hashlib.sha256("report123".encode()).hexdigest(), "reporter", "+1234567891"),
            ("viewer",   hashlib.sha256("view123".encode()).hexdigest(),   "viewer",   ""),
        ]
        for u in default_users:
            await conn.execute("""
                INSERT INTO users (username, password_hash, role, created_at, phone_number)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (username) DO NOTHING
            """, u[0], u[1], u[2], datetime.now().isoformat(), u[3])
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
        print("Database connected.")
    except Exception as e:
        print(f"Database connection failed: {e}")
    yield


app = FastAPI(title=APP_TITLE, version=APP_VERSION,
              lifespan=lifespan, redirect_slashes=False)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
        req = urllib.request.Request(overpass_url, data=params,
                                     headers={'User-Agent': 'GeoReport-DR/1.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
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


async def save_report(
    report_uuid: str, building_id: str, building_osm_id: str,
    building_name: str, building_address: str,
    damage_level: str, lat: float, lng: float,
    location_text: str, photo_path: str,
    infrastructure_type: str, crisis_nature: str,
    debris: str, notes: str, username: str,
    synced: int = 1, sms_number: str = "",
    report_type: str = "damage", severity: str = "medium",
    report_source: str = "web", gps_accuracy_m: float = None
):
    await init_db_once()
    conn = await get_db_conn()
    try:
        await conn.execute("""
            INSERT INTO reports (
                report_uuid, building_id, building_osm_id, building_name, building_address,
                damage_level, version, lat, lng, geom, location_text, photo_path,
                infrastructure_type, crisis_nature, debris, notes, username,
                timestamp, is_current, synced, sms_number,
                report_type, severity, report_source, gps_accuracy_m
            )
            VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9,
                CASE WHEN $9 IS NOT NULL AND $8 IS NOT NULL AND $9 != 0 AND $8 != 0
                     THEN ST_SetSRID(ST_MakePoint($9, $8), 4326)
                     ELSE NULL
                END,
                $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20,
                $21, $22, $23, $24
            )
        """, report_uuid, building_id, building_osm_id, building_name, building_address,
           damage_level, 1, lat, lng, location_text, photo_path,
           infrastructure_type, crisis_nature, debris, notes, username,
           datetime.now().isoformat(), 1, synced, sms_number,
           report_type, severity, report_source, gps_accuracy_m)
    finally:
        await conn.close()


async def get_reports_db(limit: int = 200):
    await init_db_once()
    conn = await get_db_conn()
    try:
        rows = await conn.fetch("""
            SELECT report_uuid, report_type, severity, verification_status,
                   damage_level, lat, lng, location_text, infrastructure_type,
                   building_name, building_address, crisis_nature, debris,
                   notes, timestamp, username, photo_path, gps_accuracy_m
            FROM reports WHERE is_current = 1
            ORDER BY timestamp DESC LIMIT $1
        """, limit)
        return [{
            "report_uuid": r[0], "report_type": r[1], "severity": r[2],
            "verification_status": r[3], "damage_level": r[4],
            "lat": r[5], "lng": r[6], "location_text": r[7] or "",
            "infrastructure_type": r[8], "building_name": r[9] or "",
            "building_address": r[10] or "", "crisis_nature": r[11],
            "debris": r[12], "notes": r[13] or "", "timestamp": r[14],
            "username": r[15],
            "photo_url": f"/photos/{os.path.basename(r[16])}" if r[16] else None,
            "gps_accuracy_m": r[17]
        } for r in rows]
    finally:
        await conn.close()


async def get_user_by_username(username: str):
    conn = await get_db_conn()
    try:
        return await conn.fetchrow(
            "SELECT password_hash, role FROM users WHERE username = $1", username)
    finally:
        await conn.close()


async def get_admin_stats(days: int = 30):
    await init_db_once()
    conn = await get_db_conn()
    try:
        date_filter = ""
        if days > 0:
            date_filter = f"AND timestamp::timestamp >= (NOW() - INTERVAL '{days} days')"
        total_reports = await conn.fetchval(
            f"SELECT COUNT(*) FROM reports WHERE is_current = 1 {date_filter}")
        total_users = await conn.fetchval(
            f"SELECT COUNT(DISTINCT username) FROM reports WHERE is_current = 1 {date_filter}")
        top_reporters = await conn.fetch(f"""
            SELECT username, COUNT(*) as reports FROM reports
            WHERE is_current = 1 {date_filter}
            GROUP BY username ORDER BY reports DESC LIMIT 10
        """)
        days_limit = min(days, 30) if days > 0 else 30
        daily_trend = await conn.fetch(f"""
            SELECT DATE(timestamp::timestamp) as date, COUNT(*) as count
            FROM reports WHERE is_current = 1
              AND timestamp::timestamp >= (NOW() - INTERVAL '{days_limit} days')
            GROUP BY DATE(timestamp::timestamp) ORDER BY date ASC
        """)
        by_damage = await conn.fetch(f"""
            SELECT damage_level, COUNT(*) as count FROM reports
            WHERE is_current = 1 {date_filter} GROUP BY damage_level
        """)
        by_infrastructure = await conn.fetch(f"""
            SELECT infrastructure_type, COUNT(*) as count FROM reports
            WHERE is_current = 1 AND infrastructure_type IS NOT NULL
              AND infrastructure_type != '' {date_filter}
            GROUP BY infrastructure_type ORDER BY count DESC LIMIT 10
        """)
        by_crisis = await conn.fetch(f"""
            SELECT crisis_nature, COUNT(*) as count FROM reports
            WHERE is_current = 1 AND crisis_nature IS NOT NULL
              AND crisis_nature != '' {date_filter}
            GROUP BY crisis_nature ORDER BY count DESC LIMIT 10
        """)
        by_type = await conn.fetch(f"""
            SELECT report_type, COUNT(*) as count FROM reports
            WHERE is_current = 1 {date_filter} GROUP BY report_type
        """)
        by_severity = await conn.fetch(f"""
            SELECT severity, COUNT(*) as count FROM reports
            WHERE is_current = 1 {date_filter} GROUP BY severity
        """)
        by_status = await conn.fetch(f"""
            SELECT verification_status, COUNT(*) as count FROM reports
            WHERE is_current = 1 {date_filter} GROUP BY verification_status
        """)
        return {
            "total_reports": total_reports or 0,
            "total_users": total_users or 0,
            "top_reporters": [{"username": r[0], "reports": r[1]} for r in top_reporters],
            "daily_trend": [{"date": r[0].isoformat(), "count": r[1]} for r in daily_trend],
            "by_damage": [{"level": r[0] or "unknown", "count": r[1]} for r in by_damage],
            "by_infrastructure": [{"type": r[0] or "unknown", "count": r[1]} for r in by_infrastructure],
            "by_crisis": [{"crisis": r[0] or "unknown", "count": r[1]} for r in by_crisis],
            "by_type": [{"type": r[0] or "unknown", "count": r[1]} for r in by_type],
            "by_severity": [{"severity": r[0] or "unknown", "count": r[1]} for r in by_severity],
            "by_status": [{"status": r[0] or "unknown", "count": r[1]} for r in by_status],
        }
    finally:
        await conn.close()


async def verify_user(credentials: HTTPBasicCredentials = Depends(security)):
    await init_db_once()
    row = await get_user_by_username(credentials.username)
    if not row:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    password_hash = hashlib.sha256(credentials.password.encode()).hexdigest()
    if password_hash != row[0]:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"username": credentials.username, "role": row[1]}


def require_admin(current_user: dict = Depends(verify_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


def require_reporter(current_user: dict = Depends(verify_user)):
    if current_user["role"] not in ["admin", "reporter"]:
        raise HTTPException(status_code=403, detail="Reporter access required")
    return current_user


@app.get("")
@app.get("/")
async def login_page():
    return HTMLResponse(LOGIN_HTML)


@app.get("/dashboard")
async def dashboard(current_user: dict = Depends(verify_user)):
    return HTMLResponse(DASHBOARD_HTML)


@app.get("/api/current_user")
async def get_current_user(current_user: dict = Depends(verify_user)):
    return current_user


@app.get("/api/building/{lat}/{lng}")
async def get_building_info(lat: float, lng: float):
    building = get_building_at_location(lat, lng)
    return building if building else None


@app.post("/api/report")
async def create_report(
    report_type: str = Form("damage"),
    severity: str = Form("medium"),
    damage_level: str = Form("minimal"),
    infrastructure_type: str = Form("residential"),
    building_name: str = Form(""),
    building_address: str = Form(""),
    building_osm_id: str = Form(""),
    crisis_nature: str = Form("earthquake"),
    debris: str = Form("no"),
    text_location: str = Form(""),
    lat: Optional[float] = Form(None),
    lng: Optional[float] = Form(None),
    gps_accuracy_m: Optional[float] = Form(None),
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
        infrastructure_type, crisis_nature, debris, notes,
        current_user['username'], 1, sms_number,
        report_type=report_type, severity=severity,
        report_source="web", gps_accuracy_m=gps_accuracy_m
    )
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
            await save_report(
                report_uuid, building_id, "", "", "",
                damage_level, lat, lng, "", None,
                "unknown", "earthquake", "no", notes,
                "sms_user", 1, sms_number,
                report_type="damage", severity="high", report_source="sms"
            )
            return {"status": "success", "message": "SMS report received",
                    "lat": lat, "lng": lng}
        except ValueError:
            return {"status": "error", "message": "Invalid coordinates"}
    return {"status": "error", "message": "Invalid SMS format. Use: DAMAGE_TYPE LAT LNG"}


@app.post("/api/sync")
async def sync_offline_reports(reports_data: List[Dict],
                               current_user: dict = Depends(require_reporter)):
    synced_count = 0
    for report in reports_data:
        try:
            conn = await get_db_conn()
            try:
                existing = await conn.fetchval(
                    "SELECT report_uuid FROM reports WHERE report_uuid = $1",
                    report.get('report_uuid'))
                if not existing:
                    await conn.execute("""
                        INSERT INTO reports (
                            report_uuid, building_id, damage_level, lat, lng, geom,
                            location_text, infrastructure_type, building_name,
                            crisis_nature, debris, notes, username, timestamp,
                            synced, is_current, report_type, severity, report_source
                        )
                        VALUES (
                            $1, $2, $3, $4, $5,
                            CASE WHEN $5 IS NOT NULL AND $4 IS NOT NULL AND $5 != 0 AND $4 != 0
                                 THEN ST_SetSRID(ST_MakePoint($5, $4), 4326)
                                 ELSE NULL
                            END,
                            $6, $7, $8, $9, $10, $11, $12, $13, $14, $15,
                            $16, $17, $18
                        )
                    """, report.get('report_uuid'), report.get('building_id'),
                        report.get('damage_level'), report.get('lat'), report.get('lng'),
                        report.get('location_text'), report.get('infrastructure_type'),
                        report.get('building_name'), report.get('crisis_nature'),
                        report.get('debris'), report.get('notes'),
                        current_user['username'], report.get('timestamp'),
                        1, 1,
                        report.get('report_type', 'damage'),
                        report.get('severity', 'medium'),
                        'offline')
                    synced_count += 1
            finally:
                await conn.close()
        except Exception as e:
            print(f"Sync error: {e}")
    return {"synced": synced_count}


@app.get("/api/reports")
async def get_reports(limit: int = 200, current_user: dict = Depends(verify_user)):
    return await get_reports_db(limit)


@app.get("/api/reports/pending")
async def pending_reports(current_user: dict = Depends(require_reporter)):
    conn = await get_db_conn()
    try:
        rows = await conn.fetch("""
            SELECT report_uuid, report_type, damage_level, severity,
                   lat, lng, notes, timestamp, username, photo_path, building_name
            FROM reports
            WHERE verification_status = 'pending' AND is_current = 1
            ORDER BY
              CASE severity WHEN 'critical' THEN 1
                            WHEN 'high' THEN 2
                            WHEN 'medium' THEN 3
                            ELSE 4 END,
              timestamp DESC
        """)
        return [dict(r) for r in rows]
    finally:
        await conn.close()


@app.post("/api/report/{report_uuid}/verify")
async def verify_report(report_uuid: str, action: str = Form(...),
                        current_user: dict = Depends(require_reporter)):
    if action not in ["verified", "rejected", "assigned", "resolved"]:
        raise HTTPException(status_code=400, detail="Invalid action")
    conn = await get_db_conn()
    try:
        if action == "resolved":
            await conn.execute("""
                UPDATE reports SET verification_status = $1,
                       resolved_at = $2, verified_by = $3
                WHERE report_uuid = $4
            """, action, datetime.now().isoformat(),
                 current_user['username'], report_uuid)
        else:
            await conn.execute("""
                UPDATE reports SET verification_status = $1,
                       verified_by = $2, verified_at = $3
                WHERE report_uuid = $4
            """, action, current_user['username'],
                 datetime.now().isoformat(), report_uuid)
        return {"status": "ok", "action": action, "report_uuid": report_uuid}
    finally:
        await conn.close()


@app.get("/api/spatial/nearest")
async def nearest_reports(lat: float, lng: float, k: int = 5,
                          current_user: dict = Depends(verify_user)):
    conn = await get_db_conn()
    try:
        rows = await conn.fetch("""
            SELECT report_uuid, building_name, damage_level, report_type, severity,
                   ST_Distance(geom::geography,
                       ST_SetSRID(ST_MakePoint($1, $2), 4326)::geography) AS distance_m
            FROM reports WHERE is_current = 1 AND geom IS NOT NULL
            ORDER BY geom <-> ST_SetSRID(ST_MakePoint($1, $2), 4326) LIMIT $3
        """, lng, lat, k)
        return [dict(r) for r in rows]
    finally:
        await conn.close()


@app.get("/api/spatial/within")
async def reports_within(lat: float, lng: float, radius_m: int = 500,
                         current_user: dict = Depends(verify_user)):
    conn = await get_db_conn()
    try:
        rows = await conn.fetch("""
            SELECT report_uuid, building_name, damage_level, report_type, severity,
                   ST_Distance(geom::geography,
                       ST_SetSRID(ST_MakePoint($1, $2), 4326)::geography) AS distance_m
            FROM reports
            WHERE is_current = 1
              AND ST_DWithin(geom::geography,
                  ST_SetSRID(ST_MakePoint($1, $2), 4326)::geography, $3)
            ORDER BY distance_m
        """, lng, lat, radius_m)
        return [dict(r) for r in rows]
    finally:
        await conn.close()


@app.get("/api/spatial/clusters")
async def damage_clusters(eps_m: int = 100, min_points: int = 3,
                          current_user: dict = Depends(verify_user)):
    conn = await get_db_conn()
    try:
        rows = await conn.fetch("""
            WITH clustered AS (
                SELECT report_uuid, damage_level, severity, geom,
                       ST_ClusterDBSCAN(geom, eps := $1 / 111320.0,
                                        minpoints := $2) OVER () AS cluster_id
                FROM reports WHERE is_current = 1 AND geom IS NOT NULL
            )
            SELECT cluster_id, COUNT(*) AS report_count,
                   ST_Y(ST_Centroid(ST_Collect(geom))) AS center_lat,
                   ST_X(ST_Centroid(ST_Collect(geom))) AS center_lng,
                   SUM(CASE WHEN damage_level = 'complete' THEN 1 ELSE 0 END) AS complete_damage,
                   SUM(CASE WHEN severity = 'critical' THEN 1 ELSE 0 END) AS critical_count
            FROM clustered WHERE cluster_id IS NOT NULL
            GROUP BY cluster_id ORDER BY report_count DESC
        """, eps_m, min_points)
        return [dict(r) for r in rows]
    finally:
        await conn.close()


@app.get("/api/reports/geojson")
async def get_geojson(current_user: dict = Depends(require_reporter)):
    conn = await get_db_conn()
    try:
        rows = await conn.fetch("""
            SELECT jsonb_build_object(
                'type', 'Feature',
                'geometry', ST_AsGeoJSON(geom)::jsonb,
                'properties', jsonb_build_object(
                    'report_uuid', report_uuid,
                    'report_type', report_type,
                    'severity', severity,
                    'verification_status', verification_status,
                    'building_name', building_name,
                    'damage_level', damage_level,
                    'infrastructure_type', infrastructure_type,
                    'crisis_nature', crisis_nature,
                    'timestamp', timestamp,
                    'username', username
                )
            ) AS feature
            FROM reports WHERE is_current = 1 AND geom IS NOT NULL
        """)
        features = [r["feature"] for r in rows]
        return {"type": "FeatureCollection", "features": features}
    finally:
        await conn.close()


@app.get("/api/reports/csv")
async def export_csv(current_user: dict = Depends(require_reporter)):
    conn = await get_db_conn()
    try:
        rows = await conn.fetch("""
            SELECT report_uuid, report_type, severity, verification_status,
                   damage_level, lat, lng, building_name, building_address,
                   infrastructure_type, crisis_nature, debris, notes,
                   timestamp, username, gps_accuracy_m
            FROM reports WHERE is_current = 1 ORDER BY timestamp DESC
        """)
        csv = ("report_uuid,report_type,severity,verification_status,damage_level,"
               "latitude,longitude,building_name,building_address,"
               "infrastructure_type,crisis_nature,debris,notes,timestamp,"
               "username,gps_accuracy_m\n")
        for r in rows:
            lat_val = f"{r[5]:.6f}" if r[5] else ""
            lng_val = f"{r[6]:.6f}" if r[6] else ""
            acc_val = f"{r[15]:.1f}" if r[15] else ""
            csv += (f"{r[0]},{r[1]},{r[2]},{r[3]},{r[4]},{lat_val},{lng_val},"
                    f"\"{r[7] or ''}\",\"{r[8] or ''}\",{r[9]},{r[10]},{r[11]},"
                    f"\"{r[12] or ''}\",{r[13]},{r[14]},{acc_val}\n")
        return HTMLResponse(csv, media_type="text/csv",
                            headers={"Content-Disposition":
                                     "attachment; filename=georeport_dr_reports.csv"})
    finally:
        await conn.close()


@app.get("/api/situation-report")
async def situation_report(hours: int = 24,
                           current_user: dict = Depends(require_reporter)):
    conn = await get_db_conn()
    try:
        since = (datetime.now() - timedelta(hours=hours)).isoformat()
        summary = await conn.fetchrow("""
            SELECT
              COUNT(*) FILTER (WHERE report_type='damage') AS damage_reports,
              COUNT(*) FILTER (WHERE report_type='need')   AS need_reports,
              COUNT(*) FILTER (WHERE report_type='hazard') AS hazard_reports,
              COUNT(*) FILTER (WHERE report_type='status') AS status_reports,
              COUNT(*) FILTER (WHERE severity='critical')  AS critical_count,
              COUNT(*) FILTER (WHERE verification_status='verified') AS verified,
              COUNT(*) FILTER (WHERE verification_status='resolved') AS resolved,
              COUNT(*) AS total
            FROM reports WHERE is_current=1 AND timestamp >= $1
        """, since)
        by_area = await conn.fetch("""
            SELECT
              ST_AsText(ST_SnapToGrid(geom, 0.01)) AS grid_cell,
              COUNT(*) AS count,
              SUM(CASE WHEN severity='critical' THEN 1 ELSE 0 END) AS critical
            FROM reports
            WHERE is_current=1 AND timestamp >= $1 AND geom IS NOT NULL
            GROUP BY grid_cell ORDER BY count DESC LIMIT 20
        """, since)
        return {
            "generated_at": datetime.now().isoformat(),
            "window_hours": hours,
            "summary": dict(summary),
            "hotspots": [dict(r) for r in by_area]
        }
    finally:
        await conn.close()


@app.get("/api/research/metrics")
async def research_metrics(current_user: dict = Depends(require_admin)):
    conn = await get_db_conn()
    try:
        latency = await conn.fetchval("""
            SELECT AVG(EXTRACT(EPOCH FROM
                (verified_at::timestamp - timestamp::timestamp))/60)
            FROM reports WHERE verified_at IS NOT NULL
        """)
        completeness = await conn.fetchrow("""
            SELECT
              AVG(CASE WHEN photo_path IS NOT NULL THEN 1 ELSE 0 END) AS photo_rate,
              AVG(CASE WHEN notes != '' THEN 1 ELSE 0 END) AS notes_rate,
              AVG(CASE WHEN building_name != '' THEN 1 ELSE 0 END) AS name_rate
            FROM reports WHERE is_current=1
        """)
        dup_rate = await conn.fetchval("""
            SELECT COUNT(*) FROM (
              SELECT a.report_uuid FROM reports a
              JOIN reports b ON a.report_uuid < b.report_uuid
                AND a.report_type = b.report_type
                AND ST_DWithin(a.geom::geography, b.geom::geography, 20)
              WHERE a.is_current=1 AND b.is_current=1
            ) x
        """)
        gps = await conn.fetchrow("""
            SELECT AVG(gps_accuracy_m) AS mean_accuracy,
                   PERCENTILE_CONT(0.5) WITHIN GROUP
                     (ORDER BY gps_accuracy_m) AS median_accuracy,
                   COUNT(*) AS samples
            FROM reports WHERE gps_accuracy_m IS NOT NULL
        """)
        return {
            "mean_verification_latency_min": latency,
            "photo_attachment_rate": completeness['photo_rate'],
            "notes_completion_rate": completeness['notes_rate'],
            "building_name_rate": completeness['name_rate'],
            "duplicate_reports": dup_rate,
            "gps_mean_accuracy_m": gps['mean_accuracy'],
            "gps_median_accuracy_m": gps['median_accuracy'],
            "gps_samples": gps['samples'],
        }
    finally:
        await conn.close()


@app.get("/api/admin/stats")
async def admin_stats(days: int = 7, current_user: dict = Depends(require_admin)):
    return await get_admin_stats(days)


@app.get("/photos/{filename}")
async def serve_photo(filename: str):
    file_path = os.path.join(PHOTOS_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="Photo not found")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
