#!/usr/bin/env python3
"""
Test script to verify adhan scheduling.
Sets up a temporary prayer time in the near future to test adhan playback.
"""

import sys
import os
import time
import logging
from datetime import datetime, timedelta

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from raspberry_pi.database import get_db
from raspberry_pi.models import PrayerTime
from raspberry_pi.audio_player import AudioPlayer
from raspberry_pi.prayer_scheduler import PrayerScheduler

def main():
    """Create a test prayer time and verify adhan playback."""
    logger.info("Starting adhan schedule test")
    
    # Create AudioPlayer instance
    audio_player = AudioPlayer()
    audio_player.start_player_thread()
    
    # Create database connection
    db = get_db()
    
    # Create a test prayer time 30 seconds from now
    now = datetime.now()
    test_prayer_time = now + timedelta(seconds=30)
    
    prayer_name = "Test"
    date_str = now.strftime("%Y-%m-%d")
    
    logger.info(f"Creating test prayer time: {prayer_name} at {test_prayer_time}")
    
    # Create PrayerTime object
    prayer = PrayerTime(
        name=prayer_name,
        time=test_prayer_time,
        enabled=True,
        date_str=date_str
    )
    
    # Save to database
    prayer_id = db.add_prayer_time(prayer)
    logger.info(f"Created prayer time with ID: {prayer_id}")
    
    # Create and start prayer scheduler
    scheduler = PrayerScheduler(audio_player)
    scheduler.start()
    
    logger.info("Prayer scheduler started")
    logger.info(f"Waiting for adhan to play at {test_prayer_time}")
    
    # Wait for 1 minute to see if adhan plays
    try:
        for i in range(60):
            time.sleep(1)
            now = datetime.now()
            if now > test_prayer_time:
                seconds_past = (now - test_prayer_time).total_seconds()
                logger.info(f"Prayer time passed {seconds_past:.1f} seconds ago")
            else:
                seconds_left = (test_prayer_time - now).total_seconds()
                logger.info(f"Prayer time in {seconds_left:.1f} seconds")
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    
    # Clean up
    scheduler.stop()
    logger.info("Prayer scheduler stopped")
    
    # Delete test prayer time
    try:
        from raspberry_pi.database_direct import get_connection
        connection = get_connection()
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM prayer_times WHERE name = %s AND date_str = %s", 
                           (prayer_name, date_str))
        connection.commit()
        logger.info("Deleted test prayer time")
    except Exception as e:
        logger.error(f"Error deleting test prayer time: {str(e)}")
    
    logger.info("Test completed")

if __name__ == "__main__":
    main()