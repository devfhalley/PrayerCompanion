#!/usr/bin/env python3
"""
Direct database functions for Raspberry Pi Prayer Alarm System.
This module provides functions for directly accessing the database.
"""

import os
import psycopg2
import psycopg2.extras
import logging
from models import Alarm, PrayerTime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_alarm_by_id(alarm_id):
    """Get an alarm by ID using direct database access."""
    try:
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cursor.execute('SELECT * FROM alarms WHERE id = %s', (alarm_id,))
        row = cursor.fetchone()
        
        if not row:
            logger.info(f"No alarm found with ID {alarm_id}")
            return None
            
        # Convert to alarm object
        alarm = row_to_alarm(row)
        
        # Close resources
        cursor.close()
        conn.close()
        
        return alarm
    except Exception as e:
        logger.error(f"Error retrieving alarm: {str(e)}")
        return None

def get_connection():
    """Get a database connection."""
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        raise Exception("DATABASE_URL environment variable not set")
        
    conn = psycopg2.connect(db_url)
    return conn

def row_to_alarm(row):
    """Convert a row to an Alarm object."""
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
    
    # Handle label specially
    label_value = row.get('label')
    if label_value:
        alarm.label = str(label_value)
        logger.info(f"Direct access set label to: '{alarm.label}'")
    else:
        alarm.label = None
        logger.info("Direct access set label to None")
    
    return alarm