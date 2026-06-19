from fastapi import FastAPI, Form, UploadFile, File, HTTPException, Depends
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import os
import json
import hashlib
import uuid
import csv
import io
from datetime import datetime
from typing import Optional, Dict, List

# ============================================
# PHOTO STORAGE (Vercel uses /tmp)
# ============================================
PHOTOS_DIR = "/tmp/photos"
os.makedirs(PHOTOS_DIR, exist_ok=True)

security = HTTPBasic()

# ============================================
# CREATE FASTAPI APP
# ============================================
app = FastAPI(title="UNDP ImpactMapper", version="28.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage (replace with PostgreSQL later)
reports_db = []
users_db = [
    {"username": "admin", "password_hash": hashlib.sha256("admin123".encode()).hexdigest(), "role": "admin", "avatar": "👑", "color": "#e74c3c", "points": 5000, "badge": "🏆 Master Responder"},
    {"username": "reporter", "password_hash": hashlib.sha256("report123".encode()).hexdigest(), "role": "reporter", "avatar": "📸", "color": "#2ecc71", "points": 1250, "badge": "⭐ Senior Responder"},
    {"username": "viewer", "password_hash": hashlib.sha256("view123".encode()).hexdigest(), "role": "viewer", "avatar": "👁️", "color": "#3498db", "points": 0, "badge": "🆕 Citizen Reporter"},
]

# ============================================
# AUTHENTICATION
# ============================================
async def verify_user(credentials: HTTPBasicCredentials = Depends(security)):
    for user in users_db:
        if user["username"] == credentials.username:
            password_hash = hashlib.sha256(credentials.password.encode()).hexdigest()
            if password_hash == user["password_hash"]:
                return user
    raise HTTPException(status_code=401, detail="Invalid credentials")

# ============================================
# LANGUAGES
# ============================================
LANGUAGES = {
    "en": {
        "name": "English", "flag": "🇬🇧",
        "total_reports": "Total Reports", "today_reports": "Today",
        "pending_sync": "Pending Sync", "logout": "Logout",
    },
    "fr": {
        "name": "Français", "flag": "🇫🇷",
        "total_reports": "Total des rapports", "today_reports": "Aujourd'hui",
        "pending_sync": "En attente", "logout": "Déconnexion",
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
      localStorage.setItem('credentials', credentials);
      window.location.href = '/dashboard';
    } else {
      alert('Invalid credentials');
    }
  } catch (e) {
    alert('Login failed: ' + e.message);
  }
}
</script>
</body>
</html>
"""

# ============================================
# DASHBOARD HTML
# ============================================
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>UNDP ImpactMapper - Dashboard</title>
<style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'Segoe UI', Arial, sans-serif; background: #f4f6f8; padding: 20px; }
    .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px; background: white; padding: 15px 20px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
    .header h1 { color: #2c3e50; font-size: 24px; }
    .user-info { display: flex; align-items: center; gap: 10px; }
    .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 25px; }
    .stat-card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
    .stat-card h4 { color: #7f8c8d; font-size: 12px; text-transform: uppercase; }
    .stat-number { font-size: 32px; font-weight: bold; color: #2c3e50; }
    .panel { background: white; border-radius: 10px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
    .panel h3 { color: #34495e; border-bottom: 3px solid #27ae60; padding-bottom: 10px; margin-bottom: 15px; }
    .damage-list { max-height: 400px; overflow-y: auto; }
    .damage-item { padding: 12px; border-bottom: 1px solid #ecf0f1; display: flex; justify-content: space-between; align-items: center; }
    .badge { padding: 6px 12px; border-radius: 15px; font-size: 11px; font-weight: bold; color: white; background: #95a5a6; }
    .badge.minimal { background: #f1c40f; color: #333; }
    .badge.partial { background: #e67e22; }
    .badge.complete { background: #e74c3c; }
    button { padding: 10px 20px; background: #27ae60; color: white; border: none; border-radius: 6px; font-size: 14px; cursor: pointer; }
    button:hover { background: #219a52; }
    button.danger { background: #e74c3c; }
    .buttons { display: flex; gap: 10px; margin-top: 15px; }
</style>
</head>
<body>
<div class="header">
  <h1>🌍 UNDP ImpactMapper</h1>
  <div class="user-info" id="userInfo"></div>
  <button class="danger" onclick="logout()">🚪 Logout</button>
</div>

<div class="stats-grid" id="statsRow"></div>

<div class="panel">
  <h3>📋 Recent Damage Reports</h3>
  <div class="damage-list" id="reportsList">Loading...</div>
</div>

<div class="buttons">
  <button onclick="window.location.href='/report'">➕ New Report</button>
  <button onclick="window.open('/api/export/csv')">📥 Export CSV</button>
</div>

<script>
const authHeader = 'Basic ' + (localStorage.getItem('credentials') || ':');

async function fetchAPI(url) {
  const res = await fetch(url, { headers: { 'Authorization': authHeader } });
  if (res.status === 401) { window.location.href = '/'; return null; }
  return res.json();
}

async function loadDashboard() {
  const user = await fetchAPI('/api/current_user');
  if (!user) return;
  document.getElementById('userInfo').innerHTML = `<span>${user.avatar}</span> <strong>${user.username}</strong> · ${user.points} pts · ${user.badge}`;
  
  const stats = await fetchAPI('/api/stats');
  document.getElementById('statsRow').innerHTML = `
    <div class="stat-card"><h4>Total Reports</h4><div class="stat-number">${stats.total_reports}</div></div>
    <div class="stat-card"><h4>Today</h4><div class="stat-number">${stats.today_reports}</div></div>
    <div class="stat-card"><h4>Pending Sync</h4><div class="stat-number">${stats.pending_sync}</div></div>
  `;
  
  const reports = await fetchAPI('/api/reports');
  const list = document.getElementById('reportsList');
  if (reports.length === 0) {
    list.innerHTML = '<p>No reports yet. Be the first to report!</p>';
  } else {
    list.innerHTML = reports.map(r => `
      <div class="damage-item">
        <div>
          <b>${r.building_name || r.infrastructure_type || 'Unknown'}</b>
          <small>${r.location_text}</small>
          <div>${r.damage_level} · ${r.crisis_nature} · ${r.timestamp}</div>
        </div>
        <span class="badge ${r.damage_level.toLowerCase().replace(/ /g,'')}">${r.damage_level}</span>
      </div>
    `).join('');
  }
}

function logout() {
  localStorage.removeItem('credentials');
  window.location.href = '/';
}

loadDashboard();
</script>
</body>
</html>
"""

# ============================================
# ROUTES
# ============================================
@app.get("/", response_class=HTMLResponse)
async def home():
    return LOGIN_HTML

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    return DASHBOARD_HTML

@app.get("/api/current_user")
async def current_user(user = Depends(verify_user)):
    return user

@app.get("/api/reports")
async def get_reports():
    return reports_db[-50:]  # Last 50 reports

@app.get("/api/stats")
async def get_stats():
    today = datetime.now().date().isoformat()
    today_count = sum(1 for r in reports_db if r.get("timestamp", "").startswith(today))
    return {
        "total_reports": len(reports_db),
        "today_reports": today_count,
        "pending_sync": 0
    }

@app.post("/api/report")
async def create_report(
    damage_level: str = Form(...),
    infrastructure_type: str = Form(...),
    building_name: str = Form(""),
    crisis_nature: str = Form(...),
    debris: str = Form(...),
    text_location: str = Form(""),
    lat: Optional[float] = Form(None),
    lng: Optional[float] = Form(None),
    notes: str = Form(""),
    current_user: dict = Depends(verify_user)
):
    report = {
        "report_uuid": str(uuid.uuid4())[:8],
        "damage_level": damage_level,
        "infrastructure_type": infrastructure_type,
        "building_name": building_name,
        "crisis_nature": crisis_nature,
        "debris": debris,
        "location_text": text_location,
        "lat": lat or 0,
        "lng": lng or 0,
        "notes": notes,
        "username": current_user["username"],
        "timestamp": datetime.now().isoformat(),
        "photo_url": None
    }
    reports_db.append(report)
    return {"status": "success", "report_uuid": report["report_uuid"]}

@app.get("/api/export/csv")
async def export_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["uuid","damage","lat","lng","location","infrastructure","crisis","timestamp","username"])
    for r in reports_db:
        writer.writerow([r["report_uuid"], r["damage_level"], r["lat"], r["lng"], r["location_text"],
                         r["infrastructure_type"], r["crisis_nature"], r["timestamp"], r["username"]])
    return HTMLResponse(content=output.getvalue(), media_type="text/csv",
                        headers={"Content-Disposition": "attachment; filename=reports.csv"})

@app.get("/api/lang/{lang}")
async def get_language(lang: str):
    return LANGUAGES.get(lang, LANGUAGES["en"])

@app.get("/health")
async def health():
    return {"status": "ok", "reports": len(reports_db)}
