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

from models import Alarm, PrayerTime, YouTubeVideo

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
            days BOOLEAN[] DEFAULT '{false,false,false,false,false,false,false}',
            days_old VARCHAR(7),
            is_tts BOOLEAN NOT NULL,
            message TEXT,
            sound_path TEXT,
            label TEXT,
            priority INTEGER
        )
        ''')
        
        # Create prayer_times table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS prayer_times (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            time TIMESTAMP NOT NULL,
            enabled BOOLEAN NOT NULL,
            custom_sound TEXT,
            date_str TEXT
        )
        ''')
        
        # Check if date_str column exists in prayer_times table
        cursor.execute('''
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'prayer_times' AND column_name = 'date_str'
        ''')
        
        if not cursor.fetchone():
            # Add date_str column if it doesn't exist and make it not null
            logger.info("Adding 'date_str' column to prayer_times table")
            cursor.execute('''
            ALTER TABLE prayer_times
            ADD COLUMN date_str TEXT
            ''')
            
            # Populate date_str for existing records
            cursor.execute('''
            UPDATE prayer_times
            SET date_str = TO_CHAR(time, 'YYYY-MM-DD')
            WHERE date_str IS NULL
            ''')
            
            # Make date_str not null once it's populated
            cursor.execute('''
            ALTER TABLE prayer_times
            ALTER COLUMN date_str SET NOT NULL
            ''')
        
        # Create youtube_videos table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS youtube_videos (
            id SERIAL PRIMARY KEY,
            url TEXT NOT NULL,
            title TEXT,
            enabled BOOLEAN NOT NULL DEFAULT TRUE,
            position INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

# This class is kept for backward compatibility but should be replaced with the one from database_pg.py
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
            
            # Convert days list to string - make sure we're using the format PostgreSQL expects for arrays
            if alarm.days and len(alarm.days) > 0:
                days_str = '{' + ','.join('true' if day else 'false' for day in alarm.days) + '}'
            else:
                # Default to all days false if no days are provided
                days_str = '{false,false,false,false,false,false,false}'
            
            cursor.execute('''
            INSERT INTO alarms (time, enabled, repeating, days, is_tts, message, sound_path, label)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            ''', (
                alarm.time,
                alarm.enabled,
                alarm.repeating,
                days_str,
                alarm.is_tts,
                alarm.message,
                alarm.sound_path,
                alarm.label
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
            
            # Convert days list to string - make sure we're using the format PostgreSQL expects for arrays
            if alarm.days and len(alarm.days) > 0:
                days_str = '{' + ','.join('true' if day else 'false' for day in alarm.days) + '}'
            else:
                # Default to all days false if no days are provided
                days_str = '{false,false,false,false,false,false,false}'
            
            cursor.execute('''
            UPDATE alarms
            SET time = %s, enabled = %s, repeating = %s, days = %s, is_tts = %s, message = %s, sound_path = %s, label = %s
            WHERE id = %s
            ''', (
                alarm.time,
                alarm.enabled,
                alarm.repeating,
                days_str,
                alarm.is_tts,
                alarm.message,
                alarm.sound_path,
                alarm.label,
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
            INSERT INTO prayer_times (name, time, enabled, custom_sound, date_str)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            ''', (
                prayer_time.name,
                prayer_time.time,
                prayer_time.enabled,
                prayer_time.custom_sound,
                prayer_time.date_str
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
            
            # Ensure date_str is set
            if not hasattr(prayer_time, 'date_str') or not prayer_time.date_str:
                prayer_time.date_str = prayer_time.time.strftime('%Y-%m-%d')
            
            cursor.execute('''
            UPDATE prayer_times
            SET name = %s, time = %s, enabled = %s, custom_sound = %s, date_str = %s
            WHERE id = %s
            ''', (
                prayer_time.name,
                prayer_time.time,
                prayer_time.enabled,
                prayer_time.custom_sound,
                prayer_time.date_str,
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
            
            try:
                # First try to query by date_str (this is more reliable)
                cursor.execute('''
                SELECT * FROM prayer_times 
                WHERE date_str = %s
                ORDER BY time
                ''', (date_str,))
                
                rows = cursor.fetchall()
                
                if rows:
                    logger.info(f"Found {len(rows)} prayer times for date {date_str} using date_str field")
                    return [self._row_to_prayer_time(row) for row in rows]
                
                # Fallback to the time range method
                logger.info(f"No prayer times found using date_str field, falling back to time range for {date_str}")
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                next_day = date_obj + timedelta(days=1)
                
                cursor.execute('''
                SELECT * FROM prayer_times 
                WHERE time >= %s AND time < %s
                ORDER BY time
                ''', (date_obj, next_day))
                
                rows = cursor.fetchall()
                
                # If we found results using time range, update their date_str
                if rows:
                    logger.info(f"Found {len(rows)} prayer times using time range for {date_str}, updating date_str field")
                    prayer_times = [self._row_to_prayer_time(row) for row in rows]
                    
                    # Update date_str in database for these prayer times
                    for prayer in prayer_times:
                        if not prayer.date_str or prayer.date_str != date_str:
                            prayer.date_str = date_str
                            self.update_prayer_time(prayer)
                            logger.info(f"Updated date_str for prayer {prayer.id} to {date_str}")
                    
                    return prayer_times
                
                return []
                
            except Exception as e:
                logger.error(f"Error getting prayer times for date {date_str}: {str(e)}")
                return []
    
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
            
            # Use both date_str field and time field for deletion to ensure all matching records are removed
            try:
                # First try to delete by date_str (this will work for records that have date_str set)
                cursor.execute('''
                DELETE FROM prayer_times 
                WHERE date_str >= %s
                ''', (date_str,))
                
                affected_rows = cursor.rowcount
                logger.info(f"Deleted {affected_rows} prayer times using date_str field from {date_str} onwards")
                
                # Also delete by time range to catch any records that don't have date_str set
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                
                cursor.execute('''
                DELETE FROM prayer_times 
                WHERE time >= %s AND (date_str IS NULL OR date_str = '')
                ''', (date_obj,))
                
                affected_rows = cursor.rowcount
                logger.info(f"Deleted {affected_rows} additional prayer times using time field from {date_str} onwards")
                
            except Exception as e:
                logger.error(f"Error deleting prayer times from date {date_str}: {str(e)}")
            
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
        
        # Handle different formats of days field
        days_data = row['days']
        if days_data is None:
            # Default to all days disabled
            alarm.days = [False, False, False, False, False, False, False]
        elif isinstance(days_data, str) and days_data.startswith('{') and days_data.endswith('}'):
            # PostgreSQL array format like '{true,false,true,false,false,false,false}'
            try:
                # Remove curly braces and split by comma
                days_values = days_data[1:-1].split(',')
                alarm.days = [val.lower() == 'true' or val == 't' for val in days_values]
                # Ensure we have 7 days
                if len(alarm.days) < 7:
                    alarm.days.extend([False] * (7 - len(alarm.days)))
            except Exception as e:
                logger.error(f"Error parsing days array: {e}")
                alarm.days = [False, False, False, False, False, False, False]
        elif isinstance(days_data, str):
            # Legacy string format like '1001000'
            alarm.days = [c == '1' for c in days_data]
            # Ensure we have 7 days
            if len(alarm.days) < 7:
                alarm.days.extend([False] * (7 - len(alarm.days)))
        else:
            # Unknown format, default to all days disabled
            logger.warning(f"Unknown days format: {days_data}")
            alarm.days = [False, False, False, False, False, False, False]
        
        alarm.is_tts = row['is_tts']
        alarm.message = row['message']
        alarm.sound_path = row['sound_path']
        
        # Set label if it exists in the row
        if 'label' in row:
            alarm.label = row['label']
        
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
        
        # Add date_str from database or extract it from time if missing
        if 'date_str' in row and row['date_str']:
            prayer_time.date_str = row['date_str']
        elif prayer_time.time:
            prayer_time.date_str = prayer_time.time.strftime('%Y-%m-%d')
        
        return prayer_time
        
    def _row_to_youtube_video(self, row):
        """Convert a database row to a YouTubeVideo object.
        
        Args:
            row: Database row
        
        Returns:
            YouTubeVideo object
        """
        video = YouTubeVideo()
        
        # Check if row is None before proceeding
        if row is None:
            return video
            
        video.id = row['id']
        video.url = row['url']
        video.title = row['title']
        video.enabled = row['enabled']
        video.position = row['position']
        
        return video
    
    def add_youtube_video(self, video):
        """Add a YouTube video to the database.
        
        Args:
            video: YouTubeVideo object to add
        
        Returns:
            YouTubeVideo ID
        """
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
            INSERT INTO youtube_videos (url, title, enabled, position)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            ''', (
                video.url,
                video.title,
                video.enabled,
                video.position
            ))
            
            result = cursor.fetchone()
            if result:
                video.id = result[0]
                return video.id
            else:
                logger.error("Failed to retrieve ID of newly inserted YouTube video")
                return None
    
    def update_youtube_video(self, video):
        """Update a YouTube video.
        
        Args:
            video: YouTubeVideo object to update
        """
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
            UPDATE youtube_videos
            SET url = %s, title = %s, enabled = %s, position = %s
            WHERE id = %s
            ''', (
                video.url,
                video.title,
                video.enabled,
                video.position,
                video.id
            ))
    
    def delete_youtube_video(self, video_id):
        """Delete a YouTube video.
        
        Args:
            video_id: ID of the video to delete
        """
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM youtube_videos WHERE id = %s', (video_id,))
    
    def get_youtube_video(self, video_id):
        """Get a YouTube video by ID.
        
        Args:
            video_id: ID of the video to get
        
        Returns:
            YouTubeVideo object or None
        """
        with _get_db_connection() as conn:
            dict_cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            dict_cursor.execute('SELECT * FROM youtube_videos WHERE id = %s', (video_id,))
            row = dict_cursor.fetchone()
            
            if row:
                return self._row_to_youtube_video(row)
            
            return None
    
    def get_all_youtube_videos(self):
        """Get all YouTube videos.
        
        Returns:
            List of YouTubeVideo objects
        """
        with _get_db_connection() as conn:
            dict_cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            dict_cursor.execute('SELECT * FROM youtube_videos ORDER BY position')
            rows = dict_cursor.fetchall()
            
            return [self._row_to_youtube_video(row) for row in rows]
    
    def get_enabled_youtube_videos(self):
        """Get all enabled YouTube videos.
        
        Returns:
            List of enabled YouTubeVideo objects
        """
        with _get_db_connection() as conn:
            dict_cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            dict_cursor.execute('SELECT * FROM youtube_videos WHERE enabled = TRUE ORDER BY position')
            rows = dict_cursor.fetchall()
            
            return [self._row_to_youtube_video(row) for row in rows]
    
    def reorder_youtube_videos(self, video_ids):
        """Reorder YouTube videos.
        
        Args:
            video_ids: List of video IDs in the new order
        """
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            
            for i, video_id in enumerate(video_ids):
                cursor.execute('''
                UPDATE youtube_videos
                SET position = %s
                WHERE id = %s
                ''', (i, video_id))