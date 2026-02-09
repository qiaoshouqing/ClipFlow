# ClipFlow 📋

macOS メニューバーに常駐する、ミニマルでエレガントなクリップボードマネージャー。

[English](./README.md) | [简体中文](./README.zh-CN.md) | [繁體中文](./README.zh-TW.md)

![ClipFlow](https://img.shields.io/badge/プラットフォーム-macOS-blue) ![Python](https://img.shields.io/badge/python-3.9+-green) ![License](https://img.shields.io/badge/ライセンス-MIT-gray)

## 特徴

- 🖥️ **メニューバー常駐** — メニューバーに静かに待機、いつでもアクセス可能
- 📝 **自動キャプチャ** — コピーしたすべてを自動保存
- 🔍 **クイックアクセス** — クリックで履歴表示、もう一度クリックでコピー
- 🌐 **ウェブ履歴** — ダークテーマの美しいウェブインターフェース
- 🌙 **ミニマルデザイン** — クリーンでクールな美学、macOS にマッチ
- ⚡ **軽量** — CPU 使用率 0.1% 未満、パフォーマンスに影響なし

## インストール

### 方法1：リリースをダウンロード（推奨）

1. [Releases](https://github.com/qiaoshouqing/ClipFlow/releases) から最新の `.app` をダウンロード
2. `/Applications` に移動
3. 開いて使用開始

### 方法2：ソースから実行

```bash
# リポジトリをクローン
git clone https://github.com/qiaoshouqing/ClipFlow.git
cd ClipFlow

# 仮想環境を作成
python3 -m venv venv
source venv/bin/activate

# 依存関係をインストール
pip install -r requirements.txt

# 実行
python clipboard_manager.py
```

## 使い方

- **メニューバーアイコンをクリック** — 最近の 8 件を表示
- **任意の項目をクリック** — クリップボードにコピー
- **📖 すべての履歴を表示** — ウェブインターフェースを開く `http://127.0.0.1:17890`
- **🗑️ 履歴をクリア** — ピン留め以外のすべてを削除
- **⏸️ モニタリング一時停止** — 一時的にキャプチャを停止

## データストレージ

すべてのクリップボード履歴はローカルに保存：
```
~/.clipflow/history.db
```

データはサーバーに送信されません。クリップボードのプライバシーは安全です。

## システム要件

- macOS 10.15+
- Python 3.9+（ソースから実行する場合）

## ライセンス

MIT ライセンス - 自由に使用、変更、配布できます。

---

Made with 🦞 by [WilsonClaw](https://github.com/qiaoshouqing)
