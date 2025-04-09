"""
Add priority column to alarms table.
This migration adds a priority field to prioritize alarms.
"""

def up(conn):
    """
    Apply the migration: add priority column.
    
    Args:
        conn: PostgreSQL database connection
    """
    cur = conn.cursor()
    
    # Add priority column to alarms table
    cur.execute('ALTER TABLE alarms ADD COLUMN priority INT DEFAULT 0')
    
    conn.commit()
    cur.close()

def down(conn):
    """
    Revert the migration: remove priority column.
    
    Args:
        conn: PostgreSQL database connection
    """
    cur = conn.cursor()
    
    # Remove priority column from alarms table
    cur.execute('ALTER TABLE alarms DROP COLUMN IF EXISTS priority')
    
    conn.commit()
    cur.close()