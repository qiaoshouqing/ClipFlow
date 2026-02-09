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

# PyObjC for native UI
from AppKit import (
    NSApplication, NSWindow, NSWindowStyleMaskTitled, NSWindowStyleMaskClosable,
    NSWindowStyleMaskResizable, NSBackingStoreBuffered, NSScrollView, NSTableView,
    NSTableColumn, NSTextField, NSButton, NSBezelStyleRounded, NSView,
    NSMakeRect, NSColor, NSFont, NSLineBreakByTruncatingTail,
    NSTextFieldCell, NSApp, NSFloatingWindowLevel, NSVisualEffectView,
    NSVisualEffectBlendingModeBehindWindow, NSVisualEffectMaterialHUDWindow
)
from Foundation import NSObject
import objc

# 配置
VERSION = "1.3.0"
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


def toggle_pin(clip_id):
    """切换收藏状态"""
    conn = sqlite3.connect(str(DB_PATH))
    try:
        current = conn.execute("SELECT pinned FROM clips WHERE id = ?", (clip_id,)).fetchone()
        if current:
            new_state = 0 if current[0] else 1
            conn.execute("UPDATE clips SET pinned = ? WHERE id = ?", (new_state, clip_id))
            conn.commit()
            return new_state
    finally:
        conn.close()
    return None


def delete_clip(clip_id):
    """删除剪贴板记录"""
    conn = sqlite3.connect(str(DB_PATH))
    try:
        conn.execute("DELETE FROM clips WHERE id = ?", (clip_id,))
        conn.commit()
    finally:
        conn.close()


class ClipFlowTableDelegate(NSObject):
    """TableView 数据源和代理"""
    
    def init(self):
        self = objc.super(ClipFlowTableDelegate, self).init()
        if self is None:
            return None
        self.clips = []
        self.on_copy = None
        self.on_refresh = None
        return self
    
    def numberOfRowsInTableView_(self, tableView):
        return len(self.clips)
    
    def tableView_viewForTableColumn_row_(self, tableView, column, row):
        if row >= len(self.clips):
            return None
        
        clip = self.clips[row]
        clip_id, content, created_at, pinned = clip
        
        identifier = column.identifier()
        
        if identifier == "time":
            cell = tableView.makeViewWithIdentifier_owner_(identifier, self)
            if cell is None:
                cell = NSTextField.alloc().initWithFrame_(NSMakeRect(0, 0, 70, 24))
                cell.setIdentifier_(identifier)
                cell.setBordered_(False)
                cell.setEditable_(False)
                cell.setBackgroundColor_(NSColor.clearColor())
            cell.setStringValue_(get_time_ago(created_at))
            cell.setTextColor_(NSColor.secondaryLabelColor())
            cell.setFont_(NSFont.monospacedSystemFontOfSize_weight_(11, 0.0))
            return cell
        
        elif identifier == "content":
            cell = tableView.makeViewWithIdentifier_owner_(identifier, self)
            if cell is None:
                cell = NSTextField.alloc().initWithFrame_(NSMakeRect(0, 0, 280, 24))
                cell.setIdentifier_(identifier)
                cell.setBordered_(False)
                cell.setEditable_(False)
                cell.setBackgroundColor_(NSColor.clearColor())
                cell.setLineBreakMode_(NSLineBreakByTruncatingTail)
            preview = content.replace('\n', ' ↵ ')[:80]
            if pinned:
                preview = "⭐ " + preview
            cell.setStringValue_(preview)
            cell.setTextColor_(NSColor.labelColor())
            cell.setFont_(NSFont.systemFontOfSize_(13))
            return cell
        
        elif identifier == "actions":
            cell = tableView.makeViewWithIdentifier_owner_(identifier, self)
            if cell is None:
                cell = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, 100, 28))
                cell.setIdentifier_(identifier)
                
                # 收藏按钮
                pinBtn = NSButton.alloc().initWithFrame_(NSMakeRect(0, 2, 40, 24))
                pinBtn.setBezelStyle_(NSBezelStyleRounded)
                pinBtn.setTag_(1)
                cell.addSubview_(pinBtn)
                
                # 删除按钮
                delBtn = NSButton.alloc().initWithFrame_(NSMakeRect(45, 2, 40, 24))
                delBtn.setBezelStyle_(NSBezelStyleRounded)
                delBtn.setTitle_("删除")
                delBtn.setTag_(2)
                cell.addSubview_(delBtn)
            
            # 更新按钮状态
            for subview in cell.subviews():
                if subview.tag() == 1:
                    subview.setTitle_("取消" if pinned else "收藏")
                    subview.setTarget_(self)
                    subview.setAction_(objc.selector(self.pinClicked_, signature=b'v@:@'))
                    subview.cell().setRepresentedObject_(clip_id)
                elif subview.tag() == 2:
                    subview.setTarget_(self)
                    subview.setAction_(objc.selector(self.deleteClicked_, signature=b'v@:@'))
                    subview.cell().setRepresentedObject_(clip_id)
            
            return cell
        
        return None
    
    def pinClicked_(self, sender):
        clip_id = sender.cell().representedObject()
        if clip_id:
            new_state = toggle_pin(clip_id)
            if self.on_refresh:
                self.on_refresh()
            msg = "已收藏" if new_state else "已取消收藏"
            rumps.notification("ClipFlow", "", msg, sound=False)
    
    def deleteClicked_(self, sender):
        clip_id = sender.cell().representedObject()
        if clip_id:
            delete_clip(clip_id)
            if self.on_refresh:
                self.on_refresh()
            rumps.notification("ClipFlow", "", "已删除", sound=False)
    
    def tableViewSelectionDidChange_(self, notification):
        tableView = notification.object()
        row = tableView.selectedRow()
        if row >= 0 and row < len(self.clips):
            clip = self.clips[row]
            content = clip[1]
            if set_clipboard(content):
                if self.on_copy:
                    self.on_copy(content)


class ClipFlowWindow:
    """原生 macOS 历史窗口"""
    
    _instance = None
    
    def __init__(self):
        self.window = None
        self.table = None
        self.delegate = None
    
    @classmethod
    def shared(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def show(self):
        if self.window is not None:
            self.window.makeKeyAndOrderFront_(None)
            self.refresh_data()
            NSApp.activateIgnoringOtherApps_(True)
            return
        
        # 创建窗口
        frame = NSMakeRect(0, 0, 580, 420)
        style = NSWindowStyleMaskTitled | NSWindowStyleMaskClosable | NSWindowStyleMaskResizable
        self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            frame, style, NSBackingStoreBuffered, False
        )
        self.window.setTitle_(f"ClipFlow v{VERSION}")
        self.window.center()
        self.window.setLevel_(NSFloatingWindowLevel)
        self.window.setMinSize_((500, 300))
        
        # 毛玻璃背景
        contentView = self.window.contentView()
        visualEffect = NSVisualEffectView.alloc().initWithFrame_(contentView.bounds())
        visualEffect.setAutoresizingMask_(18)  # NSViewWidthSizable | NSViewHeightSizable
        visualEffect.setBlendingMode_(NSVisualEffectBlendingModeBehindWindow)
        visualEffect.setMaterial_(NSVisualEffectMaterialHUDWindow)
        self.window.setContentView_(visualEffect)
        
        # 创建 TableView
        scrollFrame = NSMakeRect(10, 10, 560, 400)
        scrollView = NSScrollView.alloc().initWithFrame_(scrollFrame)
        scrollView.setAutoresizingMask_(18)
        scrollView.setHasVerticalScroller_(True)
        scrollView.setBorderType_(0)
        scrollView.setBackgroundColor_(NSColor.clearColor())
        
        self.table = NSTableView.alloc().initWithFrame_(scrollView.bounds())
        self.table.setBackgroundColor_(NSColor.clearColor())
        self.table.setRowHeight_(32)
        self.table.setSelectionHighlightStyle_(1)  # Regular
        
        # 时间列
        timeCol = NSTableColumn.alloc().initWithIdentifier_("time")
        timeCol.setWidth_(70)
        timeCol.headerCell().setStringValue_("时间")
        self.table.addTableColumn_(timeCol)
        
        # 内容列
        contentCol = NSTableColumn.alloc().initWithIdentifier_("content")
        contentCol.setWidth_(350)
        contentCol.headerCell().setStringValue_("内容")
        self.table.addTableColumn_(contentCol)
        
        # 操作列
        actionsCol = NSTableColumn.alloc().initWithIdentifier_("actions")
        actionsCol.setWidth_(100)
        actionsCol.headerCell().setStringValue_("操作")
        self.table.addTableColumn_(actionsCol)
        
        # 设置代理
        self.delegate = ClipFlowTableDelegate.alloc().init()
        self.delegate.on_copy = self.on_clip_copied
        self.delegate.on_refresh = self.refresh_data
        self.table.setDelegate_(self.delegate)
        self.table.setDataSource_(self.delegate)
        
        scrollView.setDocumentView_(self.table)
        visualEffect.addSubview_(scrollView)
        
        self.refresh_data()
        self.window.makeKeyAndOrderFront_(None)
        NSApp.activateIgnoringOtherApps_(True)
    
    def refresh_data(self):
        if self.table is None:
            return
        conn = sqlite3.connect(str(DB_PATH))
        try:
            cursor = conn.execute("""
                SELECT id, content, created_at, pinned 
                FROM clips ORDER BY pinned DESC, created_at DESC LIMIT 50
            """)
            self.delegate.clips = cursor.fetchall()
        finally:
            conn.close()
        self.table.reloadData()
    
    def on_clip_copied(self, content):
        rumps.notification("ClipFlow", "已复制", truncate_text(content, 50), sound=False)


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
        self.view_all = rumps.MenuItem("📖 查看历史", callback=self.open_history_window)
        self.view_web = rumps.MenuItem("🌐 网页版", callback=self.open_web_history)
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
        self.menu.add(self.view_web)
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
        self.menu.add(rumps.MenuItem("⭐ GitHub", callback=self.open_github))
        self.menu.add(rumps.separator)
        self.menu.add(self.quit_btn)
    
    def make_copy_callback(self, content):
        """创建复制回调函数"""
        def callback(sender):
            if set_clipboard(content):
                self.last_hash = hashlib.md5(content.encode()).hexdigest()
                rumps.notification("ClipFlow", "已复制", truncate_text(content, 50), sound=False)
        return callback
    
    def open_history_window(self, sender):
        ClipFlowWindow.shared().show()
    
    def open_web_history(self, sender):
        webbrowser.open(f"http://127.0.0.1:{WEB_PORT}")
    
    def open_github(self, sender):
        webbrowser.open("https://github.com/qiaoshouqing/ClipFlow")
    
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
