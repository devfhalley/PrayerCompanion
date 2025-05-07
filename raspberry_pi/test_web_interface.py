#!/usr/bin/env python3
"""
Test file for web interface without database dependencies.
This script provides a simple Flask server to test the web interface.
"""

import os
import logging
from flask import Flask, render_template, redirect, url_for, jsonify, request

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_web_interface')

# Create Flask app
app = Flask(__name__)

# Basic routes
@app.route('/')
def home():
    """Redirect to web home."""
    return redirect(url_for('web_home'))

@app.route('/web')
def web_redirect():
    """Redirect to web home."""
    return redirect(url_for('web_home'))

@app.route('/web/home')
def web_home():
    """Web interface home page."""
    return render_template('test_web_home.html')

@app.route('/web/push-to-talk')
def web_push_to_talk():
    """Web interface push-to-talk page."""
    return render_template('push_to_talk.html')

@app.route('/web/settings')
def web_settings():
    """Web interface settings page."""
    return "Settings Page (Test)"

@app.route('/web/alarms')
def web_alarms():
    """Web interface alarms page."""
    return "Alarms Page (Test)"

@app.route('/web/prayer-times')
def web_prayer_times():
    """Web interface prayer times page."""
    return "Prayer Times Page (Test)"

@app.route('/web/murattal')
def web_murattal():
    """Web interface murattal page."""
    return "Murattal Page (Test)"

# API endpoints
@app.route('/api/status')
def get_status():
    """Get server status."""
    return jsonify({
        "status": "ok",
        "audio_playing": False,
        "audio_type": "None"
    })

# Add cache-control headers for static files
@app.after_request
def add_cache_control(response):
    # Apply to HTML, CSS, and JS responses
    if response.mimetype in ['text/html', 'text/css', 'application/javascript']:
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response

# Custom static file handler with no-cache headers
@app.route('/static-nocache/<path:filename>')
def custom_static(filename):
    """Custom static file handler with cache busting."""
    from flask import send_from_directory, Response
    
    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
    logger.info(f"Requested static file: {filename}")
    
    try:
        response = send_from_directory(static_dir, filename)
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    except Exception as e:
        logger.error(f"Error serving static file {filename}: {str(e)}")
        return Response(f"Error: {str(e)}", status=500)

if __name__ == '__main__':
    logger.info("Starting test web interface server")
    app.run(host='0.0.0.0', port=5000, debug=False)