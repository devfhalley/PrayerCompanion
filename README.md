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
- **Audio Playback**: Plays MP3 files and text-to-speech using pygame
- **Scheduling**: Manages both prayer time notifications and custom alarms
- **Database**: Stores alarm and prayer time data in PostgreSQL (previously SQLite)

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
   pip3 install flask flask_sock gtts pydub pygame requests schedule psycopg2-binary
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
