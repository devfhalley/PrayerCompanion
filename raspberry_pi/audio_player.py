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
    
    # Priority levels for audio playback (lower number = higher priority)
    PRIORITY_ADHAN = 1     # Highest priority
    PRIORITY_PRE_ADHAN = 2 # Second highest priority
    PRIORITY_TAHRIM = 3    # Third highest priority
    PRIORITY_ALARM = 4     # Fourth priority
    PRIORITY_PUSH_TO_TALK = 5 # Fifth priority
    PRIORITY_MURATTAL = 6  # Lowest priority
    
    def __init__(self):
        """Initialize the audio player."""
        self.playing = False
        self.current_audio = None
        self.current_priority = None
        # Track the last played murattal for persistence
        self.last_murattal = None
        self.audio_queue = queue.PriorityQueue()
        self.lock = threading.Lock()
        self.player_thread = None
        self.murattal_directory = os.path.join(os.path.dirname(__file__), "murattal")
        
        # Create murattal directory if it doesn't exist
        if not os.path.exists(self.murattal_directory):
            os.makedirs(self.murattal_directory)
        
        # Initialize pygame mixer with specific parameters for Replit environment
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
            logger.info(f"Pygame mixer initialized: {pygame.mixer.get_init()}")
        except Exception as e:
            logger.error(f"Failed to initialize pygame mixer: {str(e)}")
            # Try alternative initialization
            try:
                pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=1024)
                logger.info(f"Pygame mixer initialized with fallback settings: {pygame.mixer.get_init()}")
            except Exception as e2:
                logger.error(f"Failed to initialize pygame mixer with fallback settings: {str(e2)}")
        
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
                    if self.playing:
                        if priority < self.current_priority:
                            # Higher priority audio (lower number) should interrupt
                            logger.info(f"Interrupting priority {self.current_priority} playback for priority {priority}")
                            pygame.mixer.music.stop()
                            # Add small delay to ensure audio is fully stopped
                            time.sleep(0.5)
                        else:
                            # Skip this audio if current playback has higher priority
                            logger.info(f"Skipping priority {priority} audio because priority {self.current_priority} is playing")
                            self.audio_queue.task_done()
                            continue
                    
                    # Update broadcast for global ticker about what's playing
                    # Only broadcast for adhan, alarms, and Murattal - not for utility sounds
                    if priority == self.PRIORITY_ADHAN:
                        try:
                            # Import here to avoid circular imports
                            from websocket_server import broadcast_message
                            broadcast_message({
                                'type': 'audio_status',
                                'status': 'playing',
                                'priority': 'adhan',
                                'timestamp': int(time.time() * 1000)
                            })
                        except Exception as e:
                            logger.warning(f"Error broadcasting adhan playing status: {str(e)}")
                    elif priority == self.PRIORITY_ALARM:
                        try:
                            # Import here to avoid circular imports
                            from websocket_server import broadcast_message
                            broadcast_message({
                                'type': 'audio_status',
                                'status': 'playing',
                                'priority': 'alarm',
                                'timestamp': int(time.time() * 1000)
                            })
                        except Exception as e:
                            logger.warning(f"Error broadcasting alarm playing status: {str(e)}")
                    elif priority == self.PRIORITY_MURATTAL:
                        try:
                            # Import here to avoid circular imports
                            from websocket_server import broadcast_message
                            # For murattal, we need to extract the file name for display purposes
                            murattal_name = "Unknown"
                            if audio_type == 'file' and isinstance(audio_data, str):
                                file_name = os.path.basename(audio_data)
                                murattal_name = os.path.splitext(file_name)[0]  # Remove extension
                            
                            broadcast_message({
                                'type': 'audio_status',
                                'status': 'playing',
                                'priority': 'murattal',
                                'murattal_name': murattal_name,
                                'file_path': audio_data if audio_type == 'file' else None,
                                'timestamp': int(time.time() * 1000)
                            })
                        except Exception as e:
                            logger.warning(f"Error broadcasting murattal playing status: {str(e)}")
                    
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
                elif audio_type == 'smart_file':
                    # Extract file path and smart alarm settings
                    file_path, smart_settings = audio_data
                    self._play_smart_alarm_file(file_path, smart_settings)
                elif audio_type == 'smart_tts':
                    # Extract text and smart alarm settings
                    tts_text, smart_settings = audio_data
                    self._play_smart_alarm_tts(tts_text, smart_settings)
                
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
            # Log file metadata
            file_size = os.path.getsize(file_path)
            logger.info(f"Audio file size: {file_size} bytes")
            
            # Log mixer status before loading file
            logger.info(f"Mixer initialized status: {pygame.mixer.get_init()}")
            
            # Reset pygame mixer if it's in a bad state
            try:
                pygame.mixer.quit()
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
                logger.info(f"Mixer re-initialized successfully: {pygame.mixer.get_init()}")
            except Exception as re_init_error:
                logger.warning(f"Mixer re-initialization failed: {str(re_init_error)}")
            
            # Implement playback with timeout protection
            try:
                pygame.mixer.music.load(file_path)
                logger.info(f"File loaded successfully, preparing playback")
                
                # Set volume to 1.0 (full volume)
                pygame.mixer.music.set_volume(1.0)
                logger.info(f"Volume set to: {pygame.mixer.music.get_volume()}")
                
                pygame.mixer.music.play(loops=loop)
                logger.info("Playback started")
                
                # Log if playback actually started
                if pygame.mixer.music.get_busy():
                    logger.info("Confirmed playback is active")
                else:
                    logger.warning("Playback not detected as active despite play() call")
                
                # Wait for playback to finish with timeout protection
                play_start_time = time.time()
                
                # Set timeout based on priority level
                # For Murattal playback (PRIORITY_MURATTAL=6), allow unlimited playback time
                # For other audio, limit to 5 minutes to prevent hanging
                if self.current_priority == self.PRIORITY_MURATTAL:
                    max_playback_time = float('inf')  # Unlimited for murattal
                    logger.info("Murattal playback: allowing unlimited playing time")
                else:
                    max_playback_time = 300  # Maximum 5 minutes for other audio types
                
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
                    
                    # Check for timeout (skip for Murattal which has infinite timeout)
                    elapsed = time.time() - play_start_time
                    if self.current_priority != self.PRIORITY_MURATTAL and elapsed > max_playback_time:
                        logger.warning(f"Playback timeout after {max_playback_time} seconds, forcing stop")
                        pygame.mixer.music.stop()
                        break
                        
                    # Log progress every 5 seconds to reduce log spam
                    if int(elapsed) % 5 == 0 and elapsed > 0 and int(elapsed) != 0:
                        logger.info(f"Still playing... {int(elapsed)} seconds elapsed")
                
                play_duration = time.time() - play_start_time
                logger.info(f"Audio file playback finished after {play_duration:.2f} seconds")
                
            except Exception as playback_error:
                logger.error(f"Playback error: {str(playback_error)}")
                # Try to ensure pygame mixer is stopped in case of error
                try:
                    pygame.mixer.music.stop()
                except:
                    pass
            
        except Exception as e:
            logger.error(f"Error playing audio file: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _play_tts_internal(self, text):
        """Internal method to play text-to-speech."""
        temp_filename = None
        try:
            logger.info(f"Converting text to speech: {text}")
            
            # Limit text length to prevent excessive processing
            if len(text) > 1000:
                logger.warning(f"TTS text too long ({len(text)} chars), truncating to 1000 chars")
                text = text[:1000] + "..."
            
            try:
                # Generate TTS using Google's service with timeout protection
                logger.info("Creating TTS using gTTS")
                tts = gtts.gTTS(text=text, lang='en')
                
                # Use a temporary file
                with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as fp:
                    temp_filename = fp.name
                    logger.info(f"Created temporary file for TTS: {temp_filename}")
                
                # Save to the temporary file
                logger.info("Saving TTS to temporary file")
                tts.save(temp_filename)
                logger.info(f"TTS saved successfully, file size: {os.path.getsize(temp_filename)} bytes")
                
                # Play the temporary file - always with no looping for TTS
                self._play_file_internal(temp_filename, loop=0)
                
            except Exception as tts_error:
                logger.error(f"Error in TTS generation or playback: {str(tts_error)}")
                import traceback
                logger.error(traceback.format_exc())
                
        except Exception as e:
            logger.error(f"Error with text-to-speech: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            
        finally:
            # Clean up - delete the temporary file
            if temp_filename and os.path.exists(temp_filename):
                try:
                    logger.info(f"Removing temporary TTS file: {temp_filename}")
                    os.unlink(temp_filename)
                except Exception as cleanup_error:
                    logger.warning(f"Failed to remove temporary TTS file: {str(cleanup_error)}")
    
    def _play_bytes_internal(self, audio_bytes):
        """Internal method to play audio from bytes."""
        try:
            logger.info("Playing audio from bytes")
            temp_filename = None
            webm_filename = None
            wav_filename = None
            
            try:
                # First try to directly save and play as WAV
                logger.info(f"Creating temporary WAV file for audio bytes (length: {len(audio_bytes)} bytes)")
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as fp:
                    fp.write(audio_bytes)
                    temp_filename = fp.name
                    logger.info(f"Created temporary WAV file: {temp_filename}")
                
                # Try to play the WAV file
                try:
                    logger.info(f"Attempting to play audio as WAV: {temp_filename}")
                    
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
                        logger.info(f"Removing failed WAV file: {temp_filename}")
                        os.unlink(temp_filename)
                        temp_filename = None
                    except Exception as unlink_error:
                        logger.warning(f"Failed to remove WAV file: {str(unlink_error)}")
                    
                    # Try to convert using pydub
                    logger.info("Attempting to convert audio with pydub")
                    with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as webm_fp:
                        webm_fp.write(audio_bytes)
                        webm_filename = webm_fp.name
                        logger.info(f"Created temporary WEBM file: {webm_filename}")
                
                    # Try different formats with better error handling
                    conversion_successful = False
                    for fmt in ['webm', 'ogg', 'mp3']:
                        if conversion_successful:
                            break
                            
                        try:
                            logger.info(f"Trying to load as {fmt} format")
                            audio = AudioSegment.from_file(webm_filename, format=fmt)
                            logger.info(f"Successfully loaded audio as {fmt}")
                            
                            # Convert to WAV
                            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as wav_fp:
                                wav_filename = wav_fp.name
                                logger.info(f"Created new WAV file for conversion: {wav_filename}")
                            
                            # Export as WAV
                            logger.info(f"Exporting to WAV format: {wav_filename}")
                            audio.export(wav_filename, format="wav")
                            
                            # Try to play the converted file
                            logger.info(f"Playing converted WAV file: {wav_filename}")
                            # If current priority is adhan, don't loop
                            if self.current_priority == self.PRIORITY_ADHAN:
                                self._play_file_internal(wav_filename, loop=0)
                            else:
                                self._play_file_internal(wav_filename)
                            logger.info(f"Successfully converted and played as {fmt}")
                            
                            # Set temp_filename for cleanup
                            temp_filename = wav_filename
                            conversion_successful = True
                            
                        except Exception as format_error:
                            logger.warning(f"Failed to convert as {fmt}: {str(format_error)}")
                            import traceback
                            logger.warning(traceback.format_exc())
                            
                            # Clean up failed WAV file if it exists
                            if wav_filename and os.path.exists(wav_filename):
                                try:
                                    logger.info(f"Removing failed WAV conversion: {wav_filename}")
                                    os.unlink(wav_filename)
                                    wav_filename = None
                                except Exception as unlink_error:
                                    logger.warning(f"Failed to remove WAV file: {str(unlink_error)}")
                    
                    if not conversion_successful:
                        logger.error("All audio format conversions failed")
                    
                except Exception as pydub_error:
                    logger.error(f"Error in pydub conversion process: {str(pydub_error)}")
                    import traceback
                    logger.error(traceback.format_exc())
                
            finally:
                # Clean up all temporary files
                logger.info("Cleaning up temporary files...")
                
                # Clean up the webm file
                if webm_filename and os.path.exists(webm_filename):
                    try:
                        logger.info(f"Removing temporary WEBM file: {webm_filename}")
                        os.unlink(webm_filename)
                    except Exception as cleanup_error:
                        logger.warning(f"Failed to remove WEBM file: {str(cleanup_error)}")
                
                # Clean up the main temp file (could be WAV or converted format)
                if temp_filename and os.path.exists(temp_filename):
                    try:
                        logger.info(f"Removing main temporary file: {temp_filename}")
                        os.unlink(temp_filename)
                    except Exception as cleanup_error:
                        logger.warning(f"Failed to remove temp file: {str(cleanup_error)}")
                
        except Exception as e:
            logger.error(f"Error playing audio bytes: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
    
    def play_adhan(self, file_path):
        """Play adhan audio with highest priority.
        
        Args:
            file_path: Path to the adhan audio file
        """
        self.audio_queue.put((self.PRIORITY_ADHAN, time.time(), ('file', file_path)))
    
    def play_alarm(self, file_path=None, tts_text=None, smart_alarm_settings=None):
        """Play alarm audio with high priority.
        
        Args:
            file_path: Path to the alarm audio file
            tts_text: Text to convert to speech for alarm
            smart_alarm_settings: Dictionary with smart alarm settings:
                - smart_alarm: Boolean flag to enable/disable smart alarm features
                - volume_start: Starting volume level for gradual increase (0-100)
                - volume_end: Target volume level for gradual increase (0-100)
                - volume_increment: Step size for gradual increase
                - ramp_duration: Duration in seconds for the volume ramp
        """
        if file_path:
            if smart_alarm_settings and smart_alarm_settings.get('smart_alarm', False):
                # Use smart alarm with gradual volume increase
                self.audio_queue.put((self.PRIORITY_ALARM, time.time(), 
                                     ('smart_file', (file_path, smart_alarm_settings))))
            else:
                # Use regular alarm
                self.audio_queue.put((self.PRIORITY_ALARM, time.time(), ('file', file_path)))
        elif tts_text:
            if smart_alarm_settings and smart_alarm_settings.get('smart_alarm', False):
                # Use smart alarm with gradual volume increase for TTS
                self.audio_queue.put((self.PRIORITY_ALARM, time.time(), 
                                     ('smart_tts', (tts_text, smart_alarm_settings))))
            else:
                # Use regular TTS alarm
                self.audio_queue.put((self.PRIORITY_ALARM, time.time(), ('tts', tts_text)))
    
    def play_pre_adhan(self, file_path):
        """Play pre-adhan audio with second highest priority.
        
        Args:
            file_path: Path to the pre-adhan audio file
        """
        self.audio_queue.put((self.PRIORITY_PRE_ADHAN, time.time(), ('file', file_path)))
    
    def play_tahrim(self, file_path):
        """Play tahrim audio with third highest priority.
        
        Args:
            file_path: Path to the tahrim audio file
        """
        self.audio_queue.put((self.PRIORITY_TAHRIM, time.time(), ('file', file_path)))
    
    def play_push_to_talk(self, audio_bytes):
        """Play push-to-talk audio with second lowest priority.
        
        Args:
            audio_bytes: Audio data as bytes
        """
        self.audio_queue.put((self.PRIORITY_PUSH_TO_TALK, time.time(), ('bytes', audio_bytes)))
    
    def play_murattal(self, file_path):
        """Play Murattal audio with lowest priority.
        
        Args:
            file_path: Path to the Murattal audio file
        """
        # Store file path as the last murattal for persistence
        with self.lock:
            file_name = os.path.basename(file_path)
            murattal_name = os.path.splitext(file_name)[0]  # Remove extension
            self.last_murattal = {
                'file_path': file_path,
                'name': murattal_name
            }
            logger.info(f"Setting last_murattal to: {murattal_name}")
            
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
                # If we're stopping a murattal, don't clear the last_murattal reference
                current_priority = self.current_priority
                
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
                
                # For murattal, we want to preserve the last played track
                # even after stopping, so the UI can show what was last played
                if current_priority == self.PRIORITY_MURATTAL:
                    logger.info("Preserving last murattal information after stop")
                    if self.last_murattal:
                        logger.info(f"Last played murattal: {self.last_murattal['name']}")
    
    def is_playing(self):
        """Check if audio is currently playing.
        
        For murattal persistence, this method will also check if we have information
        about a last played murattal that should be displayed in the UI.
        """
        with self.lock:
            # For normal playback check
            if self.playing:
                return True
            
            # Special case for murattal persistence
            if self.last_murattal is not None:
                # This helps the status endpoint know there's murattal data available
                # even if it's not currently playing
                return False
            
            return False
    
    def get_current_priority(self):
        """Get the priority level of currently playing audio."""
        with self.lock:
            return self.current_priority
            
    def get_current_audio(self):
        """Get the currently playing audio data.
        
        Returns:
            Tuple with (audio_type, audio_data) or None if nothing is playing.
            For murattal that isn't currently playing but was played recently,
            returns ('file', file_path) to maintain persistence.
        """
        with self.lock:
            if self.playing and self.current_audio is not None:
                return ('file', self.current_audio)
            elif self.current_priority == self.PRIORITY_MURATTAL and self.last_murattal is not None:
                # For murattal, provide the last played file for persistence
                return ('file', self.last_murattal['file_path'])
            return None
    
    def _play_smart_alarm_file(self, file_path, settings):
        """Play an audio file with gradually increasing volume.
        
        Args:
            file_path: Path to the audio file
            settings: Dictionary with smart alarm settings
        """
        try:
            if not os.path.exists(file_path):
                logger.error(f"Smart alarm audio file not found: {file_path}")
                return
            
            # Extract settings with defaults
            volume_start = int(settings.get('volume_start', 20))
            volume_end = int(settings.get('volume_end', 100))
            volume_increment = int(settings.get('volume_increment', 5))
            ramp_duration = int(settings.get('ramp_duration', 60))
            
            # Validate volume values
            volume_start = max(0, min(100, volume_start))
            volume_end = max(0, min(100, volume_end))
            volume_increment = max(1, min(20, volume_increment))
            ramp_duration = max(10, min(300, ramp_duration))
            
            logger.info(f"Playing smart alarm file with gradual volume increase: {file_path}")
            logger.info(f"Volume: {volume_start} to {volume_end}, increment: {volume_increment}, duration: {ramp_duration}s")
            
            # Load the file
            pygame.mixer.music.load(file_path)
            
            # Set initial volume (scale from 0-100 to 0.0-1.0)
            current_volume = volume_start / 100.0
            pygame.mixer.music.set_volume(current_volume)
            
            # Calculate timing
            if volume_end <= volume_start:
                # No need for gradual increase if end volume is less than or equal to start volume
                step_delay = ramp_duration
                logger.info("No volume increase needed, playing at constant volume")
            else:
                # Calculate number of steps and delay between volume changes
                steps = (volume_end - volume_start) // volume_increment
                step_delay = ramp_duration / max(steps, 1)
                logger.info(f"Volume increase: {steps} steps with {step_delay:.2f}s delay between steps")
            
            # Start playback on a loop to allow for volume changes
            pygame.mixer.music.play(loops=-1)  # Loop continuously
            
            start_time = time.time()
            elapsed_time = 0
            
            # Run volume ramp
            try:
                while pygame.mixer.music.get_busy() and elapsed_time < ramp_duration:
                    # Calculate current target volume
                    if volume_end > volume_start:
                        target_volume = min(
                            volume_end,
                            volume_start + int((elapsed_time / ramp_duration) * (volume_end - volume_start))
                        )
                        # Set new volume if needed
                        new_volume = target_volume / 100.0
                        if abs(new_volume - current_volume) >= (volume_increment / 100.0):
                            current_volume = new_volume
                            pygame.mixer.music.set_volume(current_volume)
                            logger.info(f"Smart alarm volume increased to {target_volume}%")
                    
                    # Check if we should stop due to interruption
                    with self.lock:
                        if not self.playing or self.current_audio != file_path:
                            logger.info("Smart alarm interrupted")
                            break
                    
                    # Sleep for a short time to avoid CPU hogging
                    time.sleep(0.1)
                    
                    # Update elapsed time
                    elapsed_time = time.time() - start_time
                
                # Continue playing at final volume for a period or until stop signal
                if pygame.mixer.music.get_busy():
                    logger.info(f"Smart alarm reached final volume of {volume_end}%, continuing playback")
                    
                    # Set final volume
                    pygame.mixer.music.set_volume(volume_end / 100.0)
                    
                    # Continue playing for some additional time
                    additional_time = 0
                    max_additional_time = 300  # 5 minutes max
                    
                    while pygame.mixer.music.get_busy() and additional_time < max_additional_time:
                        with self.lock:
                            if not self.playing or self.current_audio != file_path:
                                logger.info("Smart alarm playback interrupted")
                                break
                        
                        time.sleep(0.5)
                        additional_time += 0.5
                
                # Stop playback
                pygame.mixer.music.stop()
                logger.info("Smart alarm playback finished")
                
            except Exception as e:
                logger.error(f"Error during smart alarm playback: {str(e)}")
                pygame.mixer.music.stop()
                
        except Exception as e:
            logger.error(f"Error setting up smart alarm: {str(e)}")
    
    def _play_smart_alarm_tts(self, tts_text, settings):
        """Play TTS with gradually increasing volume.
        
        Args:
            tts_text: Text to convert to speech
            settings: Dictionary with smart alarm settings
        """
        try:
            logger.info(f"Converting text to speech for smart alarm: {tts_text}")
            
            # Generate TTS using Google's service
            tts = gtts.gTTS(text=tts_text, lang='en')
            
            # Use a temporary file
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as fp:
                temp_filename = fp.name
            
            # Save to the temporary file
            tts.save(temp_filename)
            
            try:
                # Play with smart alarm features
                self._play_smart_alarm_file(temp_filename, settings)
            finally:
                # Clean up - delete the temporary file
                try:
                    os.unlink(temp_filename)
                except:
                    pass
                
        except Exception as e:
            logger.error(f"Error with smart alarm TTS: {str(e)}")

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
