UNIFIED_DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>UNDP ImpactMapper - Analytics Command Center</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Inter', sans-serif; background: #121212; color: #e0e0e0; overflow: hidden; }
        .leaflet-control-attribution { display: none !important; }
        .leaflet-bottom.leaflet-right { display: none !important; }
        :root {
            --bg-dark: #121212;
            --bg-card: #1e1e1e;
            --bg-sidebar: #1a1d23;
            --border-color: #2a2d35;
            --primary: #2ecc71;
            --primary-dark: #27ae60;
            --primary-muted: rgba(46,204,113,0.12);
            --danger: #e74c3c;
            --warning: #f39c12;
            --info: #3498db;
        }

        /* ----- SMALLER HEADER ----- */
        .system-bar {
            background: #1a472a;
            padding: 6px 16px !important;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 2px solid #2ecc71;
            min-height: 48px;
        }
        .brand-center h1 { font-size: 1.1rem !important; font-weight: 700; color: white; letter-spacing: 1px; }
        .brand-center p { font-size: 0.55rem !important; color: rgba(255,255,255,0.7); margin-top: 1px; }
        .controls-right { gap: 6px !important; }
        .controls-right .sync-btn, .controls-right .logout-btn { padding: 3px 8px !important; font-size: 0.6rem !important; }
        .controls-right .lang-dropdown { padding: 3px 6px !important; font-size: 0.6rem !important; }
        .controls-right .role-badge { font-size: 0.55rem !important; padding: 2px 6px !important; }

        /* ----- GLOWING + DRAGGABLE + RESIZABLE CHAT ----- */
        .chat-panel {
            position: fixed !important;
            bottom: 20px !important;
            left: 20px !important;
            width: 340px !important;
            min-width: 200px !important;
            max-width: 500px !important;
            max-height: 480px !important;
            min-height: 200px !important;
            background: rgba(18, 25, 40, 0.95) !important;
            backdrop-filter: blur(14px) !important;
            border-radius: 20px !important;
            border: 1px solid rgba(0, 255, 200, 0.3) !important;
            box-shadow: 0 0 30px rgba(0, 255, 200, 0.25), 0 0 70px rgba(0, 255, 200, 0.1), inset 0 0 30px rgba(0, 255, 200, 0.04) !important;
            animation: pulseGlowChat 2.8s ease-in-out infinite alternate !important;
            cursor: grab !important;
            z-index: 9999 !important;
            display: flex !important;
            flex-direction: column !important;
            overflow: hidden !important;
            transition: box-shadow 0.3s ease !important;
            resize: both !important;
        }
        .chat-panel:hover {
            box-shadow: 0 0 45px rgba(0, 255, 200, 0.45), 0 0 90px rgba(0, 255, 200, 0.2), inset 0 0 40px rgba(0, 255, 200, 0.06) !important;
        }
        .chat-panel:active { cursor: grabbing !important; }
        @keyframes pulseGlowChat {
            0% { box-shadow: 0 0 20px rgba(0,255,200,0.15), 0 0 40px rgba(0,255,200,0.06); }
            100% { box-shadow: 0 0 45px rgba(0,255,200,0.45), 0 0 80px rgba(0,255,200,0.2), inset 0 0 30px rgba(0,255,200,0.04); }
        }
        .chat-header {
            padding: 10px 14px !important;
            background: rgba(0,255,200,0.06) !important;
            border-bottom: 1px solid rgba(0,255,200,0.12) !important;
            border-radius: 20px 20px 0 0 !important;
            cursor: grab !important;
            display: flex !important;
            justify-content: space-between !important;
            align-items: center !important;
            flex-shrink: 0 !important;
        }
        .chat-header:active { cursor: grabbing !important; }
        .chat-header h4 {
            color: #00ffcc !important;
            font-size: 0.75rem !important;
            font-weight: 700 !important;
            letter-spacing: 1px !important;
            text-shadow: 0 0 18px rgba(0,255,200,0.3) !important;
            display: flex !important;
            align-items: center !important;
            gap: 8px !important;
        }
        .chat-header .pulse-dot {
            display: inline-block !important;
            width: 8px !important;
            height: 8px !important;
            background: #00ffcc !important;
            border-radius: 50% !important;
            box-shadow: 0 0 18px #00ffcc !important;
            animation: blinkDotChat 1.2s infinite !important;
        }
        @keyframes blinkDotChat {
            0%,100% { opacity: 1; }
            50% { opacity: 0.15; }
        }
        .chat-header .status-badge {
            font-size: 0.55rem !important;
            background: rgba(0,255,200,0.12) !important;
            padding: 2px 10px !important;
            border-radius: 30px !important;
            color: #aaffee !important;
            border: 1px solid rgba(0,255,200,0.15) !important;
        }
        .chat-messages {
            flex: 1 !important;
            padding: 8px 12px !important;
            overflow-y: auto !important;
            max-height: 280px !important;
            min-height: 100px !important;
            display: flex !important;
            flex-direction: column !important;
            gap: 4px !important;
            scroll-behavior: smooth !important;
            background: transparent !important;
        }
        .chat-messages::-webkit-scrollbar { width: 3px; }
        .chat-messages::-webkit-scrollbar-thumb {
            background: #00ffcc;
            border-radius: 10px;
            box-shadow: 0 0 12px #00ffcc;
        }
        .chat-message {
            padding: 5px 10px !important;
            border-radius: 12px !important;
            max-width: 85% !important;
            font-size: 0.7rem !important;
            line-height: 1.3 !important;
            animation: fadeInMsg 0.2s ease !important;
        }
        .chat-message.own {
            align-self: flex-end !important;
            background: rgba(0,255,200,0.16) !important;
            border: 1px solid rgba(0,255,200,0.2) !important;
            color: #e0faf5 !important;
            border-bottom-right-radius: 4px !important;
        }
        .chat-message.other {
            align-self: flex-start !important;
            background: rgba(255,255,255,0.06) !important;
            border: 1px solid rgba(255,255,255,0.06) !important;
            color: #cdd9e6 !important;
            border-bottom-left-radius: 4px !important;
        }
        .chat-message .msg-username {
            font-weight: 700 !important;
            color: #00ffcc !important;
            font-size: 0.6rem !important;
            display: block !important;
            margin-bottom: 1px !important;
        }
        .chat-message .msg-time {
            font-size: 0.5rem !important;
            opacity: 0.4 !important;
            margin-left: 6px !important;
        }
        .chat-input-area {
            padding: 6px 12px 10px 12px !important;
            border-top: 1px solid rgba(0,255,200,0.08) !important;
            display: flex !important;
            gap: 6px !important;
            align-items: center !important;
            flex-shrink: 0 !important;
            background: transparent !important;
        }
        .chat-input-area input {
            flex: 1 !important;
            padding: 6px 12px !important;
            border-radius: 30px !important;
            border: 1px solid rgba(0,255,200,0.15) !important;
            background: rgba(0,0,0,0.45) !important;
            color: #fff !important;
            font-size: 0.7rem !important;
            outline: none !important;
        }
        .chat-input-area input:focus {
            border-color: #00ffcc !important;
            box-shadow: 0 0 25px rgba(0,255,200,0.12) !important;
        }
        .chat-input-area button {
            padding: 6px 14px !important;
            border-radius: 30px !important;
            border: none !important;
            background: #00ffcc !important;
            color: #0b0e14 !important;
            font-weight: 700 !important;
            font-size: 0.65rem !important;
            cursor: pointer !important;
            box-shadow: 0 0 28px rgba(0,255,200,0.15) !important;
            transition: 0.2s !important;
            white-space: nowrap !important;
            width: auto !important;
            margin: 0 !important;
        }
        .chat-input-area button:hover {
            transform: scale(1.05) !important;
            box-shadow: 0 0 45px rgba(0,255,200,0.35) !important;
        }
        .chat-input-area button:active {
            transform: scale(0.96) !important;
        }

        /* ----- RESIZE HANDLE (bottom-right corner) ----- */
        .chat-panel::-webkit-resizer {
            background: #00ffcc;
            border-radius: 0 0 20px 0;
            opacity: 0.3;
        }

        /* ----- TABS ----- */
        .tabs-container {
            background: var(--bg-card);
            padding: 0 16px;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            gap: 4px;
        }
        .tab-btn {
            padding: 10px 20px;
            background: transparent;
            color: #a0a0a0;
            border: none;
            font-size: 0.8rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        .tab-btn:hover { color: var(--primary); background: var(--primary-muted); transform: translateY(-2px); }
        .tab-btn.active { color: var(--primary); border-bottom: 2px solid var(--primary); }
        .tab-content { display: none; height: calc(100vh - 110px); }
        .tab-content.active { display: block; }

        /* ----- KPI ROW ----- */
        .kpi-row {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 8px;
            padding: 8px 16px;
            background: var(--bg-dark);
        }
        .kpi-card {
            background: var(--bg-card);
            border-radius: 6px;
            padding: 8px 10px;
            border: 1px solid var(--border-color);
            cursor: pointer;
            transition: all 0.3s ease;
        }
        .kpi-card:hover { border-color: var(--primary); transform: translateY(-2px); box-shadow: 0 0 15px rgba(46,204,113,0.6); }
        .kpi-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
        .kpi-header span { font-size: 0.5rem; color: #a0a0a0; text-transform: uppercase; }
        .kpi-value { font-size: 1.2rem; font-weight: 700; margin-bottom: 2px; }
        .kpi-value.warning { color: #f39c12; }
        .progress-bar { height: 2px; background: #2a2a2a; border-radius: 2px; overflow: hidden; margin-top: 4px; }
        .progress-fill { height: 100%; background: var(--primary); border-radius: 2px; }
        .pill-group { display: flex; gap: 4px; margin-top: 4px; flex-wrap: wrap; }
        .pill { padding: 1px 5px; border-radius: 12px; font-size: 0.5rem; font-weight: 500; }
        .pill-red { background: rgba(231,76,60,0.12); color: #e74c3c; }
        .pill-yellow { background: rgba(243,156,18,0.12); color: #f39c12; }
        .pill-green { background: rgba(46,204,113,0.12); color: #2ecc71; }

        /* ----- MAIN LAYOUT ----- */
        .main-layout { display: flex; height: calc(100% - 48px); }
        .sidebar { width: 380px; background: var(--bg-sidebar); overflow-y: auto; padding: 12px; border-right: 1px solid var(--border-color); transition: width 0.3s ease, padding 0.3s ease, opacity 0.3s ease; }
        .sidebar.collapsed { width: 0; padding: 0; overflow: hidden; border-right: none; }
        .right-panel { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
        .map-container { flex: 1; position: relative; }
        #map { height: 100%; width: 100%; }

        /* ----- CHARTS SECTION (collapsible) ----- */
        .charts-section {
            background: rgba(255, 255, 255, 0.8);
            backdrop-filter: blur(5px);
            padding: 8px 12px 12px 12px;
            margin: 6px 8px;
            border-radius: 10px;
            transition: all 0.3s ease;
            flex-shrink: 0;
            max-height: 220px;
            overflow: hidden;
        }
        .charts-section.collapsed {
            max-height: 40px;
            padding: 6px 12px;
        }
        .charts-section.collapsed .charts-grid {
            display: none;
        }
        .charts-title {
            font-size: 0.8rem;
            font-weight: 700;
            color: #1a1a1a;
            text-align: center;
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 10px;
        }
        .toggle-charts-btn {
            background: rgba(0,0,0,0.1);
            border: none;
            border-radius: 30px;
            padding: 1px 10px;
            cursor: pointer;
            font-size: 0.7rem;
            color: #1a1a1a;
            transition: 0.2s;
        }
        .toggle-charts-btn:hover { background: rgba(0,0,0,0.2); }
        .charts-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            margin-top: 6px;
        }
        .chart-container { background: rgba(255, 255, 255, 0.9); border-radius: 8px; padding: 8px; }
        .chart-container h4 { text-align: center; margin-bottom: 5px; color: #1a1a1a; font-size: 0.6rem; }
        canvas { max-height: 120px; width: 100%; }

        /* ----- CARDS ----- */
        .card {
            background: rgba(42, 42, 42, 0.9);
            backdrop-filter: blur(5px);
            border-radius: 8px;
            padding: 10px;
            margin-bottom: 10px;
            border: 1px solid rgba(255,255,255,0.1);
        }
        .card h3 { color: #2ecc71; margin-bottom: 8px; font-size: 0.7rem; display: flex; align-items: center; gap: 5px; }
        input, select, textarea {
            width: 100%;
            padding: 5px;
            margin: 4px 0;
            background: #1a1a1a;
            border: 1px solid #333;
            border-radius: 6px;
            color: white;
            font-size: 0.65rem;
        }
        button {
            background: linear-gradient(135deg, #1a472a, #0d2a1a);
            color: white;
            padding: 6px;
            font-weight: 600;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            width: 100%;
            margin-top: 4px;
            font-size: 0.65rem;
        }
        .btn-location { background: linear-gradient(135deg, #3498db, #2980b9); }
        .reports-list { max-height: 200px; overflow-y: auto; }
        .report-item {
            background: #1a1a1a;
            padding: 6px 8px;
            margin: 4px 0;
            border-radius: 6px;
            border-left: 3px solid #2ecc71;
            cursor: pointer;
            font-size: 0.6rem;
        }
        .report-item.severity-critical { border-left-color: #e74c3c; }
        .report-item.severity-high { border-left-color: #f39c12; }
        .building-info {
            background: rgba(46,204,113,0.1);
            padding: 6px;
            border-radius: 6px;
            margin-top: 4px;
            font-size: 0.6rem;
            text-align: center;
            cursor: pointer;
            border: 1px solid rgba(46,204,113,0.3);
            color: #2ecc71;
        }
        .sms-card { background: rgba(46,204,113,0.08); padding: 6px; border-radius: 6px; margin-top: 4px; }
        .photo-preview { margin-top: 4px; text-align: center; }
        .photo-preview img { max-width: 100%; border-radius: 6px; max-height: 60px; }

        /* ----- PRESENCE & LEADERBOARD PANELS ----- */
        .presence-panel {
            position: fixed;
            bottom: 15px;
            right: 15px;
            width: 200px;
            background: rgba(30,30,30,0.95);
            backdrop-filter: blur(12px);
            border-radius: 10px;
            border: 1px solid rgba(46,204,113,0.2);
            z-index: 1000;
        }
        .leaderboard-panel {
            position: fixed;
            bottom: 15px;
            right: 230px;
            width: 180px;
            background: rgba(30,30,30,0.95);
            backdrop-filter: blur(12px);
            border-radius: 10px;
            border: 1px solid rgba(243,156,18,0.2);
            z-index: 1000;
        }
        .presence-header, .leaderboard-header {
            padding: 6px 10px;
            border-radius: 10px 10px 0 0;
            display: flex;
            justify-content: space-between;
            cursor: pointer;
            font-size: 0.6rem;
            font-weight: 600;
        }
        .presence-header { background: rgba(46,204,113,0.08); }
        .leaderboard-header { background: rgba(243,156,18,0.08); }
        .presence-list, .leaderboard-list { max-height: 120px; overflow-y: auto; padding: 4px; }
        .presence-user, .leaderboard-item {
            display: flex;
            align-items: center;
            gap: 5px;
            padding: 3px 5px;
            border-radius: 4px;
            margin: 2px 0;
            background: rgba(255,255,255,0.03);
            font-size: 0.6rem;
            cursor: pointer;
        }
        .presence-user:hover, .leaderboard-item:hover { background: rgba(46,204,113,0.15); }
        .online-dot { width: 5px; height: 5px; border-radius: 50%; background: #2ecc71; margin-left: auto; animation: pulse 2s infinite; }
        .rank { width: 20px; font-weight: 700; color: #f39c12; }
        @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.6; } }
        @keyframes fadeInMsg { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }

        @media (max-width: 1000px) {
            .sidebar { width: 100%; max-height: 35vh; }
            .right-panel { height: 65vh; }
            .charts-grid { grid-template-columns: 1fr; }
            .kpi-row { grid-template-columns: repeat(2,1fr); }
            .leaderboard-panel { right: 210px; width: 160px; }
            .presence-panel { width: 160px; }
            .chat-panel { width: 280px !important; }
        }
        @media (max-width: 600px) {
            .system-bar { flex-wrap: wrap; gap: 4px; }
            .brand-center { order: 1; width: 100%; }
            .controls-right { order: 2; justify-content: center; }
            .chat-panel { width: 240px !important; left: 10px !important; bottom: 10px !important; }
        }
    </style>
</head>
<body>
<div class="system-bar">
    <div class="brand-left"></div>
    <div class="brand-center"><h1>🌍 UNDP <span>ImpactMapper</span></h1><p>Command Center | Live Intelligence</p></div>
    <div class="controls-right">
        <select id="languageSelect" class="lang-dropdown">
            <option value="en">🇬🇧 English</option><option value="es">🇪🇸 Español</option><option value="fr">🇫🇷 Français</option>
            <option value="pt">🇵🇹 Português</option><option value="ar">🇸🇦 العربية</option><option value="zh">🇨🇳 中文</option>
        </select>
        <div id="connectionStatus" class="status-badge status-online"><i class="fas fa-circle" style="font-size:4px;"></i> Online</div>
        <button class="sync-btn" onclick="forceSync()"><i class="fas fa-sync-alt"></i> Sync</button>
        <span id="userRoleBadge" class="role-badge"></span>
        <span id="headerExportGroup" style="display:none; gap:4px; align-items:center;">
            <button class="sync-btn" onclick="exportCSV()" title="Export CSV"><i class="fas fa-file-csv"></i> CSV</button>
            <button class="sync-btn" onclick="exportGeoJSON()" title="Export GeoJSON"><i class="fas fa-map"></i> GeoJSON</button>
        </span>
        <button class="sync-btn" id="toggleSidebarBtn" title="Toggle Command Panel"><i class="fas fa-chevron-left"></i></button>
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
            <div class="card"><h3><i class="fas fa-camera"></i> <span id="reportTitle">Report Damage</span></h3>
            <p id="clickHint" style="font-size:0.55rem; color:#2ecc71;">🏢 Click on any building on the map to select it!</p>
            <div id="selectedBuildingInfo" class="building-info" style="display:none;"></div>
            <select id="damageLevel"><option value="minimal">🏠 Minimal/No Damage</option><option value="partial">⚠️ Partially Damaged</option><option value="complete">💀 Completely Damaged</option></select>
            <select id="infrastructureType"><option value="residential">🏘️ Residential</option><option value="commercial">🏪 Commercial</option><option value="government">🏛️ Government</option><option value="utility">💡 Utility</option><option value="transport">🛣️ Transport</option><option value="community">🏥 Community</option><option value="public">🏟️ Public</option></select>
            <input type="text" id="buildingName" placeholder="Building Name">
            <select id="crisisNature"><option value="earthquake">🌋 Earthquake</option><option value="flood">💧 Flood</option><option value="tsunami">🌊 Tsunami</option><option value="hurricane">🌀 Hurricane</option><option value="wildfire">🔥 Wildfire</option><option value="explosion">💥 Explosion</option><option value="conflict">⚔️ Conflict</option></select>
            <select id="debris"><option value="yes">Yes - Requires clearing</option><option value="no">No debris</option></select>
            <input type="text" id="lat" placeholder="Latitude" readonly><input type="text" id="lng" placeholder="Longitude" readonly>
            <button class="btn-location" onclick="shareLocation()"><i class="fas fa-location-dot"></i> <span id="gpsLabel">Use My GPS</span></button>
            <input type="text" id="textLocation" placeholder="Describe location"><textarea id="notes" rows="2" placeholder="Additional notes"></textarea>
            <input type="file" id="photo" accept="image/*" capture="environment"><div id="photoPreview" class="photo-preview"></div>
            <button id="submitBtn" onclick="submitReport()"><i class="fas fa-paper-plane"></i> <span id="submitLabel">Submit Report</span></button>
            <div id="submitStatus" style="margin-top:4px; font-size:0.55rem;"></div></div>
            <div class="card"><h3><i class="fas fa-sms"></i> <span id="smsTitle">SMS Report</span></h3>
            <div class="sms-card"><input type="text" id="smsText" placeholder="Format: DAMAGE LAT LNG">
            <input type="text" id="smsNumber" placeholder="Phone Number (optional)">
            <button onclick="sendSMSReport()"><i class="fas fa-envelope"></i> <span id="smsSendLabel">Send SMS Report</span></button></div>
            <div id="smsStatus" style="margin-top:4px; font-size:0.55rem;"></div></div>
            <div class="card"><h3><i class="fas fa-list"></i> <span id="recentTitle">Recent Reports</span></h3>
            <div id="reportsList" class="reports-list">Loading...</div></div>
            <div class="card" id="exportCard"><h3><i class="fas fa-download"></i> <span id="exportTitle">Export Data (Admin Only)</span></h3>
            <div style="display:flex; gap:6px;"><button id="exportCSVBtn" onclick="exportCSV()" style="flex:1;"><i class="fas fa-file-excel"></i> <span id="csvLabel">CSV</span></button>
            <button id="exportGeoJSONBtn" onclick="exportGeoJSON()" style="flex:1;"><i class="fas fa-map"></i> <span id="geojsonLabel">GeoJSON</span></button></div></div>
        </div>
        <div class="right-panel">
            <div class="map-container"><div id="map"></div></div>
            <div class="charts-section" id="chartsSection">
                <div class="charts-title">
                    📊 DAMAGE ANALYTICS DASHBOARD
                    <button class="toggle-charts-btn" id="toggleChartsBtn" title="Toggle charts visibility">▲</button>
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
    <div style="padding:10px 15px; overflow-y:auto; height:100%;">
        <div class="stats-grid" style="display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:10px; margin-bottom:15px;">
            <div class="stat-card" style="background:#1e1e1e; border-radius:10px; padding:12px;"><div class="stat-value" id="totalReports" style="font-size:1.5rem; font-weight:800; color:#2ecc71;">-</div><div style="font-size:0.6rem; color:#a0a0a0;">Total Reports</div></div>
            <div class="stat-card" style="background:#1e1e1e; border-radius:10px; padding:12px;"><div class="stat-value" id="totalUsers" style="font-size:1.5rem; font-weight:800; color:#2ecc71;">-</div><div style="font-size:0.6rem; color:#a0a0a0;">Active Users</div></div>
            <div class="stat-card" style="background:#1e1e1e; border-radius:10px; padding:12px;"><div class="stat-value" id="avgResponse" style="font-size:1.5rem; font-weight:800; color:#2ecc71;">-</div><div style="font-size:0.6rem; color:#a0a0a0;">Avg Response (min)</div></div>
            <div class="stat-card" style="background:#1e1e1e; border-radius:10px; padding:12px;"><div class="stat-value" id="topReporter" style="font-size:1.5rem; font-weight:800; color:#2ecc71;">-</div><div style="font-size:0.6rem; color:#a0a0a0;">Top Reporter</div></div>
        </div>
        <div style="display:grid; grid-template-columns:repeat(auto-fit,minmax(300px,1fr)); gap:10px;">
            <div style="background:#1e1e1e; border-radius:10px; padding:12px;"><h3 style="color:#2ecc71; font-size:0.8rem;">📈 Daily Report Trend</h3><canvas id="trendChart"></canvas></div>
            <div style="background:#1e1e1e; border-radius:10px; padding:12px;"><h3 style="color:#2ecc71; font-size:0.8rem;">🏗️ Damage Distribution</h3><canvas id="damageChart"></canvas></div>
            <div style="background:#1e1e1e; border-radius:10px; padding:12px;"><h3 style="color:#2ecc71; font-size:0.8rem;">🏘️ Reports by Infrastructure</h3><canvas id="infraChart"></canvas></div>
            <div style="background:#1e1e1e; border-radius:10px; padding:12px;"><h3 style="color:#2ecc71; font-size:0.8rem;">🌋 Reports by Crisis Type</h3><canvas id="crisisChart"></canvas></div>
            <div style="background:#1e1e1e; border-radius:10px; padding:12px; overflow-x:auto;"><h3 style="color:#2ecc71; font-size:0.8rem;">🏆 Top Reporters</h3><table id="reportersTable" style="width:100%; font-size:0.7rem;"><thead><tr><th>Rank</th><th>Username</th><th>Reports</th></tr></thead><tbody></tbody></table></div>
            <div style="background:#1e1e1e; border-radius:10px; padding:12px; overflow-x:auto;"><h3 style="color:#2ecc71; font-size:0.8rem;">👥 Users by Role</h3><table id="rolesTable" style="width:100%; font-size:0.7rem;"><thead><tr><th>Role</th><th>Count</th></tr></thead><tbody></tbody></table></div>
        </div>
    </div>
</div>

<div class="presence-panel"><div class="presence-header" onclick="togglePresence()"><span><i class="fas fa-users"></i> Active Users</span><span id="presenceCount">0</span></div><div id="presenceList" class="presence-list"></div></div>

<!-- GLOWING + DRAGGABLE + RESIZABLE CHAT PANEL -->
<div class="chat-panel" id="glowChat">
    <div class="chat-header" id="chatDragHandle">
        <h4><span class="pulse-dot"></span> CRISIS CHAT</h4>
        <div class="status-badge">● Live</div>
    </div>
    <div id="chatMessages" class="chat-messages"></div>
    <div class="chat-input-area">
        <input type="text" id="chatInput" placeholder="Type a message…" autocomplete="off">
        <button id="chatSendBtn">Send</button>
    </div>
</div>

<div class="leaderboard-panel"><div class="leaderboard-header" onclick="toggleLeaderboard()"><span><i class="fas fa-trophy"></i> Leaderboard</span><span>🏆</span></div><div id="leaderboardList" class="leaderboard-list">Loading...</div></div>

<script>
let map, markers = [], reports = [];
let deviceId = localStorage.getItem('device_id');
let currentUser = { username: '', role: '', avatar: '', color: '#2ecc71', points: 0, badge: '' };
let ws = null;
let selectedBuilding = null;
let currentMarker = null;
let currentLang = localStorage.getItem('language') || 'en';
let translations = {};
let offlineQueue = [];
let currentTileLayer = null;
let isAdmin = false;
let pieChart, barChart, lineChart, damageChart, trendChart, infraChart, crisisChart;

function loadOfflineQueue() { const saved = localStorage.getItem('offline_reports'); if (saved) offlineQueue = JSON.parse(saved); updateOfflineUI(); }
function saveOfflineQueue() { localStorage.setItem('offline_reports', JSON.stringify(offlineQueue)); updateOfflineUI(); }
function updateOfflineUI() { document.getElementById('pendingTasks').innerHTML = offlineQueue.length; }
if (!deviceId) { deviceId = 'web_' + Date.now(); localStorage.setItem('device_id', deviceId); }
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
    try {
        const res = await fetch('/api/admin/stats');
        const data = await res.json();
        document.getElementById('totalReports').innerHTML = data.total_reports;
        document.getElementById('totalUsers').innerHTML = data.total_users;
        document.getElementById('avgResponse').innerHTML = data.avg_response_minutes;
        document.getElementById('topReporter').innerHTML = data.top_reporters[0]?.username || '-';
        if (trendChart) trendChart.destroy();
        trendChart = new Chart(document.getElementById('trendChart'), {
            type: 'line', data: { labels: data.daily_trend.map(d=>d.date), datasets: [{ label:'Reports', data:data.daily_trend.map(d=>d.count), borderColor:'#2ecc71', fill:true, backgroundColor:'rgba(46,204,113,0.1)', tension:0.4 }] },
            options: { responsive: true, maintainAspectRatio: true, plugins: { legend: { labels: { color:'#e0e0e0' } } } }
        });
        if (damageChart) damageChart.destroy();
        damageChart = new Chart(document.getElementById('damageChart'), {
            type: 'doughnut', data: { labels: data.by_damage.map(d=>d.level), datasets: [{ data:data.by_damage.map(d=>d.count), backgroundColor:['#e74c3c','#f39c12','#2ecc71'] }] },
            options: { responsive: true, plugins: { legend: { labels: { color:'#e0e0e0' } } } }
        });
        if (infraChart) infraChart.destroy();
        infraChart = new Chart(document.getElementById('infraChart'), {
            type: 'bar', data: { labels: data.by_infrastructure.map(d=>d.type), datasets: [{ label:'Reports', data:data.by_infrastructure.map(d=>d.count), backgroundColor:'#2ecc71', borderRadius:8 }] },
            options: { responsive: true, maintainAspectRatio: true, plugins: { legend: { labels: { color:'#e0e0e0' } } } }
        });
        if (crisisChart) crisisChart.destroy();
        crisisChart = new Chart(document.getElementById('crisisChart'), {
            type: 'bar', data: { labels: data.by_crisis.map(d=>d.crisis), datasets: [{ label:'Reports', data:data.by_crisis.map(d=>d.count), backgroundColor:'#3498db', borderRadius:8 }] },
            options: { responsive: true, maintainAspectRatio: true, plugins: { legend: { labels: { color:'#e0e0e0' } } } }
        });
        document.getElementById('reportersTable').querySelector('tbody').innerHTML = data.top_reporters.map((r,i)=>`<tr><td style="padding:6px;">${i+1}</td><td style="padding:6px;">${r.username}</td><td style="padding:6px;">${r.reports}</td>`).join('');
        document.getElementById('rolesTable').querySelector('tbody').innerHTML = data.users_by_role.map(r=>`<tr><td style="padding:6px;">${r.role}</td><td style="padding:6px;">${r.count}</td>`).join('');
    } catch(e) { console.error(e); }
}

function updateCommandCenterCharts() {
    const damageCounts = { minimal:0, partial:0, complete:0 };
    for(let r of reports) { if(r.damage_level==='minimal') damageCounts.minimal++; else if(r.damage_level==='partial') damageCounts.partial++; else if(r.damage_level==='complete') damageCounts.complete++; }
    if(pieChart) pieChart.destroy();
    pieChart = new Chart(document.getElementById('pieChart'), {
        type:'pie', data:{ labels:['Minimal','Partial','Complete'], datasets:[{ data:[damageCounts.minimal,damageCounts.partial,damageCounts.complete], backgroundColor:['#2ecc71','#f39c12','#e74c3c'] }] },
        options:{ responsive:true, maintainAspectRatio:true, plugins:{ legend:{ position:'bottom', labels:{ font:{ size:8, weight:'bold' }, color:'#000' } } } }
    });
    const infraCounts = {}; for(let r of reports) { let t=r.infrastructure_type||'Unknown'; infraCounts[t]=(infraCounts[t]||0)+1; }
    const infraLabels = Object.keys(infraCounts).slice(0,6);
    const infraData = infraLabels.map(l=>infraCounts[l]);
    if(barChart) barChart.destroy();
    barChart = new Chart(document.getElementById('barChart'), {
        type:'bar', data:{ labels:infraLabels, datasets:[{ label:'Reports', data:infraData, backgroundColor:'#3498db', borderRadius:6 }] },
        options:{ responsive:true, scales:{ y:{ beginAtZero:true, title:{ display:true, text:'Count', color:'#000', font:{size:8} }, ticks:{ color:'#000', font:{size:8} } }, x:{ ticks:{ color:'#000', font:{size:8} } } }, plugins:{ legend:{ labels:{ color:'#000', font:{size:8} } } } }
    });
    const dailyCounts = {}; for(let r of reports) { let d = new Date(r.timestamp).toISOString().split('T')[0]; dailyCounts[d]=(dailyCounts[d]||0)+1; }
    const last7Days = []; for(let i=6;i>=0;i--) { let d=new Date(); d.setDate(d.getDate()-i); last7Days.push(d.toISOString().split('T')[0]); }
    const lineData = last7Days.map(d=>dailyCounts[d]||0);
    if(lineChart) lineChart.destroy();
    lineChart = new Chart(document.getElementById('lineChart'), {
        type:'line', data:{ labels:last7Days.map(d=>d.slice(5)), datasets:[{ label:'Reports per Day', data:lineData, borderColor:'#2ecc71', backgroundColor:'rgba(46,204,113,0.1)', fill:true, tension:0.4 }] },
        options:{ responsive:true, scales:{ y:{ beginAtZero:true, title:{ display:true, text:'Count', color:'#000', font:{size:8} }, ticks:{ color:'#000', font:{size:8} } }, x:{ ticks:{ color:'#000', font:{size:8} } } }, plugins:{ legend:{ labels:{ color:'#000', font:{size:8} } } } }
    });
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
    map = L.map('map').setView([20, 0], 2);
    map.attributionControl.setPrefix('');
    
    // OSM MAP TILES - FIXED
    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/">CARTO</a>',
        subdomains: 'abcd',
        maxZoom: 19,
        minZoom: 1
    }).addTo(map);
    
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
        reader.onload = function(ev) { preview.innerHTML = `<img src="${ev.target.result}" style="max-width:100%; max-height:60px;">`; };
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
            let marker = L.circleMarker([r.lat,r.lng], { radius:6, fillColor:color, color:'#fff', weight:2, fillOpacity:0.8 }).addTo(map);
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
    if(isOnline) { statusDiv.innerHTML = '<i class="fas fa-circle" style="font-size:4px;"></i> Online'; statusDiv.className = 'status-badge status-online'; }
    else { statusDiv.innerHTML = '<i class="fas fa-circle" style="font-size:4px;"></i> Offline'; statusDiv.className = 'status-badge'; }
}

async function loadCurrentUser() {
    try {
        let res = await fetch('/api/current_user');
        let user = await res.json();
        currentUser = user;
        document.getElementById('userRoleBadge').innerHTML = `${user.role} ${user.points} pts`;
        if(user.role === 'admin') { document.getElementById('exportCard').style.display = 'block'; document.getElementById('tabAnalyticsBtn').style.display = 'inline-block'; isAdmin=true; }
        else { document.getElementById('exportCard').style.display = 'none'; isAdmin=false; }
        connectWebSocket();
    } catch(e) { console.error('Auth error',e); }
}

function connectWebSocket() {
    if(ws && ws.readyState === WebSocket.OPEN) return;
    let protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    let wsUrl = `${protocol}://${window.location.host}/ws/${currentUser.username}`;
    ws = new WebSocket(wsUrl);
    ws.onopen = () => { console.log('WebSocket connected'); if(window.wsPingInterval) clearInterval(window.wsPingInterval); window.wsPingInterval = setInterval(() => { if(ws.readyState===WebSocket.OPEN) ws.send(JSON.stringify({type:'ping'})); }, 30000); };
    ws.onmessage = (event) => {
        try {
            let data = JSON.parse(event.data);
            if(data.type === 'presence') updatePresence(data.users, data.count);
            else if(data.type === 'chat') addChatMessage(data.data);
            else if(data.type === 'new_report') loadReports();
            else if(data.type === 'pong') { /* keep alive */ }
        } catch(e) { console.error(e); }
    };
    ws.onclose = () => { console.log('WebSocket closed, reconnecting...'); setTimeout(connectWebSocket,3000); };
    ws.onerror = (error) => { console.error('WebSocket error',error); ws.close(); };
}

function updatePresence(users, count) {
    let container = document.getElementById('presenceList');
    let countSpan = document.getElementById('presenceCount');
    if(countSpan) countSpan.innerText = count;
    if(!container) return;
    container.innerHTML = users.map(u => `<div class="presence-user"><span>${u.avatar||'👤'}</span><span>${u.username}</span><span class="online-dot"></span></div>`).join('');
}

function sendChatMessage() {
    let input = document.getElementById('chatInput');
    let msg = input.value.trim();
    if(!msg || !ws || ws.readyState !== WebSocket.OPEN) {
        alert('Chat not connected.');
        return;
    }
    ws.send(JSON.stringify({ type:'chat', message:msg }));
    input.value = '';
}

function addChatMessage(msg) {
    let container = document.getElementById('chatMessages');
    if(!container) return;
    let div = document.createElement('div');
    div.className = msg.username === currentUser.username ? 'chat-message own' : 'chat-message other';
    div.innerHTML = `<span class="msg-username">${msg.username} <span class="msg-time">${new Date(msg.timestamp).toLocaleTimeString()}</span></span>${msg.message}`;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

async function loadLeaderboard() {
    try {
        let res = await fetch('/api/leaderboard');
        let leaders = await res.json();
        let container = document.getElementById('leaderboardList');
        if(!container) return;
        container.innerHTML = leaders.map((l,i) => `<div class="leaderboard-item"><span class="rank">${i+1}</span><span>${l.username}</span><span>🏆 ${l.points}</span></div>`).join('');
    } catch(e) { console.error(e); }
}

async function loadStats() { try { let res=await fetch('/api/stats'); let stats=await res.json(); document.getElementById('totalReports').innerText=stats.total_reports; document.getElementById('todayReports').innerText=stats.today_reports; document.getElementById('pendingSync').innerText=stats.pending_sync; } catch(e){} }

function exportCSV() { window.open('/api/reports/csv','_blank'); }

async function exportGeoJSON() {
    try { let res=await fetch('/api/reports/geojson'); let data=await res.json(); let blob=new Blob([JSON.stringify(data)],{type:'application/json'}); let url=URL.createObjectURL(blob); let a=document.createElement('a'); a.href=url; a.download='reports.geojson'; a.click(); URL.revokeObjectURL(url); } catch(e){ alert('Export failed'); }
}

function showToast(msg,type) { alert(msg); }

function togglePresence() { let el=document.querySelector('.presence-list'); if(el) el.style.display=el.style.display==='none'?'block':'none'; }
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
                let marker = L.circleMarker([r.lat, r.lng], { radius:8, fillColor:'#e74c3c', color:'#fff', weight:2, fillOpacity:0.9 }).addTo(map);
                marker.bindPopup(`<b>URGENT</b><br>${r.building_name || 'Building'}<br>Damage: ${r.damage_level}`);
                markers.push(marker);
            }
        }
        if(criticalReports.length > 0) map.setView([criticalReports[0].lat, criticalReports[0].lng], 14);
    });
}

window.addEventListener('online', () => { updateConnectionStatus(true); syncOfflineReports(); loadReports(); showToast('Back online!'); updateKPIs(); updateCommandCenterCharts(); });
window.addEventListener('offline', () => { updateConnectionStatus(false); showToast('Offline – reports saved locally.'); });

updateConnectionStatus(navigator.onLine);
initMap();
loadCurrentUser();
loadReports();
loadLeaderboard();
loadStats();
setInterval(() => loadReports(), 30000);
setInterval(() => updateKPIs(), 10000);
setInterval(() => updateCommandCenterCharts(), 15000);
setInterval(() => loadLeaderboard(), 10000);

// ================================================================
//  DRAGGABLE + RESIZABLE CHAT
// ================================================================
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

// ================================================================
//  TOGGLE CHARTS & SIDEBAR
// ================================================================
document.addEventListener('DOMContentLoaded', function() {
    const toggleBtn = document.getElementById('toggleChartsBtn');
    const chartsSection = document.getElementById('chartsSection');
    let chartsVisible = true;
    toggleBtn.addEventListener('click', function() {
        chartsVisible = !chartsVisible;
        chartsSection.classList.toggle('collapsed', !chartsVisible);
        toggleBtn.textContent = chartsVisible ? '▲' : '▼';
        setTimeout(() => { if (map) map.invalidateSize(); }, 300);
    });

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
