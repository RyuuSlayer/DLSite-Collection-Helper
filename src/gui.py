import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter.simpledialog import askstring

from styles import LIGHT_THEME, DARK_THEME, PRESENT_MARKER, MISSING_MARKER
from database import (
    setup_database, backup_database, get_connection,
    update_marked_status, reset_all_marked_status
)
from file_utils import (
    format_version, strip_version_prefix, extract_id_and_version,
    load_config, save_config
)
from config import DEBUG_ENABLED

# Global variables
FOLDER_PATH = None
current_theme = 'light'
sort_order = True  # True for ascending, False for descending
root = None
table = None
style = None

def apply_theme():
    """Apply the current theme to all widgets"""
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

def check_folder_for_ids():
    """Check if the folder contains the ID files and update the database."""
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

def refresh_table(search_query=None, check_folder=True):
    """Refresh the table with current data."""
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
        
        # Format the ID with prefix based on tested status and presence
        if marked:
            display_id = f"{PRESENT_MARKER} - {dlsite_id}"
        else:
            display_id = f"{MISSING_MARKER} - {dlsite_id}"
        table.insert("", "end", iid=rowid, values=(display_id, tested, display_version))

    conn.close()

# Folder path management functions
def load_folder_path():
    """Load the folder path from the configuration file."""
    global FOLDER_PATH, current_theme
    config = load_config()
    FOLDER_PATH = config['folder_path']
    current_theme = config['theme']

def save_folder_path(folder_path):
    """Save the folder path to the config file."""
    global FOLDER_PATH
    FOLDER_PATH = folder_path
    config = {
        'folder_path': FOLDER_PATH,
        'theme': current_theme
    }
    save_config(config)
    refresh_table()

def prompt_for_folder_path():
    """Prompt user to set the folder path."""
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
        
        # Create main frame with theme
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
def sort_table():
    global sort_order  # Declare it as global to modify it within the function

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, dlsite_id, tested, version, marked FROM dlsite_ids")

    rows = cursor.fetchall()
    
    # Sort the rows based on the dlsite_id
    rows = sorted(rows, key=lambda x: x[1], reverse=sort_order)
    sort_order = not sort_order  # Toggle sort order for next click
    
    # Clear the current table
    for item in table.get_children():
        table.delete(item)

    # Insert sorted rows into the table
    for row in rows:
        entry_id, dlsite_id, tested, version, marked = row
        tested = tested or "-"
        
        # Format version for display (add 'v' prefix if not empty and doesn't already have it)
        display_version = "-"
        if version:
            if not version.lower().startswith('v'):
                display_version = f"v{version}"
            else:
                display_version = version

        # Modify the ID display based on marked status
        if marked == 1:
            dlsite_id = f"{PRESENT_MARKER} {dlsite_id}"
        else:
            dlsite_id = f"{MISSING_MARKER} {dlsite_id}"

        # Insert the row into the table with entry_id as the unique identifier
        table.insert("", "end", iid=entry_id, values=(dlsite_id, tested, display_version), tags=("marked" if marked else ""))

    conn.close()

# ID management functions
def add_id():
    """Add a new ID to the database."""
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
    id_label.pack(side=tk.LEFT, padx=(0, 10))
    id_entry = ttk.Entry(id_frame)
    id_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
    
    # Version Entry with label frame
    version_frame = ttk.Frame(form_frame)
    version_frame.pack(fill=tk.X, pady=(0, 20))
    version_label = ttk.Label(version_frame, text="Version:", width=12, anchor='e')
    version_label.pack(side=tk.LEFT, padx=(0, 10))
    version_entry = ttk.Entry(version_frame)
    version_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
    
    def save_id():
        dlsite_id = id_entry.get().strip().upper()
        version = version_entry.get().strip()
        
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
            (dlsite_id, version, "No")
        )
        conn.commit()
        conn.close()
        
        refresh_table()
        add_window.destroy()
    
    # Buttons frame
    button_frame = ttk.Frame(main_frame)
    button_frame.pack(fill=tk.X, pady=(20, 0))
    
    # Save and Cancel buttons
    save_button = ttk.Button(button_frame, text="Save", command=save_id)
    save_button.pack(side=tk.RIGHT, padx=(5, 0))
    
    cancel_button = ttk.Button(button_frame, text="Cancel", command=add_window.destroy)
    cancel_button.pack(side=tk.RIGHT)
    
    # Center window on parent
    add_window.update_idletasks()
    x = root.winfo_x() + (root.winfo_width() // 2) - (add_window.winfo_width() // 2)
    y = root.winfo_y() + (root.winfo_height() // 2) - (add_window.winfo_height() // 2)
    add_window.geometry(f"+{x}+{y}")
    
    # Set focus to ID entry
    id_entry.focus_set()
    
    add_window.wait_window()

def edit_id(event=None):
    """Edit the selected ID's information."""
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
    edit_window.geometry("400x300")
    edit_window.resizable(False, False)
    edit_window.transient(root)
    edit_window.grab_set()
    
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
    id_label = ttk.Label(id_frame, text="DLSite ID:", width=12, anchor='e')
    id_label.pack(side=tk.LEFT, padx=(0, 10))
    id_entry = ttk.Entry(id_frame)
    id_entry.insert(0, dlsite_id)
    id_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
    
    # Version Entry with label frame
    version_frame = ttk.Frame(form_frame)
    version_frame.pack(fill=tk.X, pady=(0, 15))
    version_label = ttk.Label(version_frame, text="Version:", width=12, anchor='e')
    version_label.pack(side=tk.LEFT, padx=(0, 10))
    version_entry = ttk.Entry(version_frame)
    version_entry.insert(0, version_val)
    version_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
    
    # Tested checkbox frame
    tested_frame = ttk.Frame(form_frame)
    tested_frame.pack(fill=tk.X, pady=(0, 20))
    tested_var = tk.StringVar(value=tested_val)
    tested_check = ttk.Checkbutton(
        tested_frame,
        text="Tested",
        variable=tested_var,
        onvalue="Yes",
        offvalue="No"
    )
    tested_check.pack(padx=(70, 0))  # Align with input fields
    
    def save_changes():
        new_id = id_entry.get().strip()
        new_tested = tested_var.get()
        new_version = version_entry.get().strip()
        
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
        
        # Refresh table and check folder
        refresh_table()
        edit_window.destroy()
    
    # Buttons frame
    button_frame = ttk.Frame(main_frame)
    button_frame.pack(fill=tk.X, pady=(20, 0))
    
    # Save and Cancel buttons
    save_button = ttk.Button(button_frame, text="Save", command=save_changes)
    save_button.pack(side=tk.RIGHT, padx=(5, 0))
    
    cancel_button = ttk.Button(button_frame, text="Cancel", command=edit_window.destroy)
    cancel_button.pack(side=tk.RIGHT)
    
    # Center window on parent
    edit_window.update_idletasks()
    x = root.winfo_x() + (root.winfo_width() // 2) - (edit_window.winfo_width() // 2)
    y = root.winfo_y() + (root.winfo_height() // 2) - (edit_window.winfo_height() // 2)
    edit_window.geometry(f"+{x}+{y}")
    
    # Set focus to ID entry
    id_entry.focus_set()
    
    edit_window.wait_window()

def remove_entry():
    """Remove selected entry from the database and table."""
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
def toggle_debug():
    """Toggle debug mode and save to config."""
    global DEBUG_ENABLED
    DEBUG_ENABLED = not DEBUG_ENABLED
    save_config()
    messagebox.showinfo("Settings", 
                       "Debug logging enabled. Restart application to apply changes." 
                       if DEBUG_ENABLED else 
                       "Debug logging disabled. Restart application to apply changes.")

def show_settings():
    """Show settings window."""
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
    
    def update_folder_path():
        folder = filedialog.askdirectory()
        if folder:
            save_folder_path(folder)
            path_value.configure(text=folder)
    
    change_path_btn = ttk.Button(path_frame, text="Change Folder Path",
                                command=update_folder_path)
    change_path_btn.pack(padx=5, pady=5)
    
    def apply_settings():
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

def main():
    """Main function to setup and run the application."""
    global root, table, style, FOLDER_PATH, current_theme, DEBUG_ENABLED
    
    # Hide __pycache__ directory if it exists
    pycache_dir = os.path.join(os.path.dirname(__file__), "__pycache__")
    if os.path.exists(pycache_dir):
        os.system(f'attrib +h "{pycache_dir}"')
    
    # Main window setup
    root = tk.Tk()
    root.title("DLSite Collection Manager")
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
    table.heading("ID", text="DLSite ID", command=lambda: sort_table())
    table.heading("Tested", text="Tested")
    table.heading("Version", text="Version")
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