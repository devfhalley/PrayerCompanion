#!/usr/bin/env python3
"""
Prayer scheduler module for Raspberry Pi Prayer Alarm System.
This module handles fetching and scheduling prayer times.
"""

import logging
import threading
import time
import requests
import json
from datetime import datetime, timedelta
import schedule

from database import get_db
from models import PrayerTime
from config import Config

logger = logging.getLogger(__name__)

class PrayerScheduler:
    """Handles fetching and scheduling prayer times."""
    
    def __init__(self, audio_player):
        """Initialize the prayer scheduler.
        
        Args:
            audio_player: An instance of AudioPlayer class
        """
        self.audio_player = audio_player
        self.running = False
        self.thread = None
        self.db = get_db()
        self.lock = threading.Lock()
        
        # Get location from config
        self.city = Config.PRAYER_CITY
        self.country = Config.PRAYER_COUNTRY
        self.method = Config.PRAYER_CALCULATION_METHOD  # 11 for Indonesian Ministry of Religious Affairs
        
        # API endpoints
        self.api_url = "http://api.aladhan.com/v1/timingsByCity"
    
    def start(self):
        """Start the prayer scheduler."""
        if self.running:
            logger.warning("Prayer scheduler already running")
            return
        
        logger.info("Starting prayer scheduler")
        self.running = True
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()
        
        # Immediately fetch today's prayer times
        self.fetch_prayer_times()
    
    def stop(self):
        """Stop the prayer scheduler."""
        logger.info("Stopping prayer scheduler")
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
            self.thread = None
    
    def _run(self):
        """Main loop for the prayer scheduler."""
        # Schedule daily refresh at midnight
        schedule.every().day.at("00:01").do(self.fetch_prayer_times)
        
        # Check for upcoming prayers
        schedule.every(30).seconds.do(self._check_upcoming_prayers)
        
        while self.running:
            schedule.run_pending()
            time.sleep(1)
    
    def fetch_prayer_times(self, days=7):
        """Fetch prayer times for the next few days.
        
        Args:
            days: Number of days to fetch, defaults to 7
        """
        logger.info(f"Fetching prayer times for the next {days} days")
        
        today = datetime.now().date()
        
        for i in range(days):
            date = today + timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            
            # Check if we already have prayer times for this date
            existing_times = self.db.get_prayer_times_by_date(date_str)
            if existing_times:
                logger.info(f"Prayer times for {date_str} already exist in database")
                continue
            
            logger.info(f"Fetching prayer times for {date_str}")
            
            try:
                response = requests.get(
                    self.api_url,
                    params={
                        "city": self.city,
                        "country": self.country,
                        "method": self.method,
                        "date": date_str
                    }
                )
                
                if response.status_code != 200:
                    logger.error(f"Failed to fetch prayer times: HTTP {response.status_code}")
                    continue
                
                data = response.json()
                
                if data.get("code") != 200 or data.get("status") != "OK":
                    logger.error(f"API returned error: {data.get('data')}")
                    continue
                
                timings = data.get("data", {}).get("timings", {})
                
                # Process prayer times
                for prayer_name, time_str in timings.items():
                    # Skip meta-timings like Sunrise, Sunset, etc.
                    if prayer_name not in ['Fajr', 'Dhuhr', 'Asr', 'Maghrib', 'Isha']:
                        continue
                    
                    # Parse time
                    prayer_time = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
                    
                    # Create PrayerTime object
                    prayer = PrayerTime(
                        name=prayer_name,
                        time=prayer_time,
                        enabled=True
                    )
                    
                    # Save to database
                    self.db.add_prayer_time(prayer)
                
                logger.info(f"Successfully saved prayer times for {date_str}")
            
            except Exception as e:
                logger.error(f"Error fetching prayer times: {str(e)}")
    
    def refresh_prayer_times(self):
        """Force refresh of prayer times."""
        logger.info("Forcing refresh of prayer times")
        
        # Clear existing prayer times for today and future
        today = datetime.now().date()
        date_str = today.strftime("%Y-%m-%d")
        self.db.delete_prayer_times_from_date(date_str)
        
        # Fetch fresh prayer times
        self.fetch_prayer_times()
    
    def _check_upcoming_prayers(self):
        """Check for upcoming prayers and play adhan if it's time."""
        with self.lock:
            now = datetime.now()
            
            # Get the next prayer
            next_prayer = self.db.get_next_prayer_time()
            
            if not next_prayer:
                return
            
            # Check if it's time for adhan (within 1 minute)
            time_diff = (next_prayer.time - now).total_seconds()
            
            if 0 <= time_diff <= 60:  # Within 60 seconds
                logger.info(f"It's time for {next_prayer.name} prayer")
                
                # Play the adhan with highest priority
                if next_prayer.custom_sound:
                    logger.info(f"Using custom adhan sound for {next_prayer.name}")
                    self.audio_player.play_adhan(next_prayer.custom_sound)
                else:
                    logger.info(f"Using default adhan sound for {next_prayer.name}")
                    self.audio_player.play_adhan(Config.DEFAULT_ADHAN_SOUND)
                    
                    # After adhan, announce the prayer using TTS
                    # This will be queued with the same adhan priority
                    self.audio_player.play_tts(f"It's time for {next_prayer.name} prayer", priority=self.audio_player.PRIORITY_ADHAN)
                
                # Broadcast adhan playing message to WebSocket clients
                try:
                    from websocket_server import broadcast_message
                    import json
                    message = {
                        'type': 'adhan_playing',
                        'prayer': next_prayer.name,
                        'time': next_prayer.time.strftime('%H:%M')
                    }
                    broadcast_message(json.dumps(message))
                except Exception as e:
                    logger.warning(f"Error broadcasting adhan message: {str(e)}")
