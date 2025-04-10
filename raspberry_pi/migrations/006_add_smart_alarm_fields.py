#!/usr/bin/env python3
"""
Migration to add smart alarm fields to the alarms table.
"""

def up(conn):
    """
    Add smart alarm fields to the alarms table:
    - smart_alarm: boolean flag to enable/disable smart alarm features
    - volume_start: starting volume level for gradual increase (0-100)
    - volume_end: target volume level for gradual increase (0-100)
    - volume_increment: step size for gradual increase
    - ramp_duration: duration in seconds for the volume ramp
    """
    cur = conn.cursor()
    
    # Add smart_alarm flag
    cur.execute('ALTER TABLE alarms ADD COLUMN IF NOT EXISTS smart_alarm BOOLEAN DEFAULT FALSE')
    
    # Add volume_start
    cur.execute('ALTER TABLE alarms ADD COLUMN IF NOT EXISTS volume_start INTEGER DEFAULT 20')
    
    # Add volume_end
    cur.execute('ALTER TABLE alarms ADD COLUMN IF NOT EXISTS volume_end INTEGER DEFAULT 100')
    
    # Add volume_increment
    cur.execute('ALTER TABLE alarms ADD COLUMN IF NOT EXISTS volume_increment INTEGER DEFAULT 5')
    
    # Add ramp_duration (in seconds)
    cur.execute('ALTER TABLE alarms ADD COLUMN IF NOT EXISTS ramp_duration INTEGER DEFAULT 60')
    
    conn.commit()

def down(conn):
    """
    Remove smart alarm fields from the alarms table.
    """
    cur = conn.cursor()
    
    # Remove all smart alarm fields
    cur.execute('ALTER TABLE alarms DROP COLUMN IF EXISTS smart_alarm')
    cur.execute('ALTER TABLE alarms DROP COLUMN IF EXISTS volume_start')
    cur.execute('ALTER TABLE alarms DROP COLUMN IF EXISTS volume_end')
    cur.execute('ALTER TABLE alarms DROP COLUMN IF EXISTS volume_increment')
    cur.execute('ALTER TABLE alarms DROP COLUMN IF EXISTS ramp_duration')
    
    conn.commit()