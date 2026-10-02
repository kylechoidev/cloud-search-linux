#!/usr/bin/env bash
set -e

# Cloud Search Linux Installer
# Author: kylechoidev
# License: MIT

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"
ICON_PATH="$APP_DIR/assets/icon.png"

echo "========================================"
echo "    Installing Cloud Search Linux"
echo "========================================"
echo ""

# 1. Dependency checks
echo "[1/4] Checking prerequisites..."
if ! command -v python3 &>/dev/null; then
    echo "Error: python3 is required but not installed." >&2
    exit 1
fi

if ! command -v rclone &>/dev/null; then
    echo "Warning: 'rclone' was not found in PATH."
    echo "Cloud indexing requires rclone to fetch file metadata."
    echo "Install via: curl https://rclone.org/install.sh | sudo bash"
    echo ""
fi

# Check for browser runtime
BROWSER_FOUND=0
for b in brave-browser chromium chromium-browser google-chrome google-chrome-stable; do
    if command -v "$b" &>/dev/null; then
        BROWSER_FOUND=1
        echo "Found browser runtime: $b"
        break
    fi
done

if [ "$BROWSER_FOUND" -eq 0 ]; then
    echo "Notice: No Chromium-based browser found. Falling back to default system browser."
fi

# 2. Setup directories
echo "[2/4] Setting up directories..."
mkdir -p "$BIN_DIR"
mkdir -p "$DESKTOP_DIR"
chmod +x "$APP_DIR/src/launch.py"

# 3. Create CLI wrapper in ~/.local/bin
echo "[3/4] Installing CLI launcher to $BIN_DIR/cloud-search-lite..."
cat << 'EOF' > "$BIN_DIR/cloud-search-lite"
#!/usr/bin/env bash
INSTALL_DIR="REPLACE_APP_DIR"
export PATH="$HOME/.local/bin:$PATH"
exec "$INSTALL_DIR/src/launch.py" "$@"
EOF

# Substitute actual installation directory
sed -i "s|REPLACE_APP_DIR|$APP_DIR|g" "$BIN_DIR/cloud-search-lite"
chmod +x "$BIN_DIR/cloud-search-lite"

# 4. Create Desktop shortcut
echo "[4/4] Creating application menu shortcut..."
cat << EOF > "$DESKTOP_DIR/cloud-search-lite.desktop"
[Desktop Entry]
Version=1.0
Type=Application
Name=Cloud Search Lite
GenericName=Cloud Drive Search
Comment=Sub-millisecond local desktop search for cloud drives
Exec=$BIN_DIR/cloud-search-lite
Icon=$ICON_PATH
Terminal=false
Categories=Utility;Filesystem;DesktopUtility;
StartupWMClass=CloudSearchLite
Keywords=Search;Cloud;Drive;OneDrive;GoogleDrive;FTS5;
EOF

chmod +x "$DESKTOP_DIR/cloud-search-lite.desktop"

# Refresh desktop database if available
if command -v update-desktop-database &>/dev/null; then
    update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
fi

echo ""
echo "========================================"
echo "    Installation Complete!"
echo "========================================"
echo ""
echo "You can now run Cloud Search Linux:"
echo "  • From Terminal:       cloud-search-lite"
echo "  • From App Menu:       Search for 'Cloud Search Lite'"
echo "  • Search CLI:          cloud-search-lite search \"keyword\""
echo "  • Folder Search:       cloud-search-lite search \"folder:name\""
echo ""
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo "Note: Make sure '$HOME/.local/bin' is in your PATH in ~/.bashrc or ~/.zshrc."
fi
