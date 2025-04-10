#!/usr/bin/env python3
"""
Migration script to add pre-adhan announcement fields to prayer_times table.
"""

import psycopg2
import sqlite3
import os
import logging

logger = logging.getLogger(__name__)

def migrate():
    """Add pre-adhan announcement fields to prayer_times table."""
    logger.info("Running migration: Adding pre-adhan announcement fields to prayer_times table")
    
    # Check if using PostgreSQL or SQLite
    if 'DATABASE_URL' in os.environ:
        # PostgreSQL
        migrate_postgresql()
    else:
        # SQLite
        migrate_sqlite()
    
    logger.info("Migration completed: Added pre-adhan announcement fields to prayer_times table")

def migrate_postgresql():
    """Run migration for PostgreSQL database."""
    logger.info("Running PostgreSQL migration for pre-adhan fields")
    
    try:
        # Connect to PostgreSQL database
        conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
        cursor = conn.cursor()
        
        # Check if pre_adhan_10_min column exists
        cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'prayer_times' AND column_name = 'pre_adhan_10_min'
        """)
        
        if not cursor.fetchone():
            # Add pre_adhan_10_min column
            logger.info("Adding 'pre_adhan_10_min' column to prayer_times table")
            cursor.execute("""
            ALTER TABLE prayer_times
            ADD COLUMN pre_adhan_10_min TEXT
            """)
        
        # Check if pre_adhan_5_min column exists
        cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'prayer_times' AND column_name = 'pre_adhan_5_min'
        """)
        
        if not cursor.fetchone():
            # Add pre_adhan_5_min column
            logger.info("Adding 'pre_adhan_5_min' column to prayer_times table")
            cursor.execute("""
            ALTER TABLE prayer_times
            ADD COLUMN pre_adhan_5_min TEXT
            """)
        
        # Check if tahrim_sound column exists
        cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'prayer_times' AND column_name = 'tahrim_sound'
        """)
        
        if not cursor.fetchone():
            # Add tahrim_sound column
            logger.info("Adding 'tahrim_sound' column to prayer_times table")
            cursor.execute("""
            ALTER TABLE prayer_times
            ADD COLUMN tahrim_sound TEXT
            """)
        
        # Commit changes
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info("PostgreSQL migration for pre-adhan fields completed successfully")
    except Exception as e:
        logger.error(f"Error in PostgreSQL migration for pre-adhan fields: {str(e)}")
        raise

def migrate_sqlite():
    """Run migration for SQLite database."""
    logger.info("Running SQLite migration for pre-adhan fields")
    
    try:
        # Connect to SQLite database
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        # Get column names from prayer_times table
        cursor.execute("PRAGMA table_info(prayer_times)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Add pre_adhan_10_min column if it doesn't exist
        if 'pre_adhan_10_min' not in columns:
            logger.info("Adding 'pre_adhan_10_min' column to prayer_times table")
            cursor.execute("ALTER TABLE prayer_times ADD COLUMN pre_adhan_10_min TEXT")
        
        # Add pre_adhan_5_min column if it doesn't exist
        if 'pre_adhan_5_min' not in columns:
            logger.info("Adding 'pre_adhan_5_min' column to prayer_times table")
            cursor.execute("ALTER TABLE prayer_times ADD COLUMN pre_adhan_5_min TEXT")
        
        # Add tahrim_sound column if it doesn't exist
        if 'tahrim_sound' not in columns:
            logger.info("Adding 'tahrim_sound' column to prayer_times table")
            cursor.execute("ALTER TABLE prayer_times ADD COLUMN tahrim_sound TEXT")
        
        # Commit changes
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info("SQLite migration for pre-adhan fields completed successfully")
    except Exception as e:
        logger.error(f"Error in SQLite migration for pre-adhan fields: {str(e)}")
        raise

if __name__ == "__main__":
    migrate()