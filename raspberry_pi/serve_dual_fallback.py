#!/usr/bin/env python3
"""
Server launcher for Raspberry Pi Prayer Alarm System with fallback if the database is not available.
This script launches the test web interface if the PostgreSQL database is not available.
"""

import os
import threading
import time
import logging
import sys
import tempfile
from datetime import datetime
from pathlib import Path
import psycopg2
import traceback

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('server')

# First check if PostgreSQL is available
def check_postgres_connection():
    """Check if PostgreSQL is available."""
    try:
        # Get connection parameters from environment
        db_url = os.environ.get('DATABASE_URL')
        
        # Fallback for older versions or if not set
        if not db_url:
            # Try to build connection string from individual PostgreSQL environment variables
            pguser = os.environ.get('PGUSER')
            pgpassword = os.environ.get('PGPASSWORD')
            pghost = os.environ.get('PGHOST')
            pgport = os.environ.get('PGPORT', '5432')
            pgdatabase = os.environ.get('PGDATABASE')
            
            if pguser and pgpassword and pghost and pgdatabase:
                db_url = f"postgresql://{pguser}:{pgpassword}@{pghost}:{pgport}/{pgdatabase}"
                logger.info(f"Built connection string from individual PostgreSQL environment variables")
            else:
                return False, "DATABASE_URL and individual PostgreSQL environment variables not set"
        
        logger.info("Testing PostgreSQL database connection...")
        # Create a new connection
        conn = psycopg2.connect(db_url)
        conn.close()
        return True, "PostgreSQL database connection successful"
    except Exception as e:
        logger.error(f"PostgreSQL connection error: {e}")
        return False, str(e)

# Try to connect to PostgreSQL
postgres_available, postgres_message = check_postgres_connection()

if postgres_available:
    # PostgreSQL is available, use the full app
    logger.info("PostgreSQL is available, starting full application")
    try:
        from app import app, start_schedulers
        
        # Start schedulers in a separate thread
        def run_schedulers():
            start_schedulers()
            logger.info("Schedulers started successfully")
        
        # Start HTTP server with Flask's built-in server
        def run_http_server():
            logger.info("Starting HTTP server on port 5000 with Flask's built-in server")
            # Setting threaded=True is important for WebSocket support
            app.run(host='0.0.0.0', port=5000, threaded=True, debug=False)
        
        if __name__ == '__main__':
            # Start schedulers in a separate thread
            threading.Thread(target=run_schedulers, daemon=True).start()
            
            # Give schedulers time to initialize
            time.sleep(2)
            
            # Use Flask's built-in server to support WebSockets
            run_http_server()
            
    except Exception as e:
        logger.error(f"Error starting full application: {e}")
        logger.error(traceback.format_exc())
        postgres_available = False
        postgres_message = f"Error starting full application: {e}"

if not postgres_available:
    # PostgreSQL is not available, use the test web interface
    logger.warning(f"PostgreSQL is not available: {postgres_message}")
    logger.warning("Starting test web interface as fallback")
    try:
        from test_web_interface import app
        
        if __name__ == '__main__':
            logger.info("Starting test web interface server on port 5001")
            app.run(host='0.0.0.0', port=5001, debug=False)
            
    except Exception as e:
        logger.error(f"Error starting test web interface: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)