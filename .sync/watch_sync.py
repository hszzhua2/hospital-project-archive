# -*- coding: utf-8 -*-
"""
后台监听:轮询工作区,文件稳定后自动提交并推送到 GitHub
用法: pythonw .sync/watch_sync.py [--interval 15] [--debounce 8] [--once]
"""
import argparse, hashlib, pathlib, subprocess, sys, time, datetime, os

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from sync import sync, log, run, portrait  # noqa: E402


def snapshot():
    """工作区状态指纹:路径 + 大小 + 修改时间"""
    items, _ = portrait()
    if not items:
        return None, []
    sig = []
    for xy, p in items:
        fp = ROOT / p
        try:
            st = fp.stat()
            sig.append(f"{xy}|{p}|{st.st_size}|{int(st.st_mtime)}")
        except Exception:
            sig.append(f"{xy}|{p}|?")
    return hashlib.md5("\n".join(sig).encode()).hexdigest(), items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", type=int, default=15, help="轮询间隔秒")
    ap.add_argument("--debounce", type=int, default=8, help="变动后等待稳定秒数")
    ap.add_argument("--once", action="store_true", help="只跑一轮")
    args = ap.parse_args()

    log(f"监听启动 | 间隔 {args.interval}s | 稳定等待 {args.debounce}s | 目录 {ROOT}")
    last_sig, stable_since = None, None
    while True:
        try:
            sig, items = snapshot()
            if sig is None:
                stable_since = None
                last_sig = None
            elif sig != last_sig:
                last_sig = sig
                stable_since = time.time()
            elif stable_since and time.time() - stable_since >= args.debounce:
                log(f"检测到稳定变更 {len(items)} 项，开始同步")
                sync()
                last_sig, stable_since = None, None
        except Exception as e:
            log(f"轮询异常: {e}")
        if args.once:
            break
        time.sleep(args.interval)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("监听已停止")
