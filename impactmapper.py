<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ImpactMapper - Glowing Chat</title>
    <style>
        /* -------------------- RESET -------------------- */
        * { box-sizing: border-box; margin: 0; padding: 0; }
        
        body {
            background: #0b0e14;
            font-family: 'Segoe UI', system-ui, sans-serif;
            height: 100vh;
            overflow: hidden;
        }

        /* -------------------- CHAT CONTAINER (Draggable) -------------------- */
        #chat-container {
            position: fixed;
            bottom: 30px;
            right: 30px;
            width: 380px;
            max-height: 520px;
            background: rgba(18, 25, 40, 0.92);
            backdrop-filter: blur(12px);
            border-radius: 20px;
            border: 1px solid rgba(0, 255, 200, 0.25);
            
            /* 🔥 THE GLOW 🔥 */
            box-shadow: 
                0 0 25px rgba(0, 255, 200, 0.3),
                0 0 60px rgba(0, 255, 200, 0.15),
                inset 0 0 30px rgba(0, 255, 200, 0.05);
            
            /* Glow animation (pulse) */
            animation: pulseGlow 2.5s ease-in-out infinite alternate;
            
            display: flex;
            flex-direction: column;
            z-index: 9999;
            cursor: grab; /* Grabbing cursor for drag */
            transition: box-shadow 0.3s ease;
            user-select: none;
        }
        
        /* Make the glow even stronger on hover */
        #chat-container:hover {
            box-shadow: 
                0 0 40px rgba(0, 255, 200, 0.5),
                0 0 80px rgba(0, 255, 200, 0.25),
                inset 0 0 40px rgba(0, 255, 200, 0.08);
        }

        /* Pulse keyframes */
        @keyframes pulseGlow {
            0% {
                box-shadow: 
                    0 0 20px rgba(0, 255, 200, 0.2),
                    0 0 40px rgba(0, 255, 200, 0.1);
            }
            100% {
                box-shadow: 
                    0 0 35px rgba(0, 255, 200, 0.5),
                    0 0 80px rgba(0, 255, 200, 0.25),
                    inset 0 0 30px rgba(0, 255, 200, 0.05);
            }
        }

        /* -------------------- HEADER (Drag handle) -------------------- */
        #chat-header {
            padding: 16px 20px;
            background: rgba(0, 255, 200, 0.08);
            border-bottom: 1px solid rgba(0, 255, 200, 0.15);
            border-radius: 20px 20px 0 0;
            cursor: grab;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        #chat-header:active {
            cursor: grabbing;
        }
        #chat-header h3 {
            color: #00ffcc;
            font-weight: 600;
            font-size: 15px;
            letter-spacing: 1px;
            text-shadow: 0 0 15px rgba(0, 255, 200, 0.4);
            display: flex;
            align-items: center;
            gap: 8px;
        }
        #chat-header h3 span {
            display: inline-block;
            width: 10px;
            height: 10px;
            background: #00ffcc;
            border-radius: 50%;
            box-shadow: 0 0 15px #00ffcc;
            animation: blink 1.2s infinite;
        }
        @keyframes blink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.2; }
        }
        #chat-header .status-badge {
            font-size: 11px;
            background: rgba(0, 255, 200, 0.15);
            padding: 4px 12px;
            border-radius: 30px;
            color: #aaffee;
            border: 1px solid rgba(0, 255, 200, 0.2);
        }

        /* -------------------- MESSAGES AREA -------------------- */
        #chat-messages {
            flex: 1;
            padding: 16px 18px;
            overflow-y: auto;
            max-height: 340px;
            min-height: 200px;
            display: flex;
            flex-direction: column;
            gap: 6px;
            scroll-behavior: smooth;
        }
        #chat-messages::-webkit-scrollbar {
            width: 4px;
        }
        #chat-messages::-webkit-scrollbar-track {
            background: transparent;
        }
        #chat-messages::-webkit-scrollbar-thumb {
            background: #00ffcc;
            border-radius: 10px;
            box-shadow: 0 0 10px #00ffcc;
        }

        .chat-msg {
            padding: 8px 14px;
            border-radius: 14px;
            max-width: 85%;
            word-wrap: break-word;
            font-size: 14px;
            line-height: 1.4;
            animation: fadeIn 0.2s ease;
        }
        .chat-msg.own {
            align-self: flex-end;
            background: rgba(0, 255, 200, 0.18);
            border: 1px solid rgba(0, 255, 200, 0.2);
            color: #e0faf5;
            border-bottom-right-radius: 4px;
        }
        .chat-msg.other {
            align-self: flex-start;
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid rgba(255, 255, 255, 0.08);
            color: #cdd9e6;
            border-bottom-left-radius: 4px;
        }
        .chat-msg .username {
            font-weight: 600;
            color: #00ffcc;
            font-size: 12px;
            display: block;
            margin-bottom: 2px;
            text-shadow: 0 0 8px rgba(0, 255, 200, 0.2);
        }
        .chat-msg .time {
            font-size: 9px;
            opacity: 0.4;
            margin-left: 10px;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(8px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* -------------------- INPUT AREA -------------------- */
        #chat-input-area {
            padding: 12px 16px 16px 16px;
            border-top: 1px solid rgba(0, 255, 200, 0.1);
            display: flex;
            gap: 10px;
            align-items: center;
        }
        #chat-input-area input {
            flex: 1;
            padding: 10px 16px;
            border-radius: 40px;
            border: 1px solid rgba(0, 255, 200, 0.2);
            background: rgba(0, 0, 0, 0.4);
            color: #ffffff;
            font-size: 14px;
            outline: none;
            transition: 0.3s;
        }
        #chat-input-area input:focus {
            border-color: #00ffcc;
            box-shadow: 0 0 20px rgba(0, 255, 200, 0.15);
        }
        #chat-input-area input::placeholder {
            color: rgba(255, 255, 255, 0.3);
        }
        #chat-input-area button {
            padding: 10px 22px;
            border-radius: 40px;
            border: none;
            background: #00ffcc;
            color: #0b0e14;
            font-weight: 700;
            font-size: 14px;
            cursor: pointer;
            box-shadow: 0 0 25px rgba(0, 255, 200, 0.2);
            transition: 0.2s;
        }
        #chat-input-area button:hover {
            transform: scale(1.04);
            box-shadow: 0 0 40px rgba(0, 255, 200, 0.4);
        }

        /* -------------------- CONNECTION STATUS (top-right) -------------------- */
        #ws-status {
            position: fixed;
            top: 20px;
            right: 20px;
            background: rgba(0,0,0,0.7);
            padding: 6px 16px;
            border-radius: 30px;
            color: #aaa;
            font-size: 12px;
            border: 1px solid #333;
            z-index: 10000;
            backdrop-filter: blur(8px);
        }
        #ws-status.connected {
            border-color: #00ffcc;
            color: #00ffcc;
            box-shadow: 0 0 20px rgba(0, 255, 200, 0.2);
        }
    </style>
</head>
<body>

    <!-- WebSocket Status Indicator -->
    <div id="ws-status">🔌 Connecting...</div>

    <!-- DRAGGABLE CHAT WIDGET -->
    <div id="chat-container">
        <!-- Drag Handle -->
        <div id="chat-header">
            <h3>
                <span></span> CRISIS CHAT
            </h3>
            <div class="status-badge">● Live</div>
        </div>

        <!-- Messages -->
        <div id="chat-messages">
            <div class="chat-msg other">
                <span class="username">🚀 System</span>
                Welcome to Crisis Chat. Reports appear here live.
            </div>
        </div>

        <!-- Input -->
        <div id="chat-input-area">
            <input type="text" id="chat-input" placeholder="Type a message..." />
            <button id="chat-send">Send</button>
        </div>
    </div>

    <script>
        // ============================================
        // 1. DRAGGABLE LOGIC
        // ============================================
        const chatContainer = document.getElementById('chat-container');
        const header = document.getElementById('chat-header');
        
        let isDragging = false;
        let offsetX = 0;
        let offsetY = 0;

        // Ensure it starts at bottom-right (default CSS), but we store position if dragged.
        // We'll set initial position via CSS, and update left/top on drag.
        // To make it consistent, we convert from bottom/right to top/left on first drag.
        let posX = window.innerWidth - 410; // 380 width + 30 margin
        let posY = window.innerHeight - 560; // 520 height + 40 margin

        // Set initial position using top/left to avoid bottom/right conflicts
        chatContainer.style.left = posX + 'px';
        chatContainer.style.top = posY + 'px';
        chatContainer.style.bottom = 'auto';
        chatContainer.style.right = 'auto';

        header.addEventListener('mousedown', (e) => {
            isDragging = true;
            const rect = chatContainer.getBoundingClientRect();
            offsetX = e.clientX - rect.left;
            offsetY = e.clientY - rect.top;
            chatContainer.style.cursor = 'grabbing';
            header.style.cursor = 'grabbing';
            e.preventDefault();
        });

        document.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            
            let newX = e.clientX - offsetX;
            let newY = e.clientY - offsetY;
            
            // Boundary clamping (keep it inside viewport)
            const maxX = window.innerWidth - chatContainer.offsetWidth;
            const maxY = window.innerHeight - chatContainer.offsetHeight;
            newX = Math.max(0, Math.min(newX, maxX));
            newY = Math.max(0, Math.min(newY, maxY));
            
            chatContainer.style.left = newX + 'px';
            chatContainer.style.top = newY + 'px';
        });

        document.addEventListener('mouseup', () => {
            if (isDragging) {
                isDragging = false;
                chatContainer.style.cursor = 'grab';
                header.style.cursor = 'grab';
            }
        });

        // ============================================
        // 2. WEBSOCKET CONNECTION
        // ============================================
        const wsStatus = document.getElementById('ws-status');
        const messagesDiv = document.getElementById('chat-messages');
        const inputField = document.getElementById('chat-input');
        const sendBtn = document.getElementById('chat-send');

        // 👇 CHANGE THIS URL to your FastAPI WebSocket endpoint
        const WS_URL = 'ws://localhost:8000/ws';  // or wss://yourdomain.com/ws

        let ws;

        function connectWebSocket() {
            ws = new WebSocket(WS_URL);

            ws.onopen = () => {
                wsStatus.textContent = '✅ Connected';
                wsStatus.className = 'connected';
                addMessage('System', 'Connected to command center.', true);
            };

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    
                    // Handle different message types
                    if (data.type === 'chat' && data.data) {
                        const msg = data.data;
                        addMessage(msg.username || 'Anonymous', msg.message || '...', false, msg.timestamp);
                    } else if (data.type === 'presence') {
                        // Optional: show user count update silently
                        // console.log('Online:', data.count);
                    } else if (data.type === 'new_report') {
                        addMessage('📡 Alert', 'New report submitted! Check the map.', false);
                    }
                } catch (e) {
                    // If it's plain text fallback
                    addMessage('Peer', event.data, false);
                }
            };

            ws.onclose = () => {
                wsStatus.textContent = '❌ Disconnected';
                wsStatus.className = '';
                addMessage('System', 'Disconnected. Reconnecting in 3s...', true);
                setTimeout(connectWebSocket, 3000);
            };

            ws.onerror = (err) => {
                console.error('WebSocket error:', err);
                wsStatus.textContent = '⚠️ Error';
            };
        }

        // Helper to add message to UI
        function addMessage(username, text, isOwn = false, timestamp = null) {
            const div = document.createElement('div');
            div.className = `chat-msg ${isOwn ? 'own' : 'other'}`;
            
            const timeStr = timestamp ? new Date(timestamp).toLocaleTimeString() : new Date().toLocaleTimeString();
            
            div.innerHTML = `
                <span class="username">${username} <span class="time">${timeStr}</span></span>
                ${text}
            `;
            messagesDiv.appendChild(div);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
            
            // Keep last 150 messages to avoid memory bloat
            while (messagesDiv.children.length > 150) {
                messagesDiv.removeChild(messagesDiv.firstChild);
            }
        }

        // Send message
        function sendMessage() {
            const text = inputField.value.trim();
            if (!text || !ws || ws.readyState !== WebSocket.OPEN) {
                if (ws && ws.readyState !== WebSocket.OPEN) {
                    addMessage('System', 'Not connected. Please wait.', true);
                }
                return;
            }
            
            // Send to server (server will broadcast)
            ws.send(JSON.stringify({ type: 'chat', message: text }));
            
            // Optimistically add to UI (will also come back from server, but this feels instant)
            addMessage('You', text, true);
            inputField.value = '';
        }

        // Event listeners
        sendBtn.addEventListener('click', sendMessage);
        inputField.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') sendMessage();
        });

        // Go!
        connectWebSocket();

        // Handle resize to keep chat inside bounds
        window.addEventListener('resize', () => {
            const rect = chatContainer.getBoundingClientRect();
            const maxX = window.innerWidth - rect.width;
            const maxY = window.innerHeight - rect.height;
            if (rect.left > maxX) chatContainer.style.left = maxX + 'px';
            if (rect.top > maxY) chatContainer.style.top = maxY + 'px';
        });

        console.log('🚀 ImpactMapper Chat loaded - Draggable + Glowing!');
    </script>
</body>
</html>
