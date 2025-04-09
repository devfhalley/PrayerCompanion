"""
Add YouTube videos table to store video URLs and settings.
This migration creates a new table for storing YouTube video URLs and settings.
"""

def up(conn):
    """
    Apply the migration: add youtube_videos table.
    
    Args:
        conn: PostgreSQL database connection
    """
    cur = conn.cursor()
    
    # Create youtube_videos table
    cur.execute('''
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
    cur.close()

def down(conn):
    """
    Revert the migration: remove youtube_videos table.
    
    Args:
        conn: PostgreSQL database connection
    """
    cur = conn.cursor()
    
    # Drop youtube_videos table
    cur.execute('DROP TABLE IF EXISTS youtube_videos')
    
    conn.commit()
    cur.close()