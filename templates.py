"""HTML templates for GeoReport-DR."""

LOGIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>GeoReport-DR — Disaster Reporting Platform</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: 'Inter', sans-serif; min-height: 100vh;
       background: linear-gradient(135deg, #0a1a0f 0%, #061018 100%);
       position: relative; overflow-x: hidden; }
.hero-bg { position: fixed; inset: 0;
    background-image: url('https://images.unsplash.com/photo-1582213782179-e0d53f98f2ca?w=1600');
    background-size: cover; background-position: center 30%;
    opacity: 0.10; z-index: 0; }
.container { position: relative; z-index: 1; max-width: 1400px;
    margin: 0 auto; padding: 40px 60px; min-height: 100vh;
    display: flex; flex-direction: column; }
.navbar { display: flex; justify-content: space-between; align-items: center;
    padding: 20px 0; margin-bottom: 80px; flex-wrap: wrap; gap: 20px; }
.logo h1 { font-size: 26px; font-weight: 700; color: white; }
.logo span { color: #2ecc71; }
.logo p { font-size: 12px; color: #aaa; margin-top: 4px; }
.hero-section { display: flex; justify-content: space-between;
    align-items: center; gap: 60px; flex-wrap: wrap; margin-bottom: 80px; }
.hero-left { flex: 1; min-width: 300px; }
.hero-badge { display: inline-block; background: rgba(46,204,113,0.15);
    border: 1px solid rgba(46,204,113,0.4); padding: 6px 16px;
    border-radius: 30px; font-size: 12px; color: #2ecc71;
    margin-bottom: 24px; }
.hero-left h1 { font-size: 52px; font-weight: 800; line-height: 1.2;
    margin-bottom: 20px;
    background: linear-gradient(135deg, #fff, #2ecc71);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.hero-left p { font-size: 17px; color: #ccc; line-height: 1.6;
    margin-bottom: 32px; max-width: 600px; }
.features { display: flex; gap: 24px; flex-wrap: wrap; margin-top: 24px; }
.feature-item { font-size: 13px; color: #aaa; }
.feature-item strong { color: #2ecc71; }
.hero-right { flex: 0.8; min-width: 350px; }
.login-card { background: rgba(17, 17, 17, 0.95);
    backdrop-filter: blur(15px); border-radius: 16px; padding: 40px;
    border: 1px solid rgba(46,204,113,0.3);
    box-shadow: 0 25px 50px rgba(0,0,0,0.3); }
.login-card h2 { font-size: 22px; font-weight: 700; margin-bottom: 8px; }
.login-card p { font-size: 13px; color: #888; margin-bottom: 24px; }
.input-group { margin-bottom: 14px; }
.input-group input { width: 100%; padding: 14px 16px; background: #2a2a2a;
    border: 1px solid #3a3a3a; border-radius: 12px; color: white;
    font-size: 14px; }
.input-group input:focus { outline: none; border-color: #2ecc71;
    box-shadow: 0 0 0 3px rgba(46,204,113,0.2); }
.login-btn { width: 100%; padding: 14px;
    background: linear-gradient(135deg, #2ecc71, #27ae60);
    color: white; font-weight: 700; border: none; border-radius: 12px;
    font-size: 16px; cursor: pointer; margin-top: 8px; }
.demo-info { margin-top: 24px; padding-top: 20px;
    border-top: 1px solid #2a2a2a; text-align: center; }
.demo-info p { font-size: 11px; color: #666; margin-bottom: 8px; }
.demo-badge { display: inline-flex; gap: 12px; justify-content: center;
    flex-wrap: wrap; }
.demo-role { background: rgba(46,204,113,0.1); padding: 4px 12px;
    border-radius: 20px; font-size: 11px; color: #2ecc71; }
.footer { margin-top: auto; padding: 30px 0 20px; text-align: center;
    border-top: 1px solid rgba(255,255,255,0.05); }
.footer p { font-size: 12px; color: #666; }
@media (max-width: 968px) { .container { padding: 20px 30px; }
    .hero-section { flex-direction: column; }
    .hero-left h1 { font-size: 38px; } }
</style>
</head>
<body>
<div class="hero-bg"></div>
<div class="container">
    <div class="navbar">
        <div class="logo">
            <h1>🌍 Geo<span>Report-DR</span></h1>
            <p>Crowdsourced Disaster Reporting &amp; Triage System</p>
        </div>
    </div>
    <div class="hero-section">
        <div class="hero-left">
            <div class="hero-badge">🎓 Research Prototype — v1.0.0-dissertation</div>
            <h1>GEOTAGGED<br>DISASTER REPORTING</h1>
            <p>A GIS-based crowdsourced reporting platform that captures
               real-time GPS-tagged reports of damage, needs, hazards, and
               status updates during disasters — enabling faster, evidence-based
               response coordination.</p>
            <div class="features">
                <div class="feature-item"><strong>📸</strong> Photo-tagged reports</div>
                <div class="feature-item"><strong>📍</strong> GPS + map-pin fallback</div>
                <div class="feature-item"><strong>📶</strong> Offline-first sync</div>
                <div class="feature-item"><strong>📱</strong> SMS fallback</div>
                <div class="feature-item"><strong>✅</strong> Verification workflow</div>
            </div>
        </div>
        <div class="hero-right">
            <div class="login-card">
                <h2>Access Platform</h2>
                <p>Login to submit or triage disaster reports</p>
                <div class="input-group"><input type="text" id="username" placeholder="Username"></div>
                <div class="input-group"><input type="password" id="password" placeholder="Password"></div>
                <button class="login-btn" onclick="login()">🔐 Login</button>
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
        <p>© <span id="currentYear"></span> GeoReport-DR — Dissertation Prototype</p>
    </div>
</div>
<script>
document.getElementById('currentYear').innerText = new Date().getFullYear();
async function login() {
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const errorDiv = document.getElementById('errorMsg');
    if (!username || !password) {
        errorDiv.innerText = 'Please enter username and password'; return;
    }
    try {
        const response = await fetch('/dashboard', {
            headers: { 'Authorization': 'Basic ' + btoa(username + ':' + password) }
        });
        if (response.ok) { window.location.href = '/dashboard'; }
        else { errorDiv.innerText = 'Invalid credentials'; }
    } catch(e) { errorDiv.innerText = 'Login failed'; }
}
document.getElementById('password').addEventListener('keypress',
    function(e) { if (e.key === 'Enter') login(); });
</script>
</body>
</html>
"""


DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>GeoReport-DR — Situation Console</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body { height: 100%; overflow: hidden; }
body { font-family: 'Inter', sans-serif; background: #0e1116; color: #e0e0e0; }
.leaflet-control-attribution { display: none !important; }
.system-bar { background: #10241a; padding: 10px 24px;
    display: flex; justify-content: space-between; align-items: center;
    border-bottom: 2px solid #2ecc71; height: 64px; flex-shrink: 0; }
.brand h1 { font-size: 1.2rem; font-weight: 700; color: white; }
.brand h1 span { color: #2ecc71; }
.brand p { font-size: 0.7rem; color: rgba(255,255,255,0.6); margin-top: 2px; }
.controls-right { display: flex; gap: 8px; align-items: center; }
.btn { height: 34px; padding: 6px 14px; border-radius: 6px;
    font-size: 0.82rem; font-weight: 600; background: rgba(255,255,255,0.9);
    color: #000; border: 1px solid rgba(0,0,0,0.1); cursor: pointer;
    display: inline-flex; align-items: center; gap: 6px;
    text-decoration: none; white-space: nowrap; }
.btn:hover { background: #fff; }
.btn-danger { background: rgba(255,200,200,0.9); color: #b00000; }
.tabs-container { background: #151922; padding: 0 16px;
    border-bottom: 1px solid #222732; display: flex; gap: 4px;
    flex-shrink: 0; height: 46px; }
.tab-btn { padding: 12px 22px; background: transparent; color: #8a93a6;
    border: none; border-bottom: 3px solid transparent; font-size: 0.92rem;
    font-weight: 600; cursor: pointer; }
.tab-btn.active { color: #2ecc71; border-bottom-color: #2ecc71;
    background: rgba(46,204,113,0.08); }
#commandTab { display: flex; flex-direction: column;
    height: calc(100vh - 110px); overflow: hidden; }
.kpi-row { display: grid; grid-template-columns: repeat(4, 1fr);
    gap: 10px; padding: 10px 16px; flex-shrink: 0; }
.kpi-card { background: #171b23; border-radius: 8px; padding: 12px 14px;
    border-left: 3px solid #2ecc71; }
.kpi-header { display: flex; justify-content: space-between;
    align-items: center; margin-bottom: 6px; }
.kpi-header span { font-size: 0.72rem; color: #8a93a6;
    text-transform: uppercase; letter-spacing: 0.5px; }
.kpi-value { font-size: 1.5rem; font-weight: 700; }
.kpi-value.warning { color: #f39c12; }
.kpi-sub { font-size: 0.72rem; color: #8a93a6; margin-top: 4px; }
.main-layout { display: grid; grid-template-columns: 400px 1fr;
    flex: 1; overflow: hidden; min-height: 0; }
.sidebar { background: #151922; overflow-y: auto; padding: 14px;
    border-right: 1px solid #222732; min-width: 0; }
.sidebar::-webkit-scrollbar { width: 6px; }
.sidebar::-webkit-scrollbar-thumb { background: #2ecc71;
    border-radius: 10px; }
.sidebar.collapsed { display: none; }
.right-panel { display: flex; flex-direction: column;
    overflow: hidden; min-height: 0; min-width: 0; }
.map-container { flex: 1; min-height: 0; position: relative; }
#map { height: 100% !important; width: 100% !important; }
.charts-section { flex: 0 0 180px; background: #171b23;
    border-top: 1px solid #222732; padding: 10px 14px;
    display: flex; flex-direction: column; }
.charts-title { font-size: 0.8rem; font-weight: 700; color: #8a93a6;
    text-transform: uppercase; letter-spacing: 1px;
    margin-bottom: 8px; flex-shrink: 0; }
.charts-grid { display: grid; grid-template-columns: repeat(3, 1fr);
    gap: 10px; flex: 1; min-height: 0; }
.chart-container { background: #0e1116; border-radius: 6px;
    padding: 6px; display: flex; flex-direction: column;
    justify-content: center; min-height: 0; }
.chart-container h4 { text-align: center; margin-bottom: 4px;
    color: #8a93a6; font-size: 0.7rem; }
canvas { width: 100% !important; max-height: 110px; }
.card { background: #1a1f28; border-radius: 10px; padding: 14px;
    margin-bottom: 12px; border: 1px solid #222732; }
.card h3 { color: #2ecc71; margin-bottom: 10px; font-size: 1rem;
    display: flex; align-items: center; gap: 8px; }
label { display: block; font-size: 0.72rem; color: #8a93a6;
    margin-top: 8px; margin-bottom: 4px; text-transform: uppercase;
    letter-spacing: 0.5px; }
input, select, textarea { width: 100%; padding: 9px 11px;
    background: #0e1116; border: 1px solid #2a3040; border-radius: 7px;
    color: #e0e0e0; font-size: 0.9rem; font-family: inherit; }
input:focus, select:focus, textarea:focus { outline: none;
    border-color: #2ecc71; }
button.primary { background: linear-gradient(135deg, #2ecc71, #27ae60);
    color: white; padding: 11px; font-weight: 700; border: none;
    border-radius: 8px; cursor: pointer; width: 100%; margin-top: 10px;
    font-size: 0.95rem; }
button.secondary { background: #2a3040; color: white; padding: 9px;
    font-weight: 600; border: none; border-radius: 8px; cursor: pointer;
    width: 100%; margin-top: 6px; font-size: 0.85rem; }
.rt-tabs { display: grid; grid-template-columns: repeat(4, 1fr);
    gap: 4px; margin-bottom: 10px; }
.rt-tab { padding: 8px 4px; background: #0e1116; color: #8a93a6;
    border: 1px solid #2a3040; border-radius: 6px; cursor: pointer;
    font-size: 0.72rem; font-weight: 600; }
.rt-tab.active { background: rgba(46,204,113,0.15); color: #2ecc71;
    border-color: #2ecc71; }
.reports-list { max-height: 240px; overflow-y: auto; }
.report-item { background: #0e1116; padding: 9px 11px; margin: 6px 0;
    border-radius: 7px; border-left: 3px solid #2ecc71; cursor: pointer;
    font-size: 0.85rem; }
.report-item.sev-critical { border-left-color: #e74c3c; }
.report-item.sev-high { border-left-color: #e67e22; }
.report-item.sev-medium { border-left-color: #f39c12; }
.report-item .ri-head { display: flex; justify-content: space-between;
    margin-bottom: 3px; }
.report-item .ri-type { font-size: 0.68rem; color: #8a93a6;
    text-transform: uppercase; }
.report-item .ri-status { font-size: 0.68rem; padding: 1px 6px;
    border-radius: 10px; background: rgba(255,255,255,0.05); }
.triage-item { background: #0e1116; padding: 10px; margin: 6px 0;
    border-radius: 7px; border-left: 3px solid #f39c12; font-size: 0.82rem; }
.triage-actions { display: flex; gap: 4px; margin-top: 6px; }
.triage-actions button { flex: 1; padding: 5px; font-size: 0.72rem;
    border: none; border-radius: 5px; cursor: pointer; font-weight: 600; }
.t-verify { background: #2ecc71; color: white; }
.t-reject { background: #e74c3c; color: white; }
.t-assign { background: #3498db; color: white; }
.report-marker { background: transparent !important; border: none !important; }
.marker-pin { width: 30px; height: 30px;
    border-radius: 50% 50% 50% 0; transform: rotate(-45deg);
    display: flex; align-items: center; justify-content: center;
    box-shadow: 0 2px 6px rgba(0,0,0,0.5); }
.marker-pin span { transform: rotate(45deg); font-size: 14px;
    line-height: 1; }
.marker-pin.critical { animation: pulseCritical 1.5s infinite; }
@keyframes pulseCritical {
    0% { box-shadow: 0 0 0 0 rgba(231,76,60,0.7); }
    70% { box-shadow: 0 0 0 12px rgba(231,76,60,0); }
    100% { box-shadow: 0 0 0 0 rgba(231,76,60,0); }
}
#analyticsTab { padding: 14px 20px; overflow-y: auto;
    height: calc(100vh - 110px); display: none; }
.analytics-filter { display: flex; gap: 12px; align-items: center;
    margin-bottom: 14px; flex-wrap: wrap; }
.stat-card { background: #171b23; border-radius: 10px;
    padding: 16px; }
.stat-card .value { font-size: 1.6rem; font-weight: 800;
    color: #2ecc71; }
.stat-card .label { font-size: 0.78rem; color: #8a93a6;
    margin-top: 4px; }
.grid-4 { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 12px; margin-bottom: 14px; }
.grid-2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    gap: 12px; }
.analytics-card { background: #171b23; border-radius: 10px;
    padding: 16px; }
.analytics-card h3 { color: #2ecc71; font-size: 0.95rem;
    margin-bottom: 10px; }
@media (max-width: 1000px) {
    .main-layout { grid-template-columns: 1fr; }
    .sidebar { max-height: 45vh; }
    .charts-grid { grid-template-columns: 1fr; }
    .kpi-row { grid-template-columns: repeat(2, 1fr); }
    .rt-tabs { grid-template-columns: repeat(2, 1fr); }
}
</style>
</head>
<body>
<div class="system-bar">
    <div class="brand">
        <h1>🌍 Geo<span>Report-DR</span></h1>
        <p>Crowdsourced Disaster Reporting &amp; Triage System</p>
    </div>
    <div class="controls-right">
        <div id="connectionStatus" class="btn"><i class="fas fa-circle" style="color:#2ecc71;font-size:8px;"></i> Online</div>
        <button class="btn" onclick="forceSync()"><i class="fas fa-sync-alt"></i> Sync</button>
        <span id="userRoleBadge" class="btn"></span>
        <button class="btn" onclick="exportCSV()">CSV</button>
        <button class="btn" onclick="exportGeoJSON()">GeoJSON</button>
        <a href="/" class="btn btn-danger"><i class="fas fa-sign-out-alt"></i> Logout</a>
    </div>
</div>

<div class="tabs-container">
    <button class="tab-btn active" onclick="switchTab('command')" id="tabCommandBtn">Situation Console</button>
    <button class="tab-btn" onclick="switchTab('analytics')" id="tabAnalyticsBtn" style="display:none;">Analytics &amp; Research</button>
</div>

<div id="commandTab">
    <div class="kpi-row">
        <div class="kpi-card">
            <div class="kpi-header"><span>Total Reports</span><i class="fas fa-file-alt"></i></div>
            <div class="kpi-value" id="kpiTotal">0</div>
            <div class="kpi-sub">All categories</div>
        </div>
        <div class="kpi-card" style="border-left-color:#e74c3c;">
            <div class="kpi-header"><span>Critical</span><i class="fas fa-exclamation-triangle"></i></div>
            <div class="kpi-value" id="kpiCritical" style="color:#e74c3c;">0</div>
            <div class="kpi-sub">Life-threatening</div>
        </div>
        <div class="kpi-card" style="border-left-color:#f39c12;">
            <div class="kpi-header"><span>Pending Verification</span><i class="fas fa-clock"></i></div>
            <div class="kpi-value warning" id="kpiPending">0</div>
            <div class="kpi-sub">Awaiting triage</div>
        </div>
        <div class="kpi-card" style="border-left-color:#3498db;">
            <div class="kpi-header"><span>Verified</span><i class="fas fa-check-circle"></i></div>
            <div class="kpi-value" id="kpiVerified">0</div>
            <div class="kpi-sub">Confirmed reports</div>
        </div>
    </div>

    <div class="main-layout">
        <div class="sidebar" id="sidebarPanel">
            <div class="card">
                <h3><i class="fas fa-edit"></i> Submit Report</h3>
                <div class="rt-tabs">
                    <button class="rt-tab active" data-type="damage">🏚️ Damage</button>
                    <button class="rt-tab" data-type="need">🆘 Need</button>
                    <button class="rt-tab" data-type="hazard">⚠️ Hazard</button>
                    <button class="rt-tab" data-type="status">✅ Status</button>
                </div>
                <div id="form-damage">
                    <label>Damage Level</label>
                    <select id="damageLevel">
                        <option value="minimal">Minimal / No Damage</option>
                        <option value="partial">Partially Damaged</option>
                        <option value="complete">Completely Damaged</option>
                    </select>
                    <label>Infrastructure</label>
                    <select id="infrastructureType">
                        <option value="residential">Residential</option>
                        <option value="commercial">Commercial</option>
                        <option value="government">Government</option>
                        <option value="utility">Utility</option>
                        <option value="transport">Transport</option>
                        <option value="community">Community</option>
                        <option value="public">Public</option>
                    </select>
                    <label>Building Name</label>
                    <input type="text" id="buildingName" placeholder="e.g., City Hall">
                </div>
                <div id="form-need" style="display:none;">
                    <label>Need Type</label>
                    <select id="needType">
                        <option value="medical">Medical</option>
                        <option value="water">Water</option>
                        <option value="food">Food</option>
                        <option value="shelter">Shelter</option>
                        <option value="rescue">Rescue / Trapped</option>
                        <option value="clothing">Clothing</option>
                        <option value="sanitation">Sanitation</option>
                    </select>
                    <label>People Affected</label>
                    <input type="number" id="peopleAffected" placeholder="0">
                </div>
                <div id="form-hazard" style="display:none;">
                    <label>Hazard Type</label>
                    <select id="hazardType">
                        <option value="fire">Fire</option>
                        <option value="flood">Flood</option>
                        <option value="structural">Structural Collapse</option>
                        <option value="gas">Gas Leak</option>
                        <option value="powerline">Downed Power Line</option>
                        <option value="road">Road Blocked</option>
                        <option value="chemical">Chemical Hazard</option>
                    </select>
                </div>
                <div id="form-status" style="display:none;">
                    <label>Status Update</label>
                    <select id="statusType">
                        <option value="road_open">Road Reopened</option>
                        <option value="shelter_open">Shelter Open</option>
                        <option value="power_restored">Power Restored</option>
                        <option value="water_restored">Water Restored</option>
                        <option value="resolved">Incident Resolved</option>
                    </select>
                </div>
                <label>Severity</label>
                <select id="severity">
                    <option value="low">Low</option>
                    <option value="medium" selected>Medium</option>
                    <option value="high">High</option>
                    <option value="critical">Critical — life threatening</option>
                </select>
                <label>Crisis Context</label>
                <select id="crisisNature">
                    <option value="earthquake">Earthquake</option>
                    <option value="flood">Flood</option>
                    <option value="tsunami">Tsunami</option>
                    <option value="hurricane">Hurricane</option>
                    <option value="wildfire">Wildfire</option>
                    <option value="explosion">Explosion</option>
                    <option value="conflict">Conflict</option>
                </select>
                <label>Location</label>
                <div style="display:flex; gap:6px;">
                    <input type="text" id="lat" placeholder="Latitude" readonly>
                    <input type="text" id="lng" placeholder="Longitude" readonly>
                </div>
                <input type="hidden" id="gpsAccuracy">
                <button class="secondary" onclick="shareLocation()" style="background:linear-gradient(135deg,#3498db,#2980b9);"><i class="fas fa-location-dot"></i> Use My GPS</button>
                <input type="text" id="textLocation" placeholder="Or describe location" style="margin-top:6px;">
                <label>Notes</label>
                <textarea id="notes" rows="2" placeholder="Additional information"></textarea>
                <label>Photo (optional)</label>
                <input type="file" id="photo" accept="image/*" capture="environment">
                <div id="photoPreview" style="text-align:center;margin-top:6px;"></div>
                <button class="primary" onclick="submitReport()"><i class="fas fa-paper-plane"></i> Submit Report</button>
                <div id="submitStatus" style="margin-top:8px; font-size:0.82rem; text-align:center;"></div>
            </div>
            <div class="card">
                <h3><i class="fas fa-sms"></i> SMS Fallback</h3>
                <input type="text" id="smsText" placeholder="Format: DAMAGE LAT LNG">
                <input type="text" id="smsNumber" placeholder="Phone (optional)" style="margin-top:6px;">
                <button class="secondary" onclick="sendSMSReport()"><i class="fas fa-envelope"></i> Send SMS Report</button>
                <div id="smsStatus" style="margin-top:6px; font-size:0.82rem;"></div>
            </div>
            <div class="card">
                <h3><i class="fas fa-list"></i> Recent Reports</h3>
                <div id="reportsList" class="reports-list">Loading...</div>
            </div>
            <div class="card" id="triageCard" style="display:none;">
                <h3><i class="fas fa-tasks"></i> Triage Queue <span id="triageCount" style="background:#f39c12;color:#000;font-size:0.7rem;padding:2px 8px;border-radius:10px;margin-left:6px;">0</span></h3>
                <div id="triageList"></div>
            </div>
        </div>
        <div class="right-panel">
            <div class="map-container"><div id="map"></div></div>
            <div class="charts-section">
                <div class="charts-title">Report Analytics</div>
                <div class="charts-grid">
                    <div class="chart-container"><h4>By Type</h4><canvas id="typeChart"></canvas></div>
                    <div class="chart-container"><h4>By Severity</h4><canvas id="severityChart"></canvas></div>
                    <div class="chart-container"><h4>7-Day Trend</h4><canvas id="trendChart"></canvas></div>
                </div>
            </div>
        </div>
    </div>
</div>

<div id="analyticsTab">
    <div class="analytics-filter">
        <label style="color:#8a93a6;font-size:0.85rem;">Date Range:</label>
        <select id="analyticsDays" onchange="loadAdminStats()" style="width:auto;">
            <option value="7">Last 7 days</option>
            <option value="30" selected>Last 30 days</option>
            <option value="90">Last 90 days</option>
            <option value="0">All time</option>
        </select>
        <button class="btn" onclick="loadAdminStats()"><i class="fas fa-sync"></i> Refresh</button>
        <button class="btn" onclick="loadResearchMetrics()" style="background:linear-gradient(135deg,#2ecc71,#27ae60);color:#fff;"><i class="fas fa-flask"></i> Research Metrics</button>
    </div>
    <div class="grid-4">
        <div class="stat-card"><div class="value" id="totalReports">-</div><div class="label">Total Reports</div></div>
        <div class="stat-card"><div class="value" id="totalUsers">-</div><div class="label">Active Reporters</div></div>
        <div class="stat-card"><div class="value" id="topReporter">-</div><div class="label">Top Reporter</div></div>
        <div class="stat-card"><div class="value" id="avgLatency">-</div><div class="label">Mean Verification Latency (min)</div></div>
    </div>
    <div class="grid-2">
        <div class="analytics-card"><h3>Daily Trend</h3><canvas id="adminTrendChart"></canvas></div>
        <div class="analytics-card"><h3
