#!/usr/bin/env python3
"""
Test file for Murattal playback without database dependencies.
This script provides a simple Flask server to test murattal playback.
"""

import os
import threading
import time
import logging
from flask import Flask, jsonify, request, render_template, send_file
import pygame
import sys

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_murattal')

# Create Flask app
app = Flask(__name__)

# Audio Player Implementation (simplified for testing)
class TestAudioPlayer:
    """Simplified Audio Player for testing murattal playback."""
    
    def __init__(self):
        """Initialize the audio player."""
        self.playing = False
        self.current_file = None
        self.player_thread = None
        self.playback_start_time = None
        self.murattal_directory = os.path.join(os.path.dirname(__file__), "murattal")
        self._lock = threading.Lock()  # Thread safety
        
        # Initialize pygame mixer
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
            logger.info(f"Pygame mixer initialized: {pygame.mixer.get_init()}")
        except Exception as e:
            logger.error(f"Failed to initialize pygame mixer: {str(e)}")
            try:
                pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=1024)
                logger.info(f"Pygame mixer initialized with fallback settings: {pygame.mixer.get_init()}")
            except Exception as e2:
                logger.error(f"Failed to initialize pygame mixer with fallback settings: {str(e2)}")
    
    def play_murattal(self, file_path):
        """Play murattal audio file.
        
        Args:
            file_path: Path to the murattal audio file
        """
        with self._lock:
            if self.playing:
                self.stop()
                time.sleep(0.5)  # Give time to stop
                
            self.current_file = file_path
            self.player_thread = threading.Thread(target=self._play_file_thread, args=(file_path,))
            self.player_thread.daemon = True
            self.playing = True  # Set it before starting thread for consistency
            self.playback_start_time = time.time()
            self.player_thread.start()
            
            return True
    
    def _play_file_thread(self, file_path):
        """Thread function to play an audio file."""
        try:
            if not os.path.exists(file_path):
                logger.error(f"Audio file not found: {file_path}")
                with self._lock:
                    self.playing = False
                    self.current_file = None
                return
            
            logger.info(f"Playing murattal file: {file_path}")
            file_size = os.path.getsize(file_path)
            logger.info(f"Audio file size: {file_size} bytes")
            
            # Reset pygame mixer
            try:
                pygame.mixer.quit()
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
                logger.info(f"Mixer re-initialized successfully: {pygame.mixer.get_init()}")
            except Exception as re_init_error:
                logger.warning(f"Mixer re-initialization failed: {str(re_init_error)}")
            
            # Play the file
            try:
                pygame.mixer.music.load(file_path)
                logger.info("File loaded successfully")
                
                pygame.mixer.music.set_volume(1.0)
                pygame.mixer.music.play()
                logger.info("Playback started")
                
                # Log if playback actually started
                if pygame.mixer.music.get_busy():
                    logger.info("Confirmed playback is active")
                else:
                    logger.warning("Playback not detected as active despite play() call")
                    # Ensure we mark it as not playing if Pygame doesn't report it as active
                    with self._lock:
                        if not pygame.mixer.music.get_busy():
                            self.playing = False
                
                # Wait for playback to finish WITHOUT timeout
                play_start_time = time.time()
                
                # For murattal, we allow unlimited playback time
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
                    
                    # Update playing status periodically
                    with self._lock:
                        self.playing = pygame.mixer.music.get_busy()
                    
                    # Log progress every 5 seconds to reduce log spam
                    elapsed = time.time() - play_start_time
                    if int(elapsed) % 5 == 0 and elapsed > 0 and int(elapsed) != 0:
                        logger.info(f"Still playing... {int(elapsed)} seconds elapsed")
                
                play_duration = time.time() - play_start_time
                logger.info(f"Murattal playback finished after {play_duration:.2f} seconds")
                
            except Exception as playback_error:
                logger.error(f"Playback error: {str(playback_error)}")
                # Try to ensure pygame mixer is stopped in case of error
                try:
                    pygame.mixer.music.stop()
                except:
                    pass
        
        except Exception as e:
            logger.error(f"Error playing murattal file: {str(e)}")
        
        finally:
            with self._lock:
                self.playing = False
                # Keep current_file set for a moment for the UI to show what was last played
                # This helps with the UI showing what was just played
    
    def stop(self):
        """Stop audio playback."""
        logger.info("Stopping audio playback")
        try:
            pygame.mixer.music.stop()
            with self._lock:
                self.playing = False
        except Exception as e:
            logger.error(f"Error stopping playback: {str(e)}")
    
    def is_playing(self):
        """Check if audio is currently playing."""
        with self._lock:
            try:
                pygame_status = pygame.mixer.music.get_busy()
                # Update our internal state to match pygame
                self.playing = pygame_status
                return self.playing
            except Exception as e:
                logger.error(f"Error checking playback status: {str(e)}")
                return self.playing  # Return our internal state if pygame fails
    
    def get_murattal_files(self):
        """Get list of available murattal files."""
        murattal_files = []
        try:
            if os.path.exists(self.murattal_directory):
                for file_name in os.listdir(self.murattal_directory):
                    if file_name.endswith('.mp3'):
                        file_path = os.path.join(self.murattal_directory, file_name)
                        name = os.path.splitext(file_name)[0]
                        murattal_files.append({
                            'name': name,
                            'path': file_path
                        })
        except Exception as e:
            logger.error(f"Error getting murattal files: {str(e)}")
        
        return murattal_files

# Create the audio player
audio_player = TestAudioPlayer()

# Routes
@app.route('/')
def home():
    """Home page."""
    return render_template('murattal_test.html')

@app.route('/test-murattal')
def test_murattal_page():
    """Test murattal page."""
    murattal_files = audio_player.get_murattal_files()
    return render_template('murattal_test.html', murattal_files=murattal_files)

@app.route('/api/murattal')
def get_murattal_files():
    """Get list of murattal files."""
    murattal_files = audio_player.get_murattal_files()
    return jsonify(murattal_files)

@app.route('/api/murattal/play', methods=['POST'])
def play_murattal():
    """Play a murattal file."""
    data = request.json
    file_path = data.get('path')
    
    if not file_path:
        return jsonify({'success': False, 'error': 'No file path provided'})
    
    if not os.path.exists(file_path):
        return jsonify({'success': False, 'error': 'File not found'})
    
    success = audio_player.play_murattal(file_path)
    return jsonify({'success': success})

@app.route('/api/murattal/stop', methods=['POST'])
def stop_murattal():
    """Stop murattal playback."""
    audio_player.stop()
    return jsonify({'success': True})

@app.route('/api/status')
def get_status():
    """Get current status."""
    is_playing = audio_player.is_playing()
    current_file = audio_player.current_file
    
    file_name = None
    if current_file:
        file_name = os.path.basename(current_file)
        file_name = os.path.splitext(file_name)[0]
    
    return jsonify({
        'playing': is_playing,
        'current_file': file_name
    })

# Run the application
if __name__ == '__main__':
    logger.info("Starting test murattal server")
    app.run(host='0.0.0.0', port=5000, debug=False)