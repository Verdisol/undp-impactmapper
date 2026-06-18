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

        /* ----- GLOWING + DRAGGABLE CHAT OVERRIDES ----- */
        .chat-panel {
            position: fixed !important;
            bottom: 20px !important;
            left: 20px !important;
            width: 340px !important;
            max-height: 480px !important;
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
            padding: 14px 18px !important;
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
            font-size: 0.9rem !important;
            font-weight: 700 !important;
            letter-spacing: 1px !important;
            text-shadow: 0 0 18px rgba(0,255,200,0.3) !important;
            display: flex !important;
            align-items: center !important;
            gap: 10px !important;
        }
        .chat-header .pulse-dot {
            display: inline-block !important;
            width: 10px !important;
            height: 10px !important;
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
            font-size: 0.7rem !important;
            background: rgba(0,255,200,0.12) !important;
            padding: 2px 12px !important;
            border-radius: 30px !important;
            color: #aaffee !important;
            border: 1px solid rgba(0,255,200,0.15) !important;
        }
        .chat-messages {
            flex: 1 !important;
            padding: 10px 14px !important;
            overflow-y: auto !important;
            max-height: 280px !important;
            min-height: 160px !important;
            display: flex !important;
            flex-direction: column !important;
            gap: 5px !important;
            scroll-behavior: smooth !important;
            background: transparent !important;
        }
        .chat-messages::-webkit-scrollbar { width: 4px; }
        .chat-messages::-webkit-scrollbar-thumb {
            background: #00ffcc;
            border-radius: 10px;
            box-shadow: 0 0 12px #00ffcc;
        }
        .chat-message {
            padding: 6px 12px !important;
            border-radius: 14px !important;
            max-width: 85% !important;
            font-size: 0.75rem !important;
            line-height: 1.4 !important;
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
            font-size: 0.7rem !important;
            display: block !important;
            margin-bottom: 2px !important;
        }
        .chat-message .msg-time {
            font-size: 0.6rem !important;
            opacity: 0.4 !important;
            margin-left: 8px !important;
        }
        .chat-input-area {
            padding: 8px 14px 14px 14px !important;
            border-top: 1px solid rgba(0,255,200,0.08) !important;
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
            border: 1px solid rgba(0,255,200,0.15) !important;
            background: rgba(0,0,0,0.45) !important;
            color: #fff !important;
            font-size: 0.75rem !important;
            outline: none !important;
        }
        .chat-input-area input:focus {
            border-color: #00ffcc !important;
            box-shadow: 0 0 25px rgba(0,255,200,0.12) !important;
        }
        .chat-input-area button {
            padding: 8px 18px !important;
            border-radius: 30px !important;
            border: none !important;
            background: #00ffcc !important;
            color: #0b0e14 !important;
            font-weight: 700 !important;
            font-size: 0.75rem !important;
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

        .tabs-container {
            background: var(--bg-card);
            padding: 0 24px;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            gap: 4px;
        }
        .tab-btn {
            padding: 14px 28px;
            background: transparent;
            color: #a0a0a0;
            border: none;
            font-size: 0.9rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        .tab-btn:hover { color: var(--primary); background: var(--primary-muted); transform: translateY(-2px); }
        .tab-btn.active { color: var(--primary); border-bottom: 2px solid var(--primary); }
        .tab-content { display: none; height: calc(100vh - 130px); }
        .tab-content.active { display: block; }
        .system-bar {
            background: #1a472a;
            padding: 12px 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 2px solid #2ecc71;
        }
        .brand-left { width: 200px; visibility: hidden; }
        .brand-center { flex: 1; text-align: center; }
        .brand-center h1 { font-size: 1.4rem; font-weight: 700; color: white; letter-spacing: 1px; }
        .brand-center h1 span { color: #2ecc71; }
        .brand-center p { font-size: 0.65rem; color: rgba(255,255,255,0.8); margin-top: 2px; }
        .controls-right {
            width: 200px;
            display: flex;
            align-items: center;
            justify-content: flex-end;
            gap: 12px;
            flex-wrap: wrap;
        }
        .lang-dropdown {
            background: rgba(255,255,255,0.15);
            color: white;
            border: none;
            padding: 5px 10px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.7rem;
        }
        .lang-dropdown:hover { background: rgba(255,255,255,0.25); }
        .status-badge {
            padding: 3px 8px;
            border-radius: 30px;
            font-size: 0.65rem;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 5px;
            background: rgba(0,0,0,0.3);
        }
        .status-online { color: #2ecc71; }
        .sync-btn, .logout-btn {
            background: rgba(255,255,255,0.15);
            border: none;
            padding: 5px 10px;
            border-radius: 8px;
            color: white;
            font-size: 0.65rem;
            cursor: pointer;
            transition: all 0.3s ease;
            white-space: nowrap;
        }
        .sync-btn:hover { background: rgba(255,255,255,0.25); }
        .logout-btn { background: rgba(231,76,60,0.3); }
        .logout-btn:hover { background: rgba(231,76,60,0.5); }
        .role-badge {
            background: rgba(0,0,0,0.3);
            color: #2ecc71;
            padding: 3px 8px;
            border-radius: 30px;
            font-size: 0.65rem;
            font-weight: 600;
        }
        .kpi-row {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 12px;
            padding: 12px 24px;
            background: var(--bg-dark);
        }
        .kpi-card {
            background: var(--bg-card);
            border-radius: 8px;
            padding: 10px 12px;
            border: 1px solid var(--border-color);
            cursor: pointer;
            transition: all 0.3s ease;
        }
        .kpi-card:hover { border-color: var(--primary); transform: translateY(-2px); box-shadow: 0 0 15px rgba(46,204,113,0.6); }
        .kpi-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
        .kpi-header span { font-size: 0.6rem; color: #a0a0a0; text-transform: uppercase; }
        .kpi-value { font-size: 1.4rem; font-weight: 700; margin-bottom: 4px; }
        .kpi-value.warning { color: #f39c12; }
        .progress-bar { height: 3px; background: #2a2a2a; border-radius: 2px; overflow: hidden; margin-top: 8px; }
        .progress-fill { height: 100%; background: var(--primary); border-radius: 2px; }
        .pill-group { display: flex; gap: 5px; margin-top: 8px; flex-wrap: wrap; }
        .pill { padding: 2px 6px; border-radius: 15px; font-size: 0.55rem; font-weight: 500; }
        .pill-red { background: rgba(231,76,60,0.12); color: #e74c3c; }
        .pill-yellow { background: rgba(243,156,18,0.12); color: #f39c12; }
        .pill-green { background: rgba(46,204,113,0.12); color: #2ecc71; }
        .main-layout { display: flex; height: calc(100% - 60px); }
        .sidebar { width: 420px; background: var(--bg-sidebar); overflow-y: auto; padding: 15px; border-right: 1px solid var(--border-color); }
        .right-panel { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
        .map-container { flex: 1; position: relative; }
        #map { height: 100%; width: 100%; }
        .charts-section {
            background: rgba(255, 255, 255, 0.8);
            backdrop-filter: blur(5px);
            padding: 10px 15px 15px 15px;
            margin: 10px;
            border-radius: 12px;
            transition: all 0.3s ease;
            flex-shrink: 0;
            max-height: 300px;
            overflow: hidden;
        }
        .charts-section.collapsed {
            max-height: 60px;
            padding: 10px 15px;
        }
        .charts-section.collapsed .charts-grid {
            display: none;
        }
        .charts-title {
            font-size: 1rem;
            font-weight: 700;
            color: #1a1a1a;
            text-align: center;
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 12px;
        }
        .toggle-charts-btn {
            background: rgba(0,0,0,0.1);
            border: none;
            border-radius: 30px;
            padding: 2px 12px;
            cursor: pointer;
            font-size: 0.8rem;
            color: #1a1a1a;
            transition: 0.2s;
        }
        .toggle-charts-btn:hover {
            background: rgba(0,0,0,0.2);
        }
        .charts-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin-top: 10px;
        }
        .chart-container { background: rgba(255, 255, 255, 0.9); border-radius: 10px; padding: 10px; }
        .chart-container h4 { text-align: center; margin-bottom: 8px; color: #1a1a1a; font-size: 0.7rem; }
        canvas { max-height: 150px; width: 100%; }
        .card {
            background: rgba(42, 42, 42, 0.9);
            backdrop-filter: blur(5px);
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 15px;
            border: 1px solid rgba(255,255,255,0.1);
        }
        .card h3 { color: #2ecc71; margin-bottom: 12px; font-size: 0.8rem; display: flex; align-items: center; gap: 6px; }
        input, select, textarea {
            width: 100%;
            padding: 8px;
            margin: 6px 0;
            background: #1a1a1a;
            border: 1px solid #333;
            border-radius: 8px;
            color: white;
            font-size: 0.75rem;
        }
        button {
            background: linear-gradient(135deg, #1a472a, #0d2a1a);
            color: white;
            padding: 8px;
            font-weight: 600;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            width: 100%;
            margin-top: 6px;
            font-size: 0.75rem;
        }
        .btn-location { background: linear-gradient(135deg, #3498db, #2980b9); }
        .reports-list { max-height: 250px; overflow-y: auto; }
        .report-item {
            background: #1a1a1a;
            padding: 10px;
            margin: 8px 0;
            border-radius: 8px;
            border-left: 3px solid #2ecc71;
            cursor: pointer;
            font-size: 0.7rem;
        }
        .report-item.severity-critical { border-left-color: #e74c3c; }
        .report-item.severity-high { border-left-color: #f39c12; }
        .damage-badge { display: inline-block; padding: 2px 6px; border-radius: 15px; font-size: 0.6rem; margin-left: 5px; }
        .badge-minimal { background: rgba(46,204,113,0.2); color: #2ecc71; }
        .badge-partial { background: rgba(243,156,18,0.2); color: #f39c12; }
        .badge-complete { background: rgba(231,76,60,0.2); color: #e74c3c; }
        .building-info {
            background: rgba(46,204,113,0.1);
            padding: 8px;
            border-radius: 8px;
            margin-top: 8px;
            font-size: 0.65rem;
            text-align: center;
            cursor: pointer;
            border: 1px solid rgba(46,204,113,0.3);
            color: #2ecc71;
        }
        .sms-card { background: rgba(46,204,113,0.08); padding: 8px; border-radius: 8px; margin-top: 8px; }
        .photo-preview { margin-top: 8px; text-align: center; }
        .photo-preview img { max-width: 100%; border-radius: 8px; max-height: 80px; }
        .presence-panel, .leaderboard-panel {
            position: fixed;
            background: rgba(30,30,30,0.95);
            backdrop-filter: blur(12px);
            border-radius: 10px;
            z-index: 1000;
        }
        .presence-panel { bottom: 15px; right: 15px; width: 220px; border: 1px solid rgba(46,204,113,0.2); }
        .leaderboard-panel { bottom: 15px; right: 250px; width: 200px; border: 1px solid rgba(243,156,18,0.2); }
        .presence-header, .leaderboard-header {
            padding: 8px;
            border-radius: 10px 10px 0 0;
            display: flex;
            justify-content: space-between;
            cursor: pointer;
            font-size: 0.7rem;
            font-weight: 600;
        }
        .presence-header { background: rgba(46,204,113,0.08); }
        .leaderboard-header { background: rgba(243,156,18,0.08); }
        .presence-list, .leaderboard-list { max-height: 140px; overflow-y: auto; padding: 6px; }
        .presence-user, .leaderboard-item {
            display: flex;
            align-items: center;
            gap: 6px;
            padding: 5px;
            border-radius: 6px;
            margin: 3px 0;
            background: rgba(255,255,255,0.03);
            font-size: 0.65rem;
            cursor: pointer;
        }
        .presence-user:hover, .leaderboard-item:hover { background: rgba(46,204,113,0.15); }
        .online-dot { width: 6px; height: 6px; border-radius: 50%; background: #2ecc71; margin-left: auto; animation: pulse 2s infinite; }
        .rank { width: 25px; font-weight: 700; color: #f39c12; }
        @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.6; } }
        @media (max-width: 1000px) {
            .sidebar { width: 100%; max-height: 40vh; }
            .right-panel { height: 60vh; }
            .charts-grid { grid-template-columns: 1fr; }
            .kpi-row { grid-template-columns: repeat(2,1fr); }
            .leaderboard-panel { right: 230px; }
            .controls-right { gap: 6px; }
            .sync-btn, .logout-btn { padding: 3px 6px; font-size: 0.6rem; }
            .charts-section { max-height: 250px; }
        }
        @media (max-width: 600px) {
            .system-bar { flex-wrap: wrap; gap: 5px; }
            .brand-center { order: 1; width: 100%; }
            .controls-right { order: 2; justify-content: center; }
        }
    </style>
</head>
<body>
<div class="system-bar">
    <div class="brand-left"></div>
    <div class="brand-center"><h1>🌍 UNDP <span>ImpactMapper</span></h1><p>Analytics Command Center | Live Intelligence</p></div>
    <div class="controls-right">
        <select id="languageSelect" class="lang-dropdown">
            <option value="en">🇬🇧 English</option><option value="es">🇪🇸 Español</option><option value="fr">🇫🇷 Français</option>
            <option value="pt">🇵🇹 Português</option><option value="ar">🇸🇦 العربية</option><option value="zh">🇨🇳 中文</option>
        </select>
        <div id="connectionStatus" class="status-badge status-online"><i class="fas fa-circle" style="font-size:5px;"></i> Online</div>
        <button class="sync-btn" onclick="forceSync()"><i class="fas fa-sync-alt"></i> Sync</button>
        <span id="userRoleBadge" class="role-badge"></span>
        <!-- EXPORT BUTTONS IN HEADER (before logout) -->
        <span id="headerExportGroup" style="display:none; gap:5px; align-items:center;">
            <button class="sync-btn" onclick="exportCSV()" title="Export CSV"><i class="fas fa-file-csv"></i> CSV</button>
            <button class="sync-btn" onclick="exportGeoJSON()" title="Export GeoJSON"><i class="fas fa-map"></i> GeoJSON</button>
        </span>
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
        <div class="sidebar">
            <div class="card"><h3><i class="fas fa-camera"></i> <span id="reportTitle">Report Damage</span></h3>
            <p id="clickHint" style="font-size:0.65rem; color:#2ecc71;">🏢 Click on any building on the map to select it!</p>
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
            <div id="submitStatus" style="margin-top:8px; font-size:0.65rem;"></div></div>
            <div class="card"><h3><i class="fas fa-sms"></i> <span id="smsTitle">SMS Report</span></h3>
            <div class="sms-card"><input type="text" id="smsText" placeholder="Format: DAMAGE LAT LNG (e.g., collapsed 28.6139 77.2090)">
            <input type="text" id="smsNumber" placeholder="Your Phone Number (optional)">
            <button onclick="sendSMSReport()"><i class="fas fa-envelope"></i> <span id="smsSendLabel">Send SMS Report</span></button></div>
            <div id="smsStatus" style="margin-top:6px; font-size:0.65rem;"></div></div>
            <div class="card"><h3><i class="fas fa-list"></i> <span id="recentTitle">Recent Reports</span></h3>
            <div id="reportsList" class="reports-list">Loading...</div></div>
        </div>
        <div class="right-panel">
            <div class="map-container"><div id="map"></div></div>
            <!-- Collapsible Analytics Charts -->
            <div class="charts-section" id="chartsSection">
                <div class="charts-title">
                    📊 DAMAGE ANALYTICS DASHBOARD
                    <button class="toggle-charts-btn" id="toggleChartsBtn" title="Toggle charts visibility">▲</button>
                </div>
                <div class="charts-grid">
                    <div class="chart-container"><h4>🥧 Damage Distribution (Pie)</h4><canvas id="pieChart"></canvas></div>
                    <div class="chart-container"><h4>📊 Damage by Infrastructure</h4><canvas id="barChart"></canvas></div>
                    <div class="chart-container"><h4>📈 Damage Trend (Line)</h4><canvas id="lineChart"></canvas></div>
                </div>
            </div>
        </div>
    </div>
</div>

<div id="analyticsTab" class="tab-content">
    <div style="padding:15px 20px; overflow-y:auto; height:100%;">
        <div class="stats-grid" style="display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:15px; margin-bottom:20px;">
            <div class="stat-card" style="background:#1e1e1e; border-radius:12px; padding:15px;"><div class="stat-value" id="totalReports" style="font-size:1.8rem; font-weight:800; color:#2ecc71;">-</div><div style="font-size:0.7rem; color:#a0a0a0;">Total Reports</div></div>
            <div class="stat-card" style="background:#1e1e1e; border-radius:12px; padding:15px;"><div class="stat-value" id="totalUsers" style="font-size:1.8rem; font-weight:800; color:#2ecc71;">-</div><div style="font-size:0.7rem; color:#a0a0a0;">Active Users</div></div>
            <div class="stat-card" style="background:#1e1e1e; border-radius:12px; padding:15px;"><div class="stat-value" id="avgResponse" style="font-size:1.8rem; font-weight:800; color:#2ecc71;">-</div><div style="font-size:0.7rem; color:#a0a0a0;">Avg Response (min)</div></div>
            <div class="stat-card" style="background:#1e1e1e; border-radius:12px; padding:15px;"><div class="stat-value" id="topReporter" style="font-size:1.8rem; font-weight:800; color:#2ecc71;">-</div><div style
