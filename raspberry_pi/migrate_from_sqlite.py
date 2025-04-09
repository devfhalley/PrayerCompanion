#!/usr/bin/env python3
"""
Script to migrate data from SQLite to PostgreSQL.
This script exports data from SQLite database and imports it into PostgreSQL.
"""

import os
import sys
import sqlite3
import psycopg2
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('sqlite_to_pg_migration')

def get_sqlite_connection(db_path):
    """
    Get a connection to the SQLite database.
    
    Args:
        db_path: Path to SQLite database file
        
    Returns:
        SQLite connection
    """
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        logger.error(f"Error connecting to SQLite database: {e}")
        sys.exit(1)

def get_pg_connection():
    """
    Get a connection to the PostgreSQL database.
    
    Returns:
        PostgreSQL connection
    """
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        # Attempt to build connection string from individual environment variables
        user = os.environ.get('PGUSER')
        password = os.environ.get('PGPASSWORD')
        host = os.environ.get('PGHOST')
        port = os.environ.get('PGPORT')
        database = os.environ.get('PGDATABASE')
        
        if not all([user, password, host, port, database]):
            logger.error("Database connection information missing. Please set DATABASE_URL or individual PostgreSQL environment variables")
            sys.exit(1)
            
        database_url = f"postgresql://{user}:{password}@{host}:{port}/{database}"
    
    try:
        return psycopg2.connect(database_url)
    except psycopg2.Error as e:
        logger.error(f"Error connecting to PostgreSQL database: {e}")
        sys.exit(1)

def dump_sqlite_data(sqlite_conn, backup_dir):
    """
    Dump data from SQLite tables to JSON files.
    
    Args:
        sqlite_conn: SQLite connection
        backup_dir: Directory to save backup files
        
    Returns:
        Dictionary with table data
    """
    cursor = sqlite_conn.cursor()
    data = {}
    
    # Get list of tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row['name'] for row in cursor.fetchall()]
    
    # Create backup directory if it doesn't exist
    os.makedirs(backup_dir, exist_ok=True)
    
    # Dump each table to JSON
    for table in tables:
        logger.info(f"Exporting table: {table}")
        cursor.execute(f"SELECT * FROM {table}")
        rows = [dict(row) for row in cursor.fetchall()]
        data[table] = rows
        
        # Save to JSON file
        backup_file = os.path.join(backup_dir, f"{table}.json")
        with open(backup_file, 'w') as f:
            json.dump(rows, f, indent=2)
        logger.info(f"Saved {len(rows)} rows to {backup_file}")
    
    return data

def create_pg_schema(pg_conn):
    """
    Create PostgreSQL schema using the migration script.
    
    Args:
        pg_conn: PostgreSQL connection
    """
    # Import the migration script
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'migrations'))
    try:
        import_001_initial_schema = __import__('001_initial_schema')
        
        # Apply the migration
        import_001_initial_schema.up(pg_conn)
        logger.info("Created PostgreSQL schema")
    except Exception as e:
        logger.error(f"Error creating PostgreSQL schema: {e}")
        pg_conn.rollback()
        sys.exit(1)

def import_to_pg(pg_conn, data):
    """
    Import data to PostgreSQL.
    
    Args:
        pg_conn: PostgreSQL connection
        data: Dictionary with table data
    """
    cursor = pg_conn.cursor()
    
    # Import alarms
    if 'alarms' in data:
        logger.info(f"Importing {len(data['alarms'])} alarms")
        for alarm in data['alarms']:
            try:
                cursor.execute('''
                INSERT INTO alarms (id, time, enabled, repeating, days, sound_path, is_tts, message, label)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', (
                    alarm['id'],
                    alarm['time'],
                    bool(alarm.get('enabled', 1)),
                    bool(alarm.get('repeating', 0)),
                    [bool(int(day)) for day in json.loads(alarm.get('days', '[]'))] if alarm.get('days') else [False] * 7,
                    alarm.get('sound_path'),
                    bool(alarm.get('is_tts', 0)),
                    alarm.get('message'),
                    alarm.get('label')
                ))
            except Exception as e:
                logger.error(f"Error importing alarm {alarm.get('id')}: {e}")
    
    # Import prayer_times
    if 'prayer_times' in data:
        logger.info(f"Importing {len(data['prayer_times'])} prayer times")
        for pt in data['prayer_times']:
            try:
                cursor.execute('''
                INSERT INTO prayer_times (id, name, time, date_str, enabled, custom_sound)
                VALUES (%s, %s, %s, %s, %s, %s)
                ''', (
                    pt['id'],
                    pt['name'],
                    pt['time'],
                    pt['date_str'],
                    bool(pt.get('enabled', 1)),
                    pt.get('custom_sound')
                ))
            except Exception as e:
                logger.error(f"Error importing prayer time {pt.get('id')}: {e}")
    
    # Commit changes
    pg_conn.commit()
    logger.info("Data import completed")

def main():
    parser = argparse.ArgumentParser(description='Migrate data from SQLite to PostgreSQL')
    parser.add_argument('--sqlite-db', default='prayer_alarm.db', help='Path to SQLite database file')
    parser.add_argument('--backup-dir', default='db_backup', help='Directory to save database backup')
    parser.add_argument('--dry-run', action='store_true', help='Export data without importing to PostgreSQL')
    args = parser.parse_args()
    
    # Resolve paths
    sqlite_db_path = os.path.join(os.path.dirname(__file__), args.sqlite_db)
    backup_dir = os.path.join(os.path.dirname(__file__), args.backup_dir, datetime.now().strftime('%Y%m%d_%H%M%S'))
    
    # Check if SQLite database exists
    if not os.path.exists(sqlite_db_path):
        logger.error(f"SQLite database file not found: {sqlite_db_path}")
        sys.exit(1)
    
    # Connect to SQLite
    sqlite_conn = get_sqlite_connection(sqlite_db_path)
    
    try:
        # Dump SQLite data
        logger.info(f"Dumping SQLite data from {sqlite_db_path}")
        data = dump_sqlite_data(sqlite_conn, backup_dir)
        
        if args.dry_run:
            logger.info("Dry run complete. Data exported to backup directory.")
            return
        
        # Connect to PostgreSQL
        pg_conn = get_pg_connection()
        
        try:
            # Create PostgreSQL schema
            create_pg_schema(pg_conn)
            
            # Import data to PostgreSQL
            import_to_pg(pg_conn, data)
            
            logger.info("Migration completed successfully")
        finally:
            pg_conn.close()
    finally:
        sqlite_conn.close()

if __name__ == '__main__':
    main()