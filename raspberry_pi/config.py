#!/usr/bin/env python3
"""
Configuration module for Raspberry Pi Prayer Alarm System.
This module defines the configuration for the application.
"""

import os

class Config:
    """Configuration class."""
    
    # Prayer API configuration
    PRAYER_CITY = "Jakarta"
    PRAYER_COUNTRY = "Indonesia"
    PRAYER_CALCULATION_METHOD = 11  # 11 is for Indonesian Ministry of Religious Affairs
    
    # Audio configuration
    DEFAULT_ADHAN_SOUND = os.path.join(os.path.dirname(__file__), "sounds", "default_adhan.mp3")
    DEFAULT_ALARM_SOUND = os.path.join(os.path.dirname(__file__), "sounds", "default_alarm.mp3")
    
    # Make sure the sounds directory exists
    os.makedirs(os.path.join(os.path.dirname(__file__), "sounds"), exist_ok=True)
    
    # Download default sounds if they don't exist
    if not os.path.exists(DEFAULT_ADHAN_SOUND):
        try:
            import urllib.request
            print("Downloading default adhan sound...")
            urllib.request.urlretrieve(
                "https://cdn.islamway.net/adans/1.mp3",
                DEFAULT_ADHAN_SOUND
            )
            print("Default adhan sound downloaded.")
        except Exception as e:
            print(f"Error downloading default adhan sound: {str(e)}")
    
    if not os.path.exists(DEFAULT_ALARM_SOUND):
        try:
            import urllib.request
            print("Downloading default alarm sound...")
            urllib.request.urlretrieve(
                "https://www.soundjay.com/clock/sounds/alarm-clock-01.mp3",
                DEFAULT_ALARM_SOUND
            )
            print("Default alarm sound downloaded.")
        except Exception as e:
            print(f"Error downloading default alarm sound: {str(e)}")
