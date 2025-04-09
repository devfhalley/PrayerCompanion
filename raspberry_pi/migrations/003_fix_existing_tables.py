"""
Fix existing tables to match the expected schema.
This migration adds missing columns and adjusts data types.
"""

def up(conn):
    """
    Apply the migration: add missing columns and fix data types.
    
    Args:
        conn: PostgreSQL database connection
    """
    cur = conn.cursor()
    
    # Check if date_str column exists in prayer_times
    cur.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.columns 
            WHERE table_name = 'prayer_times' AND column_name = 'date_str'
        )
    """)
    date_str_exists = cur.fetchone()[0]
    
    if not date_str_exists:
        # Add date_str column to prayer_times table
        cur.execute("""
            ALTER TABLE prayer_times 
            ADD COLUMN date_str TEXT
        """)
        
        # Update the date_str values for existing records
        cur.execute("""
            UPDATE prayer_times
            SET date_str = to_char(time, 'YYYY-MM-DD')
        """)
        
        # Make date_str NOT NULL after setting values
        cur.execute("""
            ALTER TABLE prayer_times 
            ALTER COLUMN date_str SET NOT NULL
        """)
    
    # Check if days column is the right type
    cur.execute("""
        SELECT data_type 
        FROM information_schema.columns 
        WHERE table_name = 'alarms' AND column_name = 'days'
    """)
    days_type = cur.fetchone()[0]
    
    if days_type != 'ARRAY':
        # Create a new days_array column
        cur.execute("""
            ALTER TABLE alarms 
            ADD COLUMN days_array BOOLEAN[] DEFAULT ARRAY[false, false, false, false, false, false, false]
        """)
        
        # Convert existing string to boolean array
        cur.execute("""
            UPDATE alarms 
            SET days_array = ARRAY[
                SUBSTRING(days, 1, 1) = '1',
                SUBSTRING(days, 2, 1) = '1',
                SUBSTRING(days, 3, 1) = '1', 
                SUBSTRING(days, 4, 1) = '1',
                SUBSTRING(days, 5, 1) = '1',
                SUBSTRING(days, 6, 1) = '1',
                SUBSTRING(days, 7, 1) = '1'
            ]
            WHERE days IS NOT NULL
        """)
        
        # Rename columns
        cur.execute("""
            ALTER TABLE alarms 
            RENAME COLUMN days TO days_old
        """)
        
        cur.execute("""
            ALTER TABLE alarms 
            RENAME COLUMN days_array TO days
        """)
    
    conn.commit()
    cur.close()

def down(conn):
    """
    Revert the migration: restore original schema.
    
    Args:
        conn: PostgreSQL database connection
    """
    cur = conn.cursor()
    
    # Check if date_str column exists
    cur.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.columns 
            WHERE table_name = 'prayer_times' AND column_name = 'date_str'
        )
    """)
    date_str_exists = cur.fetchone()[0]
    
    if date_str_exists:
        # Remove date_str column
        cur.execute("""
            ALTER TABLE prayer_times 
            DROP COLUMN date_str
        """)
    
    # Check if days_old column exists
    cur.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.columns 
            WHERE table_name = 'alarms' AND column_name = 'days_old'
        )
    """)
    days_old_exists = cur.fetchone()[0]
    
    if days_old_exists:
        # Rename days back to days_array
        cur.execute("""
            ALTER TABLE alarms 
            RENAME COLUMN days TO days_array
        """)
        
        # Rename days_old back to days
        cur.execute("""
            ALTER TABLE alarms 
            RENAME COLUMN days_old TO days
        """)
        
        # Drop the days_array column
        cur.execute("""
            ALTER TABLE alarms 
            DROP COLUMN days_array
        """)
    
    conn.commit()
    cur.close()