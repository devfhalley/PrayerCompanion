# Database Migrations

This directory contains migration scripts for database schema changes. Each migration should be numbered sequentially and include both `up` and `down` methods to support rollbacks.

## Running Migrations

To apply migrations, use the migration runner script:

```
python3 run_migrations.py
```

## Creating New Migrations

When you need to add a new migration:

1. Create a new Python file with a sequential number prefix (e.g., `001_initial_schema.py`, `002_add_priority_column.py`, etc.)
2. Implement both `up` and `down` methods in your migration file
3. Test your migration in a development environment before deploying to production

Example migration file structure:

```python
# 002_add_priority_column.py

"""
Add priority column to alarms table
"""

def up(conn):
    """Apply migration"""
    cur = conn.cursor()
    cur.execute('ALTER TABLE alarms ADD COLUMN priority INT DEFAULT 0')
    conn.commit()
    cur.close()
    
def down(conn):
    """Revert migration"""
    cur = conn.cursor()
    cur.execute('ALTER TABLE alarms DROP COLUMN priority')
    conn.commit()
    cur.close()
```

## Migration Best Practices

1. **Keep migrations small and focused** - Each migration should make a small, specific change
2. **Always test migrations** in development before production
3. **Back up your database** before running migrations
4. **Include documentation** in each migration file
5. **Never modify existing migrations** after they have been applied