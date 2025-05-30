#!/usr/bin/env python3
"""
Alarm scheduler module for Raspberry Pi Prayer Alarm System.
This module handles scheduling and triggering alarms.
"""

import logging
import threading
import time
import os
from datetime import datetime, timedelta
import schedule

from database import get_db
from models import Alarm
from config import Config

logger = logging.getLogger(__name__)

class AlarmScheduler:
    """Handles scheduling and triggering alarms."""
    
    def __init__(self, audio_player):
        """Initialize the alarm scheduler.
        
        Args:
            audio_player: An instance of AudioPlayer class
        """
        self.audio_player = audio_player
        self.running = False
        self.thread = None
        self.db = get_db()
        self.lock = threading.Lock()
        self.scheduled_jobs = {}
    
    def start(self):
        """Start the alarm scheduler."""
        if self.running:
            logger.warning("Alarm scheduler already running")
            return
        
        logger.info("Starting alarm scheduler")
        self.running = True
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()
        
        # Load all alarms from database and schedule them
        self._load_alarms()
    
    def stop(self):
        """Stop the alarm scheduler."""
        logger.info("Stopping alarm scheduler")
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
            self.thread = None
        
        # Clear all scheduled jobs
        self._clear_jobs()
    
    def _run(self):
        """Main loop for the alarm scheduler."""
        # Check for one-time alarms every second
        schedule.every(1).seconds.do(self._check_one_time_alarms)
        
        while self.running:
            schedule.run_pending()
            time.sleep(0.2)  # Sleep for shorter time to be more responsive
    
    def _load_alarms(self):
        """Load all alarms from database and schedule them."""
        logger.info("Loading alarms from database")
        
        with self.lock:
            # Clear existing scheduled jobs
            self._clear_jobs()
            
            # Get all enabled alarms
            alarms = self.db.get_enabled_alarms()
            
            for alarm in alarms:
                self._schedule_alarm_internal(alarm)
    
    def _clear_jobs(self):
        """Clear all scheduled jobs."""
        with self.lock:
            # Cancel all scheduled jobs
            for job_id in self.scheduled_jobs:
                schedule.cancel_job(self.scheduled_jobs[job_id])
            
            self.scheduled_jobs = {}
    
    def _check_one_time_alarms(self):
        """Check for one-time alarms that need to be triggered."""
        logger.debug("Checking one-time alarms")
        
        now = datetime.now()
        
        # Get one-time alarms for today
        one_time_alarms = self.db.get_one_time_alarms_for_today()
        
        for alarm in one_time_alarms:
            alarm_time = datetime.fromtimestamp(alarm.time / 1000.0)
            
            # Check if it's time to trigger the alarm (within 3 seconds)
            time_diff = (alarm_time - now).total_seconds()
            
            if -2 <= time_diff <= 3:  # Trigger up to 2 seconds after or 3 seconds before alarm time
                logger.info(f"Triggering one-time alarm {alarm.id}")
                self._trigger_alarm(alarm)
                
                # Disable one-time alarm after it's triggered
                alarm.enabled = False
                self.db.update_alarm(alarm)
    
    def _schedule_alarm_internal(self, alarm):
        """Schedule an alarm internally.
        
        Args:
            alarm: Alarm object to schedule
        """
        if not alarm.enabled:
            logger.warning(f"Attempted to schedule disabled alarm {alarm.id}")
            return
        
        alarm_time = datetime.fromtimestamp(alarm.time / 1000.0)
        
        if alarm.repeating:
            # For repeating alarms, schedule for specific days of the week
            days_of_week = []
            for i, enabled in enumerate(alarm.days):
                if enabled:
                    # Convert from 0-6 (Sun-Sat) to schedule's format
                    days = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']
                    days_of_week.append(days[i])
            
            if not days_of_week:
                logger.warning(f"Repeating alarm {alarm.id} has no days selected")
                return
            
            # Schedule the alarm for each selected day
            for day in days_of_week:
                job = schedule.every().__getattribute__(day).at(
                    f"{alarm_time.hour:02d}:{alarm_time.minute:02d}"
                ).do(self._trigger_alarm, alarm)
                
                self.scheduled_jobs[f"{alarm.id}_{day}"] = job
                
            logger.info(f"Scheduled repeating alarm {alarm.id} for {', '.join(days_of_week)} at {alarm_time.hour:02d}:{alarm_time.minute:02d}")
        
        else:
            # One-time alarms are handled by the periodic check
            logger.info(f"Registered one-time alarm {alarm.id} for {alarm_time}")
    
    def _trigger_alarm(self, alarm):
        """Trigger an alarm.
        
        Args:
            alarm: Alarm object to trigger
        """
        logger.info(f"Triggering alarm {alarm.id}")
        
        # Check if higher priority audio is playing (adhan, tahrim, or pre-adhan)
        current_priority = self.audio_player.get_current_priority()
        if current_priority is not None and current_priority < self.audio_player.PRIORITY_ALARM:
            logger.info(f"Higher priority audio is playing (priority {current_priority}). Not stopping it for alarm.")
        else:
            # Stop any currently playing audio that is equal or lower priority
            logger.info("Forcefully stopping any currently playing audio to prioritize alarm")
            self.audio_player.stop()
            
            # Add a small delay to ensure audio is fully stopped
            time.sleep(0.5)
        
        # Broadcast alarm playing message for the ticker
        from websocket_server import broadcast_message
        alarm_label = alarm.label or f"Alarm {alarm.id}"
        broadcast_message({
            'type': 'alarm_playing',
            'alarm_id': alarm.id,
            'alarm_label': alarm_label,
            'timestamp': int(time.time() * 1000)
        })
        
        # Check if this is a smart alarm with gradual volume increase
        smart_alarm_settings = None
        if alarm.smart_alarm:
            logger.info(f"This is a smart alarm with gradual volume increase")
            smart_alarm_settings = {
                'smart_alarm': alarm.smart_alarm,
                'volume_start': alarm.volume_start,
                'volume_end': alarm.volume_end,
                'volume_increment': alarm.volume_increment,
                'ramp_duration': alarm.ramp_duration
            }
        
        if alarm.is_tts:
            # Play TTS message with alarm priority
            self.audio_player.play_alarm(
                tts_text=alarm.message,
                smart_alarm_settings=smart_alarm_settings
            )
        else:
            # Play sound file with alarm priority
            sound_path = None
            if alarm.sound_path and os.path.exists(alarm.sound_path):
                sound_path = alarm.sound_path
            else:
                # Use default alarm sound
                sound_path = Config.DEFAULT_ALARM_SOUND
                
                # Also announce using TTS that the default sound is being used
                self.audio_player.play_tts(
                    "This is a default alarm sound because the custom sound file was not found.", 
                    priority=self.audio_player.PRIORITY_ALARM
                )
            
            # Play the alarm with smart alarm settings if enabled
            self.audio_player.play_alarm(
                file_path=sound_path,
                smart_alarm_settings=smart_alarm_settings
            )
    
    def schedule_alarm(self, alarm):
        """Schedule an alarm.
        
        Args:
            alarm: Alarm object to schedule
        """
        with self.lock:
            # Remove any existing scheduled job for this alarm
            self.remove_alarm(alarm.id)
            
            # Schedule the alarm
            self._schedule_alarm_internal(alarm)
    
    def remove_alarm(self, alarm_id):
        """Remove a scheduled alarm.
        
        Args:
            alarm_id: ID of the alarm to remove
        """
        with self.lock:
            # Find all jobs for this alarm
            job_ids_to_remove = []
            
            for job_id in self.scheduled_jobs:
                if job_id.startswith(f"{alarm_id}_"):
                    job_ids_to_remove.append(job_id)
            
            # Cancel and remove the jobs
            for job_id in job_ids_to_remove:
                schedule.cancel_job(self.scheduled_jobs[job_id])
                del self.scheduled_jobs[job_id]
            
            logger.info(f"Removed {len(job_ids_to_remove)} scheduled jobs for alarm {alarm_id}")
