# -*- coding: utf-8 -*-
"""感知哈希去重:识别同一张图的不同 CDN 版本,重复图移入 _dupes/"""
import os, glob, shutil, pathlib
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent
IMG = ROOT / "images"
DUP = ROOT / "_dupes"
DUP.mkdir(exist_ok=True)


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


kept, sigs, moved = {}, [], 0
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
        print(f"  重复 -> 移入 _dupes: {rel.name} (≈ {dup_of})")
    else:
        sigs.append((h, w, ht, p.name))

print(f"\n保留 {len(sigs)} 张,移出重复 {moved} 张")
