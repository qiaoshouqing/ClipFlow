# ClipFlow 📋

A minimal, elegant clipboard manager for macOS that lives in your menu bar.

[中文](./README.zh-CN.md) | [繁體中文](./README.zh-TW.md) | [日本語](./README.ja.md)

![ClipFlow](https://img.shields.io/badge/platform-macOS-blue) ![Python](https://img.shields.io/badge/python-3.9+-green) ![License](https://img.shields.io/badge/license-MIT-gray)

## Features

- 🖥️ **Menu Bar Native** — Lives quietly in your menu bar, always accessible
- 📝 **Auto Capture** — Automatically saves everything you copy
- 🔍 **Quick Access** — Click to view recent clips, click again to copy
- 🌐 **Web History** — Beautiful dark-themed web interface for full history
- 🌙 **Minimal Design** — Clean, cold aesthetic that matches macOS
- ⚡ **Lightweight** — < 0.1% CPU usage, no performance impact

## Installation

### Option 1: Download Release (Recommended)

1. Download the latest `.app` from [Releases](https://github.com/qiaoshouqing/ClipFlow/releases)
2. Move to `/Applications`
3. Open and enjoy

### Option 2: Run from Source

```bash
# Clone the repository
git clone https://github.com/qiaoshouqing/ClipFlow.git
cd ClipFlow

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run
python clipboard_manager.py
```

## Usage

- **Click menu bar icon** — View recent 8 clips
- **Click any clip** — Copy it back to clipboard
- **📖 View All History** — Open web interface at `http://127.0.0.1:17890`
- **🗑️ Clear History** — Remove all non-pinned clips
- **⏸️ Pause Monitoring** — Temporarily stop capturing

## Data Storage

All clipboard history is stored locally at:
```
~/.clipflow/history.db
```

No data is ever sent to any server. Your clipboard stays private.

## Requirements

- macOS 10.15+
- Python 3.9+ (for running from source)

## License

MIT License - feel free to use, modify, and distribute.

---

Made with 🦞 by [WilsonClaw](https://github.com/qiaoshouqing)
