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
    for p in IMG_ROOT.rglob("*"):
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

    for mi, meta in enumerate(metas, 1):
        desc = (meta.get("desc") or "").strip()
        title = (meta.get("title") or "").strip()
        proj = title or desc or "未命名项目"
        folder = IMG_ROOT / f"{mi:02d}_{safe(proj, 50)}"
        folder.mkdir(exist_ok=True)
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
            ext = ".png" if "wx_fmt=png" in u else (".gif" if "wx_fmt=gif" in u else ".jpg")
            dest = folder / f"{k:02d}{ext}"
            n = 1
            while dest.exists():
                dest = folder / f"{k:02d}_{n}{ext}"
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
    projects = []
    for mi, meta in enumerate(metas, 1):
        proj = (meta.get("title") or meta.get("desc") or "未命名项目").strip()
        folder = IMG_ROOT / f"{mi:02d}_{safe(proj, 50)}"
        if not folder.exists():
            continue
        files = [p for p in sorted(folder.glob("*")) if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".gif")]
        if not files:
            continue
        projects.append({
            "编号": f"{mi:02d}",
            "项目": proj,
            "描述": (meta.get("desc") or "").strip(),
            "来源": meta.get("url", ""),
            "文件夹": folder.name,
            "图片": [str(p.relative_to(ROOT)).replace("\\", "/") for p in files],
        })
    json.dump(projects, open(ROOT / "projects.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"\n元数据写入 projects.json,共 {len(projects)} 个项目")
    return rows


if __name__ == "__main__":
    main()
