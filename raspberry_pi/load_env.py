"""
Environment variables loader for Prayer Alarm System.
This module loads environment variables from a .env file if present.
"""

import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def load_env_vars():
    """Load environment variables from .env file if it exists."""
    env_path = Path('.env')
    if env_path.exists():
        logger.info("Loading environment variables from .env file")
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                    
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()
                logger.info(f"Set environment variable: {key.strip()}")
    else:
        logger.info("No .env file found, using system environment variables")
    
    # Log WebSocket settings
    enable_websockets = os.environ.get('ENABLE_WEBSOCKETS', 'false').lower() == 'true'
    bypass_replit_check = os.environ.get('BYPASS_REPLIT_CHECK', 'false').lower() == 'true'
    
    logger.info(f"WebSocket settings from environment: ENABLE_WEBSOCKETS={enable_websockets}, BYPASS_REPLIT_CHECK={bypass_replit_check}")