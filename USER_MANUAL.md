# Prayer Alarm System - User Manual

Welcome to the Prayer Alarm System! This comprehensive user manual will guide you through all the features and functionalities of both the Raspberry Pi web interface and the Android application.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Home Screen](#home-screen)
3. [Prayer Times](#prayer-times)
4. [Alarm Management](#alarm-management)
5. [Pre-Adhan Announcement System](#pre-adhan-announcement-system)
6. [Push-to-Talk](#push-to-talk)
7. [Murattal Player](#murattal-player)
8. [YouTube Video Management](#youtube-video-management)
9. [Settings](#settings)
10. [Android App](#android-app)
11. [Troubleshooting](#troubleshooting)

## Getting Started

### Initial Setup

1. **Setting up the Raspberry Pi**:
   - Power on your Raspberry Pi and ensure it's connected to your local network
   - The Prayer Alarm System should start automatically if installed as a system service
   - If not running as a service, navigate to the `raspberry_pi` directory and run `python3 serve_dual.py`

2. **Accessing the Web Interface**:
   - Open a web browser on any device connected to the same network
   - Enter the IP address of your Raspberry Pi followed by port 5000 (e.g., `http://192.168.1.100:5000`)
   - You should see the Prayer Alarm System home page

3. **Setting up the Android App**:
   - Install the Prayer Alarm App on your Android device
   - Open the app and go to Settings
   - Enter the IP address and port of your Raspberry Pi server
   - Choose between HTTP and HTTPS (HTTPS recommended for secure communication)
   - Save your settings and restart the app

## Home Screen

The home screen displays:

- **Current Time**: Shows the current date and time
- **Next Prayer**: Displays the upcoming prayer with a countdown timer
- **System Status**: Indicates if the audio system is currently playing or idle
- **YouTube Videos**: Displays enabled YouTube videos (if configured)
- **Volume Control**: A global volume slider accessible from all pages

### Features:

- **Refresh Button**: Updates the information on the screen
- **Stop Audio Button**: Immediately stops any audio currently playing
- **Navigation Menu**: Access to all other sections of the application

## Prayer Times

The Prayer Times screen displays:

- **Today's Prayer Times**: A list of all five daily prayers (Fajr, Dhuhr, Asr, Maghrib, Isha)
- **Prayer Status**: Indicates whether a prayer time has passed, is upcoming, or is the next prayer
- **Adhan Settings**: Shows which adhan sound is configured for each prayer

### Features:

- **Calendar View**: Toggle to see prayer times for other dates
- **Refresh Button**: Force refresh prayer times from the Aladhan API
- **Test Adhan Button**: Test play the adhan sound for any prayer

## Alarm Management

The Alarms screen displays:

- **All Configured Alarms**: A list of all alarms with their details
- **Alarm Status**: Whether each alarm is enabled or disabled

### Features:

- **Add Alarm**: Create a new alarm with the following options:
  - **Time**: Set the specific time for the alarm
  - **Label**: Add a descriptive label for the alarm
  - **Repeating**: Configure the alarm to repeat on specific days
  - **Sound Options**: Choose between a custom sound or text-to-speech
  - **Custom Sound**: Upload or select an MP3 file for the alarm
  - **Text-to-Speech**: Enter text to be spoken aloud

- **Edit Alarm**: Modify an existing alarm's settings
- **Delete Alarm**: Remove an alarm from the system
- **Enable/Disable**: Toggle an alarm on or off without deleting it
- **Test Alarm**: Preview how the alarm will sound when triggered

## Pre-Adhan Announcement System

The Pre-Adhan settings are found in the Settings page under "Pre-Adhan and Tahrim Sound Settings":

### Features:

- **10-Minute Pre-Adhan**: Configure sounds to play 10 minutes before each prayer
  - Select different sounds for each prayer (Fajr, Dhuhr, Asr, Maghrib, Isha)
  - Choose from available sound files or upload custom sounds
  - Test buttons to preview each sound

- **5-Minute Pre-Adhan**: Configure sounds to play 5 minutes before each prayer
  - Customize separately from the 10-minute announcements
  - Choose from available sound files or upload custom sounds
  - Test buttons to preview each sound

- **Tahrim Sounds**: Configure sounds that play after each pre-adhan announcement
  - Customize for each prayer time
  - Choose from available sound files or upload custom sounds
  - Test buttons to preview each sound

## Push-to-Talk

The Push-to-Talk feature allows you to speak through the Raspberry Pi speaker in real-time:

### Features:

- **Push-to-Talk Button**: Press and hold to record your voice
- **Connection Status**: Shows whether WebSocket connection is established
- **Audio Format Selection**: Automatic format detection and conversion
- **Secure Connection**: Uses WSS (WebSocket Secure) for secure audio transmission

### Using Push-to-Talk:

1. Navigate to the Push-to-Talk screen
2. Press and hold the microphone button
3. Speak into your device's microphone
4. Release the button to stop recording and transmitting

## Murattal Player

The Murattal Player allows you to play Quranic recitations through the Raspberry Pi speaker:

### Features:

- **File Browser**: Browse all available Murattal files
- **Upload Function**: Add new Murattal MP3 files to the collection
- **Playback Controls**: Play, pause, and stop controls
- **File Information**: Display track title and selection status
- **Auto-Pause**: Automatically pauses when a higher priority audio (adhan/alarm) plays

### Using the Murattal Player:

1. Navigate to the Murattal Player screen
2. Select a recitation file from the list
3. Click the play button to start playback
4. Use the stop button to end playback at any time

## YouTube Video Management

The YouTube Video feature allows you to display videos on the home page:

### Features:

- **Add Videos**: Enter YouTube video URLs to add them to the system
- **Edit Videos**: Change video titles or URLs
- **Delete Videos**: Remove videos from the system
- **Enable/Disable**: Control which videos appear on the home page
- **Reorder Videos**: Drag and drop to change the display order

### Managing YouTube Videos:

1. Navigate to the Settings page
2. Scroll to the YouTube Video section
3. Use the Add/Edit/Delete buttons to manage videos
4. Drag and drop videos to reorder them
5. Toggle the enable/disable switch for each video

## Settings

The Settings page allows you to configure various aspects of the system:

### Location Settings:

- **City and Country**: Configure your location for prayer time calculations
- **Calculation Method**: Select the calculation method for prayer times

### Adhan Settings:

- **Default Adhan**: Set the default adhan sound for all prayers
- **Custom Adhans**: Configure specific adhan sounds for individual prayers
- **Upload Adhan**: Add new adhan sound files to the system

### System Preferences:

- **Volume Control**: Adjust the system-wide volume level
- **Auto-Start**: Configure automatic startup options
- **Audio Priority**: Review the system's audio playback priority

## Android App

The Android application provides most of the same features as the web interface, with some mobile-specific enhancements:

### Key Differences:

- **Native Android Interface**: Optimized for mobile screens
- **Push Notifications**: Receive alerts for upcoming prayers and alarms
- **Background Service**: Maintains connection to the Raspberry Pi server
- **Offline Mode**: Caches prayer times and alarms for offline viewing
- **Quick Actions**: Shortcuts for common operations

### Android App Navigation:

- **Home**: Overview of system status and next prayer
- **Prayer Times**: View and manage prayer times
- **Alarms**: Create and manage alarms
- **Push-to-Talk**: Speak through the Raspberry Pi speaker
- **Settings**: Configure app and server settings

## Troubleshooting

### Common Issues:

1. **Cannot connect to Raspberry Pi**:
   - Ensure the Raspberry Pi is powered on and connected to the network
   - Verify the IP address and port settings
   - Check that the Prayer Alarm System service is running

2. **Audio not playing**:
   - Check the volume settings
   - Ensure speakers are properly connected to the Raspberry Pi
   - Restart the Prayer Alarm System service

3. **WebSocket connection issues**:
   - If using HTTPS, ensure certificates are properly configured
   - Try restarting both the server and the client device
   - Check network firewall settings that might block WebSocket connections

4. **Database errors**:
   - Run migrations to ensure all tables are properly created
   - Verify PostgreSQL is running and accessible
   - Check database connection environment variables

5. **Android app not receiving updates**:
   - Verify the server address in app settings
   - Check that background services are allowed to run
   - Ensure the device has internet connectivity

### Support:

For additional support, please refer to the project documentation or contact the system administrator. You can also open an issue on the project repository for technical problems.

## Advanced Features

### Prayer Time API Integration:

The system automatically fetches prayer times from the Aladhan API based on your configured location. You can:

- Force refresh prayer times from the API
- View prayer times for any date
- Configure the calculation method used

### Audio Priority System:

The Prayer Alarm System uses a priority system to determine which audio plays when multiple sources request playback:

1. **Highest Priority**: Adhan announcements
2. **Medium Priority**: Alarms and pre-adhan announcements
3. **Lowest Priority**: Murattal player and other audio

Higher priority audio will interrupt lower priority audio, and the system will not allow lower priority audio to play while higher priority audio is playing.

### Database Migration and Backup:

For system administrators, the system includes tools for:

- Migrating from SQLite to PostgreSQL
- Creating database backups
- Applying schema changes through migrations
- Restoring data from backups

Refer to the README file for detailed instructions on these advanced operations.