#!/usr/bin/env python3
"""
WebSocket server module for Raspberry Pi Prayer Alarm System.
This module handles real-time communication with dual WebSocket support:
1. Audio status WebSocket for real-time audio playback status
2. Push-to-talk WebSocket for voice communication
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

# Global variables for dual WebSocket system
# Using dictionaries to store clients with their IDs as keys for better tracking
ptt_clients = {}  # Push-to-talk clients
audio_clients = {}  # Audio status clients
clients = {}       # Legacy clients dictionary for backward compatibility
ptt_clients_lock = threading.Lock()
audio_clients_lock = threading.Lock()

def setup_websocket(app, audio_player):
    """Setup dual WebSocket server for Flask application.
    
    Args:
        app: Flask application
        audio_player: AudioPlayer instance for playing audio
    """
    # Check if WebSockets are forcibly enabled via environment variables
    enable_websockets = os.environ.get('ENABLE_WEBSOCKETS', 'false').lower() == 'true'
    bypass_replit_check = os.environ.get('BYPASS_REPLIT_CHECK', 'false').lower() == 'true'
    
    # Update app config with the environment settings
    app.config['ENABLE_WEBSOCKETS'] = enable_websockets
    app.config['BYPASS_REPLIT_CHECK'] = bypass_replit_check
    
    logger.info(f"WebSocket environment settings: ENABLE_WEBSOCKETS={enable_websockets}, BYPASS_REPLIT_CHECK={bypass_replit_check}")
    
    if enable_websockets:
        app.logger.info("WebSockets forcibly enabled via environment variables")
    
    if bypass_replit_check:
        app.logger.info("Replit environment check bypassed via environment variables")
    
    # Make these available to templates
    @app.context_processor
    def inject_websocket_config():
        return {
            'force_enable_websockets': enable_websockets,
            'bypass_replit_check': bypass_replit_check
        }
    # Configure Flask-Sock with more permissive settings for Replit environment
    sock = Sock(app)
    
    # Set WebSocket options for better reliability in Replit environment
    sock.max_message_size = 16 * 1024 * 1024  # 16MB max message size
    
    # Set basic configuration options that are supported by the Flask-Sock library
    # Note: Flask-Sock has limited configuration options compared to other WebSocket libraries
    app.config['SOCK_SERVER_OPTIONS'] = {
        'ping_interval': 25  # Send ping frames every 25 seconds
    }
    
    # Start a background thread for sending periodic keepalive pings
    keepalive_thread = threading.Thread(target=run_keepalive_pings, daemon=True)
    keepalive_thread.start()
    
    @sock.route('/ws/ptt')
    def handle_ptt_websocket(ws):
        """Handle Push-to-Talk WebSocket connections."""
        client_id = id(ws)
        logger.info(f"New Push-to-Talk WebSocket client connected: {client_id}")
        
        # Send a welcome message to confirm connection
        try:
            welcome_message = {
                'type': 'welcome',
                'message': 'Connected to Prayer Alarm System (Push-to-Talk)',
                'server_time': int(time.time() * 1000),
                'socket_type': 'ptt'
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
                # This helps detect disconnections more quickly
                message = ws.receive(timeout=30)
                
                if message is None:
                    logger.info(f"PTT client {client_id} connection closed gracefully")
                    break
                
                try:
                    process_ptt_message(message, audio_player)
                except Exception as e:
                    logger.error(f"Error processing PTT message: {str(e)}")
                    # Continue the loop even if there's an error processing a message
                    continue
        
        except Exception as e:
            # Log the specific error type to help with debugging
            error_type = type(e).__name__
            logger.error(f"PTT WebSocket error ({error_type}): {str(e)}")
        
        finally:
            with ptt_clients_lock:
                # Remove client using its ID
                if client_id in ptt_clients:
                    del ptt_clients[client_id]
            logger.info(f"PTT WebSocket client disconnected: {client_id}")
            
    @sock.route('/ws/audio')
    def handle_audio_websocket(ws):
        """Handle Audio Status WebSocket connections."""
        client_id = id(ws)
        logger.info(f"New Audio Status WebSocket client connected: {client_id}")
        
        # Send a welcome message to confirm connection
        try:
            welcome_message = {
                'type': 'welcome',
                'message': 'Connected to Prayer Alarm System (Audio Status)',
                'server_time': int(time.time() * 1000),
                'socket_type': 'audio'
            }
            ws.send(json.dumps(welcome_message))
            logger.info(f"Sent welcome message to Audio Status client {client_id}")
            
            # Send the current audio status immediately after connection
            is_playing = audio_player.is_playing()
            current_audio = audio_player.get_current_audio()
            current_priority = audio_player.get_current_priority()
            
            status_message = {
                'type': 'audio_status',
                'is_playing': is_playing,
                'current_audio': current_audio,
                'priority': current_priority,
                'timestamp': int(time.time() * 1000)
            }
            ws.send(json.dumps(status_message))
            
        except Exception as e:
            logger.error(f"Error sending welcome message to Audio Status client: {str(e)}")
        
        with audio_clients_lock:
            # Store client with its ID as the key
            audio_clients[client_id] = ws
        
        try:
            # Keep connection alive and process messages
            while True:
                # Use a timeout to prevent blocking indefinitely
                # This helps detect disconnections more quickly
                message = ws.receive(timeout=30)
                
                if message is None:
                    logger.info(f"Audio Status client {client_id} connection closed gracefully")
                    break
                
                try:
                    process_audio_message(message, audio_player)
                except Exception as e:
                    logger.error(f"Error processing Audio Status message: {str(e)}")
                    # Continue the loop even if there's an error processing a message
                    continue
        
        except Exception as e:
            # Log the specific error type to help with debugging
            error_type = type(e).__name__
            logger.error(f"Audio Status WebSocket error ({error_type}): {str(e)}")
        
        finally:
            with audio_clients_lock:
                # Remove client using its ID
                if client_id in audio_clients:
                    del audio_clients[client_id]
            logger.info(f"Audio Status WebSocket client disconnected: {client_id}")
    
    # For backwards compatibility - redirect old endpoint to PTT
    @sock.route('/ws')
    def handle_legacy_websocket(ws):
        """Handle legacy WebSocket connections - redirect to PTT."""
        client_id = id(ws)
        logger.info(f"Legacy WebSocket client connected: {client_id}, redirecting to PTT")
        handle_ptt_websocket(ws)
    
    # Add debugging routes to check WebSocket availability
    @app.route('/ws-check')
    def ws_check():
        """Simple endpoint to check WebSocket routes."""
        routes = []
        for rule in app.url_map.iter_rules():
            if 'websocket' in str(rule.endpoint).lower() or '/ws' in str(rule):
                routes.append(str(rule))
        
        return {
            'status': 'WebSocket routes available',
            'routes': routes,
            'clients': {
                'ptt': len(ptt_clients),
                'audio': len(audio_clients),
                'legacy': len(clients)
            },
            'timestamp': int(time.time() * 1000)
        }

def run_keepalive_pings():
    """Send periodic ping messages to all connected clients to keep connections alive."""
    while True:
        try:
            # Sleep first to allow connections to be established
            time.sleep(15)
            
            current_time = int(time.time() * 1000)
            
            # Create ping messages for each socket type
            ptt_ping_message = {
                'type': 'ping',
                'timestamp': current_time,
                'message': 'keepalive',
                'socket_type': 'ptt'
            }
            
            audio_ping_message = {
                'type': 'ping',
                'timestamp': current_time,
                'message': 'keepalive',
                'socket_type': 'audio'
            }
            
            # Send to PTT clients
            with ptt_clients_lock:
                if ptt_clients:
                    broadcast_ptt_message(ptt_ping_message)
                    logger.debug(f"Sent keepalive ping to {len(ptt_clients)} PTT clients")
            
            # Send to Audio Status clients
            with audio_clients_lock:
                if audio_clients:
                    broadcast_audio_message(audio_ping_message)
                    logger.debug(f"Sent keepalive ping to {len(audio_clients)} Audio Status clients")
                    
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
        try:
            if 'temp_webm_path' in locals():
                os.unlink(temp_webm_path)
            if 'wav_path' in locals():
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
        try:
            if 'temp_pcm_path' in locals():
                os.unlink(temp_pcm_path)
            if 'wav_path' in locals():
                os.unlink(wav_path)
        except Exception as e:
            logger.error(f"Error cleaning up temporary files: {str(e)}")

def process_message(message, audio_player):
    """Process incoming WebSocket message.
    
    Args:
        message: JSON message as string
        audio_player: AudioPlayer instance for playing audio
    """
    try:
        data = json.loads(message)
        message_type = data.get('type')
        
        # Handle ping messages with immediate pong response
        if message_type == 'ping':
            logger.debug("Received ping message, sending pong")
            timestamp = data.get('timestamp', 0)
            pong_message = {
                'type': 'pong',
                'timestamp': timestamp,
                'server_time': int(time.time() * 1000)
            }
            # Send pong response to all clients - helps with keepalive
            broadcast_message(pong_message)
            return
            
        if message_type == 'ptt_start':
            logger.info("Push-to-talk started")
            # Stop any current playback
            audio_player.stop()
            
        elif message_type == 'ptt_audio':
            # Process audio data
            audio_data = data.get('data')
            audio_format = data.get('format', 'unknown')
            
            if not audio_data:
                logger.warning("Received ptt_audio message with no data")
                return
                
            # Decode base64 data
            audio_bytes = base64.b64decode(audio_data)
            
            if audio_format == 'webm_opus':
                # Convert WebM/Opus to WAV
                logger.info("Converting WebM/Opus audio to WAV")
                wav_data = convert_webm_to_wav(audio_bytes)
                if wav_data:
                    audio_player.play_bytes(wav_data)
                else:
                    logger.error("Failed to convert WebM to WAV")
            elif audio_format == 'pcm_16bit':
                # Handle PCM data from Android app
                logger.info("Processing PCM audio from Android")
                sample_rate = data.get('sample_rate', 16000)
                channels = data.get('channels', 1)
                
                # Convert PCM to WAV
                wav_data = convert_pcm_to_wav(audio_bytes, sample_rate, channels)
                if wav_data:
                    audio_player.play_bytes(wav_data)
                else:
                    logger.error("Failed to convert PCM to WAV")
            else:
                # Try to play directly as fallback
                logger.info(f"Trying to play audio with format: {audio_format}")
                audio_player.play_bytes(audio_bytes)
        
        elif message_type == 'ptt_stop':
            logger.info("Push-to-talk stopped")
            
        elif message_type == 'client_connect':
            # Client is reporting that it has connected
            client_info = data.get('client_info', {})
            logger.info(f"Client connected: {client_info}")
            
            # Send an acknowledgement
            ack_message = {
                'type': 'connect_ack',
                'server_time': int(time.time() * 1000),
                'status': 'connected'
            }
            broadcast_message(ack_message)
            
        else:
            logger.warning(f"Unknown message type: {message_type}")
    
    except json.JSONDecodeError:
        logger.error("Invalid JSON message")
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")

def process_ptt_message(message, audio_player):
    """Process incoming Push-to-Talk WebSocket message.
    
    Args:
        message: JSON message as string
        audio_player: AudioPlayer instance for playing audio
    """
    try:
        data = json.loads(message)
        message_type = data.get('type')
        
        # Handle ping messages with immediate pong response
        if message_type == 'ping':
            logger.debug("Received ping message from PTT client, sending pong")
            timestamp = data.get('timestamp', 0)
            pong_message = {
                'type': 'pong',
                'timestamp': timestamp,
                'server_time': int(time.time() * 1000),
                'socket_type': 'ptt'
            }
            # Send pong response to PTT clients
            broadcast_ptt_message(pong_message)
            return
            
        if message_type == 'ptt_start':
            logger.info("Push-to-talk started")
            # Stop any current playback
            audio_player.stop()
            
            # Notify audio status clients that PTT is active
            audio_status_message = {
                'type': 'audio_status_change',
                'status': {
                    'is_playing': True,
                    'audio_type': 'push_to_talk',
                    'timestamp': int(time.time() * 1000)
                }
            }
            broadcast_audio_message(audio_status_message)
            
        elif message_type == 'ptt_audio':
            # Process audio data
            audio_data = data.get('data')
            audio_format = data.get('format', 'unknown')
            
            if not audio_data:
                logger.warning("Received ptt_audio message with no data")
                return
                
            # Decode base64 data
            audio_bytes = base64.b64decode(audio_data)
            
            if audio_format == 'webm_opus':
                # Convert WebM/Opus to WAV
                logger.info("Converting WebM/Opus audio to WAV")
                wav_data = convert_webm_to_wav(audio_bytes)
                if wav_data:
                    audio_player.play_push_to_talk(wav_data)
                else:
                    logger.error("Failed to convert WebM to WAV")
            elif audio_format == 'pcm_16bit':
                # Handle PCM data from Android app
                logger.info("Processing PCM audio from Android")
                sample_rate = data.get('sample_rate', 16000)
                channels = data.get('channels', 1)
                
                # Convert PCM to WAV
                wav_data = convert_pcm_to_wav(audio_bytes, sample_rate, channels)
                if wav_data:
                    audio_player.play_push_to_talk(wav_data)
                else:
                    logger.error("Failed to convert PCM to WAV")
            else:
                # Try to play directly as fallback
                logger.info(f"Trying to play audio with format: {audio_format}")
                audio_player.play_push_to_talk(audio_bytes)
        
        elif message_type == 'ptt_stop':
            logger.info("Push-to-talk stopped")
            
            # Notify audio status clients that PTT has stopped
            audio_status_message = {
                'type': 'audio_status_change',
                'status': {
                    'is_playing': False,
                    'audio_type': None,
                    'timestamp': int(time.time() * 1000)
                }
            }
            broadcast_audio_message(audio_status_message)
            
        elif message_type == 'client_connect':
            # Client is reporting that it has connected
            client_info = data.get('client_info', {})
            logger.info(f"PTT client connected: {client_info}")
            
            # Send an acknowledgement
            ack_message = {
                'type': 'connect_ack',
                'server_time': int(time.time() * 1000),
                'status': 'connected',
                'socket_type': 'ptt'
            }
            broadcast_ptt_message(ack_message)
            
        else:
            logger.warning(f"Unknown PTT message type: {message_type}")
    
    except json.JSONDecodeError:
        logger.error("Invalid JSON message in PTT socket")
    except Exception as e:
        logger.error(f"Error processing PTT message: {str(e)}")

def process_audio_message(message, audio_player):
    """Process incoming Audio Status WebSocket message.
    
    Args:
        message: JSON message as string
        audio_player: AudioPlayer instance for playing audio
    """
    try:
        data = json.loads(message)
        message_type = data.get('type')
        
        # Handle ping messages with immediate pong response
        if message_type == 'ping':
            logger.debug("Received ping message from audio status client, sending pong")
            timestamp = data.get('timestamp', 0)
            pong_message = {
                'type': 'pong',
                'timestamp': timestamp,
                'server_time': int(time.time() * 1000),
                'socket_type': 'audio'
            }
            # Send pong response to audio status clients
            broadcast_audio_message(pong_message)
            return
            
        if message_type == 'get_audio_status':
            # Client is requesting current audio status
            is_playing = audio_player.is_playing()
            current_audio = audio_player.get_current_audio()
            current_priority = audio_player.get_current_priority()
            
            status_message = {
                'type': 'audio_status',
                'is_playing': is_playing,
                'current_audio': current_audio,
                'priority': current_priority,
                'timestamp': int(time.time() * 1000)
            }
            # Send to the specific client that requested it
            client_id = data.get('client_id')
            if client_id:
                with audio_clients_lock:
                    if client_id in audio_clients:
                        try:
                            audio_clients[client_id].send(json.dumps(status_message))
                        except Exception as e:
                            logger.error(f"Error sending audio status to client {client_id}: {str(e)}")
            else:
                # If no client_id specified, broadcast to all audio clients
                broadcast_audio_message(status_message)
            
        elif message_type == 'client_connect':
            # Client is reporting that it has connected
            client_info = data.get('client_info', {})
            logger.info(f"Audio status client connected: {client_info}")
            
            # Send an acknowledgement
            ack_message = {
                'type': 'connect_ack',
                'server_time': int(time.time() * 1000),
                'status': 'connected',
                'socket_type': 'audio'
            }
            broadcast_audio_message(ack_message)
            
            # Also send current audio status
            is_playing = audio_player.is_playing()
            current_audio = audio_player.get_current_audio()
            current_priority = audio_player.get_current_priority()
            
            status_message = {
                'type': 'audio_status',
                'is_playing': is_playing,
                'current_audio': current_audio,
                'priority': current_priority,
                'timestamp': int(time.time() * 1000)
            }
            broadcast_audio_message(status_message)
            
        elif message_type == 'stop_audio':
            # Client is requesting to stop audio playback
            logger.info("Received request to stop audio playback")
            audio_player.stop()
            
            # Broadcast updated status to all audio clients
            status_message = {
                'type': 'audio_status',
                'is_playing': False,
                'current_audio': None,
                'priority': None,
                'timestamp': int(time.time() * 1000)
            }
            broadcast_audio_message(status_message)
            
        else:
            logger.warning(f"Unknown audio status message type: {message_type}")
    
    except json.JSONDecodeError:
        logger.error("Invalid JSON message in audio status socket")
    except Exception as e:
        logger.error(f"Error processing audio status message: {str(e)}")

def broadcast_ptt_message(message):
    """Broadcast a message to all connected PTT clients.
    
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

def broadcast_audio_message(message):
    """Broadcast a message to all connected audio status clients.
    
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
                logger.error(f"Error sending message to audio status client {client_id}: {str(e)}")
                disconnected_client_ids.add(client_id)
        
        # Remove disconnected clients
        for client_id in disconnected_client_ids:
            if client_id in audio_clients:
                del audio_clients[client_id]
                logger.info(f"Removed disconnected audio status client: {client_id}")
                
        # Log active connection count
        if audio_clients:
            logger.debug(f"Active audio status WebSocket connections: {len(audio_clients)}")

# For backward compatibility with existing code
def broadcast_message(message):
    """Broadcast a message to all connected clients (both PTT and audio).
    
    Args:
        message: JSON message as string or dict
    """
    # Broadcast to both types of clients
    broadcast_ptt_message(message)
    broadcast_audio_message(message)

# For backward compatibility with existing code
clients = {}  # This will be used by existing code expecting the old variable name
clients_lock = threading.Lock()
