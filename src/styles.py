"""
Styles module for DLSite Collection Helper.

This module defines the visual styling and theme configurations for the application.
It includes color schemes for both light and dark themes, as well as display markers
for indicating file presence/absence status.

Color Schemes:
    - Light Theme: Clean, professional light color scheme
    - Dark Theme: Eye-friendly dark color scheme with good contrast

Display Markers:
    - PRESENT_MARKER (✓): Indicates a file is present in the collection
    - MISSING_MARKER (✗): Indicates a file is missing from the collection
"""

# Theme colors and styling configurations
LIGHT_THEME = {
    'bg': '#ffffff',
    'fg': '#000000',
    'select_bg': '#e5f3ff',  # Lighter blue for selection
    'select_fg': '#000000',
    'tree_bg': '#ffffff',
    'tree_fg': '#000000',
    'button_bg': '#f0f0f0',
    'button_fg': '#000000',
    'highlight_bg': '#e5f3ff',  # For highlighted elements
    'highlight_fg': '#000000',
    'border': '#cccccc'  # Light gray border
}

DARK_THEME = {
    'bg': '#2d2d2d',
    'fg': '#ffffff',
    'select_bg': '#404859',  # Subtle blue-gray for selection
    'select_fg': '#ffffff',
    'tree_bg': '#1e1e1e',
    'tree_fg': '#ffffff',
    'button_bg': '#383838',
    'button_fg': '#ffffff',
    'highlight_bg': '#404859',  # For highlighted elements
    'highlight_fg': '#ffffff',
    'border': '#404040'  # Dark gray border
}

# Constants for display
PRESENT_MARKER = "✓"  # Check mark (U+2713)
MISSING_MARKER = "✗"  # Ballot X (U+2717)
