#!/usr/bin/env python3
"""
Main application for Raspberry Pi Prayer Alarm System.
This module initializes all components and starts the Flask server.
"""

import os
import logging
import time
from flask import Flask, request, jsonify
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
    
    # Start Flask app
    app.run(host='0.0.0.0', port=5000, threaded=True)
