#!/usr/bin/env python3
"""
WebSocket server module for Raspberry Pi Prayer Alarm System.
This module handles real-time communication for push-to-talk feature.
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

# Global variables
clients = set()
clients_lock = threading.Lock()

def setup_websocket(app, audio_player):
    """Setup WebSocket server for Flask application.
    
    Args:
        app: Flask application
        audio_player: AudioPlayer instance for playing audio
    """
    sock = Sock(app)
    
    @sock.route('/ws')
    def handle_websocket(ws):
        """Handle WebSocket connections."""
        client_id = id(ws)
        logger.info(f"New WebSocket client connected: {client_id}")
        
        with clients_lock:
            clients.add(ws)
        
        try:
            # Keep connection alive and process messages
            while True:
                message = ws.receive()
                if message is None:
                    break
                
                try:
                    process_message(message, audio_player)
                except Exception as e:
                    logger.error(f"Error processing message: {str(e)}")
        
        except Exception as e:
            logger.error(f"WebSocket error: {str(e)}")
        
        finally:
            with clients_lock:
                if ws in clients:
                    clients.remove(ws)
            logger.info(f"WebSocket client disconnected: {client_id}")

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

def broadcast_message(message):
    """Broadcast a message to all connected clients.
    
    Args:
        message: JSON message as string or dict
    """
    if isinstance(message, dict):
        message = json.dumps(message)
    
    with clients_lock:
        disconnected_clients = set()
        
        for client in clients:
            try:
                client.send(message)
            except Exception as e:
                logger.error(f"Error sending message to client: {str(e)}")
                disconnected_clients.add(client)
        
        # Remove disconnected clients
        for client in disconnected_clients:
            clients.remove(client)
            logger.info(f"Removed disconnected client: {id(client)}")
