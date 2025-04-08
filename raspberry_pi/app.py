#!/usr/bin/env python3
"""
Main application for Raspberry Pi Prayer Alarm System.
This module initializes all components and starts the Flask server.
"""

import os
import logging
import time
from flask import Flask, request, jsonify, render_template, redirect, url_for
import threading

from database import init_db, get_db
from models import Alarm, PrayerTime
from prayer_scheduler import PrayerScheduler
from alarm_scheduler import AlarmScheduler
from audio_player import AudioPlayer
from websocket_server import setup_websocket, broadcast_message
from config import Config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Initialize components
audio_player = AudioPlayer()
alarm_scheduler = AlarmScheduler(audio_player)
prayer_scheduler = PrayerScheduler(audio_player)

# Setup WebSocket server
setup_websocket(app, audio_player)

@app.route('/', methods=['GET'])
def home():
    """Home page showing system status."""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Prayer Alarm System</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                line-height: 1.6;
            }
            h1 {
                color: #2c3e50;
                border-bottom: 1px solid #eee;
                padding-bottom: 10px;
            }
            .status {
                background-color: #e8f5e9;
                border-left: 5px solid #4caf50;
                padding: 10px 15px;
                margin: 20px 0;
            }
            .section {
                margin: 30px 0;
            }
            h2 {
                color: #34495e;
            }
            ul {
                padding-left: 20px;
            }
            .api-path {
                background-color: #f5f5f5;
                padding: 5px;
                border-radius: 3px;
                font-family: monospace;
            }
        </style>
    </head>
    <body>
        <h1>Prayer Alarm System</h1>
        
        <div class="status">
            <strong>Status:</strong> Server is running
        </div>
        
        <div class="section">
            <h2>System Overview</h2>
            <p>This system provides API endpoints for managing prayer times and alarms, as well as a WebSocket interface for push-to-talk functionality.</p>
        </div>
        
        <div class="section">
            <h2>Available API Endpoints</h2>
            <ul>
                <li><span class="api-path">/status</span> - Get server status</li>
                <li><span class="api-path">/alarms</span> - Get all alarms</li>
                <li><span class="api-path">/prayer-times</span> - Get prayer times</li>
                <li><span class="api-path">/prayer-times/refresh</span> - Force refresh of prayer times</li>
                <li><span class="api-path">/stop-audio</span> - Stop any playing audio</li>
                <li><span class="api-path">/murattal/files</span> - Get available Murattal files</li>
                <li><span class="api-path">/murattal/play</span> - Play a Murattal file</li>
                <li><span class="api-path">/murattal/upload</span> - Upload a new Murattal file</li>
            </ul>
        </div>
        
        <div class="section">
            <h2>WebSocket</h2>
            <p>WebSocket endpoint for push-to-talk: <span class="api-path">/ws</span></p>
        </div>
        
        <div class="section">
            <h2>Web Interface</h2>
            <p>A web-based control interface is available at: <a href="/web" style="color: #4CAF50; text-decoration: none;"><span class="api-path">/web</span></a></p>
        </div>
    </body>
    </html>
    '''

@app.route('/status', methods=['GET'])
def get_status():
    """Check if the server is running."""
    return jsonify({
        "status": "ok",
        "service": "Prayer Alarm System",
        "version": "1.0.0"
    })

@app.route('/alarms', methods=['GET'])
def get_alarms():
    """Get all alarms."""
    db = get_db()
    alarms = db.get_all_alarms()
    return jsonify([alarm.to_dict() for alarm in alarms])

@app.route('/alarms', methods=['POST'])
def add_or_update_alarm():
    """Add or update an alarm."""
    data = request.json
    db = get_db()
    
    # Check if alarm with this ID already exists (update case)
    alarm_id = data.get('id')
    
    # Process sound file if provided
    sound_file_name = data.get('sound_file_name')
    sound_file_content = data.get('sound_file_content')
    
    if sound_file_name and sound_file_content:
        # Create sounds directory if it doesn't exist
        os.makedirs('sounds', exist_ok=True)
        
        # Save the file
        file_path = os.path.join('sounds', sound_file_name)
        import base64
        with open(file_path, 'wb') as f:
            f.write(base64.b64decode(sound_file_content))
        data['sound_path'] = file_path
    
    # Create alarm object
    alarm = Alarm.from_dict(data)
    
    # Save to database
    if alarm_id:
        db.update_alarm(alarm)
        message = "Alarm updated"
    else:
        db.add_alarm(alarm)
        message = "Alarm added"
    
    # Schedule the alarm
    alarm_scheduler.schedule_alarm(alarm)
    
    return jsonify({"status": "success", "message": message})

@app.route('/alarms/<int:alarm_id>', methods=['DELETE'])
def delete_alarm(alarm_id):
    """Delete an alarm."""
    db = get_db()
    db.delete_alarm(alarm_id)
    alarm_scheduler.remove_alarm(alarm_id)
    return jsonify({"status": "success", "message": "Alarm deleted"})

@app.route('/alarms/<int:alarm_id>/disable', methods=['POST'])
def disable_alarm(alarm_id):
    """Disable an alarm."""
    db = get_db()
    alarm = db.get_alarm(alarm_id)
    if alarm:
        alarm.enabled = False
        db.update_alarm(alarm)
        alarm_scheduler.remove_alarm(alarm_id)
        return jsonify({"status": "success", "message": "Alarm disabled"})
    return jsonify({"status": "error", "message": "Alarm not found"}), 404

@app.route('/prayer-times', methods=['GET'])
def get_prayer_times():
    """Get prayer times for a specific date."""
    date_str = request.args.get('date')
    db = get_db()
    
    if date_str:
        prayer_times = db.get_prayer_times_by_date(date_str)
    else:
        prayer_times = db.get_todays_prayer_times()
    
    return jsonify([pt.to_dict() for pt in prayer_times])

@app.route('/prayer-times/refresh', methods=['POST'])
def refresh_prayer_times():
    """Force refresh of prayer times from API."""
    prayer_scheduler.refresh_prayer_times()
    return jsonify({"status": "success", "message": "Prayer times refreshed"})

@app.route('/stop-audio', methods=['POST'])
def stop_audio():
    """Stop any playing audio."""
    audio_player.stop()
    return jsonify({"status": "success", "message": "Audio stopped"})

@app.route('/murattal/files', methods=['GET'])
def get_murattal_files():
    """Get a list of available Murattal files."""
    files = audio_player.get_murattal_files()
    return jsonify({"status": "success", "files": files})

@app.route('/murattal/play', methods=['POST'])
def play_murattal():
    """Play a Murattal file."""
    data = request.json
    file_path = data.get('file_path')
    
    if not file_path or not os.path.exists(file_path):
        return jsonify({"status": "error", "message": "File not found"}), 404
    
    audio_player.play_murattal(file_path)
    return jsonify({"status": "success", "message": "Murattal playing"})

@app.route('/murattal/upload', methods=['POST'])
def upload_murattal():
    """Upload a new Murattal file."""
    data = request.json
    file_name = data.get('file_name')
    file_content = data.get('file_content')  # Base64 encoded
    
    if not file_name or not file_content:
        return jsonify({"status": "error", "message": "Missing file_name or file_content"}), 400
    
    try:
        import base64
        file_path = audio_player.add_murattal_file(file_name, base64.b64decode(file_content))
        return jsonify({"status": "success", "message": "Murattal file uploaded", "file_path": file_path})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Web interface routes
@app.route('/web', methods=['GET'])
def web_home():
    """Web interface home page."""
    return render_template('index.html')

@app.route('/web/prayer-times', methods=['GET'])
def web_prayer_times():
    """Web interface prayer times page."""
    return render_template('prayer_times.html')

@app.route('/web/alarms', methods=['GET'])
def web_alarms():
    """Web interface alarms page."""
    return render_template('alarms.html')

@app.route('/web/alarms/add', methods=['GET'])
def web_add_alarm():
    """Web interface add alarm page."""
    return render_template('add_alarm.html')

@app.route('/web/push-to-talk', methods=['GET'])
def web_push_to_talk():
    """Web interface push-to-talk page."""
    return render_template('push_to_talk.html')

@app.route('/web/murattal', methods=['GET'])
def web_murattal():
    """Web interface Murattal player page."""
    return render_template('murattal.html')

def start_schedulers():
    """Start the prayer and alarm schedulers."""
    logger.info("Starting schedulers...")
    
    # Initialize database first
    init_db()
    
    # Start prayer scheduler
    prayer_scheduler.start()
    
    # Start alarm scheduler
    alarm_scheduler.start()
    
    logger.info("Schedulers started successfully")

if __name__ == '__main__':
    # Start schedulers in a separate thread
    threading.Thread(target=start_schedulers, daemon=True).start()
    
    # Give schedulers time to initialize
    time.sleep(2)
    
    # Debug info about host and port
    logger.info("Starting Flask app on host='0.0.0.0', port=5000")
    
    # Start Flask app
    app.run(host='0.0.0.0', port=5000, threaded=True, debug=False)
