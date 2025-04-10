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
from pydub import AudioSegment

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
                    # Special handling for adhan - never loop
                    if priority == self.PRIORITY_ADHAN:
                        logger.info("Playing adhan with no looping")
                        self._play_file_internal(audio_data, loop=0)  # Explicitly set loop=0 for adhan
                    else:
                        # For other types, use default behavior
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
    
    def _play_file_internal(self, file_path, loop=0):
        """Internal method to play a file.
        
        Args:
            file_path: Path to the audio file
            loop: Number of times to loop the audio (-1 for infinite, 0 for once)
        """
        try:
            if not os.path.exists(file_path):
                logger.error(f"Audio file not found: {file_path}")
                return
            
            logger.info(f"Playing audio file: {file_path}, loop: {loop}")
            
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play(loops=loop)
            
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
            
            # Play the temporary file - always with no looping for TTS
            self._play_file_internal(temp_filename, loop=0)
            
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
            temp_filename = None
            
            try:
                # First try to directly save and play as WAV
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as fp:
                    fp.write(audio_bytes)
                    temp_filename = fp.name
                
                # Try to play the WAV file
                try:
                    # If current priority is adhan, don't loop
                    if self.current_priority == self.PRIORITY_ADHAN:
                        self._play_file_internal(temp_filename, loop=0)
                    else:
                        self._play_file_internal(temp_filename)
                    logger.info("Successfully played audio as WAV")
                    return
                except Exception as wav_error:
                    logger.warning(f"Failed to play as WAV, will try conversion: {str(wav_error)}")
                    
                    # Clean up the failed WAV file
                    try:
                        os.unlink(temp_filename)
                    except:
                        pass
                    
                    # Try to convert using pydub
                    logger.info("Attempting to convert audio with pydub")
                    with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as webm_fp:
                        webm_fp.write(audio_bytes)
                        webm_filename = webm_fp.name
                
                    try:
                        # Try to load as various formats
                        for fmt in ['webm', 'ogg', 'mp3']:
                            try:
                                logger.info(f"Trying to load as {fmt} format")
                                audio = AudioSegment.from_file(webm_filename, format=fmt)
                                
                                # Convert to WAV
                                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as wav_fp:
                                    wav_filename = wav_fp.name
                                
                                # Export as WAV
                                audio.export(wav_filename, format="wav")
                                
                                # Try to play the converted file
                                # If current priority is adhan, don't loop
                                if self.current_priority == self.PRIORITY_ADHAN:
                                    self._play_file_internal(wav_filename, loop=0)
                                else:
                                    self._play_file_internal(wav_filename)
                                logger.info(f"Successfully converted and played as {fmt}")
                                
                                # Set temp_filename for cleanup
                                temp_filename = wav_filename
                                break
                            except Exception as format_error:
                                logger.warning(f"Failed to convert as {fmt}: {str(format_error)}")
                                continue
                    
                    except Exception as pydub_error:
                        logger.error(f"Error converting audio: {str(pydub_error)}")
                    
                    finally:
                        # Clean up the webm file
                        try:
                            os.unlink(webm_filename)
                        except:
                            pass
                    
            finally:
                # Clean up any temporary files
                if temp_filename and os.path.exists(temp_filename):
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
