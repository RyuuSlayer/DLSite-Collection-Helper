import os
import shutil
import sqlite3
import time
from config import DEBUG_ENABLED

# Constants
BACKUP_DIR = "db-backup"
DB_FILE = "dlsite_ids.db"

def setup_database():
    """Setup the database by creating table and adding columns if necessary."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Create the table if it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dlsite_ids (
            dlsite_id TEXT NOT NULL,
            tested TEXT DEFAULT 'No',
            version TEXT,
            marked INTEGER DEFAULT 0
        )
    """)
    
    # Check if marked column exists, add it if it doesn't
    cursor.execute("PRAGMA table_info(dlsite_ids)")
    columns = [column[1] for column in cursor.fetchall()]
    if "marked" not in columns:
        cursor.execute("ALTER TABLE dlsite_ids ADD COLUMN marked INTEGER DEFAULT 0")

    conn.commit()
    conn.close()

def backup_database():
    """Creates a backup of the database, maintaining only the last 3 startup backups."""
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)

    timestamp = time.strftime("%Y%m%d%H%M%S")
    backup_file = os.path.join(BACKUP_DIR, f"dlsite_ids_backup_{timestamp}.db")

    # Only create backup if database file exists
    if os.path.exists(DB_FILE):
        shutil.copy(DB_FILE, backup_file)
        print(f"Startup backup created: {backup_file}")

        # Get list of existing backups and sort by timestamp (newest first)
        backup_files = []
        for f in os.listdir(BACKUP_DIR):
            if f.startswith("dlsite_ids_backup_") and f.endswith(".db"):
                backup_path = os.path.join(BACKUP_DIR, f)
                backup_files.append((os.path.getmtime(backup_path), f))
        
        backup_files.sort(reverse=True)  # Sort by modification time, newest first

        # Keep only the 3 newest backups
        for _, fname in backup_files[3:]:  # Skip first 3, delete the rest
            os.remove(os.path.join(BACKUP_DIR, fname))
            print(f"Deleted old backup: {fname}")

def get_connection():
    """Get a database connection."""
    return sqlite3.connect(DB_FILE)

def update_marked_status(cursor, rowid, marked):
    """Update the marked status for a specific entry."""
    if DEBUG_ENABLED:
        print(f"[DEBUG] Updating marked status - rowid: {rowid}, marked: {marked}")
    cursor.execute(
        "UPDATE dlsite_ids SET marked = ? WHERE rowid = ?",
        (marked, rowid)
    )
    cursor.connection.commit()  # Commit the change immediately

def reset_all_marked_status(cursor):
    """Reset all marked statuses to 0."""
    if DEBUG_ENABLED:
        print("[DEBUG] Resetting all marked statuses to 0")
    cursor.execute("UPDATE dlsite_ids SET marked = 0")
    cursor.connection.commit()  # Commit the change immediately
