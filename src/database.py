"""
Database module for DLSite Collection Helper.

This module handles all database operations including setup, backup, and CRUD operations
for DLSite IDs and their associated metadata. It uses SQLite for data storage and
provides functions for managing the database schema and content.

Functions:
    setup_database: Initialize or update the database schema
    backup_database: Create a backup of the current database
    get_connection: Get a connection to the SQLite database
    update_marked_status: Update the presence status of DLSite IDs
    reset_all_marked_status: Reset all presence statuses to unmarked
    add_or_update_id: Add or update a DLSite ID in the database
"""

import os
import shutil
import sqlite3
import time
from config import DEBUG_ENABLED
from typing import Optional

# Constants
BACKUP_DIR = "db-backup"
DB_FILE = "dlsite_ids.db"

def setup_database() -> None:
    """
    Initialize or update the database schema.
    
    Creates the necessary tables if they don't exist and performs any required
    schema migrations for version updates.
    """
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

def backup_database() -> None:
    """
    Create a backup of the current database.
    
    Creates a timestamped copy of the database file in the backups folder.
    Only keeps the 3 most recent backups.
    """
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

def get_connection() -> sqlite3.Connection:
    """
    Get a connection to the SQLite database.
    
    Returns:
        sqlite3.Connection object for database operations
    """
    return sqlite3.connect(DB_FILE)

def update_marked_status(cursor: sqlite3.Cursor, rowid: int, marked: bool) -> None:
    """
    Update the presence status of a DLSite ID.
    
    Args:
        cursor: SQLite cursor object
        rowid: Row ID of the DLSite ID to update
        marked: Whether the ID is present (True) or absent (False)
    """
    if DEBUG_ENABLED:
        print(f"[DEBUG] Updating marked status - rowid: {rowid}, marked: {marked}")
    cursor.execute(
        "UPDATE dlsite_ids SET marked = ? WHERE rowid = ?",
        (1 if marked else 0, rowid)
    )
    cursor.connection.commit()  # Commit the change immediately

def reset_all_marked_status(cursor: sqlite3.Cursor) -> None:
    """
    Reset all presence statuses to unmarked (absent).
    
    Args:
        cursor: SQLite cursor object
    """
    if DEBUG_ENABLED:
        print("[DEBUG] Resetting all marked statuses to 0")
    cursor.execute("UPDATE dlsite_ids SET marked = 0")
    cursor.connection.commit()  # Commit the change immediately

def add_or_update_id(dlsite_id: str, version: Optional[str] = "", tested: str = "No") -> None:
    """
    Add or update a DLSite ID in the database.
    
    Args:
        dlsite_id: The DLSite ID to add or update
        version: The version of the DLSite ID (optional)
        tested: Whether the ID has been tested (default: "No")
    """
    dlsite_id = dlsite_id.strip().upper()
    version = version.strip() if version else ""
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Check if ID exists
    cursor.execute("SELECT * FROM dlsite_ids WHERE dlsite_id = ?", (dlsite_id,))
    existing = cursor.fetchone()
    
    if existing:
        cursor.execute("""
            UPDATE dlsite_ids 
            SET version = ?, tested = ?
            WHERE dlsite_id = ?
        """, (version, tested, dlsite_id))
    else:
        cursor.execute("""
            INSERT INTO dlsite_ids (dlsite_id, version, tested)
            VALUES (?, ?, ?)
        """, (dlsite_id, version, tested))
    
    conn.commit()
    conn.close()
