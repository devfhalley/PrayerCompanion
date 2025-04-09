#!/usr/bin/env python3
"""
Debug script for Raspberry Pi Prayer Alarm System.
This script provides debugging functions for troubleshooting database issues.
"""

import os
import sys
import psycopg2
import psycopg2.extras
import json
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_direct_connection():
    """Get a direct database connection."""
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        raise Exception("DATABASE_URL environment variable not set")
        
    conn = psycopg2.connect(db_url)
    return conn

def get_alarm_raw(alarm_id):
    """Get raw alarm data directly from the database."""
    conn = get_direct_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    # Get raw data
    cursor.execute('SELECT * FROM alarms WHERE id = %s', (alarm_id,))
    row = cursor.fetchone()
    
    if not row:
        logger.error(f"Alarm {alarm_id} not found")
        return None
        
    # Log column descriptions
    columns = [desc[0] for desc in cursor.description]
    logger.info(f"Columns: {columns}")
    
    # Convert RealDictRow to regular dict for better printing
    result = dict(row)
    
    # Close resources
    cursor.close()
    conn.close()
    
    return result

def update_alarm_label(alarm_id, label):
    """Update an alarm label directly in the database."""
    conn = get_direct_connection()
    cursor = conn.cursor()
    
    cursor.execute('UPDATE alarms SET label = %s WHERE id = %s', (label, alarm_id))
    conn.commit()
    
    logger.info(f"Updated alarm {alarm_id} with label '{label}'")
    
    # Close resources
    cursor.close()
    conn.close()

def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python debug.py <command> [args...]")
        print("Commands:")
        print("  get_alarm <alarm_id> - Get raw alarm data")
        print("  update_label <alarm_id> <label> - Update alarm label")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "get_alarm":
        if len(sys.argv) < 3:
            print("Usage: python debug.py get_alarm <alarm_id>")
            sys.exit(1)
        
        alarm_id = int(sys.argv[2])
        result = get_alarm_raw(alarm_id)
        
        if result:
            print(json.dumps(result, indent=2, default=str))
        else:
            print(f"No alarm found with ID {alarm_id}")
    
    elif command == "update_label":
        if len(sys.argv) < 4:
            print("Usage: python debug.py update_label <alarm_id> <label>")
            sys.exit(1)
        
        alarm_id = int(sys.argv[2])
        label = sys.argv[3]
        
        update_alarm_label(alarm_id, label)
        print(f"Updated alarm {alarm_id} with label '{label}'")
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main()