#!/usr/bin/env python3
"""
ClipFlow - 极简剪贴板管理器
macOS 菜单栏应用，自动保存剪贴板历史
"""

import rumps
import sqlite3
import threading
import time
import hashlib
import subprocess
import webbrowser
import sys
import os
from datetime import datetime
from pathlib import Path
import re
import json
import http.server
import socketserver

# 配置
VERSION = "1.1.2"
DB_PATH = Path.home() / ".clipflow" / "history.db"
MAX_HISTORY = 100
CHECK_INTERVAL = 1.0
MAX_DISPLAY_LENGTH = 40
WEB_PORT = 17890


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS clips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            content_hash TEXT UNIQUE NOT NULL,
            content_type TEXT DEFAULT 'text',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            pinned INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()


def get_clipboard():
    try:
        result = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=1)
        return result.stdout if result.returncode == 0 else None
    except:
        return None


def set_clipboard(text):
    try:
        process = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
        process.communicate(text.encode("utf-8"))
        return True
    except:
        return False


def truncate_text(text, max_len=MAX_DISPLAY_LENGTH):
    text = text.replace("\n", " ↵ ").replace("\t", " ").strip()
    text = re.sub(r"\s+", " ", text)
    if len(text) > max_len:
        return text[:max_len] + "…"
    return text


def get_time_ago(timestamp_str):
    try:
        dt = datetime.fromisoformat(str(timestamp_str).replace("Z", "+00:00"))
        now = datetime.now()
        diff = now - dt
        if diff.days > 0:
            return f"{diff.days}天前"
        elif diff.seconds >= 3600:
            return f"{diff.seconds // 3600}小时前"
        elif diff.seconds >= 60:
            return f"{diff.seconds // 60}分钟前"
        else:
            return "刚刚"
    except:
        return ""


def get_app_path():
    """获取应用程序路径"""
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后
        return os.path.dirname(os.path.dirname(os.path.dirname(sys.executable)))
    else:
        # 开发模式
        return os.path.abspath(__file__)


def is_login_item():
    """检查是否已设置开机启动"""
    app_path = get_app_path()
    try:
        result = subprocess.run(
            ['osascript', '-e', f'''
                tell application "System Events"
                    get the name of every login item
                end tell
            '''],
            capture_output=True, text=True, timeout=5
        )
        return 'ClipFlow' in result.stdout
    except:
        return False


def add_login_item():
    """添加开机启动"""
    app_path = get_app_path()
    if app_path.endswith('.app'):
        try:
            subprocess.run(
                ['osascript', '-e', f'''
                    tell application "System Events"
                        make login item at end with properties {{path:"{app_path}", hidden:false}}
                    end tell
                '''],
                capture_output=True, timeout=5
            )
            return True
        except:
            return False
    return False


def remove_login_item():
    """移除开机启动"""
    try:
        subprocess.run(
            ['osascript', '-e', '''
                tell application "System Events"
                    delete login item "ClipFlow"
                end tell
            '''],
            capture_output=True, timeout=5
        )
        return True
    except:
        return False


class ClipFlowApp(rumps.App):
    def __init__(self):
        # 使用图标文件
        icon_path = Path(__file__).parent / "icon.png"
        super().__init__(name="ClipFlow", icon=str(icon_path) if icon_path.exists() else None, title=None, quit_button=None, template=True)
        
        init_db()
        self.last_hash = None
        self.monitoring = True
        self.need_update = False
        
        # 初始化菜单项
        self.header_item = rumps.MenuItem("ClipFlow", callback=None)
        self.clip_items = []
        self.separator1 = rumps.separator
        self.view_all = rumps.MenuItem("📖 查看全部历史", callback=self.open_web_history)
        self.clear_btn = rumps.MenuItem("🗑️ 清空历史", callback=self.clear_history)
        self.separator2 = rumps.separator
        self.toggle_btn = rumps.MenuItem("⏸️ 暂停监控", callback=self.toggle_monitoring)
        self.login_btn = rumps.MenuItem("🚀 开机启动", callback=self.toggle_login_item)
        self.separator3 = rumps.separator
        self.quit_btn = rumps.MenuItem("退出", callback=rumps.quit_application)
        
        # 构建初始菜单
        self.refresh_menu()
        
        # 默认开启开机启动
        if not is_login_item():
            add_login_item()
        
        # 启动 Web 服务器
        threading.Thread(target=self.start_web_server, daemon=True).start()
    
    def start_web_server(self):
        handler = ClipFlowWebHandler
        handler.db_path = str(DB_PATH)
        try:
            with socketserver.TCPServer(("127.0.0.1", WEB_PORT), handler) as httpd:
                httpd.serve_forever()
        except:
            pass
    
    @rumps.timer(CHECK_INTERVAL)
    def check_clipboard(self, _):
        """定时检查剪贴板"""
        if not self.monitoring:
            return
        
        try:
            content = get_clipboard()
            if content and content.strip():
                content_hash = hashlib.md5(content.encode()).hexdigest()
                if content_hash != self.last_hash:
                    self.last_hash = content_hash
                    self.save_clip(content, content_hash)
                    self.refresh_menu()
        except:
            pass
    
    def save_clip(self, content, content_hash):
        if not content.strip():
            return
        conn = sqlite3.connect(str(DB_PATH))
        try:
            conn.execute("""
                INSERT INTO clips (content, content_hash, created_at)
                VALUES (?, ?, datetime('now', 'localtime'))
                ON CONFLICT(content_hash) DO UPDATE SET created_at = datetime('now', 'localtime')
            """, (content, content_hash))
            conn.execute("""
                DELETE FROM clips WHERE id NOT IN (
                    SELECT id FROM clips ORDER BY created_at DESC LIMIT ?
                )
            """, (MAX_HISTORY,))
            conn.commit()
        finally:
            conn.close()
    
    def get_recent_clips(self, limit=8):
        conn = sqlite3.connect(str(DB_PATH))
        try:
            cursor = conn.execute("""
                SELECT id, content, created_at, pinned 
                FROM clips ORDER BY pinned DESC, created_at DESC LIMIT ?
            """, (limit,))
            return cursor.fetchall()
        finally:
            conn.close()
    
    def get_clip_count(self):
        conn = sqlite3.connect(str(DB_PATH))
        try:
            return conn.execute("SELECT COUNT(*) FROM clips").fetchone()[0]
        finally:
            conn.close()
    
    def refresh_menu(self):
        """刷新菜单"""
        self.menu.clear()
        
        count = self.get_clip_count()
        self.header_item = rumps.MenuItem(f"ClipFlow v{VERSION} · {count} 条记录")
        self.header_item.set_callback(None)
        self.menu.add(self.header_item)
        self.menu.add(rumps.separator)
        
        clips = self.get_recent_clips(8)
        if clips:
            for clip_id, content, created_at, pinned in clips:
                prefix = "📌 " if pinned else ""
                display = prefix + truncate_text(content)
                item = rumps.MenuItem(display)
                # 用闭包捕获 content
                item.set_callback(self.make_copy_callback(content))
                self.menu.add(item)
            self.menu.add(rumps.separator)
        
        self.menu.add(self.view_all)
        self.menu.add(self.clear_btn)
        self.menu.add(rumps.separator)
        
        toggle_title = "▶️ 继续监控" if not self.monitoring else "⏸️ 暂停监控"
        self.toggle_btn.title = toggle_title
        self.menu.add(self.toggle_btn)
        
        # 开机启动选项
        login_enabled = is_login_item()
        login_title = "✅ 开机启动" if login_enabled else "🚀 开机启动"
        self.login_btn.title = login_title
        self.menu.add(self.login_btn)
        
        self.menu.add(rumps.separator)
        self.menu.add(self.quit_btn)
    
    def make_copy_callback(self, content):
        """创建复制回调函数"""
        def callback(sender):
            if set_clipboard(content):
                self.last_hash = hashlib.md5(content.encode()).hexdigest()
                rumps.notification("ClipFlow", "已复制", truncate_text(content, 50), sound=False)
        return callback
    
    def open_web_history(self, sender):
        webbrowser.open(f"http://127.0.0.1:{WEB_PORT}")
    
    def toggle_monitoring(self, sender):
        self.monitoring = not self.monitoring
        self.refresh_menu()
        status = "已开启" if self.monitoring else "已暂停"
        rumps.notification("ClipFlow", "", f"剪贴板监控{status}", sound=False)
    
    def clear_history(self, sender):
        conn = sqlite3.connect(str(DB_PATH))
        conn.execute("DELETE FROM clips WHERE pinned = 0")
        conn.commit()
        conn.close()
        self.refresh_menu()
        rumps.notification("ClipFlow", "", "历史已清空", sound=False)
    
    def toggle_login_item(self, sender):
        """切换开机启动"""
        if is_login_item():
            remove_login_item()
            rumps.notification("ClipFlow", "", "已关闭开机启动", sound=False)
        else:
            if add_login_item():
                rumps.notification("ClipFlow", "", "已开启开机启动", sound=False)
            else:
                rumps.notification("ClipFlow", "提示", "请将 ClipFlow.app 放入 Applications 文件夹后重试", sound=False)
        self.refresh_menu()


class ClipFlowWebHandler(http.server.SimpleHTTPRequestHandler):
    db_path = None
    
    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_html_page()
        elif self.path == "/api/clips":
            self.send_clips_json()
        else:
            self.send_error(404)
    
    def send_html_page(self):
        html = r'''<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ClipFlow</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif;
            background: #0d0d0d;
            color: #e0e0e0;
            min-height: 100vh;
            padding: 40px;
        }
        .container { max-width: 700px; margin: 0 auto; }
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 1px solid #222;
        }
        h1 { font-size: 24px; font-weight: 600; color: #fff; }
        .stats { font-size: 14px; color: #666; }
        .clip-list { display: flex; flex-direction: column; gap: 12px; }
        .clip-item {
            background: #161616;
            border: 1px solid #222;
            border-radius: 10px;
            padding: 16px;
            transition: all 0.2s ease;
            cursor: pointer;
        }
        .clip-item:hover { background: #1a1a1a; border-color: #333; }
        .clip-item:active { background: #222; }
        .clip-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        .clip-time {
            font-size: 12px;
            color: #555;
            font-family: "SF Mono", monospace;
        }
        .clip-content {
            font-family: "SF Mono", Monaco, monospace;
            font-size: 13px;
            line-height: 1.6;
            color: #ccc;
            white-space: pre-wrap;
            word-break: break-all;
            max-height: 200px;
            overflow-y: auto;
        }
        .empty { text-align: center; padding: 60px; color: #444; }
        .toast {
            position: fixed;
            bottom: 30px;
            left: 50%;
            transform: translateX(-50%);
            background: #0066cc;
            color: #fff;
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 14px;
            opacity: 0;
            transition: opacity 0.3s ease;
            pointer-events: none;
        }
        .toast.show { opacity: 1; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📋 ClipFlow <span style="font-size:14px;color:#666">v1.1.2</span></h1>
            <span class="stats" id="stats">加载中...</span>
        </header>
        <div class="clip-list" id="clipList"></div>
    </div>
    <div class="toast" id="toast">已复制到剪贴板</div>
    <script>
        async function loadClips() {
            const res = await fetch('/api/clips');
            const data = await res.json();
            document.getElementById('stats').textContent = data.length + ' 条记录';
            const list = document.getElementById('clipList');
            if (data.length === 0) {
                list.innerHTML = '<div class="empty">暂无剪贴板记录</div>';
                return;
            }
            list.innerHTML = data.map(clip => {
                const escaped = clip.content.substring(0, 500)
                    .replace(/&/g, '&amp;')
                    .replace(/</g, '&lt;')
                    .replace(/>/g, '&gt;');
                return '<div class="clip-item" data-content="' + btoa(unescape(encodeURIComponent(clip.content))) + '">' +
                    '<div class="clip-header"><span class="clip-time">' + (clip.time_ago || clip.created_at) + '</span></div>' +
                    '<div class="clip-content">' + escaped + (clip.content.length > 500 ? '...' : '') + '</div></div>';
            }).join('');
            document.querySelectorAll('.clip-item').forEach(el => {
                el.onclick = () => {
                    const content = decodeURIComponent(escape(atob(el.dataset.content)));
                    navigator.clipboard.writeText(content).then(() => showToast('已复制到剪贴板'));
                };
            });
        }
        function showToast(msg) {
            const toast = document.getElementById('toast');
            toast.textContent = msg;
            toast.classList.add('show');
            setTimeout(() => toast.classList.remove('show'), 2000);
        }
        loadClips();
        setInterval(loadClips, 3000);
    </script>
</body>
</html>'''
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode())
    
    def send_clips_json(self):
        conn = sqlite3.connect(self.db_path)
        clips = conn.execute("""
            SELECT id, content, created_at, pinned 
            FROM clips ORDER BY pinned DESC, created_at DESC LIMIT 50
        """).fetchall()
        conn.close()
        data = [{"id": c[0], "content": c[1], "created_at": c[2], "pinned": bool(c[3]), "time_ago": get_time_ago(c[2])} for c in clips]
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())
    
    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    app = ClipFlowApp()
    app.run()
