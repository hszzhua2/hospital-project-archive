# -*- coding: utf-8 -*-
"""感知哈希去重:识别同一张图的不同 CDN 版本,重复图移入 _dupes/"""
import os, glob, shutil, pathlib
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent
IMG = ROOT / "images"
DUP = ROOT / "_dupes"
BLACK = DUP / "blacklist.json"   # 被判重复图的感知签名,供 build_archive 预先拦截
DUP.mkdir(exist_ok=True)


def load_blacklist():
    try:
        return json.load(open(BLACK, encoding="utf-8"))
    except Exception:
        return []


def save_blacklist(items):
    json.dump(items[-4000:], open(BLACK, "w", encoding="utf-8"), ensure_ascii=False)


def dhash(p, size=8):
    im = Image.open(p).convert("L").resize((size + 1, size), Image.LANCZOS)
    px = list(im.getdata())
    bits = []
    for r in range(size):
        for c in range(size):
            bits.append(px[r * (size + 1) + c] < px[r * (size + 1) + c + 1])
    return int("".join("1" if b else "0" for b in bits), 2)


def ham(a, b):
    return bin(a ^ b).count("1")


import json  # noqa: E402

sigs, moved = [], 0
black = load_blacklist()
for p in sorted(IMG.rglob("*")):
    if not p.is_file() or p.suffix.lower() not in (".jpg", ".jpeg", ".png", ".gif"):
        continue
    try:
        h = dhash(p)
        w, ht = Image.open(p).size
    except Exception as e:
        print("跳过(损坏):", p.name, e)
        continue
    dup_of = None
    # 先对照历史黑名单(避免已清理的重复图被重新下载后再次入库)
    for b in black:
        if abs(b["w"] - w) < 20 and abs(b["h"] - ht) < 20 and ham(h, b["dhash"]) <= 6:
            dup_of = b["name"]
            break
    if dup_of is None:
        for (h2, w2, h2t, name) in sigs:
            if abs(w2 - w) < 20 and abs(h2t - ht) < 20 and ham(h, h2) <= 6:
                dup_of = name
                break
    if dup_of:
        rel = p.relative_to(IMG)
        tgt = DUP / str(rel).replace("\\", "__")
        tgt.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(p), str(tgt))
        moved += 1
        black.append({"dhash": h, "w": w, "h": ht, "name": p.name})
        print(f"  重复 -> 移入 _dupes: {rel.name} (≈ {dup_of})")
    else:
        sigs.append((h, w, ht, p.name))

save_blacklist(black)
print(f"\n保留 {len(sigs)} 张,移出重复 {moved} 张,黑名单累计 {len(black)} 条")
