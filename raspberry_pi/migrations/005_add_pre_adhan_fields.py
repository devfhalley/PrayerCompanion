#!/usr/bin/env python3
"""
Migration script to add pre-adhan announcement fields to prayer_times table.
"""

import psycopg2
import logging

logger = logging.getLogger(__name__)

def up(conn):
    """Add pre-adhan announcement fields to prayer_times table (up migration)."""
    logger.info("Running migration: Adding pre-adhan announcement fields to prayer_times table")
    
    try:
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
        
        # Commit changes will be handled by the migration runner
        
        logger.info("Migration for pre-adhan fields completed successfully")
    except Exception as e:
        logger.error(f"Error in migration for pre-adhan fields: {str(e)}")
        raise

def down(conn):
    """Remove pre-adhan announcement fields from prayer_times table (down migration)."""
    logger.info("Running rollback: Removing pre-adhan announcement fields from prayer_times table")
    
    try:
        cursor = conn.cursor()
        
        # Check if pre_adhan_10_min column exists
        cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'prayer_times' AND column_name = 'pre_adhan_10_min'
        """)
        
        if cursor.fetchone():
            # Remove pre_adhan_10_min column
            logger.info("Removing 'pre_adhan_10_min' column from prayer_times table")
            cursor.execute("""
            ALTER TABLE prayer_times
            DROP COLUMN pre_adhan_10_min
            """)
        
        # Check if pre_adhan_5_min column exists
        cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'prayer_times' AND column_name = 'pre_adhan_5_min'
        """)
        
        if cursor.fetchone():
            # Remove pre_adhan_5_min column
            logger.info("Removing 'pre_adhan_5_min' column from prayer_times table")
            cursor.execute("""
            ALTER TABLE prayer_times
            DROP COLUMN pre_adhan_5_min
            """)
        
        # Check if tahrim_sound column exists
        cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'prayer_times' AND column_name = 'tahrim_sound'
        """)
        
        if cursor.fetchone():
            # Remove tahrim_sound column
            logger.info("Removing 'tahrim_sound' column from prayer_times table")
            cursor.execute("""
            ALTER TABLE prayer_times
            DROP COLUMN tahrim_sound
            """)
        
        # Commit changes will be handled by the migration runner
        
        logger.info("Rollback for pre-adhan fields completed successfully")
    except Exception as e:
        logger.error(f"Error in rollback for pre-adhan fields: {str(e)}")
        raise