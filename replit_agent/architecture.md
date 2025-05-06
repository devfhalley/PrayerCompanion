# Prayer Alarm System Architecture

## 1. Overview

The Prayer Alarm System is a comprehensive Islamic prayer time management and notification system consisting of two main components:

1. A Raspberry Pi server that functions as a headless audio playback device
2. An Android application that serves as the controller interface

The system provides features such as:
- Automated Islamic prayer time scheduling and announcements
- Pre-adhan announcements with configurable sounds
- Custom alarm scheduling with various repeat options
- Push-to-talk functionality for real-time voice broadcast
- Murattal (Quranic recitation) player with playback controls
- YouTube video management and playback

## 2. System Architecture

The Prayer Alarm System follows a client-server architecture:

```
┌───────────────────┐        ┌───────────────────────────────────┐
│                   │        │                                   │
│  Android Client   │◄─────► │  Raspberry Pi Server              │
│  (Controller)     │   HTTP │  (Audio Playback & Scheduling)    │
│                   │   WS   │                                   │
└───────────────────┘        └───────────────────────────────────┘
                                        │
                                        │
                                        ▼
                             ┌─────────────────────┐
                             │                     │
                             │  PostgreSQL         │
                             │  Database           │
                             │                     │
                             └─────────────────────┘
```

### Key Design Decisions:

1. **Separation of Concerns**: The system separates control (Android app) from audio playback (Raspberry Pi server), allowing for headless operation of the playback device.

2. **Dual Communication Protocols**:
   - RESTful HTTP API for standard operations
   - WebSockets for real-time features like push-to-talk

3. **Database-Driven Architecture**: Core system state, including alarms, prayer times, and configuration, is stored in a PostgreSQL database for persistence.

4. **Modular Design**: The server component is organized into distinct modules for prayer scheduling, alarm management, audio playback, and database interaction.

5. **Web Interface**: In addition to the Android controller, the Raspberry Pi provides a web interface for direct system management.

## 3. Key Components

### 3.1 Raspberry Pi Server

#### Core Modules:
1. **Flask Web Application (`app.py`)**
   - Serves as the main entry point for the web interface and API
   - Handles HTTP requests and renders web templates
   - Initializes other system components

2. **Prayer Scheduler (`prayer_scheduler.py`)**
   - Fetches and schedules Islamic prayer times using the Aladhan API
   - Manages prayer notifications, including pre-adhan announcements
   - Handles the prayer countdown and timing logic

3. **Alarm Scheduler (`alarm_scheduler.py`)**
   - Manages user-defined custom alarms
   - Handles repeating alarms based on day patterns
   - Prioritizes alarms according to their defined priority levels

4. **Audio Player (`audio_player.py`)**
   - Manages all audio playback using Pygame
   - Implements a priority-based audio queue system
   - Supports MP3 file playback and text-to-speech generation via gTTS

5. **WebSocket Server (`websocket_server.py`)**
   - Provides real-time communication for push-to-talk feature
   - Sends live status updates to connected clients
   - Implemented using Flask-Sock

6. **Database Interface (`database.py`, `database_pg.py`)**
   - Handles all database operations using psycopg2
   - Manages migrations via a versioned migration system
   - Provides data access methods for alarms, prayer times, and settings

#### Web Interface:
- Built with Flask templates, JavaScript, and CSS
- Responsive design for access from various devices
- Features include prayer time display, alarm management, push-to-talk controls, and Murattal player

### 3.2 Android Application

- Native Android application written in Java
- Provides a user-friendly mobile interface to control the Raspberry Pi server
- Features match those available in the web interface
- Implements background services for notifications

### 3.3 Database Schema

The system uses PostgreSQL with the following key tables:

1. **alarms**
   - Stores custom alarm configurations
   - Includes timing, repeat patterns, sound settings, and smart alarm features

2. **prayer_times**
   - Stores fetched prayer times for each day
   - Includes pre-adhan announcement configurations and custom sounds

3. **youtube_videos**
   - Stores YouTube video URLs and display settings
   - Supports positioning and enable/disable functionality

4. **migrations**
   - Tracks applied database migrations

## 4. Data Flow

### 4.1 Prayer Time Management

```
┌─────────────┐     ┌────────────────┐     ┌──────────────┐     ┌─────────────┐
│             │     │                │     │              │     │             │
│ Aladhan API │────►│ PrayerScheduler│────►│ Database     │────►│ AudioPlayer │
│             │     │                │     │              │     │             │
└─────────────┘     └────────────────┘     └──────────────┘     └─────────────┘
```

1. PrayerScheduler fetches prayer times from the Aladhan API
2. Times are stored in the database
3. As prayer times approach, pre-adhan announcements are triggered
4. At prayer time, the adhan (call to prayer) is played through the AudioPlayer

### 4.2 Alarm Management

```
┌──────────────┐     ┌────────────────┐     ┌─────────────┐
│              │     │                │     │             │
│ User Interface│────►│ AlarmScheduler │────►│ AudioPlayer │
│ (Web/Android) │     │                │     │             │
└──────────────┘     └────────────────┘     └─────────────┘
```

1. User creates/edits alarms through the web or Android interface
2. AlarmScheduler loads alarms from the database
3. When an alarm is triggered, it's sent to the AudioPlayer
4. Smart alarms gradually increase volume over time

### 4.3 Push-to-Talk

```
┌──────────────┐     ┌────────────────┐     ┌─────────────┐
│              │     │                │     │             │
│ User Interface│────►│ WebSocket     │────►│ AudioPlayer │
│ (Web/Android) │     │ Server        │     │             │
└──────────────┘     └────────────────┘     └─────────────┘
```

1. User activates push-to-talk through the interface
2. Audio is streamed via WebSockets to the server
3. WebSocket server forwards audio to the AudioPlayer
4. Audio is played in real-time through the Raspberry Pi speakers

## 5. External Dependencies

### 5.1 Backend Dependencies
- **Flask**: Web framework for the backend server
- **Flask-Sock**: WebSocket support for push-to-talk
- **psycopg2**: PostgreSQL database adapter
- **Pygame**: Audio playback
- **gTTS**: Google Text-to-Speech for TTS functionality
- **Pydub**: Audio file manipulation
- **Schedule**: Time-based job scheduling
- **Requests**: HTTP client for API calls

### 5.2 Frontend Dependencies
- **JavaScript**: Client-side functionality
- **CSS**: Styling and animations
- **Font Awesome**: Icons and visual elements

### 5.3 External Services
- **Aladhan API**: Prayer time calculations
- **YouTube API**: For video management (implicit)

## 6. Deployment Strategy

The system is designed to run on a Raspberry Pi, with the following deployment options:

### 6.1 Systemd Service
- The repository includes a `prayer_alarm.service` file
- This allows the system to run as a background service
- Automatically starts on boot and restarts on failure

### 6.2 Development Environment
- The system can also run in a Replit environment
- `.replit` configuration manages the development setup
- WebSocket functionality is limited in Replit due to proxy restrictions

### 6.3 Database Migrations
- A structured migration system manages database schema changes
- Migrations are versioned and can be applied incrementally
- Support for both forward (up) and backward (down) migrations

### 6.4 SSL Support
- The system includes SSL certificate generation for HTTPS
- This enables secure WebSocket connections (WSS)
- Required for microphone access in modern browsers

## 7. Security Considerations

- WebSocket communication can be secured with SSL
- The database connection is managed securely
- No explicit user authentication system is present (assumed to be on a private network)
- Database credentials are managed through environment variables

## 8. Limitations and Future Improvements

- The WebSocket implementation has limitations in the Replit environment
- Authentication and user management could be enhanced
- The Android app could be extended with more offline capabilities
- The system assumes a single user/household setup