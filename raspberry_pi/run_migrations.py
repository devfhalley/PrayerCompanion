#!/usr/bin/env python3
"""
Migration runner for Prayer Alarm System database migrations.
This script applies database migrations in sequence.
"""

import os
import sys
import importlib.util
import psycopg2
import argparse
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('migration_runner')

def get_connection():
    """Get a PostgreSQL database connection."""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        # Attempt to build connection string from individual environment variables
        user = os.environ.get('PGUSER')
        password = os.environ.get('PGPASSWORD')
        host = os.environ.get('PGHOST')
        port = os.environ.get('PGPORT')
        database = os.environ.get('PGDATABASE')
        
        if not all([user, password, host, port, database]):
            logger.error("Database connection information missing. Please set DATABASE_URL or individual PostgreSQL environment variables")
            sys.exit(1)
            
        database_url = f"postgresql://{user}:{password}@{host}:{port}/{database}"
    
    return psycopg2.connect(database_url)

def get_applied_migrations(conn):
    """Get a list of already applied migrations."""
    try:
        cur = conn.cursor()
        # First check if migrations table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'migrations'
            )
        """)
        table_exists = cur.fetchone()[0]
        
        if not table_exists:
            logger.info("Migrations table does not exist yet, creating it")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS migrations (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            return []
        
        # Get list of applied migrations
        cur.execute("SELECT name FROM migrations ORDER BY id")
        applied = [row[0] for row in cur.fetchall()]
        cur.close()
        return applied
    except Exception as e:
        logger.error(f"Error getting applied migrations: {e}")
        conn.rollback()
        return []

def get_migration_files():
    """Get a list of all migration files in the migrations directory."""
    migrations_dir = Path(__file__).parent / 'migrations'
    migration_files = [f for f in migrations_dir.glob("*.py") if not f.name.startswith('__')]
    return sorted(migration_files)

def load_migration_module(file_path):
    """Load a migration module from file path."""
    try:
        module_name = file_path.stem
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None:
            logger.error(f"Could not create module spec from {file_path}")
            return None
        module = importlib.util.module_from_spec(spec)
        if spec.loader is None:
            logger.error(f"Module spec has no loader for {file_path}")
            return None
        spec.loader.exec_module(module)
        return module
    except Exception as e:
        logger.error(f"Error loading migration module {file_path}: {e}")
        return None

def apply_migration(conn, migration_file, module):
    """Apply a migration."""
    migration_name = migration_file.stem
    try:
        logger.info(f"Applying migration: {migration_name}")
        
        # Apply the migration
        module.up(conn)
        
        # Record the migration
        cur = conn.cursor()
        cur.execute("INSERT INTO migrations (name) VALUES (%s)", (migration_name,))
        conn.commit()
        cur.close()
        
        logger.info(f"Successfully applied migration: {migration_name}")
        return True
    except Exception as e:
        logger.error(f"Error applying migration {migration_name}: {e}")
        conn.rollback()
        return False

def rollback_migration(conn, migration_file, module):
    """Rollback a migration."""
    migration_name = migration_file.stem
    try:
        logger.info(f"Rolling back migration: {migration_name}")
        
        # Rollback the migration
        module.down(conn)
        
        # Remove the migration record
        cur = conn.cursor()
        cur.execute("DELETE FROM migrations WHERE name = %s", (migration_name,))
        conn.commit()
        cur.close()
        
        logger.info(f"Successfully rolled back migration: {migration_name}")
        return True
    except Exception as e:
        logger.error(f"Error rolling back migration {migration_name}: {e}")
        conn.rollback()
        return False

def main():
    parser = argparse.ArgumentParser(description='Run database migrations for Prayer Alarm System')
    parser.add_argument('--rollback', action='store_true', help='Rollback the last applied migration')
    parser.add_argument('--rollback-all', action='store_true', help='Rollback all migrations')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without applying changes')
    args = parser.parse_args()
    
    conn = get_connection()
    
    try:
        # Get applied migrations
        applied_migrations = get_applied_migrations(conn)
        logger.info(f"Found {len(applied_migrations)} applied migrations")
        
        # Get all migration files
        migration_files = get_migration_files()
        logger.info(f"Found {len(migration_files)} migration files")
        
        if args.rollback or args.rollback_all:
            # Rollback migrations
            applied_migrations_dict = {m: i for i, m in enumerate(applied_migrations)}
            
            if not applied_migrations:
                logger.info("No migrations to roll back")
                return
                
            # Sort migration files in reverse order based on applied order
            migration_files = sorted(
                [f for f in migration_files if f.stem in applied_migrations_dict],
                key=lambda f: applied_migrations_dict[f.stem],
                reverse=True
            )
            
            if not args.rollback_all:
                # Only rollback the last one
                migration_files = migration_files[:1]
            
            for migration_file in migration_files:
                module = load_migration_module(migration_file)
                if not module:
                    continue
                    
                if args.dry_run:
                    logger.info(f"Would rollback migration: {migration_file.stem}")
                else:
                    rollback_migration(conn, migration_file, module)
        else:
            # Apply migrations
            applied_set = set(applied_migrations)
            
            for migration_file in migration_files:
                if migration_file.stem in applied_set:
                    logger.info(f"Migration already applied: {migration_file.stem}")
                    continue
                
                module = load_migration_module(migration_file)
                if not module:
                    continue
                    
                if args.dry_run:
                    logger.info(f"Would apply migration: {migration_file.stem}")
                else:
                    success = apply_migration(conn, migration_file, module)
                    if not success:
                        break
    finally:
        conn.close()

if __name__ == '__main__':
    main()