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
    if not os.path.exists(DEFAULT_ALARM_SOUND):
        try:
            import urllib.request
            import ssl
            # Create a context that doesn't check certificates
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            
            print("Downloading default alarm sound...")
            urllib.request.urlretrieve(
                "https://www.soundjay.com/clock/sounds/alarm-clock-01.mp3",
                DEFAULT_ALARM_SOUND
            )
            print("Default alarm sound downloaded.")
        except Exception as e:
            print(f"Error downloading default alarm sound: {str(e)}")
            
    # Create a simple default adhan sound instead of trying to download one
    if not os.path.exists(DEFAULT_ADHAN_SOUND):
        try:
            from gtts import gTTS
            print("Creating default adhan sound...")
            tts = gTTS(text="It's time for prayer", lang='en')
            tts.save(DEFAULT_ADHAN_SOUND)
            print("Default adhan sound created.")
        except Exception as e:
            print(f"Error creating default adhan sound: {str(e)}")
            # If we can't create a TTS adhan sound, copy the alarm sound as a fallback
            if os.path.exists(DEFAULT_ALARM_SOUND):
                import shutil
                shutil.copy(DEFAULT_ALARM_SOUND, DEFAULT_ADHAN_SOUND)
