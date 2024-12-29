"""
Graphical User Interface module for DLSite Collection Helper.

This module implements the main GUI interface using tkinter. It provides a user-friendly
way to manage DLSite IDs, track their versions, and monitor their presence in a collection.

Features:
    - Add, edit, and remove DLSite IDs
    - Track version information
    - Monitor file presence
    - Sort and filter entries
    - Dark/light theme support
    - Configuration management

Classes:
    None (uses functional programming style)

Functions:
    main: Initialize and run the main application window
    refresh_table: Update the display table with current data
    sort_table: Sort table entries by DLSite ID
    add_id: Add a new DLSite ID
    edit_id: Edit an existing DLSite ID
    remove_entry: Remove a DLSite ID from the database
    check_folder_for_ids: Scan folder for DLSite IDs
    apply_theme: Apply the current theme to all widgets
"""

import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter.simpledialog import askstring
import re
from typing import Optional, Dict, Any, List, Tuple

from styles import LIGHT_THEME, DARK_THEME, PRESENT_MARKER, MISSING_MARKER
from database import (
    setup_database, backup_database, get_connection,
    update_marked_status, reset_all_marked_status, add_or_update_id
)
from file_utils import (
    format_version, strip_version_prefix, extract_id_and_version,
    load_config, save_config
)
from config import DEBUG_ENABLED

# Global variables
FOLDER_PATH: Optional[str] = None
current_theme: str = 'light'
root: Optional[tk.Tk] = None
table: Optional[ttk.Treeview] = None
style: Optional[ttk.Style] = None

def apply_theme() -> None:
    """
    Apply the current theme to all widgets.
    
    Updates the visual appearance of all widgets based on the current theme
    (light or dark). This includes colors, backgrounds, and highlights for
    the table, buttons, and other UI elements.
    """
    global current_theme
    theme = DARK_THEME if current_theme == 'dark' else LIGHT_THEME
    
    # Update style configuration
    global style
    style.theme_use('clam')  # Reset to clam theme to ensure consistent styling
    
    # Configure Treeview
    style.configure('Treeview', 
                   background=theme['tree_bg'],
                   fieldbackground=theme['tree_bg'],
                   foreground=theme['tree_fg'])
    style.configure('Treeview.Heading',
                   background=theme['button_bg'],
                   foreground=theme['button_fg'])
    
    # Configure header hover color based on theme
    if current_theme == 'dark':
        style.map('Treeview.Heading',
                 background=[('active', 'gray35')])  # Lighter gray on hover for dark theme
        # Configure Entry style for dark theme
        style.configure('Search.TEntry',
                      fieldbackground='gray35',
                      foreground='white',
                      selectbackground='gray50',
                      selectforeground='white')
    else:
        style.map('Treeview.Heading',
                 background=[('active', 'SystemButtonFace')])  # Default hover for light theme
        # Configure Entry style for light theme
        style.configure('Search.TEntry',
                      fieldbackground='white',
                      foreground='black',
                      selectbackground='SystemHighlight',
                      selectforeground='SystemHighlightText')
    
    style.map('Treeview',
             background=[('selected', theme['select_bg'])],
             foreground=[('selected', theme['select_fg'])])

    # Configure Buttons
    style.configure('TButton',
                   background=theme['button_bg'],
                   foreground=theme['button_fg'])
    style.map('TButton',
             background=[('active', theme['select_bg']),
                        ('pressed', theme['select_bg'])],
             foreground=[('active', theme['select_fg']),
                        ('pressed', theme['select_fg'])])

    # Configure Checkbutton
    style.configure('TCheckbutton',
                   background=theme['bg'],
                   foreground=theme['fg'])
    style.map('TCheckbutton',
             background=[('active', theme['bg'])],
             foreground=[('active', theme['fg'])])

    # Configure Radiobutton
    style.configure('TRadiobutton',
                   background=theme['bg'],
                   foreground=theme['fg'])
    style.map('TRadiobutton',
             background=[('active', theme['bg'])],
             foreground=[('active', theme['fg'])])

    # Configure Frames and Labels
    style.configure('TFrame', background=theme['bg'])
    style.configure('TLabelframe', 
                   background=theme['bg'],
                   foreground=theme['fg'],
                   bordercolor=theme['border'],
                   darkcolor=theme['border'],
                   lightcolor=theme['border'])
    style.configure('TLabelframe.Label',
                   background=theme['bg'],
                   foreground=theme['fg'])
    style.configure('TLabel',
                   background=theme['bg'],
                   foreground=theme['fg'])

    # Configure Entry
    style.configure('TEntry',
                   fieldbackground=theme['tree_bg'],
                   foreground=theme['tree_fg'],
                   bordercolor=theme['border'])

    # Update main window
    root.configure(bg=theme['bg'])
    
    # Update all frames and widgets recursively
    def update_widget_colors(widget):
        if isinstance(widget, (ttk.Frame, ttk.LabelFrame)):
            widget.configure(style='TFrame')
        elif isinstance(widget, ttk.Label):
            widget.configure(style='TLabel')
        elif isinstance(widget, ttk.Button):
            widget.configure(style='TButton')
        elif isinstance(widget, ttk.Checkbutton):
            widget.configure(style='TCheckbutton')
        elif isinstance(widget, ttk.Radiobutton):
            widget.configure(style='TRadiobutton')
        
        # Recursively update all children
        for child in widget.winfo_children():
            update_widget_colors(child)
    
    # Start recursive update from root
    update_widget_colors(root)
    
    # Refresh table to ensure correct styling
    refresh_table()

def check_folder_for_ids() -> None:
    """
    Scan the configured folder for DLSite IDs.
    
    Searches through the configured folder for files containing DLSite IDs,
    extracts version information if available, and updates the database with
    their presence status.
    """
    if not FOLDER_PATH or not os.path.exists(FOLDER_PATH):
        if DEBUG_ENABLED:
            print(f"[DEBUG] Invalid folder path: {FOLDER_PATH}")
        return

    conn = get_connection()
    cursor = conn.cursor()

    # First, reset all marked statuses
    reset_all_marked_status(cursor)
    
    # Get all files in the folder
    try:
        files = [f for f in os.listdir(FOLDER_PATH) if os.path.isfile(os.path.join(FOLDER_PATH, f))]
        if DEBUG_ENABLED:
            print(f"\n[DEBUG] Checking folder: {FOLDER_PATH}")
            print(f"[DEBUG] Found {len(files)} files:")
            for f in files:
                print(f"  - {f}")
    except Exception as e:
        if DEBUG_ENABLED:
            print(f"[DEBUG] Error reading folder: {e}")
        return
    
    # Process each file
    for filename in files:
        full_path = os.path.join(FOLDER_PATH, filename)
        if DEBUG_ENABLED:
            print(f"\n[DEBUG] Processing file: {full_path}")
        
        dlsite_id, version = extract_id_and_version(filename, DEBUG_ENABLED)
        if dlsite_id:
            # Check if this ID exists with exact version match
            query = """
                SELECT rowid, tested, version, dlsite_id 
                FROM dlsite_ids 
                WHERE dlsite_id = ?
            """
            params = [dlsite_id]
            
            if version:
                # If version exists, add it to the query
                query += " AND version = ?"
                params.append(version)
            else:
                # If no version, match entries with no version or empty version
                query += " AND (version IS NULL OR version = '')"
            
            if DEBUG_ENABLED:
                print(f"[DEBUG] Executing query: {query}")
                print(f"[DEBUG] With parameters: {params}")
            
            cursor.execute(query, params)
            result = cursor.fetchone()
            
            if result:
                rowid, tested, db_version, db_id = result
                if DEBUG_ENABLED:
                    print(f"[DEBUG] Found exact match in DB:")
                    print(f"  DB ID: {db_id}")
                    print(f"  DB Version: '{db_version}'")
                    print(f"  File Version: '{version}'")
                # Mark existing entry as present
                update_marked_status(cursor, rowid, 1)
            elif DEBUG_ENABLED:
                print(f"[DEBUG] No exact match found in DB")
                cursor.execute("SELECT rowid, version FROM dlsite_ids WHERE dlsite_id = ?", (dlsite_id,))
                other_versions = cursor.fetchall()
                if other_versions:
                    print(f"[DEBUG] Other versions in DB for {dlsite_id}:")
                    for v in other_versions:
                        print(f"  - '{v[1]}'")

    conn.commit()
    conn.close()
    
    # Refresh the table display without checking folder again
    refresh_table(check_folder=False)

def refresh_table(search_query: Optional[str] = None, check_folder: bool = True) -> None:
    """
    Refresh the table with current data.
    
    Args:
        search_query: Optional search string to filter results
        check_folder: Whether to scan the folder for IDs before refreshing
    
    Updates the table display with the latest data from the database,
    optionally filtering by a search query. Can also update file presence
    status by scanning the configured folder.
    """
    global table
    if table is None:
        return

    # Check for files in folder first if requested
    if check_folder:
        check_folder_for_ids()
        
    for item in table.get_children():
        table.delete(item)

    conn = get_connection()
    cursor = conn.cursor()

    if search_query:
        # Search in dlsite_id field
        cursor.execute("""
            SELECT rowid, dlsite_id, tested, version, marked 
            FROM dlsite_ids 
            WHERE dlsite_id LIKE ? 
            ORDER BY dlsite_id""", 
            (f"%{search_query}%",))
    else:
        cursor.execute("""
            SELECT rowid, dlsite_id, tested, version, marked 
            FROM dlsite_ids 
            ORDER BY dlsite_id""")
    
    rows = cursor.fetchall()
    
    for rowid, dlsite_id, tested, version, marked in rows:
        # Format version for display
        display_version = format_version(version) if version else "-"
        
        # Format the ID with prefix based on tested status and presence, ensuring consistent spacing
        prefix = PRESENT_MARKER if marked else MISSING_MARKER
        display_id = f"{prefix} - {dlsite_id}".strip()  # Ensure no extra whitespace
        table.insert("", "end", iid=rowid, values=(display_id, tested, display_version))

    conn.close()
    
    # Force initial descending sort
    sort_table(True)

# Folder path management functions
def load_folder_path() -> None:
    """
    Load the folder path from the configuration file.
    """
    global FOLDER_PATH, current_theme
    config = load_config()
    FOLDER_PATH = config['folder_path']
    current_theme = config['theme']

def save_folder_path(folder_path: str) -> None:
    """
    Save the folder path to the config file.
    
    Args:
        folder_path: The path to save
    """
    global FOLDER_PATH
    FOLDER_PATH = folder_path
    config = {
        'folder_path': FOLDER_PATH,
        'theme': current_theme
    }
    save_config(config)
    refresh_table()

def prompt_for_folder_path() -> None:
    """
    Prompt user to set the folder path.
    """
    folder_path = filedialog.askdirectory()
    if folder_path:
        save_folder_path(folder_path)
        refresh_table()  # Refresh to show any new IDs from the selected folder

        # Create confirmation window with theme support
        confirm_window = tk.Toplevel(root)
        confirm_window.title("Folder Path Set")
        
        # Apply current theme
        theme = DARK_THEME if current_theme == 'dark' else LIGHT_THEME
        confirm_window.configure(bg=theme['bg'])
        
        # Main container with padding
        main_frame = ttk.Frame(confirm_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Add confirmation message
        message = ttk.Label(main_frame, 
                          text=f"Folder path has been set to:\n{folder_path}",
                          wraplength=400)
        message.pack(pady=(0, 10))
        
        # Add OK button
        ok_button = ttk.Button(main_frame, 
                             text="OK", 
                             command=confirm_window.destroy)
        ok_button.pack()
        
        # Make window modal
        confirm_window.transient(root)
        confirm_window.grab_set()
        
        # Center the window
        confirm_window.geometry("450x150")
        confirm_window.update_idletasks()
        x = root.winfo_x() + (root.winfo_width() // 2) - (confirm_window.winfo_width() // 2)
        y = root.winfo_y() + (root.winfo_height() // 2) - (confirm_window.winfo_height() // 2)
        confirm_window.geometry(f"+{x}+{y}")
        
        confirm_window.wait_window()

# Table update functions
def sort_table(reverse: bool = True) -> None:
    """
    Sort the table by DLSite ID.
    
    Args:
        reverse: Whether to sort in descending (True) or ascending (False) order
    
    Sorts the table entries by their DLSite ID, ignoring the presence markers.
    The sort order toggles between ascending and descending when clicking the
    column header.
    """
    # Get all items from the table
    items = [(table.set(item, "ID"), item) for item in table.get_children()]
    
    def natural_sort_key(id_str: str) -> str:
        # Extract the ID part after the marker, ignoring the marker character
        id_part = id_str.split(" - ", 1)[1] if " - " in id_str else id_str
        
        # For numeric IDs, pad them with zeros to align with RJ format
        if id_part.isdigit():
            return f"RJ{int(id_part):08d}"
        return id_part
    
    # Sort items based on the ID
    items.sort(key=lambda x: natural_sort_key(x[0]), reverse=reverse)
    
    # Reorder items in the table
    for index, (_, item) in enumerate(items):
        table.move(item, "", index)
    
    # Update the command to toggle the sort order next time
    table.heading("ID", command=lambda: sort_table(not reverse))

# ID management functions
def add_id() -> None:
    """
    Add a new DLSite ID.
    
    Opens a dialog for entering a new DLSite ID and its metadata (version,
    tested status). Validates the input and adds it to the database if valid.
    """
    add_window = tk.Toplevel(root)
    add_window.title("Add New Entry")
    add_window.geometry("400x250")
    add_window.resizable(False, False)
    add_window.transient(root)
    add_window.grab_set()
    
    # Apply current theme
    theme = DARK_THEME if current_theme == 'dark' else LIGHT_THEME
    add_window.configure(bg=theme['bg'])
    
    # Main container with padding
    main_frame = ttk.Frame(add_window)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
    
    # Form frame
    form_frame = ttk.Frame(main_frame)
    form_frame.pack(fill=tk.X)
    
    # ID Entry with label frame
    id_frame = ttk.Frame(form_frame)
    id_frame.pack(fill=tk.X, pady=(0, 15))
    id_label = ttk.Label(id_frame, text="DLSite ID:", width=12, anchor='e')
    id_label.pack(side=tk.LEFT, padx=(0, 15))
    id_entry = ttk.Entry(id_frame, width=30, font=('TkDefaultFont', 10))
    id_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3)
    
    # Version Entry with label frame
    version_frame = ttk.Frame(form_frame)
    version_frame.pack(fill=tk.X, pady=(0, 20))
    version_label = ttk.Label(version_frame, text="Version:", width=12, anchor='e')
    version_label.pack(side=tk.LEFT, padx=(0, 15))
    version_entry = ttk.Entry(version_frame, width=30, font=('TkDefaultFont', 10))
    version_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3)
    
    # Bottom frame for checkbox and buttons
    bottom_frame = ttk.Frame(main_frame)
    bottom_frame.pack(fill=tk.X, pady=(0, 0))
    
    # Tested checkbox
    tested_var = tk.StringVar(value="No")
    style.configure('Large.TCheckbutton',
                   padding=(15, 8),
                   font=('TkDefaultFont', 11))
                   
    tested_check = ttk.Checkbutton(
        bottom_frame,
        text="Tested",
        variable=tested_var,
        onvalue="Yes",
        offvalue="No",
        style='Large.TCheckbutton'
    )
    tested_check.pack(side=tk.LEFT)
    
    # Buttons
    button_frame = ttk.Frame(bottom_frame)
    button_frame.pack(side=tk.RIGHT)
    
    cancel_button = ttk.Button(
        button_frame,
        text="Cancel",
        command=add_window.destroy,
        style='Large.TButton'
    )
    cancel_button.pack(side=tk.LEFT, padx=(0, 10))
    
    save_button = ttk.Button(
        button_frame,
        text="Save",
        command=lambda: save_id(id_entry.get(), version_entry.get(), tested_var.get()),
        style='Large.TButton'
    )
    save_button.pack(side=tk.LEFT)
    
    # Center window on parent
    add_window.update_idletasks()
    x = root.winfo_x() + (root.winfo_width() // 2) - (add_window.winfo_width() // 2)
    y = root.winfo_y() + (root.winfo_height() // 2) - (add_window.winfo_height() // 2)
    add_window.geometry(f"+{x}+{y}")
    
    # Set focus to ID entry
    id_entry.focus_set()
    
    add_window.wait_window()

def save_id(dlsite_id: str, version: str, tested: str) -> None:
    if not dlsite_id:
        messagebox.showerror("Error", "ID cannot be empty.")
        return

    # Standardize version format
    if version:
        if version.lower().startswith('v'):
            version = version[1:]
        version = f"v{version}"
    else:
        version = ""

    if DEBUG_ENABLED:
        print(f"[DEBUG] Adding entry - ID: {dlsite_id}, Version: '{version}'")

    conn = get_connection()
    cursor = conn.cursor()

    # Check for duplicate entry
    cursor.execute(
        "SELECT rowid FROM dlsite_ids WHERE dlsite_id = ? AND version = ?",
        (dlsite_id, version)
    )
    if cursor.fetchone():
        messagebox.showerror(
            "Error",
            f"An entry with ID {dlsite_id} and version {version} already exists."
        )
        conn.close()
        return

    # Add the new entry
    cursor.execute(
        "INSERT INTO dlsite_ids (dlsite_id, version, tested) VALUES (?, ?, ?)",
        (dlsite_id, version, tested)
    )
    conn.commit()
    conn.close()
        
    refresh_table()
    add_window.destroy()

def edit_id(event: Optional[tk.Event] = None) -> None:
    """
    Edit an existing DLSite ID.
    
    Args:
        event: Optional event object from GUI interaction
    
    Opens a dialog for editing the selected DLSite ID's metadata. Updates
    the database with any changes made.
    """
    # Check if click was on header
    if event and event.widget.identify_region(event.x, event.y) == "heading":
        return
        
    # Get the selected item
    selected_items = table.selection()
    if not selected_items:
        messagebox.showwarning("Warning", "Please select an entry to edit.")
        return

    entry_id = selected_items[0]
    
    # Get current values
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT dlsite_id, tested, version FROM dlsite_ids WHERE rowid = ?", (entry_id,))
    current_values = cursor.fetchone()
    conn.close()
    
    if not current_values:
        messagebox.showerror("Error", "Could not find the selected entry.")
        return
    
    dlsite_id, tested_val, version_val = current_values
    # Clean up the ID - remove any markers that might be present
    dlsite_id = dlsite_id.replace(f"{PRESENT_MARKER} - ", "").replace(f"{MISSING_MARKER} - ", "")
    
    if version_val in ["-", ""]:
        version_val = ""
    elif version_val:
        version_val = strip_version_prefix(version_val)

    # Create edit window
    edit_window = tk.Toplevel(root)
    edit_window.title("Edit Entry")
    edit_window.geometry("400x250")
    edit_window.resizable(False, False)
    edit_window.transient(root)  # Make it modal
    edit_window.grab_set()  # Make it modal
    
    # Apply current theme
    theme = DARK_THEME if current_theme == 'dark' else LIGHT_THEME
    edit_window.configure(bg=theme['bg'])
    
    # Main container with padding
    main_frame = ttk.Frame(edit_window)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
    
    # Form frame
    form_frame = ttk.Frame(main_frame)
    form_frame.pack(fill=tk.X)
    
    # ID Entry with label frame
    id_frame = ttk.Frame(form_frame)
    id_frame.pack(fill=tk.X, pady=(0, 15))
    id_label = ttk.Label(id_frame, text="DLSite ID:", width=10, anchor='e')
    id_label.pack(side=tk.LEFT, padx=(0, 10))
    id_entry = ttk.Entry(id_frame, width=25, font=('TkDefaultFont', 10))
    id_entry.insert(0, dlsite_id)
    id_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=2)
    
    # Version Entry with label frame
    version_frame = ttk.Frame(form_frame)
    version_frame.pack(fill=tk.X, pady=(0, 20))
    version_label = ttk.Label(version_frame, text="Version:", width=10, anchor='e')
    version_label.pack(side=tk.LEFT, padx=(0, 10))
    version_entry = ttk.Entry(version_frame, width=25, font=('TkDefaultFont', 10))
    version_entry.insert(0, version_val)
    version_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=2)
    
    # Bottom frame for checkbox and buttons
    bottom_frame = ttk.Frame(main_frame)
    bottom_frame.pack(fill=tk.X, pady=(0, 0))
    
    # Tested checkbox
    tested_var = tk.StringVar(value=tested_val)
    style.configure('Large.TCheckbutton',
                   padding=(10, 5),
                   font=('TkDefaultFont', 10))
    tested_check = ttk.Checkbutton(
        bottom_frame,
        text="Tested",
        variable=tested_var,
        onvalue="Yes",
        offvalue="No",
        style='Large.TCheckbutton'
    )
    tested_check.pack(side=tk.LEFT)
    
    # Buttons
    button_frame = ttk.Frame(bottom_frame)
    button_frame.pack(side=tk.RIGHT)
    
    cancel_button = ttk.Button(
        button_frame,
        text="Cancel",
        command=edit_window.destroy,
        style='Large.TButton'
    )
    cancel_button.pack(side=tk.LEFT, padx=(0, 10))
    
    save_button = ttk.Button(
        button_frame,
        text="Save",
        command=lambda: save_changes(entry_id, id_entry.get(), version_entry.get(), tested_var.get(), edit_window),
        style='Large.TButton'
    )
    save_button.pack(side=tk.LEFT)
    
    # Center window on parent
    edit_window.update_idletasks()
    x = root.winfo_x() + (root.winfo_width() // 2) - (edit_window.winfo_width() // 2)
    y = root.winfo_y() + (root.winfo_height() // 2) - (edit_window.winfo_height() // 2)
    edit_window.geometry(f"+{x}+{y}")
    
    # Set focus to ID entry
    id_entry.focus_set()
    
    edit_window.wait_window()

def save_changes(entry_id: str, dlsite_id: str, version: str, tested: str, window: tk.Toplevel) -> None:
    new_id = dlsite_id.strip()
    new_tested = tested
    new_version = version.strip()
    
    if not new_id:
        messagebox.showerror("Error", "ID cannot be empty.")
        return

    # Standardize version format
    if new_version:
        if new_version.lower().startswith('v'):
            new_version = new_version[1:]
        new_version = f"v{new_version}"
    else:
        new_version = ""

    if DEBUG_ENABLED:
        print(f"[DEBUG] Updating entry - ID: {new_id}, Version: '{new_version}'")

    conn = get_connection()
    cursor = conn.cursor()
        
    # Check for duplicate entry
    cursor.execute("""
        SELECT rowid FROM dlsite_ids 
        WHERE dlsite_id = ? AND version = ? AND rowid != ?
    """, (new_id, new_version, entry_id))
        
    if cursor.fetchone():
        messagebox.showerror(
            "Error",
            f"An entry with ID {new_id} and version {new_version} already exists."
        )
        conn.close()
        return

    # Update the entry
    cursor.execute("""
        UPDATE dlsite_ids 
        SET dlsite_id = ?, tested = ?, version = ? 
        WHERE rowid = ?
    """, (new_id, new_tested, new_version, entry_id))
        
    conn.commit()
    conn.close()
        
    # Refresh table and close window
    refresh_table()
    window.destroy()

def remove_entry() -> None:
    """
    Remove a DLSite ID from the database.
    
    Removes the selected DLSite ID from the database after confirmation.
    Updates the table display to reflect the removal.
    """
    selected_item = table.selection()
    if not selected_item:
        messagebox.showerror("Error", "Please select an entry to remove.")
        return

    confirm = messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this entry?")
    if not confirm:
        return

    entry_id = selected_item[0]

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM dlsite_ids WHERE rowid = ?", (entry_id,))
    conn.commit()
    conn.close()

    refresh_table()

# Debug logging functions
def toggle_debug() -> None:
    """
    Toggle debug mode and save to config.
    """
    global DEBUG_ENABLED
    DEBUG_ENABLED = not DEBUG_ENABLED
    save_config()
    messagebox.showinfo("Settings", 
                       "Debug logging enabled. Restart application to apply changes." 
                       if DEBUG_ENABLED else 
                       "Debug logging disabled. Restart application to apply changes.")

def show_settings() -> None:
    """
    Show settings window.
    
    Opens a dialog for configuring application settings including:
    - Folder path for scanning
    - Theme selection (light/dark)
    - Debug mode toggle
    """
    settings_window = tk.Toplevel(root)
    settings_window.title("Settings")
    settings_window.geometry("400x320")
    settings_window.resizable(False, False)
    settings_window.transient(root)  # Make it modal
    settings_window.grab_set()  # Make it modal
    
    # Get current theme colors
    theme = DARK_THEME if current_theme == 'dark' else LIGHT_THEME
    settings_window.configure(bg=theme['bg'])
    
    # Create main frame with proper styling
    main_frame = ttk.Frame(settings_window)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # Configure styles for settings window
    style.configure('Settings.TFrame', background=theme['bg'])
    style.configure('Settings.TLabelframe',
                   background=theme['bg'],
                   foreground=theme['fg'])
    style.configure('Settings.TLabelframe.Label',
                   background=theme['bg'],
                   foreground=theme['fg'])
    style.configure('Settings.TCheckbutton',
                   background=theme['bg'],
                   foreground=theme['fg'])
    style.configure('Settings.TRadiobutton',
                   background=theme['bg'],
                   foreground=theme['fg'])
    
    # Debug mode section with border
    debug_var = tk.BooleanVar(value=DEBUG_ENABLED)
    debug_frame = tk.LabelFrame(main_frame, text="Debug Settings",
                              bg=theme['bg'],
                              fg=theme['fg'],
                              bd=2,
                              relief='groove')
    debug_frame.pack(fill=tk.X, pady=(0, 10), padx=5)
    
    debug_check = ttk.Checkbutton(debug_frame, text="Enable Debug Mode",
                                 variable=debug_var,
                                 style='Settings.TCheckbutton')
    debug_check.pack(padx=5, pady=5)
    
    # Theme section with border
    theme_frame = tk.LabelFrame(main_frame, text="Theme Settings",
                              bg=theme['bg'],
                              fg=theme['fg'],
                              bd=2,
                              relief='groove')
    theme_frame.pack(fill=tk.X, pady=(0, 10), padx=5)
    
    theme_var = tk.StringVar(value=current_theme)
    light_radio = ttk.Radiobutton(theme_frame, text="Light Theme",
                                 value="light",
                                 variable=theme_var,
                                 style='Settings.TRadiobutton')
    dark_radio = ttk.Radiobutton(theme_frame, text="Dark Theme",
                                value="dark",
                                variable=theme_var,
                                style='Settings.TRadiobutton')
    light_radio.pack(padx=5, pady=2)
    dark_radio.pack(padx=5, pady=2)
    
    # Folder path section with border
    path_frame = tk.LabelFrame(main_frame, text="Folder Path Settings",
                             bg=theme['bg'],
                             fg=theme['fg'],
                             bd=2,
                             relief='groove')
    path_frame.pack(fill=tk.X, pady=(0, 10), padx=5)
    
    # Create a frame for the path display with proper styling
    path_display_frame = ttk.Frame(path_frame)
    path_display_frame.pack(fill=tk.X, padx=5, pady=2)
    
    path_label = ttk.Label(path_display_frame, text="Current Path:",
                          style='Settings.TLabel')
    path_label.pack(side=tk.LEFT, padx=(0, 5))
    
    path_value = ttk.Label(path_display_frame,
                          text=FOLDER_PATH if FOLDER_PATH else "Not set",
                          wraplength=300,
                          style='Settings.TLabel')
    path_value.pack(side=tk.LEFT, fill=tk.X, expand=True)
    
    def update_folder_path() -> None:
        folder = filedialog.askdirectory()
        if folder:
            save_folder_path(folder)
            path_value.configure(text=folder)
    
    change_path_btn = ttk.Button(path_frame, text="Change Folder Path",
                                command=update_folder_path)
    change_path_btn.pack(padx=5, pady=5)
    
    def apply_settings() -> None:
        global current_theme, DEBUG_ENABLED
        new_debug = debug_var.get()
        new_theme = theme_var.get()
        
        # Save all settings
        config = {
            'debug_enabled': new_debug,
            'theme': new_theme,
            'folder_path': FOLDER_PATH
        }
        save_config(config)
        
        # Apply changes
        DEBUG_ENABLED = new_debug
        if new_theme != current_theme:
            current_theme = new_theme
            apply_theme()
        
        settings_window.destroy()
        messagebox.showinfo("Settings", "Settings have been saved successfully!")
    
    # Button frame at the bottom
    button_frame = ttk.Frame(main_frame)
    button_frame.pack(fill=tk.X, pady=10)
    
    # Create Apply button matching main window buttons
    apply_button = ttk.Button(button_frame, text="Apply",
                             command=apply_settings)
    apply_button.pack(side=tk.RIGHT, padx=5)
    
    settings_window.wait_window()

def main() -> None:
    """
    Initialize and run the main application window.
    
    Sets up the main window with all necessary widgets, initializes the database,
    loads configuration, and starts the main event loop. This is the entry point
    for the graphical interface.
    """
    global root, table, style, FOLDER_PATH, current_theme, DEBUG_ENABLED
    
    # Hide __pycache__ directory if it exists
    pycache_dir = os.path.join(os.path.dirname(__file__), "__pycache__")
    if os.path.exists(pycache_dir):
        os.system(f'attrib +h "{pycache_dir}"')
    
    # Main window setup
    root = tk.Tk()
    root.title("DLSite Collection Helper")
    root.geometry("800x400")
    
    # Create style for ttk widgets
    style = ttk.Style()
    
    # Load configuration and apply settings
    config = load_config()
    FOLDER_PATH = config.get('folder_path', None)
    current_theme = config.get('theme', 'light')
    DEBUG_ENABLED = config.get('debug_enabled', False)
    
    # Setup database
    setup_database()
    backup_database()
    
    # Create main frame
    main_frame = ttk.Frame(root)
    main_frame.pack(fill=tk.BOTH, expand=True)

    # Frame for the table
    tree_frame = ttk.Frame(main_frame)
    tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    # Create table style and setup
    style.configure("marked", background="lightgreen", foreground="black")

    # Create Treeview (table) first
    table = ttk.Treeview(tree_frame, columns=("ID", "Tested", "Version"), show="headings")
    table.heading("ID", text="DLSite ID", command=lambda: sort_table(False))  # First click will sort ascending
    table.heading("Tested", text="Tested")
    table.heading("Version", text="Version")
    
    # Set fixed column widths to prevent inconsistent spacing
    table.column("ID", width=150, minwidth=150)
    table.column("Tested", width=70, minwidth=70)
    table.column("Version", width=70, minwidth=70)
    
    table.pack(fill=tk.BOTH, expand=True)

    # Apply theme if dark mode
    if current_theme == 'dark':
        apply_theme()

    # Bind double-click event to open edit window
    table.bind("<Double-1>", edit_id)

    # Create button frame with proper styling
    button_frame = ttk.Frame(main_frame)
    button_frame.pack(fill=tk.X, padx=5, pady=(0, 5))

    # Add buttons with consistent spacing
    add_button = ttk.Button(button_frame, text="Add ID", command=add_id)
    add_button.pack(side=tk.LEFT, padx=(0, 2))

    remove_button = ttk.Button(button_frame, text="Remove Selected ID", command=remove_entry)
    remove_button.pack(side=tk.LEFT, padx=2)

    # Add search entry with theme-aware style
    search_frame = ttk.Frame(button_frame)
    search_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)

    search_entry = ttk.Entry(search_frame, style='Search.TEntry')
    search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
    search_entry.bind('<Return>', lambda event: refresh_table(search_entry.get()))

    settings_button = ttk.Button(button_frame, text="Settings", command=show_settings)
    settings_button.pack(side=tk.RIGHT, padx=(2, 0))

    refresh_button = ttk.Button(button_frame, text="Refresh", command=refresh_table)
    refresh_button.pack(side=tk.RIGHT, padx=2)

    # Set minimum window size
    root.minsize(600, 400)

    # Center window on screen
    window_width = 800
    window_height = 600
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    center_x = int(screen_width/2 - window_width/2)
    center_y = int(screen_height/2 - window_height/2)
    root.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')

    # Automatically refresh table on startup
    refresh_table()

    # Start the application
    root.mainloop()

if __name__ == '__main__':
    main()
