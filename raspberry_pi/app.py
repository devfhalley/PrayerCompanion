#!/usr/bin/env python3
"""
Main application for Raspberry Pi Prayer Alarm System.
This module initializes all components and starts the Flask server.
"""

import os
import logging
import time
import json
from datetime import datetime
from flask import Flask, request, jsonify, render_template, redirect, url_for
from werkzeug.utils import secure_filename
import threading

from database import init_db, get_db
from models import Alarm, PrayerTime
from prayer_scheduler import PrayerScheduler
from alarm_scheduler import AlarmScheduler
from audio_player import AudioPlayer
from config import Config
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
    """Check if the server is running and get audio status."""
    is_playing = audio_player.is_playing()
    current_priority = audio_player.get_current_priority()
    
    # Map priority to a human-readable name
    audio_type = "None"
    if is_playing:
        if current_priority == audio_player.PRIORITY_ADHAN:
            audio_type = "Adhan"
        elif current_priority == audio_player.PRIORITY_ALARM:
            audio_type = "Alarm"
        elif current_priority == audio_player.PRIORITY_MURATTAL:
            audio_type = "Murattal"
    
    return jsonify({
        "status": "ok",
        "service": "Prayer Alarm System",
        "version": "1.0.0",
        "audio_playing": is_playing,
        "audio_type": audio_type
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
    try:
        db = get_db()
        # First check if alarm exists to avoid errors
        alarm = db.get_alarm(alarm_id)
        
        if not alarm:
            return jsonify({"status": "error", "message": f"Alarm with ID {alarm_id} not found"}), 404
            
        # Remove from database first
        db.delete_alarm(alarm_id)
        
        # Then remove from scheduler
        alarm_scheduler.remove_alarm(alarm_id)
        
        # Log the deletion for debugging
        app.logger.info(f"Alarm {alarm_id} deleted successfully")
        
        return jsonify({"status": "success", "message": "Alarm deleted"})
    except Exception as e:
        app.logger.error(f"Error deleting alarm {alarm_id}: {str(e)}")
        return jsonify({"status": "error", "message": f"Failed to delete alarm: {str(e)}"}), 500

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

@app.route('/adhan/test', methods=['POST'])
def test_adhan():
    """Test play the adhan sound."""
    data = request.json
    prayer_name = data.get('prayer_name', 'Test')
    
    # Send WebSocket notification
    notification = {
        "type": "adhan_playing",
        "prayer": prayer_name if prayer_name else "Test",
        "time": datetime.now().strftime("%H:%M")
    }
    broadcast_message(notification)
    logger.info(f"Broadcasting adhan playing notification: {notification}")
    
    # Check if there's a custom sound for this prayer
    if prayer_name:
        db = get_db()
        prayer_times = db.get_todays_prayer_times()
        for prayer in prayer_times:
            if prayer.name == prayer_name and prayer.custom_sound:
                audio_player.play_adhan(prayer.custom_sound)
                return jsonify({"status": "success", "message": f"Playing custom adhan for {prayer_name}"})
    
    # Use default adhan sound
    audio_player.play_adhan(Config.DEFAULT_ADHAN_SOUND)
    return jsonify({"status": "success", "message": "Playing default adhan"})

@app.route('/adhan/sounds', methods=['GET'])
def get_adhan_sounds():
    """Get a list of available adhan sounds."""
    sounds_dir = os.path.join(os.path.dirname(__file__), "sounds")
    adhan_files = []
    
    # Check if the directory exists
    if os.path.exists(sounds_dir):
        # List all mp3 files
        for file in os.listdir(sounds_dir):
            if file.endswith(".mp3"):
                file_path = os.path.join(sounds_dir, file)
                adhan_files.append({
                    "name": file,
                    "path": file_path,
                    "is_default": file_path == Config.DEFAULT_ADHAN_SOUND
                })
    
    return jsonify({"status": "success", "sounds": adhan_files})

@app.route('/adhan/upload', methods=['POST'])
def upload_adhan():
    """Upload a new adhan sound file."""
    data = request.json
    file_name = data.get('file_name')
    file_content = data.get('file_content')  # Base64 encoded
    
    if not file_name or not file_content:
        return jsonify({"status": "error", "message": "Missing file_name or file_content"}), 400
    
    try:
        # Create sounds directory if it doesn't exist
        sounds_dir = os.path.join(os.path.dirname(__file__), "sounds")
        os.makedirs(sounds_dir, exist_ok=True)
        
        # Save the file
        import base64
        file_path = os.path.join(sounds_dir, file_name)
        with open(file_path, 'wb') as f:
            f.write(base64.b64decode(file_content))
        
        return jsonify({
            "status": "success", 
            "message": "Adhan sound uploaded", 
            "file_path": file_path
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/adhan/set-default', methods=['POST'])
def set_default_adhan():
    """Set the default adhan sound."""
    data = request.json
    file_path = data.get('file_path')
    
    if not file_path or not os.path.exists(file_path):
        return jsonify({"status": "error", "message": "Invalid file path"}), 400
    
    try:
        # Set as default in config
        Config.DEFAULT_ADHAN_SOUND = file_path
        
        return jsonify({
            "status": "success", 
            "message": "Default adhan sound set"
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/adhan/set-for-prayer', methods=['POST'])
def set_adhan_for_prayer():
    """Set a custom adhan sound for a specific prayer."""
    data = request.json
    prayer_name = data.get('prayer_name')
    file_path = data.get('file_path')
    date_str = data.get('date')  # Optional, defaults to today
    
    if not prayer_name or not file_path or not os.path.exists(file_path):
        return jsonify({"status": "error", "message": "Invalid prayer name or file path"}), 400
    
    try:
        db = get_db()
        
        # Get the prayer time for today or specified date
        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")
        
        prayer_times = db.get_prayer_times_by_date(date_str)
        updated = False
        
        for prayer in prayer_times:
            if prayer.name == prayer_name:
                prayer.custom_sound = file_path
                db.update_prayer_time(prayer)
                updated = True
                break
        
        if not updated:
            return jsonify({"status": "error", "message": f"Prayer {prayer_name} not found for date {date_str}"}), 404
        
        return jsonify({
            "status": "success", 
            "message": f"Custom adhan set for {prayer_name}"
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

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

@app.route('/web/settings', methods=['GET'])
def web_settings():
    """Web interface settings page."""
    # Get available adhan sounds
    adhan_dir = os.path.join(os.path.dirname(__file__), "sounds")
    adhan_sounds = []
    for file in os.listdir(adhan_dir):
        if file.endswith(".mp3"):
            adhan_sounds.append({
                "name": file,
                "path": os.path.join(adhan_dir, file)
            })
    
    # Get prayer times for today to display custom adhan settings
    db = get_db()
    prayer_times = db.get_todays_prayer_times()
    
    # Get configuration values
    return render_template('settings.html', 
                          adhan_sounds=adhan_sounds, 
                          prayers=prayer_times, 
                          default_adhan=Config.DEFAULT_ADHAN_SOUND,
                          prayer_city=Config.PRAYER_CITY,
                          prayer_country=Config.PRAYER_COUNTRY,
                          calculation_method=Config.PRAYER_CALCULATION_METHOD,
                          volume=90)  # Default volume, replace with actual stored value if implemented

# Settings-specific endpoints implemented below

@app.route('/settings/location', methods=['POST'])
def update_location_settings():
    """Update location settings."""
    data = request.json
    city = data.get('city')
    country = data.get('country')
    calculation_method = data.get('calculation_method')
    
    if not city or not country:
        return jsonify({"status": "error", "message": "Missing city or country"}), 400
    
    # Update Config values
    Config.PRAYER_CITY = city
    Config.PRAYER_COUNTRY = country
    
    if calculation_method is not None:
        Config.PRAYER_CALCULATION_METHOD = calculation_method
    
    return jsonify({"status": "success", "message": "Location settings updated"})

@app.route('/settings/preferences', methods=['POST'])
def update_preferences():
    """Update system preferences."""
    data = request.json
    volume = data.get('volume')
    
    # In a real implementation, you would save these settings and apply them
    # For now, we just acknowledge the change
    
    return jsonify({"status": "success", "message": "Preferences updated"})

@app.route('/volume', methods=['POST'])
def update_volume():
    """Update system volume."""
    data = request.json
    volume = data.get('volume')
    
    if volume is None or not isinstance(volume, int) or volume < 0 or volume > 100:
        return jsonify({"status": "error", "message": "Invalid volume value"}), 400
    
    # In a real Raspberry Pi, you would use system commands to adjust volume
    # Store the volume in Config
    # Use setattr to avoid LSP issues
    setattr(Config, 'VOLUME', volume)
    
    # Broadcast volume change to all connected clients
    broadcast_message({
        "type": "volume_changed",
        "volume": volume
    })
    
    return jsonify({"status": "success", "message": "Volume updated", "volume": volume})

@app.route('/volume', methods=['GET'])
def get_volume():
    """Get current system volume."""
    # Get volume from Config, defaulting to 70 if not set
    volume = getattr(Config, 'VOLUME', 70)
    
    return jsonify({"status": "success", "volume": volume})

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
