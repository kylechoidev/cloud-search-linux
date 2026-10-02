# Cloud Search Linux (v2.0)

<p align="center">
  <img src="assets/icon.svg" alt="Cloud Search Linux Icon" width="120" height="120">
</p>

<p align="center">
  <b>Sub-millisecond local desktop search & pseudo file manager for OneDrive, Google Drive, and cloud storage on Linux.</b>
  <br>
  <i>Zero FUSE crawling overhead. Pure Python standard library & vanilla web technology. Zero bloat.</i>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Version-2.0-blueviolet.svg" alt="v2.0">
  <img src="https://img.shields.io/badge/Language-Python%203-blue.svg" alt="Python 3">
  <img src="https://img.shields.io/badge/Search-SQLite%20FTS5-green.svg" alt="SQLite FTS5">
  <img src="https://img.shields.io/badge/Backend-rclone-orange.svg" alt="rclone">
  <img src="https://img.shields.io/badge/License-MIT-purple.svg" alt="MIT License">
</p>

---

## ⚡ The Problem Cloud Search Linux Solves

If you mount cloud storage on Linux using FUSE (`rclone mount`, `google-drive-ocamlfuse`, etc.), browsing and searching large hierarchies (e.g. 5 TB Google Drive, 1.1 TB OneDrive) in native file managers (**Nemo**, **Nautilus**, **Dolphin**, **Thunar**) or desktop search tools (**FSearch**, **Catfish**, **Recoll**, **Baloo**) quickly causes severe issues:
* **Blocking POSIX Directory Reads**: Opening a folder in Nemo makes synchronous HTTP calls over FUSE, freezing the desktop file manager while waiting for cloud API responses.
* **Recursive POSIX Crawling**: Standard search tools execute recursive `opendir`/`readdir`/`stat` calls across virtual mounts.
* **API Rate Limiting & Quotas**: Millions of stat calls trigger cloud provider HTTP 429 rate limits and API bans.
* **Kernel & System Freezes**: Deep directory trees cause processes to get trapped in uninterruptible sleep (`request_wait_answer` D-state), locking up your file manager and hanging the system during boot.

**Cloud Search Linux decouples search and browsing from FUSE crawling entirely:**
1. **Metadata API Streaming**: Fetches cloud file and folder hierarchies directly via cloud metadata APIs (`rclone lsf -R --fast-list`), indexing 300,000+ items in minutes without mounting.
2. **Local SQLite FTS5 Engine**: Every search query executes locally in **~1 ms to 35 ms** with BM25 relevance ranking and zero network traffic.
3. **Cloud Explorer (Pseudo File Manager Mode)**: Browse your entire cloud folder hierarchy like a native file manager with **sub-millisecond queries (~0.2 ms to 1.5 ms)** powered by indexed parent paths, complete with clickable breadcrumbs, drive tabs, list & grid views, and quick filtering.
4. **Desktop Application Bridge**: Open files with `xdg-open` or reveal items directly in your desktop file manager (**Nemo**, **Nautilus**, **Dolphin**, **Thunar**) via D-Bus / `gio`.

---

## ✨ Features

### 🔍 Instant Search Mode
* 🚀 **Sub-Millisecond Search**: SQLite FTS5 search-as-you-type with prefix matching and BM25 relevance ranking.
* 📁 **First-Class Folder Search**:
  * Dedicated `📁 Folders` filter chip.
  * Direct search syntax: `folder:<name>` or `dir:<name>`.
  * Instant "Explore" button on folder results to jump directly into Cloud Explorer at that path.
* 🏷️ **Multi-Cloud Aggregation**: Search across **OneDrive**, **Google Drive**, and other cloud providers in a unified view.

### 📁 Cloud Explorer Mode (v2.0)
* ⚡ **Instant Pseudo File Manager**: Browse your cloud files and directories folder-by-folder at **~0.2 ms per folder** from local SQLite cache—no slow FUSE network lag.
* 🧭 **Clickable Breadcrumb Bar**: Jump to any ancestor directory in the hierarchy with one click.
* 🔀 **Drive Tabs**: Switch instantly between OneDrive, Google Drive, and other cloud remotes.
* 📋 **List & Grid Views**: Toggle between compact detailed list view and spacious grid cards.
* 🔍 **Folder Filter**: Instant client-side filtering within the current folder.
* 🖱️ **Right-Click Context Menu**:
  * Enter Folder / Open File
  * Reveal in Nemo (`org.freedesktop.FileManager1.ShowItems`)
  * Copy Local Path (`~/OneDrive/...`)
  * Copy Cloud Path (`onedrive:...`)
* 💻 **CLI Folder Browser**: Browse directories directly in your terminal via `cloud-search-lite browse <remote> [path]`.

### 🧩 Zero Bloat & Dependencies
* Built strictly using the **Python 3 standard library** and **vanilla HTML/CSS/JavaScript**.
* No npm, no Electron, no pip packages required. Runs in a lightweight standalone browser window (Brave, Chromium, Chrome).

---

## 🛠️ Prerequisites

* **Linux**: Any modern Linux distribution (Linux Mint, Ubuntu, Debian, Arch, Fedora).
* **Python**: Python 3.8 or newer (uses only standard library modules).
* **rclone**: Configured with one or more cloud remotes (`rclone config`).
* **Browser Runtime**: Brave, Chromium, or Google Chrome installed for standalone window mode.

---

## 🚀 Quick Start & Installation

```bash
# 1. Clone the repository
git clone https://github.com/kylechoidev/cloud-search-linux.git
cd cloud-search-linux

# 2. Run the installer
./install.sh
```

The installer will:
1. Create the `cloud-search-lite` command in `~/.local/bin/`.
2. Install the desktop entry in `~/.local/share/applications/` so you can launch it from your application menu, panel, or application shortcuts.

---

## ⚙️ Configuration

By default, Cloud Search Linux automatically discovers your configured rclone remotes using `rclone listremotes`.

To customize remote mappings, display names, colors, or local mount locations, edit `~/.config/cloud-search-lite/config.json`:

```json
{
  "remotes": {
    "onedrive": {
      "name": "OneDrive",
      "rclone_remote": "onedrive:",
      "mount_path": "~/OneDrive",
      "color": "#0078d4"
    },
    "gdrive": {
      "name": "Google Drive",
      "rclone_remote": "gdrive:",
      "mount_path": "~/GoogleDrive",
      "color": "#34a853"
    }
  }
}
```

---

## 🖥️ Command-Line Usage

In addition to the desktop interface, you can browse, search, and manage indexes directly from your terminal:

```bash
# Check index overview and last sync timestamps:
cloud-search-lite status

# Browse cloud folders in terminal (Instant SQLite lookups):
cloud-search-lite browse onedrive
cloud-search-lite browse onedrive "Documents/Projects"
cloud-search-lite browse gdrive "Backups"

# Search across all drives:
cloud-search-lite search "report" --limit 10

# Search specifically for folders:
cloud-search-lite search "folder:projects" --limit 5

# Filter search by a specific cloud remote:
cloud-search-lite search "contract" --remote gdrive

# Trigger a background metadata re-sync:
cloud-search-lite sync
cloud-search-lite sync --remote onedrive

# Launch Model Context Protocol (MCP) JSON-RPC 2.0 server (for AI agents/Antigravity):
cloud-search-lite mcp
```

---

## ⌨️ Keyboard Shortcuts

### General
| Key | Action |
| :--- | :--- |
| <kbd>Ctrl</kbd> + <kbd>E</kbd> | Toggle between **Search Mode** and **Cloud Explorer Mode** |

### Search Mode
| Key | Action |
| :--- | :--- |
| <kbd>/</kbd> | Focus the search input field |
| <kbd>↑</kbd> / <kbd>↓</kbd> | Navigate through search results |
| <kbd>Enter</kbd> | Open the selected file or folder |
| <kbd>Ctrl</kbd> + <kbd>Enter</kbd> | Reveal the selected item in Nemo file manager |
| <kbd>Esc</kbd> | Clear the current query or unfocus |

### Cloud Explorer Mode
| Key | Action |
| :--- | :--- |
| <kbd>/</kbd> | Switch to Search Mode |
| <kbd>Backspace</kbd> or <kbd>Alt</kbd> + <kbd>↑</kbd> | Navigate up one folder level |
| <kbd>↑</kbd> / <kbd>↓</kbd> | Select previous / next item in folder |
| <kbd>Enter</kbd> | Enter selected folder or open selected file |
| <kbd>Ctrl</kbd> + <kbd>Enter</kbd> | Reveal selected item in Nemo file manager |
| <kbd>Esc</kbd> | Clear folder filter |

---

## 🗑️ Uninstallation

To remove the desktop launcher and executable wrapper:

```bash
./uninstall.sh
```

---

## 📄 License

Distributed under the **MIT License**. See [LICENSE](LICENSE) for details.

Developed with ❤️ by [kylechoidev](https://github.com/kylechoidev).
