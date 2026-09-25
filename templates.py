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

        /* ===== HEADER ===== */
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

        /* ===== TABS ===== */
        .tabs-container { background: #151922; padding: 0 16px;
            border-bottom: 1px solid #222732; display: flex; gap: 4px;
            flex-shrink: 0; height: 46px; }
        .tab-btn { padding: 12px 22px; background: transparent; color: #8a93a6;
            border: none; border-bottom: 3px solid transparent; font-size: 0.92rem;
            font-weight: 600; cursor: pointer; }
        .tab-btn.active { color: #2ecc71; border-bottom-color: #2ecc71;
            background: rgba(46,204,113,0.08); }

        /* ===== COMMAND LAYOUT ===== */
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

        /* ===== MAP AS HERO ===== */
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

        /* ===== CARDS ===== */
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

        /* Report type tabs */
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
        .t-resolve { background: #27ae60; color: white; }

        /* ===== MARKERS ===== */
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

        /* ===== ANALYTICS ===== */
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
        <div id="connectionStatus" class="btn"><i class="fas fa-circle"
            style="color:#2ecc71;font-size:8px;"></i> Online</div>
        <button class="btn" onclick="forceSync()">
            <i class="fas fa-sync-alt"></i> Sync</button>
        <span id="userRoleBadge" class="btn"></span>
        <button class="btn" onclick="exportCSV()">CSV</button>
        <button class="btn" onclick="exportGeoJSON()">GeoJSON</button>
        <a href="/" class="btn btn-danger">
            <i class="fas fa-sign-out-alt"></i> Logout</a>
    </div>
</div>

<div class="tabs-container">
    <button class="tab-btn active" onclick="switchTab('command')"
        id="tabCommandBtn">Situation Console</button>
    <button class="tab-btn" onclick="switchTab('analytics')"
        id="tabAnalyticsBtn" style="display:none;">Analytics &amp; Research</button>
</div>

<div id="commandTab">
    <div class="kpi-row">
        <div class="kpi-card">
            <div class="kpi-header"><span>Total Reports</span>
                <i class="fas fa-file-alt"></i></div>
            <div class="kpi-value" id="kpiTotal">0</div>
            <div class="kpi-sub">All categories</div>
        </div>
        <div class="kpi-card" style="border-left-color:#e74c3c;">
            <div class="kpi-header"><span>Critical</span>
                <i class="fas fa-exclamation-triangle"></i></div>
            <div class="kpi-value" id="kpiCritical"
                style="color:#e74c3c;">0</div>
            <div class="kpi-sub">Life-threatening</div>
        </div>
        <div class="kpi-card" style="border-left-color:#f39c12;">
            <div class="kpi-header"><span>Pending Verification</span>
                <i class="fas fa-clock"></i></div>
            <div class="kpi-value warning" id="kpiPending">0</div>
            <div class="kpi-sub">Awaiting triage</div>
        </div>
        <div class="kpi-card" style="border-left-color:#3498db;">
            <div class="kpi-header"><span>Verified</span>
                <i class="fas fa-check-circle"></i></div>
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
                <button class="secondary" onclick="shareLocation()"
                    style="background:linear-gradient(135deg,#3498db,#2980b9);">
                    <i class="fas fa-location-dot"></i> Use My GPS</button>
                <input type="text" id="textLocation"
                    placeholder="Or describe location" style="margin-top:6px;">

                <label>Notes</label>
                <textarea id="notes" rows="2"
                    placeholder="Additional information"></textarea>

                <label>Photo (optional)</label>
                <input type="file" id="photo" accept="image/*"
                    capture="environment">
                <div id="photoPreview" style="text-align:center;margin-top:6px;">
                </div>

                <button class="primary" onclick="submitReport()">
                    <i class="fas fa-paper-plane"></i> Submit Report</button>
                <div id="submitStatus"
                    style="margin-top:8px; font-size:0.82rem; text-align:center;">
                </div>
            </div>

            <div class="card">
                <h3><i class="fas fa-sms"></i> SMS Fallback</h3>
                <input type="text" id="smsText"
                    placeholder="Format: DAMAGE LAT LNG">
                <input type="text" id="smsNumber"
                    placeholder="Phone (optional)" style="margin-top:6px;">
                <button class="secondary" onclick="sendSMSReport()">
                    <i class="fas fa-envelope"></i> Send SMS Report</button>
                <div id="smsStatus"
                    style="margin-top:6px; font-size:0.82rem;"></div>
            </div>

            <div class="card">
                <h3><i class="fas fa-list"></i> Recent Reports</h3>
                <div id="reportsList" class="reports-list">Loading...</div>
            </div>

            <div class="card" id="triageCard" style="display:none;">
                <h3><i class="fas fa-tasks"></i> Triage Queue
                    <span id="triageCount"
                        style="background:#f39c12;color:#000;font-size:0.7rem;
                        padding:2px 8px;border-radius:10px;margin-left:6px;">0</span>
                </h3>
                <div id="triageList"></div>
            </div>
        </div>

        <div class="right-panel">
            <div class="map-container"><div id="map"></div></div>
            <div class="charts-section">
                <div class="charts-title">Report Analytics</div>
                <div class="charts-grid">
                    <div class="chart-container">
                        <h4>By Type</h4>
                        <canvas id="typeChart"></canvas>
                    </div>
                    <div class="chart-container">
                        <h4>By Severity</h4>
                        <canvas id="severityChart"></canvas>
                    </div>
                    <div class="chart-container">
                        <h4>7-Day Trend</h4>
                        <canvas id="trendChart"></canvas>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<div id="analyticsTab">
    <div class="analytics-filter">
        <label style="color:#8a93a6;font-size:0.85rem;">Date Range:</label>
        <select id="analyticsDays" onchange="loadAdminStats()"
            style="width:auto;">
            <option value="7">Last 7 days</option>
            <option value="30" selected>Last 30 days</option>
            <option value="90">Last 90 days</option>
            <option value="0">All time</option>
        </select>
        <button class="btn" onclick="loadAdminStats()">
            <i class="fas fa-sync"></i> Refresh</button>
        <button class="btn" onclick="loadResearchMetrics()"
            style="background:linear-gradient(135deg,#2ecc71,#27ae60);color:#fff;">
            <i class="fas fa-flask"></i> Research Metrics</button>
    </div>

    <div class="grid-4">
        <div class="stat-card">
            <div class="value" id="totalReports">-</div>
            <div class="label">Total Reports</div>
        </div>
        <div class="stat-card">
            <div class="value" id="totalUsers">-</div>
            <div class="label">Active Reporters</div>
        </div>
        <div class="stat-card">
            <div class="value" id="topReporter">-</div>
            <div class="label">Top Reporter</div>
        </div>
        <div class="stat-card">
            <div class="value" id="avgLatency">-</div>
            <div class="label">Mean Verification Latency (min)</div>
        </div>
    </div>

    <div class="grid-2">
        <div class="analytics-card">
            <h3>Daily Trend</h3>
            <canvas id="adminTrendChart"></canvas>
        </div>
        <div class="analytics-card">
            <h3>By Report Type</h3>
            <canvas id="adminTypeChart"></canvas>
        </div>
        <div class="analytics-card">
            <h3>By Severity</h3>
            <canvas id="adminSeverityChart"></canvas>
        </div>
        <div class="analytics-card">
            <h3>By Verification Status</h3>
            <canvas id="adminStatusChart"></canvas>
        </div>
        <div class="analytics-card">
            <h3>By Infrastructure</h3>
            <canvas id="adminInfraChart"></canvas>
        </div>
        <div class="analytics-card">
            <h3>By Crisis Nature</h3>
            <canvas id="adminCrisisChart"></canvas>
        </div>
    </div>
</div>

<script>
let map, markers = [], reports = [];
let currentUser = { username: '', role: '' };
let translations = {};
let offlineQueue = [];
let isAdmin = false;
let currentMarker = null;
let currentReportType = 'damage';
let typeChart, severityChart, trendChart;
let adminTrendChart, adminTypeChart, adminSeverityChart,
    adminStatusChart, adminInfraChart, adminCrisisChart;

const REPORT_ICONS = {
    damage: '🏚️', need: '🆘', hazard: '⚠️', status: '✅'
};
const SEVERITY_COLORS = {
    low: '#2ecc71', medium: '#f39c12', high: '#e67e22', critical: '#e74c3c'
};
const STATUS_RING = {
    pending: '#aaaaaa', verified: '#2ecc71',
    assigned: '#3498db', resolved: '#27ae60', rejected: '#7f8c8d'
};

function escapeHtml(v) {
    const t = v == null ? '' : String(v);
    return t.replace(/&/g, '&amp;').replace(/</g, '&lt;')
            .replace(/>/g, '&gt;').replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
}

// ===== Report Type Tabs =====
document.querySelectorAll('.rt-tab').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.rt-tab').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentReportType = btn.dataset.type;
        ['damage','need','hazard','status'].forEach(t => {
            const el = document.getElementById('form-' + t);
            if (el) el.style.display = (t === currentReportType) ? 'block' : 'none';
        });
    });
});

// ===== Offline Queue =====
function loadOfflineQueue() {
    const s = localStorage.getItem('offline_reports');
    if (s) offlineQueue = JSON.parse(s);
}
function saveOfflineQueue() {
    localStorage.setItem('offline_reports', JSON.stringify(offlineQueue));
}
loadOfflineQueue();

// ===== Tab switching =====
function switchTab(tab) {
    if (tab === 'command') {
        document.getElementById('commandTab').style.display = 'flex';
        document.getElementById('analyticsTab').style.display = 'none';
        document.getElementById('tabCommandBtn').classList.add('active');
        document.getElementById('tabAnalyticsBtn').classList.remove('active');
        setTimeout(() => { if (map) map.invalidateSize(); }, 150);
    } else {
        document.getElementById('commandTab').style.display = 'none';
        document.getElementById('analyticsTab').style.display = 'block';
        document.getElementById('tabCommandBtn').classList.remove('active');
        document.getElementById('tabAnalyticsBtn').classList.add('active');
        loadAdminStats();
    }
}

// ===== Map =====
function initMap() {
    map = L.map('map', { center: [20, 0], zoom: 2, zoomControl: true });
    map.attributionControl.setPrefix('');
    // Dark basemap (CARTO Dark Matter)
    L.tileLayer(
        'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
        { attribution: '&copy; OSM &copy; CARTO', maxZoom: 19,
          subdomains: 'abcd' }
    ).addTo(map);
    setTimeout(() => map.invalidateSize(), 100);
    setTimeout(() => map.invalidateSize(), 500);
    window.addEventListener('resize', () => map.invalidateSize());

    map.on('click', async function(e) {
        const lat = e.latlng.lat, lng = e.latlng.lng;
        document.getElementById('lat').value = lat.toFixed(6);
        document.getElementById('lng').value = lng.toFixed(6);
        try {
            const res = await fetch('/api/building/' + lat + '/' + lng);
            const b = await res.json();
            if (b && b.name) {
                document.getElementById('buildingName').value = b.name;
            }
        } catch(err) { console.error(err); }
        if (currentMarker) map.removeLayer(currentMarker);
        currentMarker = L.marker([lat, lng]).addTo(map)
            .bindPopup('Selected location').openPopup();
    });
}

function shareLocation() {
    if (!navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition(pos => {
        const lat = pos.coords.latitude, lng = pos.coords.longitude;
        document.getElementById('lat').value = lat.toFixed(6);
        document.getElementById('lng').value = lng.toFixed(6);
        document.getElementById('gpsAccuracy').value = pos.coords.accuracy;
        map.setView([lat, lng], 16);
        if (currentMarker) map.removeLayer(currentMarker);
        currentMarker = L.marker([lat, lng]).addTo(map)
            .bindPopup('Your location (±' + Math.round(pos.coords.accuracy) + 'm)')
            .openPopup();
    }, err => alert('GPS error: ' + err.message),
       { enableHighAccuracy: true });
}

// ===== Photo preview =====
document.getElementById('photo').addEventListener('change', function(e) {
    const preview = document.getElementById('photoPreview');
    if (e.target.files && e.target.files[0]) {
        const reader = new FileReader();
        reader.onload = ev => {
            preview.innerHTML = '<img src="' + ev.target.result +
                '" style="max-width:100%;max-height:80px;border-radius:6px;">';
        };
        reader.readAsDataURL(e.target.files[0]);
    } else { preview.innerHTML = ''; }
});

// ===== Submit =====
async function submitReport() {
    const fd = new FormData();
    fd.append('report_type', currentReportType);
    fd.append('severity', document.getElementById('severity').value);
    fd.append('crisis_nature', document.getElementById('crisisNature').value);

    if (currentReportType === 'damage') {
        fd.append('damage_level', document.getElementById('damageLevel').value);
        fd.append('infrastructure_type', document.getElementById('infrastructureType').value);
        fd.append('building_name', document.getElementById('buildingName').value);
    } else if (currentReportType === 'need') {
        fd.append('damage_level', 'minimal');
        fd.append('infrastructure_type', 'community');
        fd.append('building_name', document.getElementById('needType').value);
    } else if (currentReportType === 'hazard') {
        fd.append('damage_level', 'partial');
        fd.append('infrastructure_type', 'utility');
        fd.append('building_name', document.getElementById('hazardType').value);
    } else if (currentReportType === 'status') {
        fd.append('damage_level', 'minimal');
        fd.append('infrastructure_type', 'community');
        fd.append('building_name', document.getElementById('statusType').value);
    }

    fd.append('debris', 'no');
    fd.append('text_location', document.getElementById('textLocation').value);
    fd.append('lat', document.getElementById('lat').value);
    fd.append('lng', document.getElementById('lng').value);
    const acc = document.getElementById('gpsAccuracy').value;
    if (acc) fd.append('gps_accuracy_m', acc);
    fd.append('notes', document.getElementById('notes').value);

    const photoFile = document.getElementById('photo').files[0];
    if (photoFile) fd.append('photo', photoFile);

    const statusDiv = document.getElementById('submitStatus');
    statusDiv.innerHTML = 'Submitting...';
    statusDiv.style.color = '#8a93a6';

    try {
        const res = await fetch('/api/report', { method: 'POST', body: fd });
        const data = await res.json();
        if (data.status === 'success') {
            statusDiv.innerHTML = '✅ Report submitted';
            statusDiv.style.color = '#2ecc71';
            ['lat','lng','gpsAccuracy','buildingName','textLocation','notes'].forEach(id => {
                document.getElementById(id).value = '';
            });
            document.getElementById('photo').value = '';
            document.getElementById('photoPreview').innerHTML = '';
            if (currentMarker) map.removeLayer(currentMarker);
            loadReports();
            loadTriage();
        } else {
            statusDiv.innerHTML = '❌ Submission failed';
            statusDiv.style.color = '#e74c3c';
        }
    } catch(e) {
        statusDiv.innerHTML = '❌ Offline — queued';
        statusDiv.style.color = '#f39c12';
        offlineQueue.push({
            report_uuid: Date.now().toString(),
            report_type: currentReportType,
            severity: document.getElementById('severity').value,
            damage_level: 'minimal',
            infrastructure_type: 'community',
            building_name: '',
            crisis_nature: document.getElementById('crisisNature').value,
            debris: 'no',
            lat: document.getElementById('lat').value,
            lng: document.getElementById('lng').value,
            location_text: document.getElementById('textLocation').value,
            notes: document.getElementById('notes').value,
            timestamp: new Date().toISOString()
        });
        saveOfflineQueue();
        loadReports();
    }
}

// ===== SMS =====
async function sendSMSReport() {
    const smsText = document.getElementById('smsText').value;
    const smsNumber = document.getElementById('smsNumber').value;
    const statusDiv = document.getElementById('smsStatus');
    if (!smsText) { statusDiv.innerText = 'Enter SMS text'; return; }
    try {
        const fd = new FormData();
        fd.append('sms_text', smsText);
        fd.append('sms_number', smsNumber);
        const res = await fetch('/api/sms_report', { method: 'POST', body: fd });
        const data = await res.json();
        if (data.status === 'success') {
            statusDiv.innerHTML = '✅ SMS received';
            statusDiv.style.color = '#2ecc71';
            document.getElementById('smsText').value = '';
            loadReports();
        } else {
            statusDiv.innerHTML = '❌ ' + data.message;
            statusDiv.style.color = '#e74c3c';
        }
    } catch(e) {
        statusDiv.innerHTML = '❌ Failed';
        statusDiv.style.color = '#e74c3c';
    }
}

// ===== Sync =====
async function syncOfflineReports() {
    if (offlineQueue.length === 0) return;
    try {
        const res = await fetch('/api/sync', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(offlineQueue)
        });
        if (res.ok) {
            offlineQueue = [];
            saveOfflineQueue();
            loadReports();
        }
    } catch(e) { console.error(e); }
}
async function forceSync() { await syncOfflineReports(); }

// ===== Load reports =====
async function loadReports() {
    try {
        const res = await fetch('/api/reports');
        const serverReports = await res.json();
        reports = [...serverReports, ...offlineQueue.map(r => ({...r, is_offline: true}))];
        reports.sort((a,b) => new Date(b.timestamp) - new Date(a.timestamp));
        updateMapMarkers();
        updateReportsList();
        updateKPIs();
        updateCharts();
        updateConnectionStatus(true);
    } catch(e) {
        reports = offlineQueue.map(r => ({...r, is_offline: true}));
        updateReportsList();
        updateKPIs();
        updateCharts();
        updateConnectionStatus(false);
    }
}

function updateKPIs() {
    const total = reports.length;
    const critical = reports.filter(r => r.severity === 'critical').length;
    const pending = reports.filter(r => r.verification_status === 'pending').length;
    const verified = reports.filter(r => r.verification_status === 'verified').length;
    document.getElementById('kpiTotal').innerText = total;
    document.getElementById('kpiCritical').innerText = critical;
    document.getElementById('kpiPending').innerText = pending;
    document.getElementById('kpiVerified').innerText = verified;
}

function updateMapMarkers() {
    if (!map) return;
    markers.forEach(m => map.removeLayer(m));
    markers = [];
    reports.forEach(r => {
        if (!r.lat || !r.lng) return;
        const color = SEVERITY_COLORS[r.severity] || '#f39c12';
        const ring = STATUS_RING[r.verification_status] || '#aaaaaa';
        const icon = L.divIcon({
            className: 'report-marker',
            html: '<div class="marker-pin ' + (r.severity === 'critical' ? 'critical' : '') +
                  '" style="background:' + color + ';border:3px solid ' + ring + ';">' +
                  '<span>' + (REPORT_ICONS[r.report_type] || '📍') + '</span></div>',
            iconSize: [30, 30], iconAnchor: [15, 30]
        });
        const marker = L.marker([r.lat, r.lng], { icon }).addTo(map);
        marker.bindPopup(
            '<b>' + escapeHtml(r.building_name || r.report_type) + '</b><br>' +
            'Type: ' + escapeHtml(r.report_type) + '<br>' +
            'Severity: ' + escapeHtml(r.severity) + '<br>' +
            'Status: ' + escapeHtml(r.verification_status || 'pending') + '<br>' +
            (r.notes ? escapeHtml(r.notes) + '<br>' : '') +
            '<small>' + escapeHtml(r.timestamp || '') + '</small>'
        );
        markers.push(marker);
    });
}

function updateReportsList() {
    const container = document.getElementById('reportsList');
    if (!container) return;
    container.innerHTML = '';
    if (reports.length === 0) {
        container.innerHTML = '<div style="color:#8a93a6;font-size:0.85rem;">No reports yet.</div>';
        return;
    }
    reports.slice(0, 20).forEach(r => {
        const div = document.createElement('div');
        div.className = 'report-item sev-' + (r.severity || 'medium');
        div.innerHTML =
            '<div class="ri-head"><strong>' +
                escapeHtml(r.building_name || r.report_type || 'Report') +
            '</strong><span class="ri-status">' +
                escapeHtml(r.verification_status || 'pending') +
            '</span></div>' +
            '<div class="ri-type">' + escapeHtml(r.report_type || 'damage') +
                ' · ' + escapeHtml(r.severity || 'medium') + '</div>';
        div.onclick = () => {
            if (r.lat && r.lng && map) map.setView([r.lat, r.lng], 18);
        };
        container.appendChild(div);
    });
}

function updateCharts() {
    // By type
    const types = { damage: 0, need: 0, hazard: 0, status: 0 };
    reports.forEach(r => { if (types[r.report_type] !== undefined) types[r.report_type]++; });
    if (typeChart) typeChart.destroy();
    typeChart = new Chart(document.getElementById('typeChart'), {
        type: 'doughnut',
        data: {
            labels: ['Damage', 'Need', 'Hazard', 'Status'],
            datasets: [{
                data: [types.damage, types.need, types.hazard, types.status],
                backgroundColor: ['#e74c3c', '#3498db', '#f39c12', '#2ecc71']
            }]
        },
        options: { responsive: true, plugins: { legend: { display: false } } }
    });

    // By severity
    const sevs = { low: 0, medium: 0, high: 0, critical: 0 };
    reports.forEach(r => { if (sevs[r.severity] !== undefined) sevs[r.severity]++; });
    if (severityChart) severityChart.destroy();
    severityChart = new Chart(document.getElementById('severityChart'), {
        type: 'bar',
        data: {
            labels: ['Low', 'Med', 'High', 'Crit'],
            datasets: [{
                data: [sevs.low, sevs.medium, sevs.high, sevs.critical],
                backgroundColor: ['#2ecc71', '#f39c12', '#e67e22', '#e74c3c']
            }]
        },
        options: {
            responsive: true,
            plugins: { legend: { display: false } },
            scales: {
                x: { ticks: { color: '#8a93a6', font: { size: 9 } } },
                y: { ticks: { color: '#8a93a6', font: { size: 9 } } }
            }
        }
    });

    // Trend
    const daily = {};
    reports.forEach(r => {
        if (!r.timestamp) return;
        const d = new Date(r.timestamp).toISOString().split('T')[0];
        daily[d] = (daily[d] || 0) + 1;
    });
    const last7 = [];
    for (let i = 6; i >= 0; i--) {
        const d = new Date();
        d.setDate(d.getDate() - i);
        last7.push(d.toISOString().split('T')[0]);
    }
    if (trendChart) trendChart.destroy();
    trendChart = new Chart(document.getElementById('trendChart'), {
        type: 'line',
        data: {
            labels: last7.map(d => d.slice(5)),
            datasets: [{
                data: last7.map(d => daily[d] || 0),
                borderColor: '#2ecc71',
                backgroundColor: 'rgba(46,204,113,0.15)',
                fill: true, tension: 0.4
            }]
        },
        options: {
            responsive: true,
            plugins: { legend: { display: false } },
            scales: {
                x: { ticks: { color: '#8a93a6', font: { size: 9 } } },
                y: { ticks: { color: '#8a93a6', font: { size: 9 } } }
            }
        }
    });
}

// ===== Triage =====
async function loadTriage() {
    if (!isAdmin && currentUser.role !== 'reporter') return;
    try {
        const res = await fetch('/api/reports/pending');
        const pending = await res.json();
        document.getElementById('triageCard').style.display = 'block';
        document.getElementById('triageCount').innerText = pending.length;
        const container = document.getElementById('triageList');
        if (pending.length === 0) {
            container.innerHTML = '<div style="color:#8a93a6;font-size:0.82rem;">No pending reports.</div>';
            return;
        }
        container.innerHTML = pending.slice(0, 10).map(r => (
            '<div class="triage-item">' +
            '<strong>' + escapeHtml(r.building_name || r.report_type) + '</strong><br>' +
            'Type: ' + escapeHtml(r.report_type) + ' · Severity: ' +
            escapeHtml(r.severity) + '<br>' +
            '<div class="triage-actions">' +
            '<button class="t-verify" onclick="triageAction(\\'' + r.report_uuid + '\\',\\'verified\\')">Verify</button>' +
            '<button class="t-reject" onclick="triageAction(\\'' + r.report_uuid + '\\',\\'rejected\\')">Reject</button>' +
            '<button class="t-assign" onclick="triageAction(\\'' + r.report_uuid + '\\',\\'assigned\\')">Assign</button>' +
            '</div></div>'
        )).join('');
    } catch(e) { console.warn(e); }
}

async function triageAction(uuid, action) {
    const fd = new FormData();
    fd.append('action', action);
    try {
        const res = await fetch('/api/report/' + uuid + '/verify',
            { method: 'POST', body: fd });
        if (res.ok) { loadTriage(); loadReports(); }
    } catch(e) { console.error(e); }
}

// ===== Analytics =====
async function loadAdminStats() {
    const days = document.getElementById('analyticsDays').value;
    try {
        const res = await fetch('/api/admin/stats?days=' + days);
        const data = await res.json();
        document.getElementById('totalReports').innerText = data.total_reports || 0;
        document.getElementById('totalUsers').innerText = data.total_users || 0;
        document.getElementById('topReporter').innerText =
            data.top_reporters[0]?.username || '-';

        if (adminTrendChart) adminTrendChart.destroy();
        adminTrendChart = new Chart(document.getElementById('adminTrendChart'), {
            type: 'line',
            data: {
                labels: data.daily_trend.map(d => d.date.slice(5)),
                datasets: [{
                    label: 'Reports',
                    data: data.daily_trend.map(d => d.count),
                    borderColor: '#2ecc71',
                    backgroundColor: 'rgba(46,204,113,0.15)',
                    fill: true, tension: 0.4
                }]
            },
            options: { responsive: true,
                plugins: { legend: { labels: { color: '#e0e0e0' } } },
                scales: {
                    x: { ticks: { color: '#8a93a6' } },
                    y: { ticks: { color: '#8a93a6' } }
                }
            }
        });

        if (adminTypeChart) adminTypeChart.destroy();
        adminTypeChart = new Chart(document.getElementById('adminTypeChart'), {
            type: 'doughnut',
            data: {
                labels: data.by_type.map(d => d.type),
                datasets: [{
                    data: data.by_type.map(d => d.count),
                    backgroundColor: ['#e74c3c', '#3498db', '#f39c12', '#2ecc71']
                }]
            },
            options: { responsive: true,
                plugins: { legend: { labels: { color: '#e0e0e0' } } } }
        });

        if (adminSeverityChart) adminSeverityChart.destroy();
        adminSeverityChart = new Chart(document.getElementById('adminSeverityChart'), {
            type: 'bar',
            data: {
                labels: data.by_severity.map(d => d.severity),
                datasets: [{
                    data: data.by_severity.map(d => d.count),
                    backgroundColor: ['#2ecc71', '#f39c12', '#e67e22', '#e74c3c']
                }]
            },
            options: { responsive: true,
                plugins: { legend: { display: false } },
                scales: {
                    x: { ticks: { color: '#8a93a6' } },
                    y: { ticks: { color: '#8a93a6' } }
                }
            }
        });

        if (adminStatusChart) adminStatusChart.destroy();
        adminStatusChart = new Chart(document.getElementById('adminStatusChart'), {
            type: 'bar',
            data: {
                labels: data.by_status.map(d => d.status),
                datasets: [{
                    data: data.by_status.map(d => d.count),
                    backgroundColor: '#3498db'
                }]
            },
            options: { responsive: true,
                plugins: { legend: { display: false } },
                scales: {
                    x: { ticks: { color: '#8a93a6' } },
                    y: { ticks: { color: '#8a93a6' } }
                }
            }
        });

        if (adminInfraChart) adminInfraChart.destroy();
        adminInfraChart = new Chart(document.getElementById('adminInfraChart'), {
            type: 'bar',
            data: {
                labels: data.by_infrastructure.map(d => d.type),
                datasets: [{
                    data: data.by_infrastructure.map(d => d.count),
                    backgroundColor: '#2ecc71'
                }]
            },
            options: { responsive: true,
                plugins: { legend: { display: false } },
                scales: {
                    x: { ticks: { color: '#8a93a6' } },
                    y: { ticks: { color: '#8a93a6' } }
                }
            }
        });

        if (adminCrisisChart) adminCrisisChart.destroy();
        adminCrisisChart = new Chart(document.getElementById('adminCrisisChart'), {
            type: 'bar',
            data: {
                labels: data.by_crisis.map(d => d.crisis),
                datasets: [{
                    data: data.by_crisis.map(d => d.count),
                    backgroundColor: '#f39c12'
                }]
            },
            options: { responsive: true,
                plugins: { legend: { display: false } },
                scales: {
                    x: { ticks: { color: '#8a93a6' } },
                    y: { ticks: { color: '#8a93a6' } }
                }
            }
        });
    } catch(e) { console.error(e); }
}

async function loadResearchMetrics() {
    try {
        const res = await fetch('/api/research/metrics');
        const data = await res.json();
        document.getElementById('avgLatency').innerText =
            data.mean_verification_latency_min
                ? Math.round(data.mean_verification_latency_min) : '-';
        alert(
            'Research Metrics\\n\\n' +
            'Mean verification latency: ' +
                (data.mean_verification_latency_min?.toFixed(1) || 'N/A') + ' min\\n' +
            'Photo attachment rate: ' +
                ((data.photo_attachment_rate || 0) * 100).toFixed(1) + '%\\n' +
            'Notes completion rate: ' +
                ((data.notes_completion_rate || 0) * 100).toFixed(1) + '%\\n' +
            'Duplicate reports: ' + (data.duplicate_reports || 0) + '\\n' +
            'GPS mean accuracy: ' +
                (data.gps_mean_accuracy_m?.toFixed(1) || 'N/A') + ' m\\n' +
            'GPS median accuracy: ' +
                (data.gps_median_accuracy_m?.toFixed(1) || 'N/A') + ' m'
        );
    } catch(e) { alert('Could not load metrics'); }
}

function updateConnectionStatus(online) {
    const el = document.getElementById('connectionStatus');
    if (!el) return;
    if (online) {
        el.innerHTML = '<i class="fas fa-circle" style="color:#2ecc71;font-size:8px;"></i> Online';
    } else {
        el.innerHTML = '<i class="fas fa-circle" style="color:#e74c3c;font-size:8px;"></i> Offline';
    }
}

// ===== User =====
async function loadCurrentUser() {
    try {
        const res = await fetch('/api/current_user');
        currentUser = await res.json();
        document.getElementById('userRoleBadge').innerText =
            currentUser.role + ' · ' + currentUser.username;
        if (currentUser.role === 'admin') {
            isAdmin = true;
            document.getElementById('tabAnalyticsBtn').style.display = 'inline-block';
        }
        if (currentUser.role === 'admin' || currentUser.role === 'reporter') {
            loadTriage();
        }
        loadReports();
    } catch(e) { console.error(e); }
}

// ===== Exports =====
function exportCSV() { window.open('/api/reports/csv', '_blank'); }
async function exportGeoJSON() {
    try {
        const res = await fetch('/api/reports/geojson');
        const data = await res.json();
        const blob = new Blob([JSON.stringify(data)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; a.download = 'georeport_dr.geojson'; a.click();
        URL.revokeObjectURL(url);
    } catch(e) { alert('Export failed'); }
}

// ===== Online/Offline =====
window.addEventListener('online', () => {
    updateConnectionStatus(true); syncOfflineReports(); loadReports();
});
window.addEventListener('offline', () => updateConnectionStatus(false));

// ===== Init =====
window.addEventListener('load', function() {
    setTimeout(function() {
        initMap();
        loadCurrentUser();
        setInterval(() => loadReports(), 30000);
        setInterval(() => { if (isAdmin) loadTriage(); }, 20000);
    }, 200);
});
</script>
</body>
</html>
"""
