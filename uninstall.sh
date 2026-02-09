#!/bin/bash
# ClipFlow Uninstaller

echo "🗑️  Uninstalling ClipFlow..."

# Stop the process
pkill -f "clipflow.*clipboard_manager" 2>/dev/null || true

# Unload and remove LaunchAgent
launchctl unload "$HOME/Library/LaunchAgents/com.wilsonclaw.clipflow.plist" 2>/dev/null || true
rm -f "$HOME/Library/LaunchAgents/com.wilsonclaw.clipflow.plist"

# Remove app files
rm -rf "$HOME/.clipflow/app"

echo ""
echo "✅ ClipFlow uninstalled."
echo ""
echo "📝 Note: Your clipboard history is preserved at ~/.clipflow/history.db"
echo "   To remove it too, run: rm -rf ~/.clipflow"
