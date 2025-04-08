#!/usr/bin/env python3
"""
Audio player module for Raspberry Pi Prayer Alarm System.
This module handles audio playback, including MP3 files and text-to-speech.
"""

import logging
import os
import threading
import queue
import time
import pygame
import gtts
from io import BytesIO
import tempfile

logger = logging.getLogger(__name__)

class AudioPlayer:
    """Handles audio playback, including MP3 files and text-to-speech."""
    
    # Priority levels for audio playback
    PRIORITY_ADHAN = 1  # Highest priority
    PRIORITY_ALARM = 2
    PRIORITY_MURATTAL = 3  # Lowest priority
    
    def __init__(self):
        """Initialize the audio player."""
        self.playing = False
        self.current_audio = None
        self.current_priority = None
        self.audio_queue = queue.PriorityQueue()
        self.lock = threading.Lock()
        self.player_thread = None
        self.murattal_directory = os.path.join(os.path.dirname(__file__), "murattal")
        
        # Create murattal directory if it doesn't exist
        if not os.path.exists(self.murattal_directory):
            os.makedirs(self.murattal_directory)
        
        # Initialize pygame mixer
        pygame.mixer.init()
        
        # Start player thread
        self.start_player_thread()
    
    def start_player_thread(self):
        """Start the player thread that processes the audio queue."""
        self.player_thread = threading.Thread(target=self._process_queue)
        self.player_thread.daemon = True
        self.player_thread.start()
    
    def _process_queue(self):
        """Process the audio queue."""
        while True:
            try:
                # Get the next audio item
                priority, _, (audio_type, audio_data) = self.audio_queue.get()
                
                with self.lock:
                    # Check if we should override current playback
                    if self.playing and priority < self.current_priority:
                        # Higher priority audio (lower number) should interrupt
                        logger.info(f"Interrupting priority {self.current_priority} playback for priority {priority}")
                        pygame.mixer.music.stop()
                    elif self.playing:
                        # Skip this audio if current playback has higher priority
                        logger.info(f"Skipping priority {priority} audio because priority {self.current_priority} is playing")
                        self.audio_queue.task_done()
                        continue
                    
                    self.playing = True
                    self.current_audio = audio_data
                    self.current_priority = priority
                
                if audio_type == 'file':
                    self._play_file_internal(audio_data)
                elif audio_type == 'tts':
                    self._play_tts_internal(audio_data)
                elif audio_type == 'bytes':
                    self._play_bytes_internal(audio_data)
                
                with self.lock:
                    self.playing = False
                    self.current_audio = None
                    self.current_priority = None
                
                # Mark task as done
                self.audio_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error in audio player: {str(e)}")
                with self.lock:
                    self.playing = False
                    self.current_audio = None
                    self.current_priority = None
            
            # Small delay to prevent CPU hogging
            time.sleep(0.1)
    
    def _play_file_internal(self, file_path):
        """Internal method to play a file."""
        try:
            if not os.path.exists(file_path):
                logger.error(f"Audio file not found: {file_path}")
                return
            
            logger.info(f"Playing audio file: {file_path}")
            
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()
            
            # Wait for playback to finish
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
            
            logger.info("Audio file playback finished")
            
        except Exception as e:
            logger.error(f"Error playing audio file: {str(e)}")
    
    def _play_tts_internal(self, text):
        """Internal method to play text-to-speech."""
        try:
            logger.info(f"Converting text to speech: {text}")
            
            # Generate TTS using Google's service
            tts = gtts.gTTS(text=text, lang='en')
            
            # Use a temporary file
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as fp:
                temp_filename = fp.name
            
            # Save to the temporary file
            tts.save(temp_filename)
            
            # Play the temporary file
            self._play_file_internal(temp_filename)
            
            # Clean up - delete the temporary file
            try:
                os.unlink(temp_filename)
            except:
                pass
            
        except Exception as e:
            logger.error(f"Error with text-to-speech: {str(e)}")
    
    def _play_bytes_internal(self, audio_bytes):
        """Internal method to play audio from bytes."""
        try:
            logger.info("Playing audio from bytes")
            
            # Create a temporary file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as fp:
                fp.write(audio_bytes)
                temp_filename = fp.name
            
            # Play the temporary file
            self._play_file_internal(temp_filename)
            
            # Clean up - delete the temporary file
            try:
                os.unlink(temp_filename)
            except:
                pass
            
        except Exception as e:
            logger.error(f"Error playing audio bytes: {str(e)}")
    
    def play_adhan(self, file_path):
        """Play adhan audio with highest priority.
        
        Args:
            file_path: Path to the adhan audio file
        """
        self.audio_queue.put((self.PRIORITY_ADHAN, time.time(), ('file', file_path)))
    
    def play_alarm(self, file_path=None, tts_text=None):
        """Play alarm audio with high priority.
        
        Args:
            file_path: Path to the alarm audio file
            tts_text: Text to convert to speech for alarm
        """
        if file_path:
            self.audio_queue.put((self.PRIORITY_ALARM, time.time(), ('file', file_path)))
        elif tts_text:
            self.audio_queue.put((self.PRIORITY_ALARM, time.time(), ('tts', tts_text)))
    
    def play_murattal(self, file_path):
        """Play Murattal audio with lowest priority.
        
        Args:
            file_path: Path to the Murattal audio file
        """
        self.audio_queue.put((self.PRIORITY_MURATTAL, time.time(), ('file', file_path)))
    
    def play_file(self, file_path, priority=None):
        """Play an audio file with specified priority.
        
        Args:
            file_path: Path to the audio file
            priority: Priority level (default: PRIORITY_MURATTAL)
        """
        if priority is None:
            priority = self.PRIORITY_MURATTAL
        self.audio_queue.put((priority, time.time(), ('file', file_path)))
    
    def play_tts(self, text, priority=None):
        """Play text-to-speech with specified priority.
        
        Args:
            text: Text to convert to speech
            priority: Priority level (default: PRIORITY_ALARM)
        """
        if priority is None:
            priority = self.PRIORITY_ALARM
        self.audio_queue.put((priority, time.time(), ('tts', text)))
    
    def play_bytes(self, audio_bytes, priority=None):
        """Play audio from bytes with specified priority.
        
        Args:
            audio_bytes: Audio data as bytes
            priority: Priority level (default: PRIORITY_MURATTAL)
        """
        if priority is None:
            priority = self.PRIORITY_MURATTAL
        self.audio_queue.put((priority, time.time(), ('bytes', audio_bytes)))
    
    def get_murattal_files(self):
        """Get a list of all available Murattal files.
        
        Returns:
            List of file info dictionaries with 'name' and 'path' keys
        """
        murattal_files = []
        
        if os.path.exists(self.murattal_directory):
            for filename in os.listdir(self.murattal_directory):
                if filename.endswith('.mp3'):
                    file_path = os.path.join(self.murattal_directory, filename)
                    # Remove .mp3 extension for display name
                    display_name = os.path.splitext(filename)[0]
                    murattal_files.append({
                        'name': display_name,
                        'path': file_path
                    })
        
        return murattal_files
    
    def stop(self):
        """Stop all audio playback."""
        with self.lock:
            if self.playing:
                logger.info("Stopping audio playback")
                pygame.mixer.music.stop()
                self.playing = False
                self.current_audio = None
                self.current_priority = None
                
                # Clear the queue
                while not self.audio_queue.empty():
                    try:
                        self.audio_queue.get_nowait()
                        self.audio_queue.task_done()
                    except queue.Empty:
                        break
    
    def is_playing(self):
        """Check if audio is currently playing."""
        with self.lock:
            return self.playing
    
    def get_current_priority(self):
        """Get the priority level of currently playing audio."""
        with self.lock:
            return self.current_priority if self.playing else None
    
    def add_murattal_file(self, file_name, file_data):
        """Add a new Murattal file to the collection.
        
        Args:
            file_name: Name of the file (with .mp3 extension)
            file_data: Binary content of the MP3 file
            
        Returns:
            Path to the saved file
        """
        # Ensure it has .mp3 extension
        if not file_name.endswith('.mp3'):
            file_name += '.mp3'
            
        file_path = os.path.join(self.murattal_directory, file_name)
        
        # Save the file
        with open(file_path, 'wb') as f:
            f.write(file_data)
            
        return file_path
