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
    
    def __init__(self):
        """Initialize the audio player."""
        self.playing = False
        self.current_audio = None
        self.audio_queue = queue.Queue()
        self.lock = threading.Lock()
        self.player_thread = None
        
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
                audio_type, audio_data = self.audio_queue.get()
                
                with self.lock:
                    self.playing = True
                    self.current_audio = audio_data
                
                if audio_type == 'file':
                    self._play_file_internal(audio_data)
                elif audio_type == 'tts':
                    self._play_tts_internal(audio_data)
                elif audio_type == 'bytes':
                    self._play_bytes_internal(audio_data)
                
                with self.lock:
                    self.playing = False
                    self.current_audio = None
                
                # Mark task as done
                self.audio_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error in audio player: {str(e)}")
                with self.lock:
                    self.playing = False
                    self.current_audio = None
            
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
    
    def play_file(self, file_path):
        """Play an audio file.
        
        Args:
            file_path: Path to the audio file
        """
        self.audio_queue.put(('file', file_path))
    
    def play_tts(self, text):
        """Play text-to-speech immediately.
        
        Args:
            text: Text to convert to speech
        """
        self.audio_queue.put(('tts', text))
    
    def queue_tts(self, text):
        """Queue text-to-speech to play after current audio.
        
        Args:
            text: Text to convert to speech
        """
        self.audio_queue.put(('tts', text))
    
    def play_bytes(self, audio_bytes):
        """Play audio from bytes.
        
        Args:
            audio_bytes: Audio data as bytes
        """
        self.audio_queue.put(('bytes', audio_bytes))
    
    def stop(self):
        """Stop all audio playback."""
        with self.lock:
            if self.playing:
                logger.info("Stopping audio playback")
                pygame.mixer.music.stop()
                self.playing = False
                self.current_audio = None
                
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
