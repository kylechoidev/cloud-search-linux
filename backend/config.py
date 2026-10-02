"""Configuration settings and dynamic remote auto-discovery for Cloud Search Linux."""
import json
import os
import subprocess
from pathlib import Path
from typing import Dict, Any

APP_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = APP_DIR / "data"
SRC_DIR = APP_DIR / "src"
WEB_DIR = SRC_DIR / "web"
ASSETS_DIR = APP_DIR / "assets"

CONFIG_DIR = Path.home() / ".config" / "cloud-search-lite"
CONFIG_FILE = CONFIG_DIR / "config.json"
USER_DATA_DIR = CONFIG_DIR / "browser-profile"

DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "index.db"

# Fallback: if running from dev repo and local DB is unindexed, use the installed production DB
INSTALLED_DB = Path.home() / ".local" / "share" / "cloud-search-lite-app" / "data" / "index.db"
if (not DB_PATH.exists() or DB_PATH.stat().st_size < 100000) and INSTALLED_DB.exists():
    DB_PATH = INSTALLED_DB

PORT = 8799
HOST = "127.0.0.1"
WM_CLASS = "CloudSearchLite"

DEFAULT_COLORS = [
    ("#0078d4", "rgba(0, 120, 212, 0.15)"),   # Blue (OneDrive)
    ("#34a853", "rgba(52, 168, 83, 0.15)"),   # Green (Google Drive)
    ("#0061ff", "rgba(0, 97, 255, 0.15)"),    # Blue (Dropbox)
    ("#ea4335", "rgba(234, 67, 53, 0.15)"),   # Red
    ("#a855f7", "rgba(168, 85, 247, 0.15)"),  # Purple
    ("#f59e0b", "rgba(245, 158, 11, 0.15)"),  # Amber
    ("#06b6d4", "rgba(6, 182, 212, 0.15)"),   # Cyan
]

KNOWN_REMOTE_NAMES = {
    "onedrive": "OneDrive",
    "gdrive": "Google Drive",
    "googledrive": "Google Drive",
    "dropbox": "Dropbox",
    "box": "Box",
    "nextcloud": "Nextcloud",
    "owncloud": "OwnCloud",
    "s3": "Amazon S3",
}

def discover_rclone_remotes() -> Dict[str, Dict[str, Any]]:
    """Automatically discover configured rclone remotes."""
    remotes = {}
    try:
        out = subprocess.check_output(
            ["rclone", "listremotes"],
            text=True,
            stderr=subprocess.DEVNULL
        )
        remote_lines = [r.strip() for r in out.splitlines() if r.strip()]
        for idx, r in enumerate(remote_lines):
            raw_id = r.rstrip(":").lower()
            clean_name = KNOWN_REMOTE_NAMES.get(raw_id, raw_id.capitalize())
            color, badge_bg = DEFAULT_COLORS[idx % len(DEFAULT_COLORS)]
            
            # Look for common mount directories
            candidate_mounts = [
                Path.home() / clean_name,
                Path.home() / raw_id,
                Path.home() / (clean_name.replace(" ", "")),
                Path(f"/mnt/{raw_id}"),
                Path(f"/media/{raw_id}")
            ]
            mount_path = Path.home() / clean_name
            for c in candidate_mounts:
                if c.exists() and (c.is_mount() or c.is_dir()):
                    mount_path = c
                    break

            remotes[raw_id] = {
                "id": raw_id,
                "name": clean_name,
                "rclone_remote": r if r.endswith(":") else f"{r}:",
                "mount_path": mount_path,
                "color": color,
                "badge_bg": badge_bg,
                "icon": "cloud"
            }
    except Exception:
        pass
    return remotes

def load_remotes() -> Dict[str, Dict[str, Any]]:
    """Load remotes from config file or auto-discover."""
    discovered = discover_rclone_remotes()

    # If config file exists, merge custom mappings
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                user_conf = json.load(f)
                custom_remotes = user_conf.get("remotes", {})
                for r_id, r_info in custom_remotes.items():
                    if "mount_path" in r_info:
                        r_info["mount_path"] = Path(os.path.expanduser(r_info["mount_path"]))
                    discovered[r_id] = {**discovered.get(r_id, {}), **r_info}
        except Exception:
            pass

    # Fallback default if nothing discovered
    if not discovered:
        discovered = {
            "onedrive": {
                "id": "onedrive",
                "name": "OneDrive",
                "rclone_remote": "onedrive:",
                "mount_path": Path.home() / "OneDrive",
                "color": "#0078d4",
                "badge_bg": "rgba(0, 120, 212, 0.15)",
                "icon": "cloud",
            },
            "gdrive": {
                "id": "gdrive",
                "name": "Google Drive",
                "rclone_remote": "gdrive:",
                "mount_path": Path.home() / "GoogleDrive",
                "color": "#34a853",
                "badge_bg": "rgba(52, 168, 83, 0.15)",
                "icon": "google",
            }
        }
    return discovered

REMOTES = load_remotes()
