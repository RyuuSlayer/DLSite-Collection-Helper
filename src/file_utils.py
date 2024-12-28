import os
import re
import json
from config import DEBUG_ENABLED

CONFIG_FILE = "config.json"

def format_version(version):
    """Format version string to ensure proper 'v' prefix."""
    if not version or version.strip() == "-":  # Handle empty or placeholder
        return ""
    # Remove any existing 'v' prefix and any surrounding whitespace
    version = version.strip().lower()
    if version.startswith('v'):
        version = version[1:]
    # Only add 'v' prefix if there's actually a version
    return f"v{version}" if version else ""

def strip_version_prefix(version):
    """Remove 'v' prefix from version if present."""
    if not version:
        return None
    version = version.strip()
    if version.lower().startswith('v'):
        return version[1:]
    return version

def extract_id_and_version(filename, debug_enabled=False):
    """Extract DLSite ID and version from filename."""
    # Remove file extension
    name_without_ext = os.path.splitext(filename)[0]
    
    if debug_enabled:
        print(f"\n[DEBUG] Analyzing file: '{filename}'")
        print(f"[DEBUG] Name without extension: '{name_without_ext}'")
    
    # Extract just the RJ part first
    rj_match = re.search(r'(RJ\d+)', name_without_ext)
    if not rj_match:
        if debug_enabled:
            print(f"[DEBUG] No RJ ID found in filename")
        return None, None
    
    dlsite_id = rj_match.group(1)
    
    # First try to find version in parentheses with v prefix
    version_match = re.search(r'\((v?(\d+(\.\d+)*))\)', name_without_ext)
    
    # If no version found in parentheses, check for just numbers in parentheses
    if not version_match:
        version_match = re.search(r'\((\d+(\.\d+)*)\)', name_without_ext)
    
    if version_match:
        # Get the full version string from the match
        raw_version = version_match.group(1)
        if debug_enabled:
            print(f"[DEBUG] Found version in parentheses: '{raw_version}'")
        
        # Remove 'v' prefix if present and add it back in a standardized way
        if raw_version.lower().startswith('v'):
            version = raw_version[1:]
        else:
            version = raw_version
        version = f"v{version}"
        
        if debug_enabled:
            print(f"[DEBUG] Standardized version: '{version}'")
    else:
        version = None
        if debug_enabled:
            print(f"[DEBUG] No version found in filename")
    
    if debug_enabled:
        print(f"[DEBUG] Final result - ID: {dlsite_id}, Version: {version}")
    
    return dlsite_id, version

def load_config():
    """Load configuration from file."""
    default_config = {
        'folder_path': None,
        'debug_enabled': False,
        'theme': 'light'
    }
    
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                loaded_config = json.load(f)
                # Update default config with loaded values
                default_config.update(loaded_config)
    except Exception as e:
        print(f"Error loading config: {e}")
    
    return default_config

def save_config(config):
    """Save configuration to file."""
    try:
        # Ensure all required keys are present
        required_keys = {'folder_path', 'debug_enabled', 'theme'}
        if not all(key in config for key in required_keys):
            raise ValueError("Missing required configuration keys")
            
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        print(f"Error saving config: {e}")
