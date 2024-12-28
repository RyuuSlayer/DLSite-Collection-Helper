# DLSite Collection Helper

A desktop application for managing and tracking DLSite content versions with a user-friendly interface.

## Features

- **Content Management**: Track and manage DLSite content with unique IDs and versions
- **Version Tracking**: Automatically detects and marks ID's as found with version information from filenames
- **Search Functionality**: Quickly find specific entries in your database
- **Testing Status**: Mark content as tested/untested for quality assurance
- **Dark/Light Theme**: Customizable interface with support for both light and dark themes
- **Database Backup**: Automatic database backups to prevent data loss
- **Debug Mode**: Optional debug mode for troubleshooting

## Getting Started

1. Launch the application by running `start_dlsite_manager.pyw`
2. On first launch, you'll be prompted to select a folder containing your DLSite content
3. The application will automatically scan the folder and populate the database

## Usage

### Basic Operations

- **Add New Entry**: Click the "Add" button to manually add a new entry
- **Edit Entry**: Double-click on any entry to edit its details
- **Remove Entry**: Select an entry and use the remove option to delete it
- **Sort Entries**: Click on ID column header to sort entries
- **Search**: Use the search bar to filter entries

### Settings

Access the settings menu to:
- Change theme (Light/Dark)
- Toggle debug mode
- Configure folder path
- Manage database settings

### File Naming Convention

The application automatically extracts IDs and versions from filenames following these patterns:
- ID format: `RJ######`
- Version format: Either `(v#.#)` or `(#.#)`
Example: `RJ123456 (v1.2)`

### Database

- Automatically backs up on startup
- Maintains the last 3 backup copies
- Stores IDs, versions, and testing status

## Technical Details

- Written in Python using tkinter for the GUI
- SQLite database for data storage
- Configurable via autocreated `config.json`
- Debug logging available for troubleshooting

## Files

- `start_dlsite_manager.pyw`: Main entry point
- `src/gui.py`: Main GUI implementation
- `src/database.py`: Database operations
- `src/file_utils.py`: File handling utilities
- `dlsite_ids.db`: SQLite database file
- `config.json`: Configuration settings
