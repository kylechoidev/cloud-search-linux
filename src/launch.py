#!/usr/bin/env python3
"""Launcher & CLI Dispatcher for Cloud Search Lite."""
import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
import urllib.parse
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = APP_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from config import PORT, HOST, WM_CLASS, USER_DATA_DIR, REMOTES

def check_already_running() -> bool:
    """Focus existing window if already open."""
    try:
        out = subprocess.check_output(
            ["wmctrl", "-l", "-x"],
            text=True,
            env={**os.environ, "DISPLAY": os.environ.get("DISPLAY", ":0")},
            stderr=subprocess.DEVNULL
        )
        for line in out.splitlines():
            parts = line.split(None, 4)
            if len(parts) >= 3:
                win_class = parts[2].lower()
                if WM_CLASS.lower() in win_class:
                    print("Cloud Search Lite is already running. Focusing existing window...")
                    subprocess.call(
                        ["wmctrl", "-x", "-a", WM_CLASS],
                        env={**os.environ, "DISPLAY": os.environ.get("DISPLAY", ":0")},
                        stderr=subprocess.DEVNULL
                    )
                    return True
    except Exception:
        pass
    return False

def is_backend_alive() -> bool:
    """Check if local HTTP server is responding."""
    try:
        req = urllib.request.Request(
            f"http://{HOST}:{PORT}/api/ping",
            headers={"User-Agent": "CloudSearchLauncher"}
        )
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            return resp.status == 200
    except Exception:
        return False

def ensure_backend_running():
    """Start backend server as daemon process if not already running."""
    if is_backend_alive():
        return None

    server_script = BACKEND_DIR / "server.py"
    proc = subprocess.Popen(
        [sys.executable, str(server_script)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=str(BACKEND_DIR),
        start_new_session=True
    )

    start = time.time()
    while time.time() - start < 4.0:
        if is_backend_alive():
            return proc
        time.sleep(0.1)

    print("Warning: Backend server took longer than expected to start.")
    return proc

def get_screen_size():
    """Determine root screen width and height."""
    try:
        out = subprocess.check_output(
            ["xwininfo", "-root"],
            text=True,
            env={**os.environ, "DISPLAY": os.environ.get("DISPLAY", ":0")},
            stderr=subprocess.DEVNULL
        )
        w = int(re.search(r"Width:\s+(\d+)", out).group(1))
        h = int(re.search(r"Height:\s+(\d+)", out).group(1))
        return w, h
    except Exception:
        return 1920, 1080

def find_browser_bin() -> str:
    """Find installed Chromium/Brave/Chrome executable."""
    candidates = [
        "brave-browser",
        "chromium",
        "chromium-browser",
        "google-chrome-stable",
        "google-chrome"
    ]
    for b in candidates:
        try:
            path = subprocess.check_output(["which", b], text=True, stderr=subprocess.DEVNULL).strip()
            if path and os.path.exists(path):
                return path
        except Exception:
            continue
    return "brave-browser"

def handle_cli():
    """Handle CLI commands if arguments are provided."""
    parser = argparse.ArgumentParser(description="Cloud Search Lite CLI")
    subparsers = parser.add_subparsers(dest="command")

    # status
    subparsers.add_parser("status", help="Show total indexed files and sync timestamps")

    # search
    p_search = subparsers.add_parser("search", help="Search indexed files from command line")
    p_search.add_argument("query", help="Search term")
    p_search.add_argument("--remote", "-r", choices=["onedrive", "gdrive"], help="Filter by remote")
    p_search.add_argument("--limit", "-n", type=int, default=20, help="Max results")

    # sync
    p_sync = subparsers.add_parser("sync", help="Trigger cloud index sync")
    p_sync.add_argument("--remote", "-r", choices=["onedrive", "gdrive"], help="Sync specific remote")

    # browse
    p_browse = subparsers.add_parser("browse", help="Browse indexed cloud folder hierarchy")
    p_browse.add_argument("remote", choices=["onedrive", "gdrive"], help="Remote to browse")
    p_browse.add_argument("path", nargs="?", default="", help="Folder path (optional, default root)")

    # mcp
    subparsers.add_parser("mcp", help="Run Model Context Protocol (MCP) JSON-RPC server")

    args = parser.parse_args()

    if args.command == "mcp":
        from mcp_server import run_stdio_server
        run_stdio_server()
        return

    ensure_backend_running()

    if args.command == "status":
        req = urllib.request.urlopen(f"http://{HOST}:{PORT}/api/stats")
        data = json.loads(req.read().decode("utf-8"))
        print(f"\nCloud Search Lite Index:")
        print(f"Total Files: {data.get('total_files', 0):,}\n")
        for r in data.get("remotes", []):
            synced = r.get("last_synced_at") or "Never"
            print(f" • {r['name']:<14} {r.get('item_count', 0):>8,} files  (Last Synced: {synced})")
        print()

    elif args.command == "search":
        params = urllib.parse.urlencode({"q": args.query, "limit": args.limit, "remote": args.remote or ""})
        req = urllib.request.urlopen(f"http://{HOST}:{PORT}/api/search?{params}")
        data = json.loads(req.read().decode("utf-8"))
        results = data.get("results", [])
        total = data.get("total", 0)
        total_str = f"{total:,}" if isinstance(total, int) else str(total)
        ms = data.get("elapsed_ms", 0)

        print(f"\nFound {total_str} results in {ms} ms for '{args.query}':\n")
        for r in results:
            print(f"[{r['remote_name']}] {r['filename']} ({r['size_formatted']})")
            print(f"  Path: {r['local_path']}\n")

    elif args.command == "browse":
        params = urllib.parse.urlencode({"remote": args.remote, "path": args.path})
        req = urllib.request.urlopen(f"http://{HOST}:{PORT}/api/browse?{params}")
        data = json.loads(req.read().decode("utf-8"))
        items = data.get("items", [])
        crumbs = " / ".join([c["name"] for c in data.get("breadcrumbs", [])])
        print(f"\n📁 {crumbs} ({data.get('folder_count', 0)} folders, {data.get('file_count', 0)} files, {data.get('elapsed_ms', 0)} ms)\n")
        for item in items:
            prefix = "📁 [DIR] " if item["is_dir"] else "📄 [FILE]"
            size_str = f"({item['size_formatted']})" if not item["is_dir"] else ""
            print(f"  {prefix} {item['filename']:<40} {size_str}")
        print()

    elif args.command == "sync":
        body = json.dumps({"remote_id": args.remote}).encode("utf-8")
        req = urllib.request.Request(
            f"http://{HOST}:{PORT}/api/sync",
            data=body,
            headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(req)
        print("Sync started. Tracking progress...")
        while True:
            time.sleep(1.0)
            st_req = urllib.request.urlopen(f"http://{HOST}:{PORT}/api/sync/status")
            status = json.loads(st_req.read().decode("utf-8"))
            if not status.get("is_syncing"):
                print("\nSync completed successfully!")
                break
            remote_name = status.get("current_remote_name") or "cloud drives"
            count = status.get("progress_count", 0)
            print(f"\rSyncing {remote_name}... {count:,} files indexed", end="", flush=True)

def clean_stale_locks(profile_dir: Path):
    """Clean leftover Chromium singleton locks."""
    for lock_name in ["SingletonLock", "SingletonSocket", "SingletonCookie"]:
        f = profile_dir / lock_name
        try:
            if f.is_symlink() or f.exists():
                f.unlink(missing_ok=True)
        except Exception:
            pass

def main():
    if len(sys.argv) > 1:
        handle_cli()
        return

    if check_already_running():
        sys.exit(0)

    ensure_backend_running()

    screen_w, screen_h = get_screen_size()
    win_w, win_h = 1040, 740
    left = max(0, (screen_w - win_w) // 2)
    top = max(0, (screen_h - win_h) // 2 - 30)

    browser_bin = find_browser_bin()
    USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
    clean_stale_locks(USER_DATA_DIR)

    browser_args = [
        browser_bin,
        f"--app=http://{HOST}:{PORT}",
        f"--class={WM_CLASS}",
        f"--name={WM_CLASS}",
        f"--user-data-dir={USER_DATA_DIR}",
        f"--window-size={win_w},{win_h}",
        f"--window-position={left},{top}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-component-update",
        "--password-store=basic",
    ]

    print("Launching Cloud Search Lite desktop window...")
    try:
        subprocess.Popen(
            browser_args,
            env={**os.environ, "DISPLAY": os.environ.get("DISPLAY", ":0")},
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
    except Exception as e:
        print(f"Error launching browser: {e}")

if __name__ == "__main__":
    main()
