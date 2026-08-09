"""GitHub Release based updater for Moviu Print Server."""

import json
import logging
import urllib.request
import webbrowser
from typing import Optional, Dict

from .config import VERSION

GITHUB_REPO = "dancoLgh/moviu"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
WEBSITE_DOWNLOAD_URL = "https://dancolgh.github.io/moviu/#descargas"

logger = logging.getLogger(__name__)

def get_latest_release_info(token: Optional[str] = None) -> Optional[Dict]:
    """Fetch the latest release information from GitHub."""
    try:
        headers = {"User-Agent": "Moviu-Print-Server-Updater"}
        if token:
            headers["Authorization"] = f"token {token}"
            
        request = urllib.request.Request(GITHUB_API_URL, headers=headers)
        with urllib.request.urlopen(request, timeout=5) as response:
            if response.status == 200:
                return json.loads(response.read().decode())
    except Exception as e:
        logger.error(f"Error checking for updates: {e}")
    return None

def check_for_updates(token: Optional[str] = None) -> tuple[bool, Optional[str], Optional[str]]:
    """
    Check if a newer version is available.
    Returns: (is_update_available, latest_version, download_url)
    """
    info = get_latest_release_info(token)
    if not info:
        return False, None, None
    
    latest_tag = info.get("tag_name", "").strip("v")
    current_tag = VERSION.strip("v")
    
    # Simple semantic versioning check (assuming x.y.z format)
    try:
        latest_parts = [int(p) for p in latest_tag.split(".")]
        current_parts = [int(p) for p in current_tag.split(".")]
        
        if latest_parts > current_parts:
            return True, f"v{latest_tag}", WEBSITE_DOWNLOAD_URL
    except ValueError:
        # Fallback to string comparison if not numeric
        if latest_tag != current_tag:
            return True, f"v{latest_tag}", WEBSITE_DOWNLOAD_URL
            
    return False, VERSION, None

def open_release_page(url: str):
    """Open the supplied download page in the system browser."""
    webbrowser.open(url)
