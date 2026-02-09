# ClipFlow 📋

一款極簡優雅的 macOS 剪貼簿管理器，常駐選單列。

[English](./README.md) | [简体中文](./README.zh-CN.md) | [日本語](./README.ja.md)

![ClipFlow](https://img.shields.io/badge/平台-macOS-blue) ![Python](https://img.shields.io/badge/python-3.9+-green) ![License](https://img.shields.io/badge/授權-MIT-gray)

## 特色

- 🖥️ **選單列常駐** — 安靜地待在選單列，隨時可用
- 📝 **自動擷取** — 自動儲存你複製的所有內容
- 🔍 **快速存取** — 點擊查看最近紀錄，再點即可複製
- 🌐 **網頁歷史** — 精美深色主題的網頁介面，查看完整歷史
- 🌙 **極簡設計** — 簡潔冷淡風，與 macOS 風格一致
- ⚡ **輕量高效** — CPU 佔用 < 0.1%，不影響效能

## 安裝

### 方式一：下載安裝包（推薦）

1. 從 [Releases](https://github.com/qiaoshouqing/ClipFlow/releases) 下載最新 `.app`
2. 移動到 `/Applications`
3. 開啟即可使用

### 方式二：從原始碼執行

```bash
# 複製儲存庫
git clone https://github.com/qiaoshouqing/ClipFlow.git
cd ClipFlow

# 建立虛擬環境
python3 -m venv venv
source venv/bin/activate

# 安裝相依套件
pip install -r requirements.txt

# 執行
python clipboard_manager.py
```

## 使用方法

- **點擊選單列圖示** — 查看最近 8 筆紀錄
- **點擊任意條目** — 複製回剪貼簿
- **📖 查看全部歷史** — 開啟網頁介面 `http://127.0.0.1:17890`
- **🗑️ 清空歷史** — 刪除所有非置頂紀錄
- **⏸️ 暫停監控** — 暫時停止擷取

## 資料儲存

所有剪貼簿歷史儲存在本機：
```
~/.clipflow/history.db
```

資料永遠不會傳送到任何伺服器。你的剪貼簿隱私安全。

## 系統需求

- macOS 10.15+
- Python 3.9+（從原始碼執行時需要）

## 授權條款

MIT 授權條款 - 可自由使用、修改和散佈。

---

Made with 🦞 by [WilsonClaw](https://github.com/qiaoshouqing)
