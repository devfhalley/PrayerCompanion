#!/usr/bin/env python3
"""
Server launcher for Raspberry Pi Prayer Alarm System.
This script launches the Flask application directly to support WebSockets.
"""

import os
import threading
import time
import logging
from app import app, start_schedulers

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('server')

# Start schedulers
def run_schedulers():
    start_schedulers()
    logger.info("Schedulers started successfully")

# Start HTTP server with Flask's built-in server
def run_http_server():
    logger.info("Starting HTTP server on port 5000 with Flask's built-in server")
    # Setting threaded=True is important for WebSocket support
    app.run(host='0.0.0.0', port=5000, threaded=True, debug=False)

# Start HTTPS server
def run_https_server():
    logger.info("Starting HTTPS server on port 5000")
    ssl_dir = os.path.join(os.path.dirname(__file__), 'ssl')
    cert_path = os.path.join(ssl_dir, 'server.crt')
    key_path = os.path.join(ssl_dir, 'server.key')
    
    if os.path.exists(cert_path) and os.path.exists(key_path):
        app.run(host='0.0.0.0', port=5000, threaded=True, debug=False, 
                ssl_context=(cert_path, key_path))
    else:
        logger.warning("SSL certificates not found, HTTPS server not started")
        logger.warning("Push-to-Talk feature may not work without HTTPS")

if __name__ == '__main__':
    # Start schedulers in a separate thread
    threading.Thread(target=run_schedulers, daemon=True).start()
    
    # Give schedulers time to initialize
    time.sleep(2)
    
    # Use Flask's built-in server to support WebSockets
    run_http_server()