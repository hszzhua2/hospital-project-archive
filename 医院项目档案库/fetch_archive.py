# -*- coding: utf-8 -*-
"""
微信公众号图集图片批量归档工具
用法:
    python fetch_archive.py            # 处理 links.txt 中全部链接
    python fetch_archive.py <url>      # 处理单个链接
说明:
    使用 agent-browser(真实 Chrome)打开页面,遇微信滑块验证时等待人工完成,
    随后提取 mmbiz.qpic.cn 图片链接并以最高画质下载,自动去重,写入档案索引。
"""
import subprocess, re, os, sys, json, time, hashlib, csv, pathlib

ROOT = pathlib.Path(__file__).resolve().parent
IMG_DIR = ROOT / "images"
HTML_DIR = ROOT / "_pages"
INDEX = ROOT / "档案库.csv"
IMG_DIR.mkdir(exist_ok=True)
HTML_DIR.mkdir(exist_ok=True)

IMG_RE = re.compile(r'(https?:)?//mmbiz\.qpic\.cn/[^\s"\'\\<>]+')
TITLE_RE = re.compile(r'var\s+(?:msg_title|msg_desc)\s*=\s*[\'"]([^\'"]*)[\'"]')
META_RE = re.compile(r'<meta[^>]+property="og:(?:title|description)"[^>]+content="([^"]*)"')
CDNSRC_RE = re.compile(r'(?:cdn_url|cdnUrl|url)\s*[:=]\s*["\']((https?:)?//mmbiz\.qpic\.cn/[^"\']+)["\']')


def ab(*args, timeout=120):
    r = subprocess.run(["agent-browser", *args], capture_output=True, text=True, timeout=timeout)
    return (r.stdout or "") + (r.stderr or "")


def fetch_page(url, attempts=30):
    """打开页面,如遇微信验证则等待人工处理,返回页面 HTML"""
    ab("open", url, "--headed")
    time.sleep(3)
    for i in range(attempts):
        try:
            html = ab("get", "html")
        except subprocess.TimeoutExpired:
            html = ""
        (HTML_DIR / f"page_{int(time.time())}.html").write_text(html, encoding="utf-8")
        blocked = ("环境异常" in html) or ("wappoc_appmsgcaptcha" in html)
        imgs = extract_images(html)
        if not blocked and imgs:
            return html
        if i == 0 and blocked:
            print("  [!] 页面出现微信验证,请在弹出的浏览器窗口中拖动滑块完成验证...")
        time.sleep(5)
    return html


def extract_images(html):
    urls = []
    for m in IMG_RE.finditer(html):
        u = m.group(0)
        if u.startswith("//"):
            u = "https:" + u
        u = u.replace("&amp;", "&")
        urls.append(u)
    for m in CDNSRC_RE.finditer(html):
        u = m.group(1)
        if u.startswith("//"):
            u = "https:" + u
        urls.append(u.replace("&amp;", "&"))
    # 去重并保持顺序,剔除无关小图标
    seen, out = set(), []
    for u in urls:
        key = u.split("?")[0]
        if key in seen:
            continue
        if any(x in u for x in ("mmbiz_png/", "mmbiz_jpg/", "mmbiz_gif/", "mmbiz_svg/", "/mmbiz_")):
            seen.add(key)
            out.append(u)
    return out


def to_full_size(u):
    """把 640 / 750 / 0 等尺寸后缀换成 0 取原图"""
    return re.sub(r'(mmbiz\.(?:qpic|qlogo)\.cn/[^?]+?)/(\d+)(\?|$)', r'\1/0\3', u)


def title_of(html):
    for rx in (TITLE_RE, META_RE):
        m = rx.search(html)
        if m:
            t = m.group(1).strip()
            t = re.sub(r'\s*\|\s*$', '', t).replace("&#39;", "'").replace("&quot;", '"')
            if t:
                return t[:80]
    m = re.search(r'<title>([^<]*)</title>', html)
    return (m.group(1).strip()[:80] if m else "")


def safe_name(s, maxlen=40):
    s = re.sub(r'[\\/:*?"<>|\r\n\t]', '_', s).strip().strip('.')
    return (s[:maxlen] or "未命名")


def download(u, dest):
    for url in (to_full_size(u), u):
        r = subprocess.run(
            ["curl", "-sL", "--max-time", "60", "-A",
             "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 "
             "(KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.42",
             "-e", "https://mp.weixin.qq.com/", url, "-o", str(dest)],
            capture_output=True)
        if dest.exists() and dest.stat().st_size > 1024:
            with open(dest, "rb") as f:
                head = f.read(12)
            if head[:3] == b"\xff\xd8\xff" or head[:8] == b"\x89PNG\r\n\x1a\n" or head[:4] == b"GIF8" \
               or head[:4] == b"RIFF" or head[:6] == b"<svg "[:6] or head[:2] == b"BM":
                return True
            dest.unlink()
    return False


def load_index():
    rows = {}
    if INDEX.exists():
        with open(INDEX, "r", encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                rows[r["文件名"]] = r
    return rows


def save_index(rows):
    with open(INDEX, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["序号", "项目名称", "文件名", "原图链接", "来源链接", "下载时间"])
        w.writeheader()
        for i, r in enumerate(rows.values(), 1):
            r["序号"] = i
            w.writerow(r)


def main():
    args = [a.strip() for a in sys.argv[1:] if a.strip().startswith("http")]
    if not args:
        lf = ROOT / "links.txt"
        args = [l.strip() for l in lf.read_text(encoding="utf-8").splitlines()
                if l.strip().startswith("http")] if lf.exists() else []
    rows = load_index()
    existing_md5 = {}
    for p in IMG_DIR.glob("*"):
        if p.is_file():
            existing_md5.setdefault(hashlib.md5(p.read_bytes()).hexdigest(), p.name)

    for url in args:
        print(f"\n>>> 处理: {url[:90]}...")
        html = fetch_page(url)
        imgs = extract_images(html)
        title = title_of(html)
        print(f"    标题: {title or '(无)'} | 图片数: {len(imgs)}")
        for u in imgs:
            tmp = IMG_DIR / "_tmp"
            if not download(u, tmp):
                print(f"    [x] 下载失败: {u[:70]}")
                continue
            md5 = hashlib.md5(tmp.read_bytes()).hexdigest()
            if md5 in existing_md5:
                tmp.unlink()
                print(f"    [=] 已存在(跳过重复): {existing_md5[md5]}")
                continue
            ext = ".png" if "wx_fmt=png" in u else (".gif" if "wx_fmt=gif" in u else ".jpg")
            name = f"{len(rows)+1:03d}_{safe_name(title)}{ext}"
            dest = IMG_DIR / name
            tmp.rename(dest)
            existing_md5[md5] = name
            rows[name] = {"序号": len(rows) + 1, "项目名称": title, "文件名": name,
                          "原图链接": u, "来源链接": url,
                          "下载时间": time.strftime("%Y-%m-%d %H:%M")}
            print(f"    [√] 保存: {name}")
        save_index(rows)
    print(f"\n完成,档案共 {len(rows)} 张图片 -> {IMG_DIR}")
    save_index(rows)


if __name__ == "__main__":
    main()
