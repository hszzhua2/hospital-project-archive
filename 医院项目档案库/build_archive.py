# -*- coding: utf-8 -*-
"""
把 _pages 中已抓取的页面归档:
  - 解析每个项目的正文图片(cdn_url),下载原图到 images/<项目文件夹>/
  - 生成 档案库.csv 索引 + 档案库.html 可视化档案库(可搜索)
"""
import re, os, json, glob, csv, time, hashlib, subprocess, pathlib

ROOT = pathlib.Path(__file__).resolve().parent
PAGES = ROOT / "_pages"
IMG_ROOT = ROOT / "images"
IMG_ROOT.mkdir(exist_ok=True)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")


def safe(s, n=60):
    s = re.sub(r'[\\/:*?"<>|\r\n\t]', '_', s or "").strip().strip('. ')
    s = re.sub(r'\s+', '', s)
    return s[:n] or "未命名"


def hosp_key(s):
    """医院识别 key:去掉'国家区域医疗中心'等前缀与分隔符,用于判断同一家医院"""
    s = re.sub(r'国家区域医疗中心\s*[•·\-—]?\s*', '', s or "")
    s = re.sub(r'[•·\s（）()【】\[\]、,，。]', '', s)
    return s.strip()


def merge_index(keys):
    """
    把新项目归并到已存在的同一家医院。
    返回 {新meta下标: 主meta下标}
    规则(保守,宁可不合并也不错并):
      1) key 完全相同 -> 同一条目的多期推送
      2) 短者是长者的前缀或后缀,且短者 >= 10 字 -> 同一家医院(如"XX医院"与"XX医院(新院区)")
    注意:不能用 min/max(key=len) 取长短串——两者等长时返回同一对象,会自己包含自己
    """
    owner = {}      # 主 meta 下标 -> key
    merged = {}     # 被合并的 meta 下标 -> 主 meta 下标
    for mi, k in keys.items():
        if not k:
            continue
        hit = None
        for ok, okk in owner.items():
            if k == okk:
                hit = ok
                break
            a, b = (k, okk) if len(k) <= len(okk) else (okk, k)
            if len(a) >= 10 and a != b and (b.startswith(a) or b.endswith(a)):
                hit = ok
                break
        if hit is None:
            owner[mi] = k
        else:
            merged[mi] = hit
    return merged


try:                       # 感知去重需要 PIL,缺失时退化为仅 md5 去重
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


def dhash(p, size=8):
    im = Image.open(p).convert("L").resize((size + 1, size), Image.LANCZOS)
    px = list(im.getdata())
    bits = []
    for r in range(size):
        for c in range(size):
            bits.append(px[r * (size + 1) + c] < px[r * (size + 1) + c + 1])
    return int("".join("1" if b else "0" for b in bits), 2)


def load_seen():
    """已处理过(保留或已去重)的图的感知签名,按项目隔离"""
    f = ROOT / "_dupes" / "seen.json"
    if not HAS_PIL or not f.exists():
        return []
    try:
        return json.load(open(f, encoding="utf-8"))
    except Exception:
        return []


def is_duplicate(p, proj):
    """新下载的图是否与本项目已处理过的某张图是同一张(不同 CDN 版本)"""
    if not HAS_PIL:
        return False
    try:
        h = dhash(p)
        w, ht = Image.open(p).size
    except Exception:
        return False
    for b in SEEN:
        if b.get("proj") != proj:
            continue
        if abs(b["w"] - w) < 20 and abs(b["h"] - ht) < 20 and \
           bin(h ^ b["dhash"]).count("1") <= 6:
            return True
    return False


SEEN = load_seen()


def dl(url, dest):
    for u in (url, re.sub(r'(mmbiz\.(?:qpic|qlogo)\.cn/[^?]+?)/(\d+)(\?|$)', r'\1/0\3', url)):
        subprocess.run(["curl", "-sL", "--max-time", "90", "-A", UA,
                        "-e", "https://mp.weixin.qq.com/", u, "-o", str(dest)],
                       capture_output=True)
        if dest.exists() and dest.stat().st_size > 2048:
            with open(dest, "rb") as f:
                h = f.read(8)
            if h[:3] == b"\xff\xd8\xff" or h[:8] == b"\x89PNG\r\n\x1a\n" or h[:4] == b"GIF8":
                return True
            dest.unlink()
    return False


def main():
    metas = []
    for jf in sorted(PAGES.glob("*.json")):
        try:
            metas.append(json.load(open(jf, encoding="utf-8")))
        except Exception:
            pass
    # 兼容只有 html 的情况
    html_only = [h for h in sorted(PAGES.glob("*.html"))
                 if not (PAGES / (h.stem + ".json")).exists()]
    for h in html_only:
        txt = h.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r"picture_page_info_list:\s*\[", txt)
        imgs = []
        if m:
            seg = txt[m.end(): m.end() + 30000]
            imgs = [u for u in re.findall(r"cdn_url:\s*'([^']+)'", seg)
                    if "mmbiz.qpic.cn" in u]
        name = (re.findall(r'window\.name\s*=\s*"([^"]*)"', txt) or [""])[0]
        desc = (re.findall(r'window\.desc\s*=\s*"([^"]*)"', txt) or [""])[0]
        title = (re.findall(r'<title>([^<]*)</title>', txt) or [""])[0]
        metas.append({"url": "", "title": title, "desc": desc, "imgs": imgs, "ts": h.stat().st_mtime})

    rows, seen_md5 = [], {}
    # 已入库图 + 已判重复的图(_dupes)都参与精确去重,避免重复图被反复下载回来
    for base in (IMG_ROOT, ROOT / "_dupes"):
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if p.is_file():
                seen_md5.setdefault(hashlib.md5(p.read_bytes()).hexdigest(), str(p))

    # JSON 记录的图片可能不全(懒加载),用同批 HTML 正则补全
    for meta in metas:
        hfile = PAGES / ("page_%s.html" % meta.get("ts"))
        if hfile.exists():
            txt = hfile.read_text(encoding="utf-8", errors="ignore")
            m = re.search(r"picture_page_info_list:\s*\[", txt)
            if m:
                seg = txt[m.end(): m.end() + 30000]
                for u in re.findall(r"cdn_url:\s*'([^']+)'", seg):
                    if "mmbiz.qpic.cn" in u and u not in meta["imgs"]:
                        meta["imgs"].append(u)

    # 同一家医院归并:后来的页面并到最早出现的那个项目文件夹
    keys = {mi: hosp_key((m.get("title") or m.get("desc") or "").strip())
            for mi, m in enumerate(metas, 1)}
    merged = merge_index(keys)
    if merged:
        print(f"\n检测到同医院条目 {len(merged)} 个,将合并到已有项目")

    for mi, meta in enumerate(metas, 1):
        desc = (meta.get("desc") or "").strip()
        title = (meta.get("title") or "").strip()
        proj = title or desc or "未命名项目"
        main_i = merged.get(mi, mi)
        if main_i != mi:
            main_meta = metas[main_i - 1]
            main_proj = (main_meta.get("title") or main_meta.get("desc") or "未命名项目").strip()
            folder = IMG_ROOT / f"{main_i:02d}_{safe(main_proj, 50)}"
            folder.mkdir(exist_ok=True)
            start = len([p for p in folder.glob("*")
                         if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".gif")])
            print(f"[{mi}] {proj[:50]} → 合并进 {folder.name} (已有 {start} 张)")
        else:
            folder = IMG_ROOT / f"{mi:02d}_{safe(proj, 50)}"
            folder.mkdir(exist_ok=True)
            start = 0
            print(f"[{mi}] {proj[:60]} | 图片 {len(meta.get('imgs', []))} 张")
        ok = 0
        for k, u in enumerate(meta.get("imgs", []), 1):
            tmp = folder / "_tmp"
            if not dl(u, tmp):
                print(f"    [x] 失败 {u[:60]}")
                continue
            md5 = hashlib.md5(tmp.read_bytes()).hexdigest()
            if md5 in seen_md5:
                tmp.unlink()
                continue
            seen_md5[md5] = str(tmp)
            if is_duplicate(tmp, folder.name):
                tmp.unlink()
                continue
            ext = ".png" if "wx_fmt=png" in u else (".gif" if "wx_fmt=gif" in u else ".jpg")
            n = 0
            while True:
                dest = folder / (f"{start + ok + 1:03d}{ext}" if n == 0
                                 else f"{start + ok + 1:03d}_{n}{ext}")
                if not dest.exists():
                    break
                n += 1
            tmp.rename(dest)
            seen_md5[md5] = str(dest)
            rows.append({"序号": len(rows) + 1, "项目": proj, "项目描述": desc[:200],
                         "文件": str(dest.relative_to(ROOT)).replace("\\", "/"),
                         "原图链接": u, "来源链接": meta.get("url", ""),
                         "下载时间": time.strftime("%Y-%m-%d %H:%M")})
            ok += 1
        print(f"    新增 {ok} 张 -> {folder.name}")

    # 保存项目级元数据,供可视化档案库使用
    # 同一家医院合并后:图片汇总,描述与来源链接去重后保留多条
    projects = []
    for mi, meta in enumerate(metas, 1):
        if mi in merged:          # 被合并掉的条目不单独出卡片
            continue
        group = [mi] + [m for m, main in merged.items() if main == mi]
        proj = (meta.get("title") or meta.get("desc") or "未命名项目").strip()
        folder = IMG_ROOT / f"{mi:02d}_{safe(proj, 50)}"
        if not folder.exists():
            continue
        files = [p for p in sorted(folder.glob("*")) if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".gif")]
        if not files:
            continue
        descs, srcs = [], []
        for g in group:
            m = metas[g - 1]
            d = (m.get("desc") or "").strip()
            if d and d not in descs:
                descs.append(d)
            u = (m.get("url") or "").strip()
            if u and u not in srcs:
                srcs.append(u)
        projects.append({
            "编号": f"{mi:02d}",
            "项目": proj,
            "描述": " ｜ ".join(descs)[:400],
            "来源": srcs[0] if srcs else "",
            "来源列表": srcs,
            "合并条目": len(group),
            "文件夹": folder.name,
            "图片": [str(p.relative_to(ROOT)).replace("\\", "/") for p in files],
        })
    json.dump(projects, open(ROOT / "projects.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"\n元数据写入 projects.json,共 {len(projects)} 个项目")
    return rows


if __name__ == "__main__":
    main()
