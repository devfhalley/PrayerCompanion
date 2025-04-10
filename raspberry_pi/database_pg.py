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
            days VARCHAR(7),
            is_tts BOOLEAN NOT NULL,
            message TEXT,
            sound_path TEXT
        )
        ''')
        
        # Check if label column exists in alarms table
        cursor.execute('''
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'alarms' AND column_name = 'label'
        ''')
        
        if not cursor.fetchone():
            # Add label column if it doesn't exist
            logger.info("Adding 'label' column to alarms table")
            cursor.execute('''
            ALTER TABLE alarms
            ADD COLUMN label TEXT
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
        # Use RealDictCursor instead of DictCursor for better dictionary access
        conn = psycopg2.connect(db_url, cursor_factory=psycopg2.extras.RealDictCursor)
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
    
    # Import YouTubeVideo model
    from models import YouTubeVideo
    
    def add_alarm(self, alarm):
        """Add an alarm to the database.
        
        Args:
            alarm: Alarm object to add
        
        Returns:
            Alarm ID
        """
        with _get_db_connection() as conn:
            # This connection will be used for both insert and verification
            conn.autocommit = False  # Manually control transaction
            cursor = conn.cursor()
            
            # Convert days list to string
            days_str = ''.join('1' if day else '0' for day in alarm.days)
            
            # Log label value before saving to database
            logger.info(f"Saving label to database: '{alarm.label}'")
            
            # Prepare the label value for insertion
            label_value = alarm.label if alarm.label else None
            logger.info(f"Label value prepared for SQL insertion: {label_value}")
            
            # Verify it's a string if not None
            if label_value is not None:
                label_value = str(label_value)
                logger.info(f"Converted label to string: {label_value}")
            
            # Execute the insertion with a single statement for all cases
            try:
                logger.info(f"Executing SQL with label value: '{label_value}'")
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
                    label_value,  # This will be NULL if label_value is None
                ))
            except Exception as e:
                logger.error(f"Error inserting alarm: {str(e)}")
                raise
                
            result = cursor.fetchone()
            if result:
                alarm.id = result[0]
                logger.info(f"Added alarm with ID {alarm.id}")
                
                # Verify the data was inserted correctly by retrieving it again
                try:
                    # DEBUGGING: Print the SQL parameters for insertion
                    logger.info(f"VALUES in INSERT query: {alarm.time}, {alarm.enabled}, {alarm.repeating}, {days_str}, {alarm.is_tts}, {alarm.message}, {alarm.sound_path}, {label_value}")
                    
                    # Force update of the label with a direct approach
                    try:
                        logger.info(f"Performing direct label update for alarm {alarm.id}")
                        if label_value:
                            conn.cursor().execute(
                                "UPDATE alarms SET label = %s WHERE id = %s", 
                                (label_value, alarm.id)
                            )
                            conn.commit()
                            logger.info(f"Label directly set to '{label_value}' for alarm {alarm.id}")
                        else:
                            logger.info(f"No label to set for alarm {alarm.id}")
                    except Exception as e:
                        logger.error(f"Error with direct label update: {e}")
                    
                    # Verify with direct query using RealDictCursor
                    direct_cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                    direct_cursor.execute('SELECT * FROM alarms WHERE id = %s', (alarm.id,))
                    direct_result = direct_cursor.fetchone()
                    
                    if direct_result:
                        for key, value in direct_result.items():
                            logger.info(f"Verification - field '{key}': '{value}'")
                        
                        label_from_db = direct_result.get('label')
                        logger.info(f"Verification - label in database via direct query: '{label_from_db}'")
                        
                        # If label is still missing, try one more direct update
                        if label_value is not None and (label_from_db is None or label_from_db != label_value):
                            logger.warning(f"Label mismatch! Expected: '{label_value}', got: '{label_from_db}'. Fixing...")
                            fix_cursor = conn.cursor()
                            fix_cursor.execute('UPDATE alarms SET label = %s WHERE id = %s', (label_value, alarm.id))
                            conn.commit()
                            logger.info(f"Label fixed for alarm {alarm.id}")
                except Exception as e:
                    logger.error(f"Error in verification step: {str(e)}")
                    
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
            
            # Log label value before updating in database
            logger.info(f"Updating label in database: '{alarm.label}'")
            
            # Prepare the label value for update
            label_value = alarm.label if alarm.label else None
            logger.info(f"Label value prepared for SQL update: {label_value}")
            
            # Verify it's a string if not None
            if label_value is not None:
                label_value = str(label_value)
                logger.info(f"Converted update label to string: {label_value}")
                
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
                label_value,  # Use our prepared value
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
        # Get the alarm using a direct SQL query
        try:
            logger.info(f"Retrieving alarm with ID {alarm_id}")
            
            # Use direct database_direct.py approach which is known to work
            import psycopg2.extras
            
            conn = _get_db_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            # Get all fields including label
            cursor.execute('SELECT * FROM alarms WHERE id = %s', (alarm_id,))
            row = cursor.fetchone()
            
            if not row:
                logger.info(f"No alarm found with ID {alarm_id}")
                cursor.close()
                conn.close()
                return None
                
            # Log all fields
            logger.info(f"Row keys from database: {list(row.keys())}")
            for key, value in row.items():
                logger.info(f"Field '{key}': {value} (type: {type(value)})")
            
            # Convert to alarm object - creating it directly from dict
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
                logger.info(f"Set label to: '{alarm.label}'")
            else:
                alarm.label = None
                logger.info("Set label to None")
            
            # Close resources
            cursor.close()
            conn.close()
            
            logger.info(f"Successfully retrieved alarm {alarm_id}, label='{alarm.label}'")
            return alarm
            
        except Exception as e:
            logger.error(f"Error retrieving alarm {alarm_id}: {str(e)}")
            return None
    
    def get_all_alarms(self):
        """Get all alarms.
        
        Returns:
            List of Alarm objects
        """
        alarms = []
        
        with _get_db_connection() as conn:
            dict_cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            dict_cursor.execute('SELECT * FROM alarms ORDER BY time')
            rows = dict_cursor.fetchall()
            
            for row_dict in rows:
                # Create the alarm object directly from the dictionary
                alarm = Alarm()
                alarm.id = row_dict.get('id')
                alarm.time = row_dict.get('time')
                alarm.enabled = row_dict.get('enabled')
                alarm.repeating = row_dict.get('repeating')
                
                # Convert days string to boolean list
                days_str = row_dict.get('days') or '0000000'
                alarm.days = [c == '1' for c in days_str]
                
                # Other fields
                alarm.is_tts = row_dict.get('is_tts')
                alarm.message = row_dict.get('message')
                alarm.sound_path = row_dict.get('sound_path')
                
                # Label handling
                label_value = row_dict.get('label')
                alarm.label = str(label_value) if label_value else None
                
                alarms.append(alarm)
                
            return alarms
    
    def get_enabled_alarms(self):
        """Get all enabled alarms.
        
        Returns:
            List of enabled Alarm objects
        """
        alarms = []
        
        with _get_db_connection() as conn:
            dict_cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            dict_cursor.execute('SELECT * FROM alarms WHERE enabled = TRUE ORDER BY time')
            rows = dict_cursor.fetchall()
            
            for row_dict in rows:
                # Create the alarm object directly from the dictionary
                alarm = Alarm()
                alarm.id = row_dict.get('id')
                alarm.time = row_dict.get('time', 0)
                alarm.enabled = True  # We know it's enabled from the query
                alarm.repeating = row_dict.get('repeating', False)
                
                # Convert days string to boolean list
                days_str = row_dict.get('days') or '0000000'
                alarm.days = [c == '1' for c in days_str]
                
                # Other fields
                alarm.is_tts = row_dict.get('is_tts', False)
                alarm.message = row_dict.get('message')
                alarm.sound_path = row_dict.get('sound_path')
                
                # Label handling
                label_value = row_dict.get('label')
                alarm.label = str(label_value) if label_value else None
                
                alarms.append(alarm)
                
            return alarms
    
    def get_one_time_alarms_for_today(self):
        """Get one-time alarms for today.
        
        Returns:
            List of one-time Alarm objects for today
        """
        alarms = []
        
        with _get_db_connection() as conn:
            dict_cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            # Get start and end of today
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            tomorrow = today + timedelta(days=1)
            
            # Convert to milliseconds
            start_time = int(today.timestamp() * 1000)
            end_time = int(tomorrow.timestamp() * 1000)
            
            dict_cursor.execute('''
            SELECT * FROM alarms 
            WHERE enabled = TRUE AND repeating = FALSE AND time >= %s AND time < %s
            ORDER BY time
            ''', (start_time, end_time))
            
            rows = dict_cursor.fetchall()
            
            for row_dict in rows:
                # Create the alarm object directly from the dictionary
                alarm = Alarm()
                alarm.id = row_dict.get('id')
                alarm.time = row_dict.get('time', 0)
                alarm.enabled = True  # We know it's enabled from the query
                alarm.repeating = False  # We know it's not repeating from the query
                
                # Convert days string to boolean list
                days_str = row_dict.get('days') or '0000000'
                alarm.days = [c == '1' for c in days_str]
                
                # Other fields
                alarm.is_tts = row_dict.get('is_tts', False)
                alarm.message = row_dict.get('message')
                alarm.sound_path = row_dict.get('sound_path')
                
                # Label handling
                label_value = row_dict.get('label')
                alarm.label = str(label_value) if label_value else None
                
                alarms.append(alarm)
                
            return alarms
    
    def add_prayer_time(self, prayer_time):
        """Add a prayer time to the database.
        
        Args:
            prayer_time: PrayerTime object to add
        
        Returns:
            PrayerTime ID
        """
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Ensure date_str is set
            if not hasattr(prayer_time, 'date_str') or not prayer_time.date_str:
                if prayer_time.time:
                    prayer_time.date_str = prayer_time.time.strftime('%Y-%m-%d')
                    logger.info(f"Setting date_str for prayer time: {prayer_time.date_str}")
                else:
                    logger.error("Cannot set date_str: prayer_time.time is None")
                    return None
            
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
                if prayer_time.time:
                    prayer_time.date_str = prayer_time.time.strftime('%Y-%m-%d')
                    logger.info(f"Setting date_str for prayer time update: {prayer_time.date_str}")
            
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
        # Use the simplified, tested version from database_direct.py
        alarm = Alarm()
        
        # Check if row is None before proceeding
        if row is None:
            return alarm
            
        try:
            # First check what type of row we're dealing with
            row_dict = None
            
            # Support different cursor types (RealDictCursor or regular cursor)
            if hasattr(row, 'items'):  # It's a dict-like object
                row_dict = row  # It's already a dict-like object
                logger.info(f"Row is a dict-like object: {type(row)}")
            else:  # It's likely a tuple
                # Convert tuple to dict based on cursor description
                logger.info(f"Row is a tuple-like object: {type(row)}")
                
                # Get the cursor description if available
                if hasattr(row, 'cursor') and hasattr(row.cursor, 'description'):
                    # This is a cleaner way to get column names
                    columns = [desc[0] for desc in row.cursor.description]
                    row_dict = dict(zip(columns, row))
                    logger.info(f"Converted tuple to dict using cursor description")
                else:
                    # Hardcoded column order based on schema - risky but last resort
                    columns = ['id', 'time', 'enabled', 'repeating', 'days', 'is_tts', 'message', 'sound_path', 'label']
                    
                    # Check if we need to truncate the list of columns
                    if len(row) < len(columns):
                        columns = columns[:len(row)]
                        
                    row_dict = dict(zip(columns, row))
                    logger.info(f"Converted tuple to dict using hardcoded column names: {columns}")
            
            # Now use the dictionary to populate the alarm object
            if row_dict is not None:
                # Basic fields
                alarm.id = row_dict.get('id')
                alarm.time = row_dict.get('time', 0)
                alarm.enabled = row_dict.get('enabled', False)
                alarm.repeating = row_dict.get('repeating', False)
                
                # Convert days string to boolean list
                days_str = row_dict.get('days', '0000000') or '0000000'
                alarm.days = [c == '1' for c in days_str]
                
                # Other fields
                alarm.is_tts = row_dict.get('is_tts', False)
                alarm.message = row_dict.get('message')
                alarm.sound_path = row_dict.get('sound_path')
                
                # Label handling - carefully extract and convert
                label_value = row_dict.get('label')
                logger.info(f"Raw label value from dict: {label_value}, type: {type(label_value)}")
                
                if label_value is None or label_value == '':
                    alarm.label = None
                    logger.info("Setting label to None (null)")
                else:
                    alarm.label = str(label_value)  # Ensure it's a string
                    logger.info(f"Setting label to: '{alarm.label}'")
            else:
                logger.error("Failed to convert row to dictionary")
        except Exception as e:
            logger.error(f"Error in _row_to_alarm: {str(e)}")
            
        # Fallback: If we couldn't get the label properly, query it directly
        if alarm.id is not None and alarm.label is None:
            try:
                # Last resort: direct query
                with _get_db_connection() as conn:
                    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                    cursor.execute('SELECT label FROM alarms WHERE id = %s', (alarm.id,))
                    label_row = cursor.fetchone()
                    
                    if label_row and label_row.get('label'):
                        alarm.label = str(label_row.get('label'))
                        logger.info(f"Set label via direct query: '{alarm.label}'")
            except Exception as e:
                logger.error(f"Error in fallback label query: {str(e)}")
                
        # Final log of the result
        logger.info(f"Final alarm object: id={alarm.id}, label={alarm.label}")
        
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
        
        # Handle date_str field
        if 'date_str' in row and row['date_str']:
            prayer_time.date_str = row['date_str']
        elif prayer_time.time:
            # If date_str is not in the database but we have time, generate it
            prayer_time.date_str = prayer_time.time.strftime('%Y-%m-%d')
            logger.info(f"Generated date_str from time field: {prayer_time.date_str}")
        
        return prayer_time
        
    # YouTube Video Management
    
    def add_youtube_video(self, youtube_video):
        """Add a YouTube video to the database.
        
        Args:
            youtube_video: YouTubeVideo object to add
        
        Returns:
            YouTubeVideo ID
        """
        try:
            with _get_db_connection() as conn:
                # Use RealDictCursor to get column names
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                
                # First check if the youtube_videos table exists
                cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_name = 'youtube_videos'
                )
                """)
                result = cursor.fetchone()
                table_exists = result and result.get('exists', False)
                
                if not table_exists:
                    logger.warning("Cannot add YouTube video: table does not exist")
                    return None
                
                cursor.execute('''
                INSERT INTO youtube_videos (url, title, enabled, position)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                ''', (
                    youtube_video.url,
                    youtube_video.title,
                    youtube_video.enabled,
                    youtube_video.position
                ))
                
                result = cursor.fetchone()
                if result:
                    youtube_video.id = result['id']
                    return youtube_video.id
                else:
                    logger.error("Failed to retrieve ID of newly inserted YouTube video")
                    return None
        except Exception as e:
            logger.error(f"Error adding YouTube video: {str(e)}")
            return None
                
    def update_youtube_video(self, youtube_video):
        """Update an existing YouTube video.
        
        Args:
            youtube_video: YouTubeVideo object to update
        """
        try:
            with _get_db_connection() as conn:
                # Use RealDictCursor for consistency
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                
                # First check if the youtube_videos table exists
                cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_name = 'youtube_videos'
                )
                """)
                result = cursor.fetchone()
                table_exists = result and result.get('exists', False)
                
                if not table_exists:
                    logger.warning("Cannot update YouTube video: table does not exist")
                    return
                
                cursor.execute('''
                UPDATE youtube_videos
                SET url = %s, title = %s, enabled = %s, position = %s
                WHERE id = %s
                ''', (
                    youtube_video.url,
                    youtube_video.title,
                    youtube_video.enabled,
                    youtube_video.position,
                    youtube_video.id
                ))
                
                logger.info(f"Successfully updated YouTube video with ID {youtube_video.id}")
        except Exception as e:
            logger.error(f"Error updating YouTube video: {str(e)}")
            
    def delete_youtube_video(self, video_id):
        """Delete a YouTube video.
        
        Args:
            video_id: ID of the YouTube video to delete
        """
        try:
            with _get_db_connection() as conn:
                # Use RealDictCursor for consistency
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                
                # First check if the youtube_videos table exists
                cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_name = 'youtube_videos'
                )
                """)
                result = cursor.fetchone()
                table_exists = result and result.get('exists', False)
                
                if not table_exists:
                    logger.warning("Cannot delete YouTube video: table does not exist")
                    return
                
                cursor.execute('DELETE FROM youtube_videos WHERE id = %s', (video_id,))
                logger.info(f"Successfully deleted YouTube video with ID {video_id}")
        except Exception as e:
            logger.error(f"Error deleting YouTube video: {str(e)}")
            
    def get_youtube_video(self, video_id):
        """Get a YouTube video by ID.
        
        Args:
            video_id: ID of the YouTube video to get
        
        Returns:
            YouTubeVideo object or None
        """
        try:
            with _get_db_connection() as conn:
                dict_cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                
                # First check if the youtube_videos table exists
                dict_cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_name = 'youtube_videos'
                )
                """)
                result = dict_cursor.fetchone()
                table_exists = result and result.get('exists', False)
                
                if not table_exists:
                    logger.warning("Cannot get YouTube video: table does not exist")
                    return None
                
                dict_cursor.execute('SELECT * FROM youtube_videos WHERE id = %s', (video_id,))
                row = dict_cursor.fetchone()
                
                if row:
                    return self._row_to_youtube_video(row)
                else:
                    return None
        except Exception as e:
            logger.error(f"Error getting YouTube video {video_id}: {str(e)}")
            return None
                
    def get_all_youtube_videos(self):
        """Get all YouTube videos.
        
        Returns:
            List of YouTubeVideo objects
        """
        try:
            with _get_db_connection() as conn:
                dict_cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                
                # First check if the youtube_videos table exists
                dict_cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_name = 'youtube_videos'
                )
                """)
                result = dict_cursor.fetchone()
                table_exists = result and result.get('exists', False)
                
                if not table_exists:
                    logger.warning("YouTube videos table does not exist")
                    return []
                
                dict_cursor.execute('SELECT * FROM youtube_videos ORDER BY position')
                rows = dict_cursor.fetchall()
                
                return [self._row_to_youtube_video(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting YouTube videos: {str(e)}")
            return []
            
    def get_enabled_youtube_videos(self):
        """Get all enabled YouTube videos.
        
        Returns:
            List of enabled YouTubeVideo objects
        """
        try:
            with _get_db_connection() as conn:
                dict_cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                
                # First check if the youtube_videos table exists
                dict_cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_name = 'youtube_videos'
                )
                """)
                result = dict_cursor.fetchone()
                table_exists = result and result.get('exists', False)
                
                if not table_exists:
                    logger.warning("YouTube videos table does not exist")
                    return []
                
                dict_cursor.execute('SELECT * FROM youtube_videos WHERE enabled = TRUE ORDER BY position')
                rows = dict_cursor.fetchall()
                
                return [self._row_to_youtube_video(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting enabled YouTube videos: {str(e)}")
            return []
            
    def reorder_youtube_videos(self, video_ids):
        """Reorder YouTube videos.
        
        Args:
            video_ids: List of video IDs in the desired order
        """
        try:
            with _get_db_connection() as conn:
                # Use RealDictCursor for consistency
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                
                # First check if the youtube_videos table exists
                cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_name = 'youtube_videos'
                )
                """)
                result = cursor.fetchone()
                table_exists = result and result.get('exists', False)
                
                if not table_exists:
                    logger.warning("Cannot reorder videos: YouTube videos table does not exist")
                    return
                
                # Update positions in a transaction
                for position, video_id in enumerate(video_ids):
                    cursor.execute('''
                    UPDATE youtube_videos
                    SET position = %s
                    WHERE id = %s
                    ''', (position, video_id))
                
                logger.info(f"Successfully reordered {len(video_ids)} YouTube videos")
        except Exception as e:
            logger.error(f"Error reordering YouTube videos: {str(e)}")
                
    def _row_to_youtube_video(self, row):
        """Convert a database row to a YouTubeVideo object.
        
        Args:
            row: Database row
        
        Returns:
            YouTubeVideo object
        """
        from models import YouTubeVideo
        
        video = YouTubeVideo()
        
        # Check if row is None before proceeding
        if row is None:
            return video
            
        video.id = row['id']
        video.url = row['url']
        video.title = row['title']
        video.enabled = row['enabled']
        video.position = row['position']
        video.created_at = row.get('created_at')
        
        return video