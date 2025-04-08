# Prayer Alarm System

A comprehensive Islamic prayer alarm and reminder system with two main components:
1. An Android app that serves as the controller
2. A Raspberry Pi that functions as a headless speaker device

## System Overview

The Prayer Alarm System provides the following features:

- **Islamic Prayer Time Scheduling**: Automatically fetches and announces prayer times for Jakarta, Indonesia using the Aladhan API
- **Custom Alarm System**: Set alarms for specific times/days with repeat options and custom sounds (MP3 files or text-to-speech)
- **Push-to-Talk**: Speak through the Android app and have your voice played through the Raspberry Pi speaker in real-time

## Project Structure

The project is organized into two main components:

```
/android_app      - Android controller application
  /app/src/main   - Main Android application source code
    /java         - Java source files
    /res          - Android resource files
/raspberry_pi     - Raspberry Pi server for audio playback
  /sounds         - Default sound files for alarms and adhans
  app.py          - Main Flask server application
  audio_player.py - Audio playback module
  prayer_scheduler.py - Prayer time scheduling module
  alarm_scheduler.py - Alarm scheduling module
  websocket_server.py - WebSocket server for push-to-talk
  database.py     - SQLite database interface
  models.py       - Data models
  config.py       - Configuration settings
/build            - Contains the Android APK and build information
```

## Raspberry Pi Server Features

The Raspberry Pi component serves as a headless speaker device with the following capabilities:

- **RESTful API**: Provides endpoints for managing alarms and prayer times
- **WebSocket Server**: Enables real-time push-to-talk functionality
- **Audio Playback**: Plays MP3 files and text-to-speech using pygame
- **Scheduling**: Manages both prayer time notifications and custom alarms
- **Database**: Stores alarm and prayer time data in SQLite

## Android App Features

The Android application serves as a controller with the following capabilities:

- **Alarm Management**: Create, edit, and delete alarms with various configuration options
- **Prayer Time Visualization**: View today's prayer times and upcoming prayers
- **Push-to-Talk Interface**: Speak through your phone to the Raspberry Pi speaker
- **Settings**: Configure server connection details and preferences
- **Room Database**: Stores a local cache of alarms and prayer times

## API Endpoints

The Raspberry Pi server exposes the following API endpoints:

- `GET /status` - Check server status
- `GET /alarms` - Get all alarms
- `POST /alarms` - Add or update an alarm
- `DELETE /alarms/{id}` - Delete an alarm
- `POST /alarms/{id}/disable` - Disable an alarm
- `GET /prayer-times` - Get prayer times for a specific date
- `POST /prayer-times/refresh` - Force refresh of prayer times from API
- `POST /stop-audio` - Stop any playing audio
- `WebSocket /ws` - WebSocket endpoint for push-to-talk

## Setup and Installation

### Raspberry Pi Setup

1. Clone the repository to your Raspberry Pi
2. Install the required dependencies:
   ```
   pip3 install flask flask_sock gtts pydub pygame requests schedule
   ```
3. Run the server manually (for testing):
   ```
   cd raspberry_pi
   python3 app.py
   ```

### Running as a System Service

For automatic startup at boot time, you can install the application as a systemd service:

1. Use the test script to verify your setup:
   ```
   cd raspberry_pi
   ./test_service.sh
   ```

2. Follow the installation instructions in the `raspberry_pi/INSTALL_SERVICE.md` file to set up the systemd service.

Once installed as a service, the Prayer Alarm System will automatically start when your Raspberry Pi boots up, and will restart if it crashes.

### Android App Setup

1. Import the android_app directory into Android Studio
2. Configure your Raspberry Pi's IP address and port in the settings
3. Build and install the APK on your Android device
