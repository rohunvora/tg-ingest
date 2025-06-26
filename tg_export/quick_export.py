import asyncio
from flask import Flask, render_template, request, jsonify, send_file
from pathlib import Path
import os
from datetime import datetime, timedelta
import json
import tempfile
from typing import Optional
import threading
import time

from telethon import TelegramClient
from telethon.errors import FloodWaitError
from telethon.sessions import StringSession
from telethon.utils import get_peer_id
from dotenv import load_dotenv

from .cli import parse_chat_url, serialize_entities
from .clean_export import convert_to_clean_format

load_dotenv()

app = Flask(__name__)

# Global variables for export status
export_status = {
    'running': False,
    'progress': 0,
    'message': '',
    'error': None,
    'file_path': None
}

# Cache for recent exports
recent_exports = []

async def quick_export(chat_url: str, hours: int, clean: bool = True):
    """Export messages from the last N hours"""
    global export_status
    
    api_id = int(os.getenv("TELEGRAM_API_ID"))
    api_hash = os.getenv("TELEGRAM_API_HASH")
    session_file = Path(".session")
    
    if not session_file.exists():
        export_status['error'] = "Not logged in. Run 'tg_export login' first"
        return None
    
    session = session_file.read_text()
    client = TelegramClient(StringSession(session), api_id, api_hash)
    
    try:
        await client.start()
        
        # Parse chat
        chat_identifier = parse_chat_url(chat_url)
        chat = await client.get_entity(chat_identifier)
        
        # Set time limit
        since = datetime.now() - timedelta(hours=hours)
        
        # Create temp file
        temp_dir = Path("exports/quick")
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = temp_dir / f"quick_export_{hours}h_{timestamp}.jsonl"
        
        # Export messages
        export_status['message'] = f"Exporting last {hours} hours..."
        messages = []
        count = 0
        
        async for message in client.iter_messages(chat):
            if message.date.replace(tzinfo=None) < since:
                break
            
            # Skip empty messages
            if not message.text:
                continue
            
            # Build message data
            media_type = None
            if message.photo:
                media_type = "photo"
            elif message.video:
                media_type = "video"
            elif message.document:
                media_type = "doc"
            
            data = {
                "msg_id": message.id,
                "chat_id": get_peer_id(message.peer_id),
                "date": message.date.isoformat() + "Z",
                "sender_id": message.sender_id,
                "sender_username": getattr(message.sender, 'username', None) if message.sender else None,
                "reply_to": message.reply_to.reply_to_msg_id if message.reply_to else None,
                "text": message.text or "",
                "entities": serialize_entities(message.entities),
                "media_type": media_type,
                "media_file_id": None
            }
            
            messages.append(data)
            count += 1
            export_status['progress'] = count
            
            # Small delay every 50 messages
            if count % 50 == 0:
                await asyncio.sleep(0.5)
        
        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            for msg in messages:
                f.write(json.dumps(msg, ensure_ascii=False) + '\n')
        
        # Clean if requested
        if clean:
            clean_file = output_file.with_suffix('.txt')
            stats = convert_to_clean_format(output_file, clean_file, filter_bots=True)
            export_status['message'] = f"Exported {stats['kept']} messages (filtered {stats['filtered_bots']} bots)"
            return clean_file
        else:
            export_status['message'] = f"Exported {count} messages"
            return output_file
            
    except FloodWaitError as e:
        export_status['error'] = f"Rate limited. Try again in {e.seconds} seconds"
        return None
    except Exception as e:
        export_status['error'] = str(e)
        return None
    finally:
        await client.disconnect()


def run_export_async(chat_url: str, hours: int, clean: bool):
    """Run export in background thread"""
    global export_status
    
    export_status = {
        'running': True,
        'progress': 0,
        'message': 'Starting export...',
        'error': None,
        'file_path': None
    }
    
    # Run export
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        file_path = loop.run_until_complete(quick_export(chat_url, hours, clean))
        if file_path:
            export_status['file_path'] = str(file_path)
            export_status['running'] = False
            
            # Add to recent exports
            recent_exports.insert(0, {
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M"),
                'hours': hours,
                'file': str(file_path),
                'size': file_path.stat().st_size
            })
            # Keep only last 10
            if len(recent_exports) > 10:
                recent_exports.pop()
    finally:
        export_status['running'] = False
        loop.close()


@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')


@app.route('/export', methods=['POST'])
def start_export():
    """Start export process"""
    global export_status
    
    if export_status.get('running'):
        return jsonify({'error': 'Export already running'}), 400
    
    data = request.json
    chat_url = data.get('chat_url')
    hours = int(data.get('hours', 1))
    clean = data.get('clean', True)
    
    if not chat_url:
        return jsonify({'error': 'Chat URL required'}), 400
    
    # Start export in background
    thread = threading.Thread(
        target=run_export_async,
        args=(chat_url, hours, clean)
    )
    thread.start()
    
    return jsonify({'status': 'started'})


@app.route('/status')
def get_status():
    """Get export status"""
    return jsonify(export_status)


@app.route('/download/<path:filename>')
def download_file(filename):
    """Download exported file"""
    file_path = Path("exports/quick") / filename
    if file_path.exists():
        return send_file(file_path, as_attachment=True)
    return "File not found", 404


@app.route('/recent')
def get_recent():
    """Get recent exports"""
    return jsonify(recent_exports)


def create_app():
    """Create Flask app with templates"""
    # Create templates directory
    templates_dir = Path(__file__).parent / "templates"
    templates_dir.mkdir(exist_ok=True)
    
    # Create index.html
    index_html = templates_dir / "index.html"
    index_html.write_text('''<!DOCTYPE html>
<html>
<head>
    <title>Telegram Quick Export</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .container {
            background: white;
            border-radius: 10px;
            padding: 30px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            margin-bottom: 30px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            color: #666;
            font-weight: 500;
        }
        input, select {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 16px;
            box-sizing: border-box;
        }
        button {
            background: #007bff;
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 5px;
            font-size: 16px;
            cursor: pointer;
            width: 100%;
            margin-top: 10px;
        }
        button:hover {
            background: #0056b3;
        }
        button:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        .status {
            margin-top: 20px;
            padding: 15px;
            border-radius: 5px;
            display: none;
        }
        .status.info {
            background: #e3f2fd;
            color: #1976d2;
        }
        .status.success {
            background: #e8f5e9;
            color: #388e3c;
        }
        .status.error {
            background: #ffebee;
            color: #c62828;
        }
        .presets {
            display: flex;
            gap: 10px;
            margin-top: 10px;
        }
        .preset {
            flex: 1;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 5px;
            text-align: center;
            cursor: pointer;
            background: #f8f9fa;
        }
        .preset:hover {
            background: #e9ecef;
        }
        .preset.active {
            background: #007bff;
            color: white;
            border-color: #007bff;
        }
        .recent-exports {
            margin-top: 30px;
            border-top: 1px solid #eee;
            padding-top: 20px;
        }
        .recent-item {
            padding: 10px;
            border: 1px solid #eee;
            border-radius: 5px;
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .download-link {
            color: #007bff;
            text-decoration: none;
            font-weight: 500;
        }
        .checkbox-group {
            display: flex;
            align-items: center;
            margin-top: 15px;
        }
        .checkbox-group input {
            width: auto;
            margin-right: 10px;
        }
        .instructions {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
            font-size: 14px;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Telegram Quick Export</h1>
        
        <div class="instructions">
            <strong>Tip:</strong> Get chat URL by copying any message link from the group
        </div>
        
        <div class="form-group">
            <label>Chat URL</label>
            <input type="text" id="chatUrl" placeholder="https://t.me/c/123456789/12345">
        </div>
        
        <div class="form-group">
            <label>Time Range</label>
            <div class="presets">
                <div class="preset" data-hours="1">1 hour</div>
                <div class="preset" data-hours="6">6 hours</div>
                <div class="preset" data-hours="24">24 hours</div>
                <div class="preset" data-hours="48">2 days</div>
            </div>
            <input type="number" id="customHours" placeholder="Or enter custom hours" style="margin-top: 10px;">
        </div>
        
        <div class="checkbox-group">
            <input type="checkbox" id="cleanExport" checked>
            <label for="cleanExport">Clean export (remove bots & format for LLM)</label>
        </div>
        
        <button id="exportBtn" onclick="startExport()">Export Messages</button>
        
        <div id="status" class="status"></div>
        
        <div class="recent-exports" id="recentExports" style="display: none;">
            <h3>Recent Exports</h3>
            <div id="recentList"></div>
        </div>
    </div>
    
    <script>
        let selectedHours = null;
        
        // Preset buttons
        document.querySelectorAll('.preset').forEach(btn => {
            btn.addEventListener('click', function() {
                document.querySelectorAll('.preset').forEach(b => b.classList.remove('active'));
                this.classList.add('active');
                selectedHours = parseInt(this.dataset.hours);
                document.getElementById('customHours').value = '';
            });
        });
        
        // Custom hours input
        document.getElementById('customHours').addEventListener('input', function() {
            document.querySelectorAll('.preset').forEach(b => b.classList.remove('active'));
            selectedHours = parseInt(this.value) || null;
        });
        
        // Load recent exports
        loadRecent();
        
        function startExport() {
            const chatUrl = document.getElementById('chatUrl').value;
            const customHours = document.getElementById('customHours').value;
            const hours = customHours || selectedHours || 1;
            const clean = document.getElementById('cleanExport').checked;
            
            if (!chatUrl) {
                showStatus('Please enter a chat URL', 'error');
                return;
            }
            
            const exportBtn = document.getElementById('exportBtn');
            exportBtn.disabled = true;
            showStatus('Starting export...', 'info');
            
            fetch('/export', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({chat_url: chatUrl, hours: hours, clean: clean})
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    showStatus(data.error, 'error');
                    exportBtn.disabled = false;
                } else {
                    checkStatus();
                }
            })
            .catch(error => {
                showStatus('Error: ' + error, 'error');
                exportBtn.disabled = false;
            });
        }
        
        function checkStatus() {
            fetch('/status')
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    showStatus('Error: ' + data.error, 'error');
                    document.getElementById('exportBtn').disabled = false;
                } else if (data.running) {
                    showStatus(data.message + ' (' + data.progress + ' messages)', 'info');
                    setTimeout(checkStatus, 1000);
                } else if (data.file_path) {
                    const filename = data.file_path.split('/').pop();
                    showStatus(
                        data.message + '<br><br>' +
                        '<a href="/download/' + filename + '" class="download-link">📥 Download Export</a>',
                        'success'
                    );
                    document.getElementById('exportBtn').disabled = false;
                    loadRecent();
                }
            });
        }
        
        function showStatus(message, type) {
            const status = document.getElementById('status');
            status.className = 'status ' + type;
            status.innerHTML = message;
            status.style.display = 'block';
        }
        
        function loadRecent() {
            fetch('/recent')
            .then(response => response.json())
            .then(data => {
                if (data.length > 0) {
                    document.getElementById('recentExports').style.display = 'block';
                    const list = document.getElementById('recentList');
                    list.innerHTML = data.map(item => `
                        <div class="recent-item">
                            <div>
                                <strong>${item.hours}h export</strong><br>
                                <small>${item.timestamp} • ${(item.size / 1024).toFixed(1)} KB</small>
                            </div>
                            <a href="/download/${item.file.split('/').pop()}" class="download-link">Download</a>
                        </div>
                    `).join('');
                }
            });
        }
    </script>
</body>
</html>''')
    
    return app


if __name__ == '__main__':
    app = create_app()
    print("\n🚀 Starting Quick Export server...")
    print("📱 Open your browser to: http://127.0.0.1:5000\n")
    print("Press Ctrl+C to stop the server\n")
    app.run(host='127.0.0.1', port=5000, debug=False)