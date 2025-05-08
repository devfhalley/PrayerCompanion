#!/usr/bin/env python3
"""
WebSocket server module for Raspberry Pi Prayer Alarm System.
This module provides two WebSocket connections:
1. /ws/audio - For playing sounds and audio notifications
2. /ws/ptt - For push-to-talk functionality
"""

import logging
import json
import base64
import io
import tempfile
import os
import threading
import time
from flask_sock import Sock
from pydub import AudioSegment

logger = logging.getLogger(__name__)

# Global variables for different types of clients
# Using dictionaries to store clients with their IDs as keys for better tracking
audio_clients = {}  # Clients connected to /ws/audio endpoint
ptt_clients = {}    # Clients connected to /ws/ptt endpoint
audio_clients_lock = threading.Lock()
ptt_clients_lock = threading.Lock()

def setup_websocket(app, audio_player):
    """Setup WebSocket server for Flask application with multiple endpoints.
    
    Args:
        app: Flask application
        audio_player: AudioPlayer instance for playing audio
    """
    # Configure Flask-Sock with more permissive settings for Replit environment
    sock = Sock(app)
    
    # Set basic configuration options that are supported by the Flask-Sock library
    app.config['SOCK_SERVER_OPTIONS'] = {
        'ping_interval': 25,  # Send ping frames every 25 seconds
        'max_message_size': 16 * 1024 * 1024  # 16MB max message size
    }
    
    # Start a background thread for sending periodic keepalive pings to all clients
    keepalive_thread = threading.Thread(target=run_keepalive_pings, daemon=True)
    keepalive_thread.start()
    
    @sock.route('/ws/audio')
    def handle_audio_websocket(ws):
        """Handle WebSocket connections for audio playback notifications."""
        client_id = id(ws)
        logger.info(f"New audio WebSocket client connected: {client_id}")
        
        # Send a welcome message to confirm connection
        try:
            welcome_message = {
                'type': 'welcome',
                'message': 'Connected to Prayer Alarm System (Audio Channel)',
                'server_time': int(time.time() * 1000),
                'channel': 'audio'
            }
            ws.send(json.dumps(welcome_message))
            logger.info(f"Sent welcome message to audio client {client_id}")
        except Exception as e:
            logger.error(f"Error sending welcome message to audio client: {str(e)}")
        
        with audio_clients_lock:
            # Store client with its ID as the key
            audio_clients[client_id] = ws
        
        try:
            # Keep connection alive and process messages
            while True:
                # Use a timeout to prevent blocking indefinitely
                message = ws.receive(timeout=30)
                
                if message is None:
                    logger.info(f"Audio client {client_id} connection closed gracefully")
                    break
                
                try:
                    # Process messages for the audio channel (like play requests, volume changes)
                    process_audio_message(message, audio_player)
                except Exception as e:
                    logger.error(f"Error processing audio message: {str(e)}")
                    continue
        
        except Exception as e:
            error_type = type(e).__name__
            logger.error(f"Audio WebSocket error ({error_type}): {str(e)}")
        
        finally:
            with audio_clients_lock:
                if client_id in audio_clients:
                    del audio_clients[client_id]
            logger.info(f"Audio WebSocket client disconnected: {client_id}")
    
    @sock.route('/ws/ptt')
    def handle_ptt_websocket(ws):
        """Handle WebSocket connections for push-to-talk functionality."""
        client_id = id(ws)
        logger.info(f"New push-to-talk WebSocket client connected: {client_id}")
        
        # Send a welcome message to confirm connection
        try:
            welcome_message = {
                'type': 'welcome',
                'message': 'Connected to Prayer Alarm System (Push-to-Talk Channel)',
                'server_time': int(time.time() * 1000),
                'channel': 'ptt'
            }
            ws.send(json.dumps(welcome_message))
            logger.info(f"Sent welcome message to PTT client {client_id}")
        except Exception as e:
            logger.error(f"Error sending welcome message to PTT client: {str(e)}")
        
        with ptt_clients_lock:
            # Store client with its ID as the key
            ptt_clients[client_id] = ws
        
        try:
            # Keep connection alive and process messages
            while True:
                # Use a timeout to prevent blocking indefinitely
                message = ws.receive(timeout=30)
                
                if message is None:
                    logger.info(f"PTT client {client_id} connection closed gracefully")
                    break
                
                try:
                    # Process messages for the push-to-talk channel
                    process_ptt_message(message, audio_player)
                except Exception as e:
                    logger.error(f"Error processing PTT message: {str(e)}")
                    continue
        
        except Exception as e:
            error_type = type(e).__name__
            logger.error(f"PTT WebSocket error ({error_type}): {str(e)}")
        
        finally:
            with ptt_clients_lock:
                if client_id in ptt_clients:
                    del ptt_clients[client_id]
            logger.info(f"PTT WebSocket client disconnected: {client_id}")

def run_keepalive_pings():
    """Send periodic ping messages to all connected clients to keep connections alive."""
    while True:
        try:
            # Sleep first to allow connections to be established
            time.sleep(15)
            
            ping_message = {
                'type': 'ping',
                'timestamp': int(time.time() * 1000),
                'message': 'keepalive'
            }
            
            # Send to audio clients
            with audio_clients_lock:
                if audio_clients:
                    broadcast_audio_message(ping_message)
                    logger.debug(f"Sent keepalive ping to {len(audio_clients)} audio clients")
            
            # Send to push-to-talk clients
            with ptt_clients_lock:
                if ptt_clients:
                    broadcast_ptt_message(ping_message)
                    logger.debug(f"Sent keepalive ping to {len(ptt_clients)} PTT clients")
                    
        except Exception as e:
            logger.error(f"Error in keepalive thread: {str(e)}")
            # Sleep a bit longer on error to prevent rapid retries
            time.sleep(5)



def convert_webm_to_wav(webm_data):
    """Convert WebM audio data to WAV format.
    
    Args:
        webm_data: WebM audio data as bytes
        
    Returns:
        WAV audio data as bytes
    """
    # Create a temporary file for the WebM data
    with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as temp_webm:
        temp_webm.write(webm_data)
        temp_webm_path = temp_webm.name
    
    try:
        # Convert WebM to WAV using pydub
        audio = AudioSegment.from_file(temp_webm_path, format="webm")
        
        # Create a temporary file for WAV output
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav:
            wav_path = temp_wav.name
        
        # Export to WAV format
        audio.export(wav_path, format="wav")
        
        # Read the WAV file
        with open(wav_path, 'rb') as wav_file:
            wav_data = wav_file.read()
        
        return wav_data
    
    except Exception as e:
        logger.error(f"Error converting WebM to WAV: {str(e)}")
        return None
    
    finally:
        # Clean up temporary files
        temp_webm_path = locals().get('temp_webm_path', None)
        wav_path = locals().get('wav_path', None)
        
        try:
            if temp_webm_path and os.path.exists(temp_webm_path):
                os.unlink(temp_webm_path)
            if wav_path and os.path.exists(wav_path):
                os.unlink(wav_path)
        except Exception as e:
            logger.error(f"Error cleaning up temporary files: {str(e)}")

def convert_pcm_to_wav(pcm_data, sample_rate=16000, channels=1):
    """Convert PCM audio data to WAV format.
    
    Args:
        pcm_data: PCM audio data as bytes
        sample_rate: Sample rate of the PCM data (default: 16000)
        channels: Number of channels (1=mono, 2=stereo) (default: 1)
        
    Returns:
        WAV audio data as bytes
    """
    try:
        # The WAV file format requires a header followed by the PCM data
        # We'll use pydub to create a proper WAV file from the raw PCM data
        
        # First, write the PCM data to a temporary file
        with tempfile.NamedTemporaryFile(suffix='.pcm', delete=False) as temp_pcm:
            temp_pcm.write(pcm_data)
            temp_pcm_path = temp_pcm.name
            
        # Create an AudioSegment from the raw PCM data
        # For PCM 16-bit, we need to specify the format as 's16le' (signed 16-bit little-endian)
        sample_width = 2  # 16-bit = 2 bytes per sample
        audio = AudioSegment.from_file(
            temp_pcm_path,
            format="raw",
            sample_width=sample_width,
            channels=channels,
            frame_rate=sample_rate
        )
        
        # Create a temporary file for WAV output
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav:
            wav_path = temp_wav.name
        
        # Export to WAV format
        audio.export(wav_path, format="wav")
        
        # Read the WAV file
        with open(wav_path, 'rb') as wav_file:
            wav_data = wav_file.read()
        
        return wav_data
    
    except Exception as e:
        logger.error(f"Error converting PCM to WAV: {str(e)}")
        return None
    
    finally:
        # Clean up temporary files
        temp_pcm_path = locals().get('temp_pcm_path', None)
        wav_path = locals().get('wav_path', None)
        
        try:
            if temp_pcm_path and os.path.exists(temp_pcm_path):
                os.unlink(temp_pcm_path)
            if wav_path and os.path.exists(wav_path):
                os.unlink(wav_path)
        except Exception as e:
            logger.error(f"Error cleaning up temporary files: {str(e)}")

def process_audio_message(message, audio_player):
    """Process incoming WebSocket message from the audio channel.
    
    Args:
        message: JSON message as string
        audio_player: AudioPlayer instance for playing audio
    """
    # Process the audio message in a separate thread to avoid blocking the WebSocket connection
    def process_message_thread():
        try:
            data = json.loads(message)
            message_type = data.get('type')
            
            # Handle ping messages with immediate pong response
            if message_type == 'ping':
                logger.debug("Received ping message on audio channel, sending pong")
                timestamp = data.get('timestamp', 0)
                pong_message = {
                    'type': 'pong',
                    'timestamp': timestamp,
                    'server_time': int(time.time() * 1000),
                    'channel': 'audio'
                }
                # Send pong response to audio clients
                broadcast_audio_message(pong_message)
                return
        except Exception as e:
            logger.error(f"Error in audio message processing thread: {str(e)}")
    
    # Start the processing thread
    processing_thread = threading.Thread(target=process_message_thread)
    processing_thread.daemon = True
    processing_thread.start()
    
    # Continue with the original function for backward compatibility
    try:
        data = json.loads(message)
        message_type = data.get('type')
        
        # Handle ping messages with immediate pong response
        if message_type == 'ping':
            logger.debug("Received ping message on audio channel, sending pong")
            timestamp = data.get('timestamp', 0)
            pong_message = {
                'type': 'pong',
                'timestamp': timestamp,
                'server_time': int(time.time() * 1000),
                'channel': 'audio'
            }
            # Send pong response to audio clients
            broadcast_audio_message(pong_message)
            return
        
        elif message_type == 'play_sound':
            # Play a sound file on the server
            sound_file = data.get('file_path')
            sound_priority = data.get('priority', audio_player.PRIORITY_ALARM)
            
            if sound_file:
                logger.info(f"Playing sound file: {sound_file} with priority {sound_priority}")
                audio_player.play_file(sound_file, priority=sound_priority)
                
                # Notify all audio clients about the playback
                notify_message = {
                    'type': 'audio_status_change',
                    'status': 'playing',
                    'file': sound_file,
                    'timestamp': int(time.time() * 1000)
                }
                broadcast_audio_message(notify_message)
            else:
                logger.warning("Received play_sound message with no file path")
        
        elif message_type == 'play_tts':
            # Play text-to-speech
            tts_text = data.get('text')
            tts_priority = data.get('priority', audio_player.PRIORITY_ALARM)
            
            if tts_text:
                logger.info(f"Playing TTS: '{tts_text}' with priority {tts_priority}")
                audio_player.play_tts(tts_text, priority=tts_priority)
                
                # Notify all audio clients about the TTS playback
                notify_message = {
                    'type': 'audio_status_change',
                    'status': 'playing_tts',
                    'text': tts_text,
                    'timestamp': int(time.time() * 1000)
                }
                broadcast_audio_message(notify_message)
            else:
                logger.warning("Received play_tts message with no text")
        
        elif message_type == 'stop_audio':
            # Stop all audio playback
            logger.info("Stopping all audio playback via WebSocket command")
            audio_player.stop()
            
            # Notify all audio clients
            notify_message = {
                'type': 'audio_status_change',
                'status': 'stopped',
                'timestamp': int(time.time() * 1000)
            }
            broadcast_audio_message(notify_message)
            
        elif message_type == 'client_connect':
            # Client is reporting that it has connected to the audio channel
            client_info = data.get('client_info', {})
            logger.info(f"Audio client connected: {client_info}")
            
            # Send an acknowledgement
            ack_message = {
                'type': 'connect_ack',
                'server_time': int(time.time() * 1000),
                'status': 'connected',
                'channel': 'audio'
            }
            broadcast_audio_message(ack_message)
            
        else:
            logger.warning(f"Unknown audio message type: {message_type}")
    
    except json.JSONDecodeError:
        logger.error("Invalid JSON message on audio channel")
    except Exception as e:
        logger.error(f"Error processing audio message: {str(e)}")


def process_ptt_message(message, audio_player):
    """Process incoming WebSocket message from the push-to-talk channel.
    
    Args:
        message: JSON message as string
        audio_player: AudioPlayer instance for playing audio
    """
    # Create a thread to handle the message processing to avoid blocking the WebSocket connection
    # This is especially important for audio processing which can be CPU-intensive
    def process_message_thread():
        try:
            data = json.loads(message)
            message_type = data.get('type')
            
            # Handle ping messages with immediate pong response
            if message_type == 'ping':
                logger.debug("Received ping message on PTT channel, sending pong")
                timestamp = data.get('timestamp', 0)
                pong_message = {
                    'type': 'pong',
                    'timestamp': timestamp,
                    'server_time': int(time.time() * 1000),
                    'channel': 'ptt'
                }
                # Send pong response to PTT clients
                broadcast_ptt_message(pong_message)
                return
        except Exception as e:
            logger.error(f"Error in PTT message processing thread: {str(e)}")
    
    # Start the processing thread
    processing_thread = threading.Thread(target=process_message_thread)
    processing_thread.daemon = True
    processing_thread.start()
    
    # Continue with the original function for backward compatibility
    try:
        data = json.loads(message)
        message_type = data.get('type')
        
        # Handle ping messages with immediate pong response
        if message_type == 'ping':
            logger.debug("Received ping message on PTT channel, sending pong")
            timestamp = data.get('timestamp', 0)
            pong_message = {
                'type': 'pong',
                'timestamp': timestamp,
                'server_time': int(time.time() * 1000),
                'channel': 'ptt'
            }
            # Send pong response to PTT clients
            broadcast_ptt_message(pong_message)
            return
            
        if message_type == 'ptt_start':
            logger.info("Push-to-talk started")
            # Stop any current playback
            audio_player.stop()
            
            # Notify audio clients that PTT has started
            notify_message = {
                'type': 'ptt_status',
                'status': 'active',
                'timestamp': int(time.time() * 1000)
            }
            broadcast_audio_message(notify_message)
            
        elif message_type == 'ptt_audio':
            # Process audio data
            audio_data = data.get('data')
            audio_format = data.get('format', 'unknown')
            is_interim = data.get('is_interim', False)
            
            if not audio_data:
                logger.warning("Received ptt_audio message with no data")
                return
            
            # Log the audio data receipt
            data_length = len(audio_data) if audio_data else 0
            logger.info(f"Received PTT audio: format={audio_format}, size={data_length}, interim={is_interim}")
                
            try:
                # Decode base64 data
                audio_bytes = base64.b64decode(audio_data)
                logger.info(f"Decoded audio bytes: {len(audio_bytes)} bytes")
                
                # Process the audio based on its format
                if audio_format == 'webm_opus':
                    # Convert WebM/Opus to WAV
                    logger.info("Converting WebM/Opus audio to WAV")
                    
                    # Create a temporary file for the WebM data
                    with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as temp_webm:
                        temp_webm_path = temp_webm.name
                        temp_webm.write(audio_bytes)
                        logger.info(f"Wrote {len(audio_bytes)} bytes to temporary WebM file: {temp_webm_path}")
                    
                    try:
                        # Convert WebM to WAV using pydub with explicit format
                        audio = AudioSegment.from_file(temp_webm_path, format="webm")
                        logger.info(f"Successfully loaded WebM audio: {len(audio)} ms duration")
                        
                        # Create a temporary file for WAV output
                        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav:
                            wav_path = temp_wav.name
                        
                        # Export to WAV format with specific parameters for best compatibility
                        audio.export(
                            wav_path, 
                            format="wav",
                            parameters=["-ac", "1", "-ar", "44100"]  # Mono, 44.1kHz
                        )
                        logger.info(f"Exported WAV to: {wav_path}")
                        
                        # Read the WAV file
                        with open(wav_path, 'rb') as wav_file:
                            wav_data = wav_file.read()
                            logger.info(f"Read {len(wav_data)} bytes from WAV file")
                        
                        # Play the audio with push-to-talk priority
                        logger.info("Sending audio to player...")
                        audio_player.play_push_to_talk(wav_data)
                        
                        # Send acknowledgment of audio receipt
                        ack_message = {
                            'type': 'ptt_acknowledgement',
                            'message': 'Audio received and playing',
                            'timestamp': int(time.time() * 1000),
                            'size': len(wav_data),
                            'format': 'wav'
                        }
                        broadcast_ptt_message(ack_message)
                        
                        # Notify audio clients that PTT audio is playing
                        notify_message = {
                            'type': 'ptt_status',
                            'status': 'playing',
                            'timestamp': int(time.time() * 1000)
                        }
                        broadcast_audio_message(notify_message)
                        
                    except Exception as conv_e:
                        logger.error(f"Error in WebM to WAV conversion: {str(conv_e)}")
                        # Send error notification
                        error_message = {
                            'type': 'ptt_error',
                            'message': f'Failed to convert audio: {str(conv_e)}',
                            'timestamp': int(time.time() * 1000)
                        }
                        broadcast_ptt_message(error_message)
                    
                    finally:
                        # Clean up temporary files
                        try:
                            if os.path.exists(temp_webm_path):
                                os.unlink(temp_webm_path)
                                logger.info(f"Deleted temporary WebM file: {temp_webm_path}")
                            
                            wav_path_local = locals().get('wav_path')
                            if wav_path_local and os.path.exists(wav_path_local):
                                os.unlink(wav_path_local)
                                logger.info(f"Deleted temporary WAV file: {wav_path_local}")
                        except Exception as e:
                            logger.error(f"Error cleaning up temporary files: {str(e)}")
                
                elif audio_format == 'pcm_16bit':
                    # Handle PCM data from Android app
                    logger.info("Processing PCM audio from Android")
                    sample_rate = data.get('sample_rate', 16000)
                    channels = data.get('channels', 1)
                    
                    # Convert PCM to WAV
                    wav_data = convert_pcm_to_wav(audio_bytes, sample_rate, channels)
                    if wav_data:
                        logger.info(f"Successfully converted PCM to WAV: {len(wav_data)} bytes")
                        audio_player.play_push_to_talk(wav_data)
                        
                        # Send acknowledgment 
                        ack_message = {
                            'type': 'ptt_acknowledgement',
                            'message': 'PCM audio received and playing',
                            'timestamp': int(time.time() * 1000),
                            'size': len(wav_data)
                        }
                        broadcast_ptt_message(ack_message)
                    else:
                        logger.error("Failed to convert PCM to WAV")
                        # Send error notification
                        error_message = {
                            'type': 'ptt_error',
                            'message': 'Failed to convert PCM audio format',
                            'timestamp': int(time.time() * 1000)
                        }
                        broadcast_ptt_message(error_message)
                
                else:
                    # Try to play directly as fallback
                    logger.info(f"Trying to play PTT audio with format: {audio_format}")
                    audio_player.play_push_to_talk(audio_bytes)
                    
                    # Send acknowledgment
                    ack_message = {
                        'type': 'ptt_acknowledgement',
                        'message': f'Raw audio with format {audio_format} received and playing',
                        'timestamp': int(time.time() * 1000),
                        'size': len(audio_bytes)
                    }
                    broadcast_ptt_message(ack_message)
            except Exception as e:
                logger.error(f"Error processing PTT audio: {str(e)}")
                # Send error notification
                error_message = {
                    'type': 'ptt_error',
                    'message': f'Server error: {str(e)}',
                    'timestamp': int(time.time() * 1000)
                }
                broadcast_ptt_message(error_message)
        
        elif message_type == 'ptt_stop':
            logger.info("Push-to-talk stopped")
            
            # Notify audio clients that PTT has stopped
            notify_message = {
                'type': 'ptt_status',
                'status': 'inactive',
                'timestamp': int(time.time() * 1000)
            }
            broadcast_audio_message(notify_message)
            
        elif message_type == 'client_connect':
            # Client is reporting that it has connected to the PTT channel
            client_info = data.get('client_info', {})
            logger.info(f"PTT client connected: {client_info}")
            
            # Send an acknowledgement
            ack_message = {
                'type': 'connect_ack',
                'server_time': int(time.time() * 1000),
                'status': 'connected',
                'channel': 'ptt'
            }
            broadcast_ptt_message(ack_message)
            
        else:
            logger.warning(f"Unknown PTT message type: {message_type}")
    
    except json.JSONDecodeError:
        logger.error("Invalid JSON message on PTT channel")
    except Exception as e:
        logger.error(f"Error processing PTT message: {str(e)}")


def broadcast_audio_message(message):
    """Broadcast a message to all connected audio clients.
    
    Args:
        message: JSON message as string or dict
    """
    if isinstance(message, dict):
        message = json.dumps(message)
    
    with audio_clients_lock:
        disconnected_client_ids = set()
        
        # Iterate over items to get both client_id and websocket object
        for client_id, ws in list(audio_clients.items()):
            try:
                ws.send(message)
            except Exception as e:
                logger.error(f"Error sending message to audio client {client_id}: {str(e)}")
                disconnected_client_ids.add(client_id)
        
        # Remove disconnected clients
        for client_id in disconnected_client_ids:
            if client_id in audio_clients:
                del audio_clients[client_id]
                logger.info(f"Removed disconnected audio client: {client_id}")
                
        # Log active connection count
        if audio_clients:
            logger.debug(f"Active audio WebSocket connections: {len(audio_clients)}")


def broadcast_ptt_message(message):
    """Broadcast a message to all connected push-to-talk clients.
    
    Args:
        message: JSON message as string or dict
    """
    if isinstance(message, dict):
        message = json.dumps(message)
    
    with ptt_clients_lock:
        disconnected_client_ids = set()
        
        # Iterate over items to get both client_id and websocket object
        for client_id, ws in list(ptt_clients.items()):
            try:
                ws.send(message)
            except Exception as e:
                logger.error(f"Error sending message to PTT client {client_id}: {str(e)}")
                disconnected_client_ids.add(client_id)
        
        # Remove disconnected clients
        for client_id in disconnected_client_ids:
            if client_id in ptt_clients:
                del ptt_clients[client_id]
                logger.info(f"Removed disconnected PTT client: {client_id}")
                
        # Log active connection count
        if ptt_clients:
            logger.debug(f"Active PTT WebSocket connections: {len(ptt_clients)}")
