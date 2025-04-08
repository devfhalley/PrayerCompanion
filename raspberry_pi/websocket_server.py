#!/usr/bin/env python3
"""
WebSocket server module for Raspberry Pi Prayer Alarm System.
This module handles real-time communication for push-to-talk feature.
"""

import logging
import json
import base64
import io
import threading
from flask_sock import Sock

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

def process_message(message, audio_player):
    """Process incoming WebSocket message.
    
    Args:
        message: JSON message as string
        audio_player: AudioPlayer instance for playing audio
    """
    try:
        data = json.loads(message)
        message_type = data.get('type')
        
        if message_type == 'ptt_start':
            logger.info("Push-to-talk started")
            # Stop any current playback
            audio_player.stop()
            
        elif message_type == 'ptt_audio':
            # Process audio data
            audio_data = data.get('data')
            if audio_data:
                audio_bytes = base64.b64decode(audio_data)
                audio_player.play_bytes(audio_bytes)
        
        elif message_type == 'ptt_stop':
            logger.info("Push-to-talk stopped")
            
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
