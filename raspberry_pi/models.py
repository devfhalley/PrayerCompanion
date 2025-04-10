#!/usr/bin/env python3
"""
Models module for Raspberry Pi Prayer Alarm System.
This module defines the data models used by the application.
"""
import logging

logger = logging.getLogger(__name__)

from datetime import datetime

class Alarm:
    """Alarm model."""
    
    def __init__(self):
        """Initialize a new Alarm."""
        self.id = None
        self.time = 0  # milliseconds since epoch
        self.enabled = True
        self.repeating = False
        self.days = [False] * 7  # Sunday to Saturday
        self.is_tts = False
        self.message = None
        self.sound_path = None
        # Label is str or None - needed for type annotations
        self.label = None  # type: str | None  # Label for the alarm to display when it rings
    
    @classmethod
    def from_dict(cls, data):
        """Create an Alarm from a dictionary.
        
        Args:
            data: Dictionary with alarm data
        
        Returns:
            Alarm object
        """
        alarm = cls()
        
        if 'id' in data:
            alarm.id = data['id']
        
        # Time can be specified in different ways
        if 'time' in data:
            # Handle time string (HH:MM or HH:MM:SS)
            if isinstance(data['time'], str):
                time_parts = data['time'].split(':')
                if len(time_parts) >= 2:
                    hour = int(time_parts[0])
                    minute = int(time_parts[1])
                    
                    # If date is specified, use it
                    if 'date' in data:
                        date_obj = datetime.strptime(data['date'], '%Y-%m-%d')
                        time_obj = datetime(
                            date_obj.year, date_obj.month, date_obj.day,
                            hour, minute
                        )
                        alarm.time = int(time_obj.timestamp() * 1000)
                    else:
                        # Use today's date with the specified time
                        now = datetime.now()
                        time_obj = datetime(now.year, now.month, now.day, hour, minute)
                    alarm.time = int(time_obj.timestamp() * 1000)
            else:
                # Assume it's already in milliseconds
                alarm.time = data['time']
        elif 'time_str' in data:
            # Handle time string (HH:MM) from time_str field
            hour, minute = map(int, data['time_str'].split(':'))
            
            # If date_str is specified, use it
            if 'date_str' in data:
                date_obj = datetime.strptime(data['date_str'], '%Y-%m-%d')
                time_obj = datetime(
                    date_obj.year, date_obj.month, date_obj.day,
                    hour, minute
                )
                alarm.time = int(time_obj.timestamp() * 1000)
            else:
                # Use today's date with the specified time
                now = datetime.now()
                time_obj = datetime(now.year, now.month, now.day, hour, minute)
                alarm.time = int(time_obj.timestamp() * 1000)
        elif 'hour' in data and 'minute' in data:
            # If hour and minute are specified directly
            hour = data['hour']
            minute = data['minute']
            
            # If date is specified, use it
            if 'date' in data:
                date_obj = datetime.strptime(data['date'], '%Y-%m-%d')
                time_obj = datetime(
                    date_obj.year, date_obj.month, date_obj.day,
                    hour, minute
                )
                alarm.time = int(time_obj.timestamp() * 1000)
            else:
                # Use today's date with the specified time
                now = datetime.now()
                time_obj = datetime(now.year, now.month, now.day, hour, minute)
                alarm.time = int(time_obj.timestamp() * 1000)
        
        if 'enabled' in data:
            alarm.enabled = bool(data['enabled'])
        
        if 'repeating' in data:
            alarm.repeating = bool(data['repeating'])
        
        if 'days' in data:
            # Days can be a JSON array
            if isinstance(data['days'], list):
                alarm.days = [bool(day) for day in data['days']]
            elif isinstance(data['days'], str):
                # Or a string of 0s and 1s
                alarm.days = [c == '1' for c in data['days']]
        
        if 'is_tts' in data:
            alarm.is_tts = bool(data['is_tts'])
        
        if 'message' in data:
            alarm.message = data['message']
        
        if 'sound_path' in data:
            alarm.sound_path = data['sound_path']
            
        if 'label' in data:
            # Ensure label is either a string or None
            label_value = data['label']
            if label_value is None or label_value == '':
                alarm.label = None
            else:
                alarm.label = str(label_value)
                
            # Add debug logging
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Setting alarm label from dict: '{data['label']}' -> '{alarm.label}'")
        
        return alarm
    
    def to_dict(self):
        """Convert the Alarm to a dictionary.
        
        Returns:
            Dictionary representation of the Alarm
        """
        time_obj = datetime.fromtimestamp(self.time / 1000.0)
        
        # Debug info for label value
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Converting Alarm to dict, label value: '{self.label}'")
        
        return {
            'id': self.id,
            'time': self.time,
            'time_str': time_obj.strftime('%H:%M'),
            'date_str': time_obj.strftime('%Y-%m-%d'),
            'enabled': self.enabled,
            'repeating': self.repeating,
            'days': self.days,
            'is_tts': self.is_tts,
            'message': self.message,
            'sound_path': self.sound_path,
            'label': self.label
        }

class PrayerTime:
    """Prayer time model."""
    
    def __init__(self, name=None, time=None, enabled=True, custom_sound=None, date_str=None):
        """Initialize a new PrayerTime.
        
        Args:
            name: Prayer name
            time: Prayer time as datetime
            enabled: Whether the prayer notification is enabled
            custom_sound: Path to custom sound file
            date_str: Date string in YYYY-MM-DD format
        """
        self.id = None
        self.name = name
        self.time = time
        self.enabled = enabled
        self.custom_sound = custom_sound
        # If date_str is not provided, extract it from time
        if date_str is None and time is not None:
            self.date_str = time.strftime('%Y-%m-%d')
        else:
            self.date_str = date_str
    
    def to_dict(self):
        """Convert the PrayerTime to a dictionary.
        
        Returns:
            Dictionary representation of the PrayerTime
        """
        return {
            'id': self.id,
            'name': self.name,
            'time': self.time.isoformat() if self.time else None,
            'time_str': self.time.strftime('%H:%M') if self.time else None,
            'date_str': self.date_str,
            'enabled': self.enabled,
            'custom_sound': self.custom_sound
        }


class YouTubeVideo:
    """YouTube video model."""
    
    def __init__(self, url=None, title=None, enabled=True, position=0):
        """Initialize a new YouTubeVideo.
        
        Args:
            url: YouTube video URL
            title: Optional title for the video
            enabled: Whether the video is enabled
            position: Position in the playlist (0 = first)
        """
        self.id = None
        self.url = url
        self.title = title
        self.enabled = enabled
        self.position = position
        self.created_at = datetime.now()
    
    @classmethod
    def from_dict(cls, data):
        """Create a YouTubeVideo from a dictionary.
        
        Args:
            data: Dictionary with YouTube video data
        
        Returns:
            YouTubeVideo object
        """
        video = cls()
        
        if 'id' in data:
            video.id = data['id']
        
        if 'url' in data:
            video.url = data['url']
        
        if 'title' in data:
            video.title = data['title']
        
        if 'enabled' in data:
            video.enabled = bool(data['enabled'])
        
        if 'position' in data:
            video.position = int(data['position'])
        
        if 'created_at' in data and data['created_at']:
            if isinstance(data['created_at'], str):
                video.created_at = datetime.fromisoformat(data['created_at'])
            else:
                video.created_at = data['created_at']
        
        return video
    
    def to_dict(self):
        """Convert the YouTubeVideo to a dictionary.
        
        Returns:
            Dictionary representation of the YouTubeVideo
        """
        return {
            'id': self.id,
            'url': self.url,
            'title': self.title,
            'enabled': self.enabled,
            'position': self.position,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def get_video_id(self):
        """Extract the YouTube video ID from the URL.
        
        Returns:
            YouTube video ID or None if not found
        """
        if not self.url:
            return None
        
        import re
        
        # YouTube URL patterns
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})',  # Standard and shortened URLs
            r'youtube\.com\/embed\/([a-zA-Z0-9_-]{11})',  # Embed URLs
            r'youtube\.com\/v\/([a-zA-Z0-9_-]{11})'  # Old embed URLs
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self.url)
            if match:
                return match.group(1)
        
        return None
