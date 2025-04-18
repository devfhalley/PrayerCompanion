# Prayer Alarm System

A comprehensive Islamic prayer alarm and reminder system with two main components:
1. An Android app that serves as the controller
2. A Raspberry Pi that functions as a headless speaker device

## System Overview

The Prayer Alarm System provides the following features:

- **Islamic Prayer Time Scheduling**: Automatically fetches and announces prayer times for Jakarta, Indonesia using the Aladhan API
- **Pre-Adhan Announcements**: Configurable 10-minute and 5-minute pre-adhan announcements with customizable sounds for each prayer
- **Tahrim Sound System**: Plays customizable tahrim sounds after each pre-adhan announcement
- **Custom Alarm System**: Set alarms for specific times/days with repeat options and custom sounds (MP3 files or text-to-speech)
- **Push-to-Talk**: Speak through the Android app and have your voice played through the Raspberry Pi speaker in real-time
- **Murattal Player**: Play Quranic recitations with a professional interface including playback controls and track management
- **YouTube Player**: Display and manage YouTube videos on the homepage with full CRUD operations and drag-and-drop reordering
- **Global Volume Control**: Adjust system volume from any page with a sticky volume slider
- **Real-time WebSocket Communication**: Get instant prayer time notifications and status updates

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
  database.py     - Database interface (PostgreSQL)
  database_pg.py  - PostgreSQL implementation
  database_direct.py - Direct database access utilities
  models.py       - Data models
  config.py       - Configuration settings
/build            - Contains the Android APK and build information
```

## Raspberry Pi Server Features

The Raspberry Pi component serves as a headless speaker device with the following capabilities:

- **RESTful API**: Provides endpoints for managing alarms and prayer times
- **WebSocket Server**: Enables real-time push-to-talk functionality
- **Secure Communications**: Supports HTTPS and WSS connections with self-signed certificates
- **Audio Playback**: Plays MP3 files and text-to-speech using pygame
- **Scheduling**: Manages both prayer time notifications and custom alarms
- **Database**: Stores alarm and prayer time data in PostgreSQL (previously SQLite)

## Android App Features

The Android application serves as a controller with the following capabilities:

- **Alarm Management**: Create, edit, and delete alarms with various configuration options
- **Prayer Time Visualization**: View today's prayer times and upcoming prayers
- **Push-to-Talk Interface**: Speak through your phone to the Raspberry Pi speaker
- **Secure Communications**: Supports HTTPS and WSS (WebSocket Secure) with self-signed certificates
- **Settings**: Configure server connection details and preferences
- **Room Database**: Stores a local cache of alarms and prayer times

## API Endpoints

The Raspberry Pi server exposes the following API endpoints:

### Prayer and Alarm Management
- `GET /status` - Check server status
- `GET /alarms` - Get all alarms
- `POST /alarms` - Add or update an alarm
- `DELETE /alarms/{id}` - Delete an alarm
- `POST /alarms/{id}/disable` - Disable an alarm
- `POST /alarm/{id}/test` - Test play a specific alarm
- `GET /prayer-times` - Get prayer times for a specific date
- `POST /prayer-times/refresh` - Force refresh of prayer times from API

### Pre-Adhan Announcement System
- `POST /pre-adhan/10-min` - Set custom 10-minute pre-adhan sound for a prayer
- `POST /pre-adhan/5-min` - Set custom 5-minute pre-adhan sound for a prayer
- `POST /pre-adhan/tahrim` - Set custom tahrim sound for a prayer
- `POST /pre-adhan/test` - Test pre-adhan or tahrim sounds

### Audio Control
- `POST /stop-audio` - Stop any playing audio
- `GET /adhan-sounds` - Get list of available adhan sounds
- `POST /adhan/upload` - Upload a new adhan sound
- `POST /adhan/default` - Set default adhan sound
- `POST /adhan/prayer` - Set custom adhan for specific prayer
- `POST /test-adhan` - Test play adhan sound
- `GET /volume` - Get current system volume
- `POST /volume` - Update system volume

### Murattal Player
- `GET /murattal` - Get list of available Murattal files
- `POST /murattal/play` - Play a Murattal file
- `POST /murattal/upload` - Upload a new Murattal file

### YouTube Video Management
- `GET /youtube-videos` - Get all YouTube videos
- `GET /youtube-videos/enabled` - Get enabled YouTube videos
- `POST /youtube-videos` - Add a new YouTube video
- `PUT /youtube-videos/{id}` - Update an existing YouTube video
- `DELETE /youtube-videos/{id}` - Delete a YouTube video
- `POST /youtube-videos/reorder` - Reorder YouTube videos

### Real-time Communication
- `WebSocket /ws` - WebSocket endpoint for push-to-talk and real-time notifications

## Setup and Installation

### Raspberry Pi Setup

1. Clone the repository to your Raspberry Pi
2. Install the required dependencies:
   ```
   pip3 install flask flask_sock gtts pydub pygame requests schedule psycopg2-binary
   ```
3. Run the server manually (for testing):
   ```
   cd raspberry_pi
   python3 app.py
   ```

### HTTPS Setup

The application now uses HTTPS with self-signed certificates for secure communication between the Android app and Raspberry Pi server. This is necessary for secure WebSocket connections (WSS) which are required by modern browsers for Push-to-Talk functionality.

#### Certificate Generation

1. Generate self-signed certificates on the Raspberry Pi:
   ```bash
   cd raspberry_pi
   mkdir -p ssl
   cd ssl
   
   # Generate a private key
   openssl genrsa -out server.key 2048
   
   # Generate a certificate signing request
   openssl req -new -key server.key -out server.csr -subj "/CN=localhost"
   
   # Generate a self-signed certificate (valid for 365 days)
   openssl x509 -req -days 365 -in server.csr -signkey server.key -out server.crt
   
   # Create a PEM file that combines the certificate and key
   cat server.crt server.key > server.pem
   ```

2. Configure the server to use the certificates:
   - The Flask app automatically looks for certificates in the `ssl` directory
   - The certificate and key paths can be customized in `config.py`

#### Android App Configuration

The Android app is configured to trust self-signed certificates by implementing a trust-all certificate strategy:

1. The `RaspberryPiApi` class uses a custom `configureTrustAllCertificates` method for HTTPS connections
2. The `WebSocketService` class implements a similar strategy for secure WebSocket connections (WSS)
3. Settings now include an option to toggle between HTTP and HTTPS (defaulting to HTTPS)

> **Security Note**: Trusting all certificates is not recommended for production environments exposed to the internet. This implementation is appropriate for a local network where the Raspberry Pi and Android app are on the same trusted network.

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
3. Enable HTTPS in the app settings (recommended for secure communications)
4. Build and install the APK on your Android device
5. The app automatically trusts the self-signed certificate from the Raspberry Pi server

## Database Migration

The system has been migrated from SQLite to PostgreSQL to improve concurrency, performance, and reliability. If you're working with this codebase, this section provides important information about database operations.

### Database Connection

The system requires a PostgreSQL database connection. The connection details are read from environment variables:
```
DATABASE_URL=postgresql://username:password@hostname:port/database
```

Alternatively, these individual environment variables can be set:
```
PGUSER=username
PGPASSWORD=password
PGHOST=hostname
PGPORT=port
PGDATABASE=database
```

### Running Database Migrations

After setting up a fresh installation, you must run database migrations to create all necessary tables. This is especially important for newer features like the YouTube videos functionality.

1. Ensure your PostgreSQL database environment variables are properly set up
2. Navigate to the raspberry_pi directory:
   ```bash
   cd raspberry_pi
   ```
3. Make the migration script executable:
   ```bash
   chmod +x run_migrations.py
   ```
4. Run all migrations:
   ```bash
   ./run_migrations.py
   ```
5. To check what migrations would be applied without making changes:
   ```bash
   ./run_migrations.py --dry-run
   ```

If you see errors about missing tables (e.g., "relation youtube_videos does not exist"), this indicates you need to run the migrations.

### Migration Strategy

To maintain data integrity and support continuous development/integration, follow these principles when making database changes:

1. **Never modify database tables directly** with destructive SQL statements like `DROP TABLE` or `ALTER TABLE`
2. **Always use migration scripts** when making schema changes
3. **Test migrations thoroughly** in development before applying to production
4. **Back up data** before applying schema changes

### Migration Process

The project includes dedicated tools to help with migrations. To migrate from SQLite to PostgreSQL, use the provided scripts as follows:

1. **Use the migration script**:
   ```bash
   cd raspberry_pi
   ./migrate_from_sqlite.py
   ```
   
   This script will:
   - Export all data from SQLite to JSON backup files
   - Create the necessary tables in PostgreSQL
   - Import the data into PostgreSQL
   
   The script provides several options:
   ```bash
   # Show help
   ./migrate_from_sqlite.py --help
   
   # Perform a dry run (export only, no import)
   ./migrate_from_sqlite.py --dry-run
   
   # Specify custom SQLite database path
   ./migrate_from_sqlite.py --sqlite-db /path/to/database.db
   
   # Specify custom backup directory
   ./migrate_from_sqlite.py --backup-dir /path/to/backup/dir
   ```

2. **For future schema changes**, use the migration system:
   ```bash
   cd raspberry_pi
   
   # Apply pending migrations
   ./run_migrations.py
   
   # Rollback the last migration
   ./run_migrations.py --rollback
   
   # Show what migrations would be applied without making changes
   ./run_migrations.py --dry-run
   ```
   
3. **Create new migrations** by adding files to the `migrations` directory:
   ```bash
   # Create a new migration file
   cd raspberry_pi/migrations
   touch 002_add_new_column.py
   
   # Edit the file to include up() and down() methods
   # See example in migrations/README.md
   ```

### Schema Updates

When you need to make schema updates to the PostgreSQL database:

1. **Create a migration script** with both `up` and `down` methods to allow rollbacks:
   ```python
   # migration_001_add_column.py
   
   def up(conn):
       cur = conn.cursor()
       # Add new column
       cur.execute('ALTER TABLE alarms ADD COLUMN priority INT DEFAULT 0')
       conn.commit()
       
   def down(conn):
       cur = conn.cursor()
       # Remove column
       cur.execute('ALTER TABLE alarms DROP COLUMN priority')
       conn.commit()
   ```

2. **Track migrations** in a migrations table:
   ```python
   # Create migrations table if it doesn't exist
   cur.execute('''
   CREATE TABLE IF NOT EXISTS migrations (
       id SERIAL PRIMARY KEY,
       name TEXT NOT NULL,
       applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   )
   ''')
   conn.commit()
   ```

3. **Apply migrations** in sequence and record their application:
   ```python
   # Apply migration
   import migration_001_add_column
   migration_001_add_column.up(conn)
   
   # Record migration
   cur.execute('INSERT INTO migrations (name) VALUES (%s)', ('migration_001_add_column',))
   conn.commit()
   ```

### Debugging Database Issues

For debugging PostgreSQL database issues, use the `database_direct.py` module which provides direct SQL access. Always use this approach carefully and only for diagnostic purposes.

#### Common Database Issues

1. **Array Format Error**: If you see an error like `malformed array literal: "0000000"` with a detail mentioning "Array value must start with "{" or dimension information", this is due to PostgreSQL's array format requirements. The system needs to be updated to store days as a proper PostgreSQL array format like `{0,0,0,0,0,0,0}` instead of a string like `"0000000"`. Run the migration scripts to ensure database schema is properly set up.

### Direct SQL Access (for debugging only)

```python
import psycopg2
import os

# Connect directly to the database
conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
cursor = conn.cursor()

# Execute direct SQL
cursor.execute("SELECT * FROM alarms WHERE id = %s", (alarm_id,))
row = cursor.fetchone()

# Close connection
cursor.close()
conn.close()
```

Remember to always close your database connections properly to avoid connection leaks.

## Recent Feature Additions

### Pre-Adhan Announcement System

The system now includes a comprehensive pre-adhan announcement feature that allows users to configure custom sounds to play before each prayer time:

- **10-Minute Pre-Adhan Announcements**: Customizable sounds that play 10 minutes before each prayer
- **5-Minute Pre-Adhan Announcements**: Customizable sounds that play 5 minutes before each prayer
- **Tahrim Sounds**: Sounds that play after each pre-adhan announcement
- **Per-Prayer Configuration**: Each prayer time can have different announcement sounds
- **Test Functionality**: Preview buttons to test each sound before saving

### Murattal Player Enhancements

The Murattal player has been enhanced with a professional interface that includes:

- **Improved Playback Controls**: Play, pause, and stop with visual feedback
- **Track Selection**: Clearer track selection with visual highlighting
- **Track Title Display**: Improved display of track information
- **Upload Capability**: Easily add new Murattal files to the collection

### YouTube Video Integration

The system now allows displaying YouTube videos on the home page:

- **Full CRUD Operations**: Add, edit, delete, and enable/disable videos
- **Drag-and-Drop Reordering**: Change the display order of videos with intuitive drag-and-drop
- **URL Validation**: Automatic extraction of video IDs from YouTube URLs
- **Responsive Display**: Videos are displayed responsively on the home page

### Global Volume Control

A global volume control has been added:

- **Persistent Volume Slider**: Accessible from all pages
- **Real-time Adjustment**: Instantly changes system volume
- **Visual Feedback**: Shows current volume level

## User Manual

For detailed instructions on how to use all features of the Prayer Alarm System, please refer to the [User Manual](USER_MANUAL.md).
