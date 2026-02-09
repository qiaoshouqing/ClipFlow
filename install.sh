#!/bin/bash
# ClipFlow Installer for macOS

set -e

INSTALL_DIR="$HOME/.clipflow/app"
LAUNCH_AGENT="$HOME/Library/LaunchAgents/com.wilsonclaw.clipflow.plist"

echo "📋 Installing ClipFlow..."

# Create install directory
mkdir -p "$INSTALL_DIR"

# Copy files
cp clipboard_manager.py "$INSTALL_DIR/"
cp icon.png "$INSTALL_DIR/"
cp requirements.txt "$INSTALL_DIR/"

# Create virtual environment and install dependencies
echo "📦 Setting up Python environment..."
python3 -m venv "$INSTALL_DIR/venv"
source "$INSTALL_DIR/venv/bin/activate"
pip install -q -r "$INSTALL_DIR/requirements.txt"

# Create launch script
cat > "$INSTALL_DIR/run.sh" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
exec python clipboard_manager.py
EOF
chmod +x "$INSTALL_DIR/run.sh"

# Create LaunchAgent for auto-start
cat > "$LAUNCH_AGENT" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.wilsonclaw.clipflow</string>
    <key>ProgramArguments</key>
    <array>
        <string>$INSTALL_DIR/run.sh</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
EOF

# Load the agent
launchctl load "$LAUNCH_AGENT" 2>/dev/null || true

# Start ClipFlow
"$INSTALL_DIR/run.sh" &

echo ""
echo "✅ ClipFlow installed successfully!"
echo ""
echo "📍 Install location: $INSTALL_DIR"
echo "🚀 ClipFlow will start automatically on login"
echo "📋 Look for the clipboard icon in your menu bar"
echo ""
echo "To uninstall, run: ~/.clipflow/app/uninstall.sh"
