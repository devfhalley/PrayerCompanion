"""
Initial database schema for PostgreSQL migration from SQLite.
This migration creates the initial tables for the Prayer Alarm System.
"""

def up(conn):
    """
    Apply the initial schema migration.
    
    Args:
        conn: PostgreSQL database connection
    """
    cur = conn.cursor()
    
    # Create migrations table to track applied migrations
    cur.execute('''
    CREATE TABLE IF NOT EXISTS migrations (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create alarms table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS alarms (
        id SERIAL PRIMARY KEY,
        time BIGINT NOT NULL,
        enabled BOOLEAN NOT NULL DEFAULT TRUE,
        repeating BOOLEAN NOT NULL DEFAULT FALSE,
        days BOOLEAN[] DEFAULT ARRAY[false, false, false, false, false, false, false],
        sound_path TEXT,
        is_tts BOOLEAN NOT NULL DEFAULT FALSE,
        message TEXT,
        label TEXT
    )
    ''')
    
    # Create prayer_times table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS prayer_times (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        time TIMESTAMP NOT NULL,
        date_str TEXT NOT NULL,
        enabled BOOLEAN NOT NULL DEFAULT TRUE,
        custom_sound TEXT
    )
    ''')
    
    conn.commit()
    cur.close()

def down(conn):
    """
    Revert the initial schema migration.
    Warning: This will delete all data in the tables!
    
    Args:
        conn: PostgreSQL database connection
    """
    cur = conn.cursor()
    
    # Drop tables in reverse order of creation
    cur.execute('DROP TABLE IF EXISTS prayer_times')
    cur.execute('DROP TABLE IF EXISTS alarms')
    cur.execute('DROP TABLE IF EXISTS migrations')
    
    conn.commit()
    cur.close()