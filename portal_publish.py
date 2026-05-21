#!/usr/bin/env python3
"""
ZOCHA Admin Portal 統一發布工具

Usage:
  python portal_publish.py --key <shortage|reviews|news|battery> \
                            --html <path_to_html> \
                           [--data <path_to_data_json>] \
                           [--message "自訂 commit 訊息"]

功能：
  1. 將 HTML 複製到 portal 目錄（shortage.html / reviews.html / news.html / battery.html）
  2. 若提供 --data，一併複製為 <key>_data.json（供跨看板整合使用）
  3. 更新 status.json 的對應時間戳
  4. git add + commit + push 到 zocha-admin-portal repo
"""
import argparse, json, shutil, subprocess, sys, datetime
from pathlib import Path

PORTAL_DIR = Path(r"D:\OneDrive\桌面\Cowork\ZOCHA 管理系統")

KEY_MAP = {
    'shortage': 'shortage.html',
    'reviews':  'reviews.html',
    'news':     'news.html',
    'battery':  'battery.html',
}

COMMIT_PREFIX = {
    'shortage': '🚗 缺車分析週報更新',
    'reviews':  '⭐ 客戶評論週報更新',
    'news':     '📰 時事新聞標案週報更新',
    'battery':  '🔋 電池資費月報更新',
}


def git(args, cwd=PORTAL_DIR):
    r = subprocess.run(
        ["git"] + args, cwd=str(cwd),
        capture_output=True, text=True, encoding='utf-8', errors='replace'
    )
    return r


def main():
    parser = argparse.ArgumentParser(description='Publish dashboard to ZOCHA Admin Portal')
    parser.add_argument('--key',     required=True, choices=KEY_MAP.keys(), help='看板代號')
    parser.add_argument('--html',    required=True, help='HTML 來源路徑')
    parser.add_argument('--data',    default=None,  help='JSON 資料來源路徑（可選）')
    parser.add_argument('--message', default=None,  help='自訂 commit 訊息')
    args = parser.parse_args()

    html_src = Path(args.html)
    if not html_src.exists():
        print(f"[portal] ERROR: HTML 檔案不存在：{html_src}", file=sys.stderr)
        sys.exit(1)

    # 1. 複製 HTML
    dest_html = PORTAL_DIR / KEY_MAP[args.key]
    shutil.copy2(html_src, dest_html)
    print(f"[portal] ✓ HTML → {dest_html.name}")

    # 2. 複製 data JSON（可選）
    files_to_add = [KEY_MAP[args.key], 'status.json']
    if args.data:
        data_src = Path(args.data)
        if data_src.exists():
            dest_data = PORTAL_DIR / f"{args.key}_data.json"
            shutil.copy2(data_src, dest_data)
            print(f"[portal] ✓ Data → {dest_data.name}")
            files_to_add.append(f"{args.key}_data.json")
        else:
            print(f"[portal] WARNING: data 檔案不存在，略過：{data_src}", file=sys.stderr)

    # 3. 更新 status.json
    status_path = PORTAL_DIR / 'status.json'
    status = json.loads(status_path.read_text(encoding='utf-8'))
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    status[args.key] = now_iso
    status_path.write_text(json.dumps(status, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f"[portal] ✓ status.json 已更新：{args.key} = {now_iso}")

    # 4. Git: add → commit → push
    today = datetime.date.today().strftime('%Y-%m-%d')
    commit_msg = args.message or f"{COMMIT_PREFIX[args.key]} {today}"

    git(["add"] + files_to_add)

    r_commit = git(["commit", "-m", commit_msg])
    if r_commit.returncode != 0:
        out = r_commit.stdout + r_commit.stderr
        if 'nothing to commit' in out:
            print("[portal] 無新變更，略過 commit。")
            return
        print(f"[portal] ERROR git commit: {r_commit.stderr}", file=sys.stderr)
        sys.exit(1)
    print(f"[portal] ✓ Committed: {commit_msg}")

    r_push = git(["push"])
    if r_push.returncode != 0:
        print(f"[portal] ERROR git push: {r_push.stderr}", file=sys.stderr)
        sys.exit(1)
    print("[portal] ✓ 已推送到 zocha-admin-portal")


if __name__ == '__main__':
    main()
