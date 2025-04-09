# Running Missing Migrations

When installing the Prayer Alarm System on a new machine, you need to run database migrations to create all the necessary tables. This guide will help you apply the missing migrations, especially for the YouTube videos feature.

## Prerequisites

Make sure your PostgreSQL database is properly configured with environment variables:

```bash
# Set these environment variables with your PostgreSQL database credentials
export PGUSER=your_username
export PGPASSWORD=your_password
export PGHOST=localhost
export PGPORT=5432
export PGDATABASE=your_database_name

# Alternatively, you can set DATABASE_URL directly
export DATABASE_URL=postgresql://your_username:your_password@localhost:5432/your_database_name
```

## Running Migrations

1. Navigate to the raspberry_pi directory:

```bash
cd raspberry_pi
```

2. Make the migration script executable (if it's not already):

```bash
chmod +x run_migrations.py
```

3. Run the migrations:

```bash
./run_migrations.py
```

4. To check what migrations would be applied without making changes:

```bash
./run_migrations.py --dry-run
```

## Verifying Migrations

After running the migrations, verify that the YouTube videos table was created:

```bash
psql -U your_username -d your_database_name -c "SELECT * FROM youtube_videos LIMIT 5;"
```

This should display the table structure with no errors.

## Troubleshooting

If you encounter any issues:

1. Check if the migrations table exists:

```bash
psql -U your_username -d your_database_name -c "SELECT * FROM migrations;"
```

2. If migrations are failing, try running with more verbose output:

```bash
PYTHONPATH=. python -m run_migrations.py
```

3. If needed, you can create the YouTube videos table manually:

```sql
CREATE TABLE IF NOT EXISTS youtube_videos (
    id SERIAL PRIMARY KEY,
    url TEXT NOT NULL,
    title TEXT,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    position INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

Remember to add this migration to the migrations table if you create it manually:

```sql
INSERT INTO migrations (name) VALUES ('004_add_youtube_videos_table');
```