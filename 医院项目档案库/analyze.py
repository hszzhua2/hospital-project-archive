# -*- coding: utf-8 -*-
"""分析已抓取页面:提取正文图片(cdn_url)、描述、以及页内其他文章链接"""
import re, glob, sys, os

os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "_pages"))
files = sorted(glob.glob("*.html"))
f = files[-1] if len(sys.argv) < 2 else sys.argv[1]
h = open(f, encoding="utf-8", errors="ignore").read()
print("文件:", f, "大小:", len(h))

links = re.findall(r'https?://mp\.weixin\.qq\.com/s[^\s"\'<>\\]+', h)
uniq = list(dict.fromkeys(links))
print("站内文章链接数:", len(uniq))
for l in uniq[:15]:
    print("   ", l[:170])

print("name:", re.findall(r'window\.name\s*=\s*"([^"]*)"', h)[:2])
print("desc:", re.findall(r'window\.desc\s*=\s*"([^"]*)"', h)[:2])

m = re.search(r"picture_page_info_list:\s*\[", h)
if m:
    seg = h[m.end(): m.end() + 20000]
    urls = re.findall(r"cdn_url:\s*'([^']+)'", seg)
    print("正文图片数:", len(urls))
    for u in urls:
        print("   ", u[:150])
else:
    print("未找到 picture_page_info_list")
