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
from models import Alarm, PrayerTime, YouTubeVideo
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

# Watchdog variables for scheduler health monitoring
last_prayer_check_time = time.time()
prayer_scheduler_healthy = True

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
    # Use direct database connection for consistent label handling
    try:
        # Use the database_direct approach with custom SQL query
        import os
        import psycopg2
        import psycopg2.extras
        from models import Alarm
        
        logger.info("Getting all alarms with direct DB query")
        conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Query alarms ordered by time
        cursor.execute('SELECT * FROM alarms ORDER BY time')
        rows = cursor.fetchall()
        
        # Convert to Alarm objects
        alarms = []
        for row in rows:
            alarm = Alarm()
            
            # Map fields
            alarm.id = row['id']
            alarm.time = row['time']
            alarm.enabled = row['enabled']
            alarm.repeating = row['repeating']
            
            # Days
            days_str = row['days'] or '0000000'
            alarm.days = [c == '1' for c in days_str]
            
            # Other fields
            alarm.is_tts = row['is_tts']
            alarm.message = row['message']
            alarm.sound_path = row['sound_path']
            
            # Handle label field
            label_value = row.get('label')
            if label_value:
                alarm.label = str(label_value)
            else:
                alarm.label = None
                
            alarms.append(alarm)
            
        cursor.close()
        conn.close()
        
        # Convert to dict and return
        return jsonify([alarm.to_dict() for alarm in alarms])
        
    except Exception as e:
        logger.error(f"Error getting alarms with direct DB query: {e}")
        
        # Fall back to ORM method
        db = get_db()
        alarms = db.get_all_alarms()
        return jsonify([alarm.to_dict() for alarm in alarms])

@app.route('/alarms', methods=['POST'])
def add_or_update_alarm():
    """Add or update an alarm."""
    # Define a background thread function for processing the alarm
    def process_alarm_creation(data, alarm_id):
        try:
            db = get_db()
            alarm = None
            
            # Process sound file if provided
            sound_file_name = data.get('sound_file_name')
            sound_file_content = data.get('sound_file_content')
            
            if sound_file_name and sound_file_content:
                # Create sounds directory if it doesn't exist
                sounds_dir = os.path.join(os.path.dirname(__file__), "sounds")
                os.makedirs(sounds_dir, exist_ok=True)
                
                # Save the file
                import base64
                file_path = os.path.join(sounds_dir, sound_file_name)
                with open(file_path, 'wb') as f:
                    f.write(base64.b64decode(sound_file_content))
                data['sound_path'] = file_path
            
            # Start of fix for duplicate alarm entries
            
            # Normalize form data
            # Handle the case where we get 'time' like "13:04" instead of separate hour and minute
            if 'time' in data and ':' in str(data['time']):
                try:
                    time_parts = data['time'].split(':')
                    data['hour'] = int(time_parts[0])
                    data['minute'] = int(time_parts[1])
                    logger.info(f"Converted time string '{data['time']}' to hour={data['hour']}, minute={data['minute']}")
                except Exception as e:
                    logger.error(f"Error converting time string: {str(e)}")
            
            # Convert string "true"/"false" to boolean for is_tts
            if 'is_tts' in data and isinstance(data['is_tts'], str):
                data['is_tts'] = data['is_tts'].lower() == 'true'
                logger.info(f"Converted is_tts string to boolean: {data['is_tts']}")
            
            # If we have any existing alarms with the same time (hour and minute), check if this might be a duplicate
            if not alarm_id:  # Only check for duplicates when adding, not updating
                hour = data.get('hour')
                minute = data.get('minute')
                
                if hour is not None and minute is not None:
                    # First see if we've already got an alarm at this time
                    all_alarms = db.get_all_alarms()
                    potential_duplicates = []
                    
                    for existing_alarm in all_alarms:
                        # Convert timestamp to hour and minute
                        existing_time = datetime.fromtimestamp(existing_alarm.time / 1000)
                        if existing_time.hour == hour and existing_time.minute == minute:
                            potential_duplicates.append(existing_alarm)
                    
                    if potential_duplicates:
                        logger.warning(f"Found {len(potential_duplicates)} potential duplicate alarms with time {hour}:{minute}")
                        # If we're adding a non-repeating alarm that matches a repeating one, or vice versa, 
                        # this is likely user error - we'll update the first matching alarm instead of adding a new one
                        
                        # Check what we're trying to add
                        is_repeating = data.get('repeating', False)
                        
                        for dup in potential_duplicates:
                            # If we find an alarm with the same repeating status and the same date (for non-repeating alarms), 
                            # update it instead of adding a new one
                            if dup.repeating == is_repeating:
                                # For non-repeating alarms, also check that the date is the same
                                update_existing = True
                                
                                # For non-repeating alarms, ensure the date is the same
                                if not is_repeating and 'date' in data:
                                    # Convert the alarm's timestamp to a date
                                    alarm_date = datetime.fromtimestamp(dup.time / 1000).strftime('%Y-%m-%d')
                                    if alarm_date != data['date']:
                                        # Different date, so don't update
                                        update_existing = False
                                        logger.info(f"Not updating alarm {dup.id} because date is different")
                                        
                                if update_existing:
                                    logger.info(f"Updating existing alarm {dup.id} instead of creating duplicate")
                                    # Set the alarm ID so we update instead of insert
                                    alarm_id = dup.id
                                    break
            
            # Ensure repeating is explicitly set
            if 'repeating' not in data:
                # Default to false if not specified
                data['repeating'] = False
            
            # Handle repeating vs non-repeating alarms properly
            if data.get('repeating', False):
                # For repeating alarms, ensure we have days data
                if 'days' not in data or not any(data['days']):
                    # If no days are selected but alarm is marked as repeating, log a warning and default to today
                    if 'days' not in data:
                        logger.warning("Repeating alarm without days specified, defaulting to no days selected")
                        data['days'] = [False] * 7
                    # Validate at least one day is selected
                    if not any(data['days']):
                        logger.warning("Repeating alarm with no days selected, defaulting to today")
                        # Set today's weekday
                        today_weekday = datetime.now().weekday()
                        # Convert to Sunday-based (0=Sunday) if using Monday-based (0=Monday)
                        sunday_based_weekday = (today_weekday + 1) % 7
                        data['days'] = [False] * 7
                        data['days'][sunday_based_weekday] = True
            else:
                # For non-repeating alarms:
                # 1. Ensure repeating is explicitly false
                data['repeating'] = False
                # 2. Make sure no days are set to avoid confusion
                if 'days' in data:
                    del data['days']
                # 3. Ensure we have a date
                if 'date' not in data:
                    # Default to today if no date specified for one-time alarms
                    data['date'] = datetime.now().strftime('%Y-%m-%d')
                    logger.warning(f"Non-repeating alarm without date, defaulting to today: {data['date']}")
            
            # End of fix for duplicate alarm entries
            
            # Create alarm object
            alarm = Alarm.from_dict(data)
            
            # Debug label value
            logger.info(f"Alarm data from client: {data}")
            logger.info(f"Label value before saving: {alarm.label}")
            
            # Save to database
            if alarm_id:
                # Set the ID on the alarm object
                alarm.id = alarm_id
                db.update_alarm(alarm)
                logger.info(f"Alarm {alarm_id} updated in background thread")
            else:
                new_id = db.add_alarm(alarm)
                alarm.id = new_id
                logger.info(f"Alarm {new_id} added in background thread")
                
                # Special handling for label: If a label was provided but might not have been saved correctly,
                # do a direct update using raw SQL to ensure it's properly saved
                if alarm.label:
                    try:
                        # Use execute_sql directly to set the label
                        import psycopg2
                        conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
                        conn.autocommit = True
                        cursor = conn.cursor()
                        cursor.execute("UPDATE alarms SET label = %s WHERE id = %s", (alarm.label, alarm.id))
                        logger.info(f"Direct SQL update: Set label to '{alarm.label}' for alarm {alarm.id}")
                        conn.close()
                    except Exception as e:
                        logger.error(f"Error in direct label update: {str(e)}")
                
            # Debug: Retrieve and log the saved alarm to check if label is present
            saved_alarm = db.get_alarm(alarm.id)
            logger.info(f"Saved alarm retrieved from database: {saved_alarm.to_dict() if saved_alarm else 'None'}")
            
            # Schedule the alarm
            alarm_scheduler.schedule_alarm(alarm)
            
        except Exception as e:
            logger.error(f"Error in background thread adding/updating alarm: {str(e)}")
    
    try:
        # Get the data and check if it's an update or new alarm
        data = request.json
        alarm_id = data.get('id')
        
        # Start a background thread for processing
        process_thread = threading.Thread(
            target=process_alarm_creation, 
            args=(data, alarm_id)
        )
        process_thread.daemon = True
        process_thread.start()
        
        # Return immediately with a response
        message = "Alarm update started" if alarm_id else "Alarm creation started"
        logger.info(f"{message} in background thread")
        
        return jsonify({"status": "success", "message": message}), 202
    
    except Exception as e:
        logger.error(f"Error initiating alarm creation/update: {str(e)}")
        return jsonify({"status": "error", "message": f"Failed to process alarm: {str(e)}"}), 500

@app.route('/alarms/<int:alarm_id>', methods=['GET'])
def get_alarm(alarm_id):
    """Get a specific alarm by ID."""
    # Add extra debug logging
    logger.info(f"GET /alarms/{alarm_id} - Getting alarm from database")
    
    # Create a direct database connection and query - use the same approach as debug.py
    try:
        from database_direct import get_alarm_by_id
        alarm = get_alarm_by_id(alarm_id)
        
        if alarm:
            logger.info(f"Found alarm {alarm_id} with direct query, label: '{alarm.label}'")
            result = alarm.to_dict()
            logger.info(f"Direct alarm to_dict result: {result}")
            return jsonify(result)
        else:
            return jsonify({"status": "error", "message": f"No alarm found with ID {alarm_id}"}), 404
            
    except Exception as e:
        logger.error(f"Error using direct alarm query: {str(e)}")
        
        # Fall back to regular method
        db = get_db()
        alarm = db.get_alarm(alarm_id)
        
        if alarm:
            return jsonify(alarm.to_dict())
        else:
            return jsonify({"status": "error", "message": f"No alarm found with ID {alarm_id}"}), 404

@app.route('/alarms/<int:alarm_id>', methods=['PUT'])
def update_alarm(alarm_id):
    """Update an existing alarm."""
    # Check if the alarm exists first
    db = get_db()
    existing_alarm = db.get_alarm(alarm_id)
    
    if not existing_alarm:
        return jsonify({"status": "error", "message": f"No alarm found with ID {alarm_id}"}), 404
    
    # Define a background thread function for processing the alarm update
    def process_alarm_update(data, alarm_id):
        try:
            logger.info(f"Processing alarm update for ID {alarm_id}, data: {data}")
            db = get_db()
            alarm = db.get_alarm(alarm_id)
            
            if not alarm:
                logger.error(f"Alarm {alarm_id} not found in background update task")
                return
            
            # Process sound file if provided
            sound_file_name = data.get('sound_file_name')
            sound_file_content = data.get('sound_file_content')
            
            if sound_file_name and sound_file_content:
                # Create sounds directory if it doesn't exist
                sounds_dir = os.path.join(os.path.dirname(__file__), "sounds")
                os.makedirs(sounds_dir, exist_ok=True)
                
                # Save the file
                import base64
                file_path = os.path.join(sounds_dir, sound_file_name)
                with open(file_path, 'wb') as f:
                    f.write(base64.b64decode(sound_file_content))
                data['sound_path'] = file_path
            
            # Handle the case where we get 'time' like "13:04" instead of separate hour and minute
            if 'time' in data and ':' in str(data['time']):
                try:
                    time_parts = data['time'].split(':')
                    data['hour'] = int(time_parts[0])
                    data['minute'] = int(time_parts[1])
                    logger.info(f"Converted time string '{data['time']}' to hour={data['hour']}, minute={data['minute']}")
                except Exception as e:
                    logger.error(f"Error converting time string: {e}")
            
            # Create timestamp from hour and minute if provided
            if 'hour' in data and 'minute' in data:
                # Create a new datetime with the specified hour and minute
                import calendar
                from datetime import datetime, time as dt_time
                
                # Start with current date
                now = datetime.now()
                
                # If a date is specified, use it
                if 'date' in data and data['date']:
                    try:
                        # Parse the date string (expected format: YYYY-MM-DD)
                        date_obj = datetime.strptime(data['date'], "%Y-%m-%d").date()
                        # Combine with the current date
                        now = datetime.combine(date_obj, now.time())
                    except Exception as e:
                        logger.error(f"Error parsing date string: {e}")
                
                # Create a datetime with the specified hour and minute
                alarm_time = dt_time(hour=int(data['hour']), minute=int(data['minute']))
                alarm_datetime = datetime.combine(now.date(), alarm_time)
                
                # Convert to milliseconds timestamp
                timestamp = int(calendar.timegm(alarm_datetime.timetuple()) * 1000)
                data['time'] = timestamp
            
            # Handle repeating vs one-time alarms
            if 'repeating' in data:
                repeating = data['repeating'] in [True, 'true', 1]
                data['repeating'] = repeating
                
                if repeating:
                    # For repeating alarms, ensure we have days data
                    if 'days' not in data or not any(data['days']):
                        # Set today's weekday if no days selected
                        from datetime import datetime
                        today_weekday = datetime.now().weekday()
                        sunday_based_weekday = (today_weekday + 1) % 7  # Convert to Sunday-based
                        data['days'] = [False] * 7
                        data['days'][sunday_based_weekday] = True
                else:
                    # For one-time alarms, we don't set any days
                    data['days'] = [False] * 7
            
            # Update the alarm with the new data
            alarm.from_dict(data)
            
            # Log the label value before saving
            label_value = data.get('label')
            if label_value:
                logger.info(f"Label value before saving: {label_value}")
            
            # Save the alarm
            db.update_alarm(alarm)
            logger.info(f"Alarm {alarm_id} updated in database")
            
            # Direct SQL update for label field to ensure it's saved correctly
            if label_value:
                try:
                    import psycopg2
                    conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
                    cursor = conn.cursor()
                    cursor.execute("UPDATE alarms SET label = %s WHERE id = %s", (label_value, alarm_id))
                    conn.commit()
                    cursor.close()
                    conn.close()
                    logger.info(f"Direct SQL update: Set label to '{label_value}' for alarm {alarm_id}")
                except Exception as e:
                    logger.error(f"Error updating label with direct SQL: {e}")
            
            # Get the updated alarm to verify changes
            updated_alarm = db.get_alarm(alarm_id)
            if updated_alarm:
                logger.info(f"Saved alarm retrieved from database: {updated_alarm.to_dict()}")
            
            # Update the scheduler
            # Use the global alarm_scheduler instance
            alarm_scheduler.schedule_alarm(alarm)
            
            logger.info(f"Alarm {alarm_id} updated in background thread")
            
        except Exception as e:
            logger.error(f"Error updating alarm in background thread: {e}")
    
    # Get the request data
    data = request.get_json()
    
    # Set alarm_id for update mode
    data['id'] = alarm_id
    
    # Start a background thread to process the alarm update
    logger.info(f"Alarm update started in background thread")
    threading.Thread(target=process_alarm_update, args=(data, alarm_id)).start()
    
    # Return a 202 Accepted response
    return jsonify({
        "status": "success",
        "message": "Alarm update started",
        "alarm_id": alarm_id
    }), 202

@app.route('/alarms/<int:alarm_id>', methods=['DELETE'])
def delete_alarm(alarm_id):
    """Delete an alarm."""
    # Create a background thread to process the deletion
    def process_deletion(alarm_id):
        try:
            db = get_db()
            # Remove from database
            db.delete_alarm(alarm_id)
            # Remove from scheduler
            alarm_scheduler.remove_alarm(alarm_id)
            app.logger.info(f"Alarm {alarm_id} deleted successfully in background thread")
        except Exception as e:
            app.logger.error(f"Error in background thread deleting alarm {alarm_id}: {str(e)}")
    
    try:
        db = get_db()
        # Quick check if alarm exists to avoid errors
        alarm = db.get_alarm(alarm_id)
        
        if not alarm:
            return jsonify({"status": "error", "message": f"Alarm with ID {alarm_id} not found"}), 404
            
        # Start a background thread for the deletion
        deletion_thread = threading.Thread(target=process_deletion, args=(alarm_id,))
        deletion_thread.daemon = True
        deletion_thread.start()
        
        # Log the deletion request
        app.logger.info(f"Deletion of alarm {alarm_id} started in background thread")
        
        # Return immediately - this prevents the browser from hanging
        return jsonify({"status": "success", "message": "Alarm deletion started"}), 202
    except Exception as e:
        app.logger.error(f"Error initiating alarm deletion for {alarm_id}: {str(e)}")
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
    from datetime import datetime
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
    app.logger.info("Adhan upload request received")
    
    # Check if request has JSON data
    if not request.is_json:
        app.logger.error("Adhan upload error: Request does not contain JSON data")
        return jsonify({
            "status": "error", 
            "message": "Request must contain JSON data"
        }), 400
    
    data = request.json
    file_name = data.get('file_name')
    file_content = data.get('file_content')  # Base64 encoded
    
    app.logger.info(f"Processing adhan upload for file: {file_name}")
    
    if not file_name:
        app.logger.error("Adhan upload error: Missing file_name")
        return jsonify({
            "status": "error", 
            "message": "Missing file_name parameter"
        }), 400
    
    if not file_content:
        app.logger.error("Adhan upload error: Missing file_content")
        return jsonify({
            "status": "error", 
            "message": "Missing file_content parameter"
        }), 400
    
    # Validate that the file has a .mp3 extension
    if not file_name.lower().endswith('.mp3'):
        app.logger.error(f"Adhan upload error: File {file_name} is not an MP3 file")
        return jsonify({
            "status": "error", 
            "message": "File must be an MP3 file"
        }), 400
    
    try:
        # Create sounds directory if it doesn't exist
        sounds_dir = os.path.join(os.path.dirname(__file__), "sounds")
        os.makedirs(sounds_dir, exist_ok=True)
        app.logger.info(f"Sounds directory ensured: {sounds_dir}")
        
        # Save the file
        import base64
        try:
            decoded_content = base64.b64decode(file_content)
            app.logger.info(f"Successfully decoded base64 content for {file_name}")
        except Exception as decode_error:
            app.logger.error(f"Base64 decoding error: {str(decode_error)}")
            return jsonify({
                "status": "error", 
                "message": f"Invalid base64 content: {str(decode_error)}"
            }), 400
        
        file_path = os.path.join(sounds_dir, file_name)
        with open(file_path, 'wb') as f:
            f.write(decoded_content)
        
        app.logger.info(f"Adhan sound file saved successfully at: {file_path}")
        
        return jsonify({
            "status": "success", 
            "message": f"Adhan sound '{file_name}' uploaded successfully", 
            "file_path": file_path,
            "file_size": len(decoded_content)
        })
    except Exception as e:
        app.logger.error(f"Adhan upload error: {str(e)}")
        return jsonify({
            "status": "error", 
            "message": f"Error saving file: {str(e)}"
        }), 500

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
@app.route('/adhan/set-prayer', methods=['POST'])
def set_adhan_for_prayer():
    """Set a custom adhan sound for a specific prayer."""
    data = request.json
    prayer_name = data.get('prayer_name')
    file_path = data.get('file_path')
    date_str = data.get('date')  # Optional, defaults to today
    
    # Log request details for debugging
    app.logger.info(f"Setting adhan for prayer {prayer_name} with file path {file_path}")
    
    if not prayer_name or not file_path or not os.path.exists(file_path):
        return jsonify({"status": "error", "message": "Invalid prayer name or file path"}), 400
    
    try:
        db = get_db()
        
        # Get the prayer time for today or specified date
        if not date_str:
            from datetime import datetime
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
    
    # Extract file name from path for display in notifications
    file_name = os.path.basename(file_path)
    murattal_name = os.path.splitext(file_name)[0]  # Remove extension
    
    # Play the murattal
    audio_player.play_murattal(file_path)
    
    # Broadcast WebSocket message about murattal playing
    app.logger.info(f"Broadcasting murattal_playing message for: {murattal_name}")
    # Use the imported broadcast_message function directly
    broadcast_message({
        'type': 'murattal_playing',
        'murattal_name': murattal_name,
        'file_path': file_path,
        'timestamp': int(time.time() * 1000)
    })
    
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
    # Get enabled YouTube videos with error handling
    youtube_videos = []
    try:
        db = get_db()
        logger.info("Attempting to fetch YouTube videos for home page")
        youtube_videos = db.get_enabled_youtube_videos()
        logger.info(f"Successfully retrieved {len(youtube_videos)} YouTube videos")
    except Exception as e:
        logger.error(f"Error retrieving YouTube videos: {e}")
        # Continue without YouTube videos
    
    return render_template('index.html', youtube_videos=youtube_videos)

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

@app.route('/web/alarms/edit/<int:alarm_id>', methods=['GET'])
def web_edit_alarm(alarm_id):
    """Web interface edit alarm page."""
    # Check if the alarm exists
    db = get_db()
    alarm = db.get_alarm(alarm_id)
    if not alarm:
        # Flash an error message and redirect to the alarms page
        # For now, just redirect to alarms page
        return redirect(url_for('web_alarms'))
    
    return render_template('edit_alarm.html', alarm_id=alarm_id)

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
    
    # Get YouTube videos with error handling
    youtube_videos = []
    try:
        logger.info("Attempting to fetch YouTube videos for settings page")
        youtube_videos = db.get_all_youtube_videos()
        logger.info(f"Successfully retrieved {len(youtube_videos)} YouTube videos for settings page")
    except Exception as e:
        logger.error(f"Error retrieving YouTube videos for settings page: {e}")
        # Continue without YouTube videos
    
    # Get configuration values
    return render_template('settings.html', 
                          adhan_sounds=adhan_sounds, 
                          prayers=prayer_times, 
                          youtube_videos=youtube_videos,
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

# YouTube Video Management Routes

@app.route('/youtube-videos', methods=['GET'])
def get_youtube_videos():
    """Get all YouTube videos."""
    try:
        db = get_db()
        logger.info("Fetching all YouTube videos via API")
        videos = db.get_all_youtube_videos()
        logger.info(f"Successfully retrieved {len(videos)} YouTube videos")
        return jsonify([video.to_dict() for video in videos])
    except Exception as e:
        logger.error(f"Error retrieving YouTube videos: {e}")
        return jsonify({"status": "error", "message": f"Error retrieving YouTube videos: {str(e)}"}), 500

@app.route('/youtube-videos/enabled', methods=['GET'])
def get_enabled_youtube_videos():
    """Get all enabled YouTube videos."""
    try:
        db = get_db()
        logger.info("Fetching enabled YouTube videos via API")
        videos = db.get_enabled_youtube_videos()
        logger.info(f"Successfully retrieved {len(videos)} enabled YouTube videos")
        return jsonify([video.to_dict() for video in videos])
    except Exception as e:
        logger.error(f"Error retrieving enabled YouTube videos: {e}")
        return jsonify({"status": "error", "message": f"Error retrieving enabled YouTube videos: {str(e)}"}), 500

@app.route('/youtube-videos', methods=['POST'])
def add_youtube_video():
    """Add a new YouTube video."""
    try:
        data = request.json
        
        # Validate data
        if 'url' not in data:
            return jsonify({"status": "error", "message": "URL is required"}), 400
            
        # Create and populate YouTube video object
        video = YouTubeVideo()
        video.url = data['url']
        video.title = data.get('title', '')
        video.enabled = data.get('enabled', True)
        
        # Get position if provided, otherwise add to the end
        if 'position' in data:
            video.position = int(data['position'])
        else:
            try:
                # Get all videos to determine the next position
                db = get_db()
                existing_videos = db.get_all_youtube_videos()
                video.position = len(existing_videos)
            except Exception as e:
                logger.warning(f"Error getting existing videos for position: {e}")
                video.position = 0  # Default to position 0 if we can't get the list
        
        # Add to database
        db = get_db()
        logger.info(f"Adding new YouTube video: {video.url}")
        video_id = db.add_youtube_video(video)
        
        if video_id:
            # Return the saved video
            saved_video = db.get_youtube_video(video_id)
            if saved_video:
                logger.info(f"Successfully added YouTube video with ID {video_id}")
                return jsonify({"status": "success", "message": "YouTube video added", "video": saved_video.to_dict()})
            else:
                logger.warning(f"Video was added with ID {video_id} but couldn't be retrieved")
                return jsonify({"status": "success", "message": "YouTube video added", "video_id": video_id})
        else:
            return jsonify({"status": "error", "message": "Failed to add YouTube video"}), 500
    except Exception as e:
        logger.error(f"Error adding YouTube video: {e}")
        return jsonify({"status": "error", "message": f"Error adding YouTube video: {str(e)}"}), 500

@app.route('/youtube-videos/<int:video_id>', methods=['PUT'])
def update_youtube_video(video_id):
    """Update an existing YouTube video."""
    try:
        data = request.json
        
        # Get the existing video
        db = get_db()
        logger.info(f"Retrieving YouTube video {video_id} for update")
        video = db.get_youtube_video(video_id)
        
        if not video:
            logger.warning(f"YouTube video with ID {video_id} not found")
            return jsonify({"status": "error", "message": f"YouTube video with ID {video_id} not found"}), 404
        
        # Update fields
        if 'url' in data:
            video.url = data['url']
        if 'title' in data:
            video.title = data['title']
        if 'enabled' in data:
            video.enabled = bool(data['enabled'])
        if 'position' in data:
            video.position = int(data['position'])
        
        # Save changes
        logger.info(f"Updating YouTube video {video_id}")
        db.update_youtube_video(video)
        
        # Return the updated video
        updated_video = db.get_youtube_video(video_id)
        if updated_video:
            logger.info(f"Successfully updated YouTube video {video_id}")
            return jsonify({"status": "success", "message": "YouTube video updated", "video": updated_video.to_dict()})
        else:
            logger.warning(f"Video {video_id} was updated but couldn't be retrieved after update")
            return jsonify({"status": "success", "message": "YouTube video updated"})
    except Exception as e:
        logger.error(f"Error updating YouTube video {video_id}: {e}")
        return jsonify({"status": "error", "message": f"Error updating YouTube video: {str(e)}"}), 500

@app.route('/youtube-videos/<int:video_id>', methods=['DELETE'])
def delete_youtube_video(video_id):
    """Delete a YouTube video."""
    try:
        db = get_db()
        
        # Check if the video exists
        logger.info(f"Checking if YouTube video {video_id} exists before deletion")
        video = db.get_youtube_video(video_id)
        if not video:
            logger.warning(f"YouTube video with ID {video_id} not found for deletion")
            return jsonify({"status": "error", "message": f"YouTube video with ID {video_id} not found"}), 404
        
        # Delete the video
        logger.info(f"Deleting YouTube video {video_id}")
        db.delete_youtube_video(video_id)
        
        logger.info(f"Successfully deleted YouTube video {video_id}")
        return jsonify({"status": "success", "message": f"YouTube video with ID {video_id} deleted"})
    except Exception as e:
        logger.error(f"Error deleting YouTube video {video_id}: {e}")
        return jsonify({"status": "error", "message": f"Error deleting YouTube video: {str(e)}"}), 500

@app.route('/youtube-videos/reorder', methods=['POST'])
def reorder_youtube_videos():
    """Reorder YouTube videos."""
    try:
        data = request.json
        
        if 'video_ids' not in data or not isinstance(data['video_ids'], list):
            logger.warning("Invalid request data for reordering: missing or invalid video_ids")
            return jsonify({"status": "error", "message": "video_ids list is required"}), 400
        
        # Update positions
        db = get_db()
        logger.info(f"Reordering YouTube videos with IDs: {data['video_ids']}")
        db.reorder_youtube_videos(data['video_ids'])
        
        try:
            # Return the reordered videos
            videos = db.get_all_youtube_videos()
            logger.info(f"Successfully reordered {len(videos)} YouTube videos")
            return jsonify({"status": "success", "message": "YouTube videos reordered", "videos": [video.to_dict() for video in videos]})
        except Exception as inner_e:
            logger.warning(f"Videos were reordered but couldn't be retrieved: {inner_e}")
            return jsonify({"status": "success", "message": "YouTube videos reordered"})
    except Exception as e:
        logger.error(f"Error reordering YouTube videos: {e}")
        return jsonify({"status": "error", "message": f"Error reordering YouTube videos: {str(e)}"}), 500

# Pre-Adhan and Tahrim sound routes
@app.route('/pre-adhan/10-min', methods=['POST'])
def set_pre_adhan_10_min():
    """Set a 10-minute pre-adhan announcement sound for a specific prayer."""
    data = request.json
    prayer_name = data.get('prayer_name')
    sound_path = data.get('sound_path')
    
    if not prayer_name:
        return jsonify({"status": "error", "message": "Prayer name is required"}), 400
    
    # Empty sound path is allowed (to disable the announcement)
    if sound_path and not os.path.exists(sound_path):
        return jsonify({"status": "error", "message": "Invalid sound file path"}), 400
    
    try:
        db = get_db()
        
        # Get prayer times for today
        from datetime import datetime
        date_str = datetime.now().strftime("%Y-%m-%d")
        prayer_times = db.get_prayer_times_by_date(date_str)
        updated = False
        
        for prayer in prayer_times:
            if prayer.name == prayer_name:
                prayer.pre_adhan_10_min = sound_path
                db.update_prayer_time(prayer)
                updated = True
                break
        
        if not updated:
            return jsonify({"status": "error", "message": "Prayer not found"}), 404
        
        return jsonify({
            "status": "success", 
            "message": f"10-minute pre-adhan sound for {prayer_name} updated"
        })
    except Exception as e:
        logger.error(f"Error setting 10-minute pre-adhan sound: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/pre-adhan/5-min', methods=['POST'])
def set_pre_adhan_5_min():
    """Set a 5-minute pre-adhan announcement sound for a specific prayer."""
    data = request.json
    prayer_name = data.get('prayer_name')
    sound_path = data.get('sound_path')
    
    if not prayer_name:
        return jsonify({"status": "error", "message": "Prayer name is required"}), 400
    
    # Empty sound path is allowed (to disable the announcement)
    if sound_path and not os.path.exists(sound_path):
        return jsonify({"status": "error", "message": "Invalid sound file path"}), 400
    
    try:
        db = get_db()
        
        # Get prayer times for today
        from datetime import datetime
        date_str = datetime.now().strftime("%Y-%m-%d")
        prayer_times = db.get_prayer_times_by_date(date_str)
        updated = False
        
        for prayer in prayer_times:
            if prayer.name == prayer_name:
                prayer.pre_adhan_5_min = sound_path
                db.update_prayer_time(prayer)
                updated = True
                break
        
        if not updated:
            return jsonify({"status": "error", "message": "Prayer not found"}), 404
        
        return jsonify({
            "status": "success", 
            "message": f"5-minute pre-adhan sound for {prayer_name} updated"
        })
    except Exception as e:
        logger.error(f"Error setting 5-minute pre-adhan sound: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/pre-adhan/tahrim', methods=['POST'])
def set_tahrim_sound():
    """Set a tahrim sound for a specific prayer."""
    data = request.json
    prayer_name = data.get('prayer_name')
    sound_path = data.get('sound_path')
    
    if not prayer_name:
        return jsonify({"status": "error", "message": "Prayer name is required"}), 400
    
    # Empty sound path is allowed (to disable the tahrim sound)
    if sound_path and not os.path.exists(sound_path):
        return jsonify({"status": "error", "message": "Invalid sound file path"}), 400
    
    try:
        db = get_db()
        
        # Get prayer times for today
        from datetime import datetime
        date_str = datetime.now().strftime("%Y-%m-%d")
        prayer_times = db.get_prayer_times_by_date(date_str)
        updated = False
        
        for prayer in prayer_times:
            if prayer.name == prayer_name:
                prayer.tahrim_sound = sound_path
                db.update_prayer_time(prayer)
                updated = True
                break
        
        if not updated:
            return jsonify({"status": "error", "message": "Prayer not found"}), 404
        
        return jsonify({
            "status": "success", 
            "message": f"Tahrim sound for {prayer_name} updated"
        })
    except Exception as e:
        logger.error(f"Error setting tahrim sound: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/alarms/test/<int:alarm_id>', methods=['POST'])
def test_alarm(alarm_id):
    """Test play a specific alarm sound."""
    try:
        db = get_db()
        alarm = db.get_alarm(alarm_id)
        
        if not alarm:
            return jsonify({
                'status': 'error',
                'message': 'Alarm not found'
            }), 404
        
        # Broadcast alarm playing message for the ticker
        alarm_label = alarm.label or f"Alarm {alarm.id}"
        broadcast_message({
            'type': 'alarm_playing',
            'alarm_id': alarm.id,
            'alarm_label': alarm_label,
            'timestamp': int(time.time() * 1000)
        })
        
        # Play alarm sound
        if alarm.is_tts and alarm.message:
            audio_player.play_tts(alarm.message, audio_player.PRIORITY_ALARM)
        elif alarm.sound_path and os.path.exists(alarm.sound_path):
            audio_player.play_file(alarm.sound_path, audio_player.PRIORITY_ALARM)
        else:
            # Use the default alarm sound if no specific sound is set
            audio_player.play_file(Config.DEFAULT_ALARM_SOUND, audio_player.PRIORITY_ALARM)
        
        return jsonify({
            'status': 'success',
            'message': f'Testing alarm {alarm_id}'
        })
    
    except Exception as e:
        logger.error(f"Error testing alarm: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/pre-adhan/test', methods=['POST'])
def test_pre_adhan_sound():
    """Test a pre-adhan or tahrim sound."""
    data = request.json
    prayer_id = data.get('prayer_id')
    prayer_name = data.get('prayer_name')
    sound_type = data.get('sound_type')  # 'pre_adhan_10_min', 'pre_adhan_5_min', or 'tahrim_sound'
    
    if not prayer_name or not sound_type:
        return jsonify({"status": "error", "message": "Prayer name and sound type are required"}), 400
    
    try:
        db = get_db()
        
        # Get prayer times for today
        from datetime import datetime
        date_str = datetime.now().strftime("%Y-%m-%d")
        prayer_times = db.get_prayer_times_by_date(date_str)
        
        for prayer in prayer_times:
            if prayer.name == prayer_name:
                if sound_type == 'pre_adhan_10_min' and prayer.pre_adhan_10_min:
                    audio_player.play_file(prayer.pre_adhan_10_min)
                    return jsonify({"status": "success", "message": f"Playing 10-minute pre-adhan sound for {prayer_name}"})
                elif sound_type == 'pre_adhan_5_min' and prayer.pre_adhan_5_min:
                    audio_player.play_file(prayer.pre_adhan_5_min)
                    return jsonify({"status": "success", "message": f"Playing 5-minute pre-adhan sound for {prayer_name}"})
                elif sound_type == 'tahrim_sound' and prayer.tahrim_sound:
                    audio_player.play_file(prayer.tahrim_sound)
                    return jsonify({"status": "success", "message": f"Playing tahrim sound for {prayer_name}"})
                else:
                    return jsonify({"status": "error", "message": f"No {sound_type.replace('_', ' ')} set for {prayer_name}"}), 404
        
        return jsonify({"status": "error", "message": "Prayer not found"}), 404
    except Exception as e:
        logger.error(f"Error testing pre-adhan sound: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

def prayer_scheduler_watchdog():
    """Monitor the prayer scheduler and restart it if it becomes unresponsive."""
    global last_prayer_check_time, prayer_scheduler_healthy
    
    try:
        # Check for flag files first
        flag_dir = os.path.join(os.path.dirname(__file__), "flags")
        os.makedirs(flag_dir, exist_ok=True)
        
        starting_flag = os.path.join(flag_dir, "prayer_check_starting.flag")
        completed_flag = os.path.join(flag_dir, "prayer_check_completed.flag")
        
        # Check if flags exist and their timestamps
        starting_time = None
        completed_time = None
        
        if os.path.exists(starting_flag):
            try:
                with open(starting_flag, 'r') as f:
                    starting_time = float(f.read().strip())
            except Exception as e:
                logger.error(f"Error reading starting flag: {str(e)}")
        
        if os.path.exists(completed_flag):
            try:
                with open(completed_flag, 'r') as f:
                    completed_time = float(f.read().strip())
            except Exception as e:
                logger.error(f"Error reading completed flag: {str(e)}")
        
        # If we have both timestamps, check if the process is stuck
        current_time = time.time()
        
        if starting_time and completed_time:
            # If completed time is after starting time, the process completed normally
            if completed_time > starting_time:
                logger.debug("Prayer check process completed normally")
            else:
                # Something's wrong with the timestamps
                logger.warning(f"Strange timestamp values: starting={starting_time}, completed={completed_time}")
        
        elif starting_time and not completed_time:
            # Process started but never completed - it might be stuck
            stuck_duration = current_time - starting_time
            if stuck_duration > 20:  # If stuck for more than 20 seconds
                logger.critical(f"Prayer check process appears stuck for {stuck_duration:.1f} seconds")
                # Force restart the prayer scheduler
                force_restart_scheduler()
        
        # Check last update time from the main system
        time_since_last_check = current_time - last_prayer_check_time
        
        # If it's been more than 30 seconds since the last check, consider it unresponsive
        if time_since_last_check > 30:
            logger.warning(f"Prayer scheduler may be unresponsive. Last check was {time_since_last_check:.1f} seconds ago")
            
            # Force restart the scheduler
            force_restart_scheduler()
    
    except Exception as e:
        logger.error(f"Error in prayer scheduler watchdog: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
    
    # Schedule the next check
    threading.Timer(10.0, prayer_scheduler_watchdog).start()  # Check more frequently

def force_restart_scheduler():
    """Force restart the prayer scheduler."""
    global last_prayer_check_time, prayer_scheduler_healthy
    
    # Stop and restart the prayer scheduler
    try:
        # Kill any potentially frozen threads by creating a fresh scheduler
        global prayer_scheduler
        
        # First stop the existing one if possible
        try:
            prayer_scheduler.stop()
            logger.info("Stopped unresponsive prayer scheduler")
        except Exception as e:
            logger.error(f"Error stopping prayer scheduler: {str(e)}")
        
        # Create and start a new prayer scheduler
        # Import modules locally to avoid circular imports
        import sys
        import importlib
        
        # Reload the audio_player module to get a fresh instance
        if 'audio_player' in sys.modules:
            importlib.reload(sys.modules['audio_player'])
        
        # Import the audio_player instance
        try:
            from audio_player import AudioPlayer
            # Create a new audio player instance
            new_audio_player = AudioPlayer()
            # Create a new prayer scheduler with the new audio player
            prayer_scheduler = PrayerScheduler(new_audio_player)
        except Exception as e:
            logger.error(f"Error creating new audio player: {str(e)}")
            # Fall back to the global audio_player if available
            try:
                from audio_player import audio_player
                prayer_scheduler = PrayerScheduler(audio_player)
            except Exception as e2:
                logger.error(f"Error using fallback audio player: {str(e2)}")
                # Last resort - recreate the prayer scheduler with the existing audio player
                from prayer_scheduler import prayer_scheduler as existing_scheduler
                prayer_scheduler = existing_scheduler
        
        # Delete any lock files that might be causing issues
        flag_dir = os.path.join(os.path.dirname(__file__), "flags")
        for flag_file in os.listdir(flag_dir):
            if flag_file.endswith('.flag'):
                try:
                    os.remove(os.path.join(flag_dir, flag_file))
                    logger.info(f"Removed potential lock file: {flag_file}")
                except Exception as e:
                    logger.error(f"Error removing lock file {flag_file}: {str(e)}")
        
        # Start the scheduler
        prayer_scheduler.start()
        logger.info("Created and started a new prayer scheduler instance")
        
        # Reset the check time
        last_prayer_check_time = time.time()
        prayer_scheduler_healthy = True
        
    except Exception as e:
        logger.error(f"Error force-restarting prayer scheduler: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        prayer_scheduler_healthy = False

# Add a method to update the last check time
def update_prayer_check_time():
    """Update the last prayer check time to indicate the scheduler is healthy."""
    global last_prayer_check_time
    last_prayer_check_time = time.time()

def start_schedulers():
    """Start the prayer and alarm schedulers."""
    logger.info("Starting schedulers...")
    
    # Initialize database first
    init_db()
    
    # Start prayer scheduler
    prayer_scheduler.start()
    
    # Start alarm scheduler
    alarm_scheduler.start()
    
    # Start the prayer scheduler watchdog
    threading.Timer(15.0, prayer_scheduler_watchdog).start()
    
    logger.info("Schedulers started successfully")

if __name__ == '__main__':
    # Start schedulers in a separate thread
    threading.Thread(target=start_schedulers, daemon=True).start()
    
    # Give schedulers time to initialize
    time.sleep(2)
    
    # Check for Replit environment
    in_replit = os.environ.get('REPL_ID') is not None
    
    # SSL Certificate paths
    ssl_dir = os.path.join(os.path.dirname(__file__), 'ssl')
    cert_path = os.path.join(ssl_dir, 'server.crt')
    key_path = os.path.join(ssl_dir, 'server.key')
    
    # Check if SSL certificates exist, use them if available
    if os.path.exists(cert_path) and os.path.exists(key_path):
        # Debug info about host and port with SSL
        logger.info(f"Starting Flask app with SSL on host='0.0.0.0', port=5000")
        # Start Flask app with SSL
        app.run(host='0.0.0.0', port=5000, threaded=True, debug=False, 
                ssl_context=(cert_path, key_path))
    else:
        # Debug info about host and port without SSL
        logger.info("SSL certificates not found, starting Flask app without SSL on host='0.0.0.0', port=5000")
        logger.info("Push-to-Talk feature may not work without HTTPS")
        # Start Flask app without SSL
        app.run(host='0.0.0.0', port=5000, threaded=True, debug=False)
