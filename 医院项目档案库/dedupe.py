# -*- coding: utf-8 -*-
"""
感知哈希去重:识别同一张图的不同 CDN 版本,重复图移入 _dupes/

设计要点:
  - 单次运行内按遍历顺序累积签名,先出现的保留,后出现的重复版本移入 _dupes/
  - 所有扫描过的图(无论保留还是移走)的签名都写入 _dupes/seen.json,
    供 build_archive.py 在【下载阶段】拦截"已经处理过的图"的其他 CDN 版本。
  - 重要:seen.json 只用于下载阶段拦截新图,不在本脚本内用于过滤,
    否则会把上次保留下来的图误判为重复(保留图与其重复版本签名相同)。
"""
import shutil, json, pathlib
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent
IMG = ROOT / "images"
DUP = ROOT / "_dupes"
SEEN = DUP / "seen.json"
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


def load_seen():
    try:
        return json.load(open(SEEN, encoding="utf-8"))
    except Exception:
        return []


sigs, moved = [], 0
seen_map = {(s["proj"], s["name"]): s for s in load_seen()}

for p in sorted(IMG.rglob("*")):
    if not p.is_file() or p.suffix.lower() not in (".jpg", ".jpeg", ".png", ".gif"):
        continue
    proj = p.parent.name
    try:
        h = dhash(p)
        w, ht = Image.open(p).size
    except Exception as e:
        print("跳过(损坏):", p.name, e)
        continue
    dup_of = None
    # 只在同一项目内比较:不同项目不可能出现同一张图的另一个 CDN 版本,
    # 跨项目比较会把不同医院的相似效果图误判为重复
    for (pj2, h2, w2, h2t, name) in sigs:
        if pj2 == proj and abs(w2 - w) < 20 and abs(h2t - ht) < 20 and ham(h, h2) <= 6:
            dup_of = name
            break
    if dup_of:
        shutil.move(str(p), str(DUP / (proj + "__" + p.name)))
        moved += 1
        print(f"  重复 -> 移入 _dupes: {proj}/{p.name} (≈ {dup_of})")
    else:
        sigs.append((proj, h, w, ht, p.name))
    seen_map[(proj, p.name)] = {"proj": proj, "name": p.name,
                                "dhash": h, "w": w, "h": ht}

json.dump(list(seen_map.values())[-6000:], open(SEEN, "w", encoding="utf-8"),
          ensure_ascii=False)
print(f"\n保留 {len(sigs)} 张,本次移出重复 {moved} 张,签名库累计 {len(seen_map)} 条")
