"""GitHub Release based updater for Moviu Print Server."""

import json
import logging
import urllib.request
import webbrowser
from typing import Optional, Dict

from .config import VERSION

GITHUB_REPO = "dancoLgh/moviu"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

logger = logging.getLogger(__name__)

def get_latest_release_info() -> Optional[Dict]:
    """Fetch the latest release information from GitHub."""
    try:
        # User-Agent is required by GitHub API
        request = urllib.request.Request(
            GITHUB_API_URL, 
            headers={"User-Agent": "Moviu-Print-Server-Updater"}
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            if response.status == 200:
                return json.loads(response.read().decode())
    except Exception as e:
        logger.error(f"Error checking for updates: {e}")
    return None

def check_for_updates() -> tuple[bool, Optional[str], Optional[str]]:
    """
    Check if a newer version is available.
    Returns: (is_update_available, latest_version, download_url)
    """
    info = get_latest_release_info()
    if not info:
        return False, None, None
    
    latest_tag = info.get("tag_name", "").strip("v")
    current_tag = VERSION.strip("v")
    
    # Simple semantic versioning check (assuming x.y.z format)
    try:
        latest_parts = [int(p) for p in latest_tag.split(".")]
        current_parts = [int(p) for p in current_tag.split(".")]
        
        if latest_parts > current_parts:
            return True, f"v{latest_tag}", info.get("html_url")
    except ValueError:
        # Fallback to string comparison if not numeric
        if latest_tag != current_tag:
            return True, f"v{latest_tag}", info.get("html_url")
            
    return False, VERSION, None

def open_release_page(url: str):
    """Open the GitHub release page in the system browser."""
    webbrowser.open(url)
