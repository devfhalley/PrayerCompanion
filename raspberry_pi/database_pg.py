#!/usr/bin/env python3
"""
Database module for Raspberry Pi Prayer Alarm System.
This module provides functions for interacting with the PostgreSQL database.
"""

import logging
import os
import psycopg2
import psycopg2.extras
from datetime import datetime, timedelta
import threading
from contextlib import contextmanager

from models import Alarm, PrayerTime

logger = logging.getLogger(__name__)

# Global database connection pool
_conn_pool = None
_conn_lock = threading.Lock()

def init_db():
    """Initialize the database."""
    logger.info("Initializing PostgreSQL database")
    
    with _get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Create alarms table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS alarms (
            id SERIAL PRIMARY KEY,
            time BIGINT NOT NULL,
            enabled BOOLEAN NOT NULL,
            repeating BOOLEAN NOT NULL,
            days VARCHAR(7),
            is_tts BOOLEAN NOT NULL,
            message TEXT,
            sound_path TEXT
        )
        ''')
        
        # Create prayer_times table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS prayer_times (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            time TIMESTAMP NOT NULL,
            enabled BOOLEAN NOT NULL,
            custom_sound TEXT
        )
        ''')
        
        conn.commit()
    
    logger.info("PostgreSQL database initialized")

@contextmanager
def _get_db_connection():
    """Get a database connection."""
    conn = None
    
    try:
        # Get connection parameters from environment
        db_url = os.environ.get('DATABASE_URL')
        if not db_url:
            raise Exception("DATABASE_URL environment variable not set")
            
        # Create a new connection
        conn = psycopg2.connect(db_url, cursor_factory=psycopg2.extras.DictCursor)
        conn.autocommit = False
        
        # Yield the connection
        yield conn
        
        # If we get here without an exception, commit the transaction
        if not conn.closed:
            conn.commit()
            
    except Exception as e:
        # If there's an exception, rollback any changes
        logger.error(f"Database error: {e}")
        if conn and not conn.closed:
            conn.rollback()
        raise
        
    finally:
        # Always close the connection when done
        if conn and not conn.closed:
            conn.close()

def get_db():
    """Get the database wrapper."""
    init_db()  # Make sure database is initialized
    return DatabaseWrapper()

class DatabaseWrapper:
    """Wrapper class for database operations."""
    
    def add_alarm(self, alarm):
        """Add an alarm to the database.
        
        Args:
            alarm: Alarm object to add
        
        Returns:
            Alarm ID
        """
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Convert days list to string
            days_str = ''.join('1' if day else '0' for day in alarm.days)
            
            cursor.execute('''
            INSERT INTO alarms (time, enabled, repeating, days, is_tts, message, sound_path)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            ''', (
                alarm.time,
                alarm.enabled,
                alarm.repeating,
                days_str,
                alarm.is_tts,
                alarm.message,
                alarm.sound_path
            ))
            
            result = cursor.fetchone()
            if result:
                alarm.id = result[0]
                logger.info(f"Added alarm with ID {alarm.id}")
                return alarm.id
            else:
                logger.error("Failed to retrieve ID of newly inserted alarm")
                return None
    
    def update_alarm(self, alarm):
        """Update an existing alarm.
        
        Args:
            alarm: Alarm object to update
        """
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Convert days list to string
            days_str = ''.join('1' if day else '0' for day in alarm.days)
            
            cursor.execute('''
            UPDATE alarms
            SET time = %s, enabled = %s, repeating = %s, days = %s, is_tts = %s, message = %s, sound_path = %s
            WHERE id = %s
            ''', (
                alarm.time,
                alarm.enabled,
                alarm.repeating,
                days_str,
                alarm.is_tts,
                alarm.message,
                alarm.sound_path,
                alarm.id
            ))
            
            logger.info(f"Updated alarm with ID {alarm.id}")
    
    def delete_alarm(self, alarm_id):
        """Delete an alarm.
        
        Args:
            alarm_id: ID of the alarm to delete
        """
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM alarms WHERE id = %s', (alarm_id,))
            
            logger.info(f"Deleted alarm with ID {alarm_id}")
    
    def get_alarm(self, alarm_id):
        """Get an alarm by ID.
        
        Args:
            alarm_id: ID of the alarm to get
        
        Returns:
            Alarm object or None
        """
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM alarms WHERE id = %s', (alarm_id,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_alarm(row)
            
            return None
    
    def get_all_alarms(self):
        """Get all alarms.
        
        Returns:
            List of Alarm objects
        """
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM alarms ORDER BY time')
            rows = cursor.fetchall()
            
            return [self._row_to_alarm(row) for row in rows]
    
    def get_enabled_alarms(self):
        """Get all enabled alarms.
        
        Returns:
            List of enabled Alarm objects
        """
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM alarms WHERE enabled = TRUE ORDER BY time')
            rows = cursor.fetchall()
            
            return [self._row_to_alarm(row) for row in rows]
    
    def get_one_time_alarms_for_today(self):
        """Get one-time alarms for today.
        
        Returns:
            List of one-time Alarm objects for today
        """
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get start and end of today
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            tomorrow = today + timedelta(days=1)
            
            # Convert to milliseconds
            start_time = int(today.timestamp() * 1000)
            end_time = int(tomorrow.timestamp() * 1000)
            
            cursor.execute('''
            SELECT * FROM alarms 
            WHERE enabled = TRUE AND repeating = FALSE AND time >= %s AND time < %s
            ORDER BY time
            ''', (start_time, end_time))
            
            rows = cursor.fetchall()
            
            return [self._row_to_alarm(row) for row in rows]
    
    def add_prayer_time(self, prayer_time):
        """Add a prayer time to the database.
        
        Args:
            prayer_time: PrayerTime object to add
        
        Returns:
            PrayerTime ID
        """
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
            INSERT INTO prayer_times (name, time, enabled, custom_sound)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            ''', (
                prayer_time.name,
                prayer_time.time,
                prayer_time.enabled,
                prayer_time.custom_sound
            ))
            
            result = cursor.fetchone()
            if result:
                prayer_time.id = result[0]
                return prayer_time.id
            else:
                logger.error("Failed to retrieve ID of newly inserted prayer time")
                return None
    
    def update_prayer_time(self, prayer_time):
        """Update an existing prayer time.
        
        Args:
            prayer_time: PrayerTime object to update
        """
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
            UPDATE prayer_times
            SET name = %s, time = %s, enabled = %s, custom_sound = %s
            WHERE id = %s
            ''', (
                prayer_time.name,
                prayer_time.time,
                prayer_time.enabled,
                prayer_time.custom_sound,
                prayer_time.id
            ))
    
    def get_prayer_times_by_date(self, date_str):
        """Get prayer times for a specific date.
        
        Args:
            date_str: Date string in YYYY-MM-DD format
        
        Returns:
            List of PrayerTime objects for the date
        """
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get start and end of the day
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            next_day = date_obj + timedelta(days=1)
            
            cursor.execute('''
            SELECT * FROM prayer_times 
            WHERE time >= %s AND time < %s
            ORDER BY time
            ''', (date_obj, next_day))
            
            rows = cursor.fetchall()
            
            return [self._row_to_prayer_time(row) for row in rows]
    
    def get_todays_prayer_times(self):
        """Get prayer times for today.
        
        Returns:
            List of PrayerTime objects for today
        """
        today = datetime.now().strftime('%Y-%m-%d')
        return self.get_prayer_times_by_date(today)
    
    def get_next_prayer_time(self):
        """Get the next prayer time.
        
        Returns:
            Next PrayerTime object or None
        """
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            
            now = datetime.now()
            
            cursor.execute('''
            SELECT * FROM prayer_times 
            WHERE time > %s AND enabled = TRUE
            ORDER BY time
            LIMIT 1
            ''', (now,))
            
            row = cursor.fetchone()
            
            if row:
                return self._row_to_prayer_time(row)
            
            return None
    
    def delete_prayer_times_from_date(self, date_str):
        """Delete prayer times from a specific date onwards.
        
        Args:
            date_str: Date string in YYYY-MM-DD format
        """
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            
            cursor.execute('''
            DELETE FROM prayer_times 
            WHERE time >= %s
            ''', (date_obj,))
            
            logger.info(f"Deleted prayer times from {date_str} onwards")
    
    def _row_to_alarm(self, row):
        """Convert a database row to an Alarm object.
        
        Args:
            row: Database row
        
        Returns:
            Alarm object
        """
        alarm = Alarm()
        
        # Check if row is None before proceeding
        if row is None:
            return alarm
            
        alarm.id = row['id']
        alarm.time = row['time']
        alarm.enabled = row['enabled']
        alarm.repeating = row['repeating']
        
        # Convert days string to boolean list
        days_str = row['days'] or '0000000'
        alarm.days = [c == '1' for c in days_str]
        
        alarm.is_tts = row['is_tts']
        alarm.message = row['message']
        alarm.sound_path = row['sound_path']
        
        return alarm
    
    def _row_to_prayer_time(self, row):
        """Convert a database row to a PrayerTime object.
        
        Args:
            row: Database row
        
        Returns:
            PrayerTime object
        """
        prayer_time = PrayerTime()
        
        # Check if row is None before proceeding
        if row is None:
            return prayer_time
            
        prayer_time.id = row['id']
        prayer_time.name = row['name']
        prayer_time.time = row['time']
        prayer_time.enabled = row['enabled']
        prayer_time.custom_sound = row['custom_sound']
        
        return prayer_time