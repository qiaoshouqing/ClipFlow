# ClipFlow 📋

一款极简优雅的 macOS 剪贴板管理器，常驻菜单栏。

[English](./README.md) | [繁體中文](./README.zh-TW.md) | [日本語](./README.ja.md)

![ClipFlow](https://img.shields.io/badge/平台-macOS-blue) ![Python](https://img.shields.io/badge/python-3.9+-green) ![License](https://img.shields.io/badge/许可证-MIT-gray)

## 特性

- 🖥️ **菜单栏常驻** — 安静地待在菜单栏，随时可用
- 📝 **自动捕获** — 自动保存你复制的所有内容
- 🔍 **快速访问** — 点击查看最近记录，再点即可复制
- 🌐 **网页历史** — 精美深色主题的网页界面，查看完整历史
- 🌙 **极简设计** — 简洁冷淡风，与 macOS 风格一致
- ⚡ **轻量高效** — CPU 占用 < 0.1%，不影响性能

## 安装

### 方式一：下载安装包（推荐）

1. 从 [Releases](https://github.com/qiaoshouqing/ClipFlow/releases) 下载最新 `.app`
2. 移动到 `/Applications`
3. 打开即可使用

### 方式二：从源码运行

```bash
# 克隆仓库
git clone https://github.com/qiaoshouqing/ClipFlow.git
cd ClipFlow

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 运行
python clipboard_manager.py
```

## 使用方法

- **点击菜单栏图标** — 查看最近 8 条记录
- **点击任意条目** — 复制回剪贴板
- **📖 查看全部历史** — 打开网页界面 `http://127.0.0.1:17890`
- **🗑️ 清空历史** — 删除所有非置顶记录
- **⏸️ 暂停监控** — 临时停止捕获

## 数据存储

所有剪贴板历史存储在本地：
```
~/.clipflow/history.db
```

数据永远不会发送到任何服务器。你的剪贴板隐私安全。

## 系统要求

- macOS 10.15+
- Python 3.9+（从源码运行时需要）

## 许可证

MIT 许可证 - 可自由使用、修改和分发。

---

Made with 🦞 by [WilsonClaw](https://github.com/qiaoshouqing)
