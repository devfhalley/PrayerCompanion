#!/usr/bin/env python3
"""
Database module for Raspberry Pi Prayer Alarm System.
This module provides functions for interacting with the SQLite database.
"""

import logging
import os
import sqlite3
from datetime import datetime, timedelta
import threading
from contextlib import contextmanager

from models import Alarm, PrayerTime

logger = logging.getLogger(__name__)

# Global database connection
_conn = None
_conn_lock = threading.Lock()

def init_db():
    """Initialize the database."""
    logger.info("Initializing database")
    
    with _get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Create alarms table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS alarms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            time INTEGER NOT NULL,
            enabled INTEGER NOT NULL,
            repeating INTEGER NOT NULL,
            days TEXT,
            is_tts INTEGER NOT NULL,
            message TEXT,
            sound_path TEXT
        )
        ''')
        
        # Create prayer_times table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS prayer_times (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            time TEXT NOT NULL,
            enabled INTEGER NOT NULL,
            custom_sound TEXT
        )
        ''')
        
        conn.commit()
    
    logger.info("Database initialized")

@contextmanager
def _get_db_connection():
    """Get a database connection."""
    # Use a thread-local connection for SQLite
    db_path = 'prayer_alarm.db'
    conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    
    try:
        yield conn
    except sqlite3.Error as e:
        logger.error(f"Database error: {str(e)}")
        raise
    finally:
        # We don't close the connection as we're using check_same_thread=False
        pass

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
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                alarm.time,
                1 if alarm.enabled else 0,
                1 if alarm.repeating else 0,
                days_str,
                1 if alarm.is_tts else 0,
                alarm.message,
                alarm.sound_path
            ))
            
            conn.commit()
            alarm.id = cursor.lastrowid
            
            logger.info(f"Added alarm with ID {alarm.id}")
            return alarm.id
    
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
            SET time = ?, enabled = ?, repeating = ?, days = ?, is_tts = ?, message = ?, sound_path = ?
            WHERE id = ?
            ''', (
                alarm.time,
                1 if alarm.enabled else 0,
                1 if alarm.repeating else 0,
                days_str,
                1 if alarm.is_tts else 0,
                alarm.message,
                alarm.sound_path,
                alarm.id
            ))
            
            conn.commit()
            logger.info(f"Updated alarm with ID {alarm.id}")
    
    def delete_alarm(self, alarm_id):
        """Delete an alarm.
        
        Args:
            alarm_id: ID of the alarm to delete
        """
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM alarms WHERE id = ?', (alarm_id,))
            conn.commit()
            
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
            
            cursor.execute('SELECT * FROM alarms WHERE id = ?', (alarm_id,))
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
            
            cursor.execute('SELECT * FROM alarms WHERE enabled = 1 ORDER BY time')
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
            WHERE enabled = 1 AND repeating = 0 AND time >= ? AND time < ?
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
            VALUES (?, ?, ?, ?)
            ''', (
                prayer_time.name,
                prayer_time.time.isoformat(),
                1 if prayer_time.enabled else 0,
                prayer_time.custom_sound
            ))
            
            conn.commit()
            prayer_time.id = cursor.lastrowid
            
            return prayer_time.id
    
    def update_prayer_time(self, prayer_time):
        """Update an existing prayer time.
        
        Args:
            prayer_time: PrayerTime object to update
        """
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
            UPDATE prayer_times
            SET name = ?, time = ?, enabled = ?, custom_sound = ?
            WHERE id = ?
            ''', (
                prayer_time.name,
                prayer_time.time.isoformat(),
                1 if prayer_time.enabled else 0,
                prayer_time.custom_sound,
                prayer_time.id
            ))
            
            conn.commit()
    
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
            WHERE time >= ? AND time < ?
            ORDER BY time
            ''', (date_obj.isoformat(), next_day.isoformat()))
            
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
            
            now = datetime.now().isoformat()
            
            cursor.execute('''
            SELECT * FROM prayer_times 
            WHERE time > ? AND enabled = 1
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
            WHERE time >= ?
            ''', (date_obj.isoformat(),))
            
            conn.commit()
            
            logger.info(f"Deleted prayer times from {date_str} onwards")
    
    def _row_to_alarm(self, row):
        """Convert a database row to an Alarm object.
        
        Args:
            row: Database row
        
        Returns:
            Alarm object
        """
        alarm = Alarm()
        
        alarm.id = row['id']
        alarm.time = row['time']
        alarm.enabled = bool(row['enabled'])
        alarm.repeating = bool(row['repeating'])
        
        # Convert days string to boolean list
        days_str = row['days'] or '0000000'
        alarm.days = [c == '1' for c in days_str]
        
        alarm.is_tts = bool(row['is_tts'])
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
        
        prayer_time.id = row['id']
        prayer_time.name = row['name']
        prayer_time.time = datetime.fromisoformat(row['time'])
        prayer_time.enabled = bool(row['enabled'])
        prayer_time.custom_sound = row['custom_sound']
        
        return prayer_time
