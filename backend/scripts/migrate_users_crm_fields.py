"""
Migration script to add CRM fields to the users table.

Fields added:
- ss_crm_name: CRM display name
- ss_name: Employee name
- ss_sm_name: SM name
- ss_dept4_name: Department name
- ss_group: Group name
"""
import os
import sys

# Add parent directory to path to import config
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    import psycopg2
except ImportError:
    print("Installing psycopg2-binary...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg2-binary"])
    import psycopg2

from src.infrastructure.config import get_settings


def migrate():
    """Add CRM fields to users table."""
    settings = get_settings()
    
    # Parse DATABASE_URL for psycopg2
    # Format: postgresql+asyncpg://user:pass@host:port/dbname
    db_url = settings.DATABASE_URL
    # Remove asyncpg driver prefix for psycopg2
    db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    
    print(f"Connecting to database...")
    
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    cursor = conn.cursor()
    
    # Check existing columns
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'users'
    """)
    existing_columns = {row[0] for row in cursor.fetchall()}
    print(f"Existing columns: {existing_columns}")
    
    # Columns to add
    new_columns = [
        ("ss_crm_name", "VARCHAR(100)"),
        ("ss_name", "VARCHAR(100)"),
        ("ss_sm_name", "VARCHAR(100)"),
        ("ss_dept4_name", "VARCHAR(100)"),
        ("ss_group", "VARCHAR(100)"),
        ("crm_synced_at", "TIMESTAMP WITH TIME ZONE"),
    ]
    
    for col_name, col_type in new_columns:
        if col_name in existing_columns:
            print(f"Column '{col_name}' already exists, skipping...")
        else:
            print(f"Adding column '{col_name}'...")
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
            print(f"✅ Column '{col_name}' added successfully")
    
    cursor.close()
    conn.close()
    
    print("\n✅ Migration completed!")


if __name__ == "__main__":
    migrate()
