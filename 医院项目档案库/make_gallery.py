# -*- coding: utf-8 -*-
"""生成 档案库.csv 索引 与 档案库.html 可视化档案库(暗色、可搜索、灯箱大图)"""
import json, csv, pathlib, html, time

ROOT = pathlib.Path(__file__).resolve().parent
PJ = ROOT / "projects.json"
projects = json.load(open(PJ, encoding="utf-8")) if PJ.exists() else []

rows = []
for p in projects:
    for f in p["图片"]:
        fp = ROOT / f
        if not fp.exists():
            continue
        rows.append({
            "序号": len(rows) + 1,
            "项目": p["项目"],
            "项目描述": p["描述"][:200],
            "文件": f,
            "大小KB": round(fp.stat().st_size / 1024),
            "来源链接": p["来源"],
        })

with open(ROOT / "档案库.csv", "w", encoding="utf-8-sig", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=["序号", "项目", "项目描述", "文件", "大小KB", "来源链接"])
    w.writeheader()
    w.writerows(rows)

cards = []
for p in projects:
    imgs = [f for f in p["图片"] if (ROOT / f).exists()]
    if not imgs:
        continue
    thumbs = "".join(
        f'<a class="thumb" href="{html.escape(f)}" data-proj="{html.escape(p["项目"])}">'
        f'<img loading="lazy" src="{html.escape(f)}" alt=""></a>' for f in imgs)
    src = f'<a class="src" href="{html.escape(p["来源"])}" target="_blank">原文链接 ↗</a>' if p["来源"] else ""
    cards.append(f"""
    <section class="card" data-name="{html.escape(p['项目'])} {html.escape(p['描述'])}">
      <header>
        <span class="num">{p['编号']}</span>
        <h2>{html.escape(p['项目'])}</h2>
        <span class="cnt">{len(imgs)} 张</span>
      </header>
      {f'<p class="desc">{html.escape(p["描述"])}</p>' if p['描述'] else ''}
      <div class="grid">{thumbs}</div>
      {src}
    </section>""")

HTML = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>医院项目图片档案库 · 国家区域医疗中心</title>
<style>
:root{{--bg:#0f1216;--card:#171b21;--line:#252b33;--tx:#e6e9ef;--dim:#9aa4b2;--acc:#4a9eff}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--tx);font:14px/1.6 -apple-system,"Microsoft YaHei",sans-serif}}
header.top{{position:sticky;top:0;background:var(--bg);border-bottom:1px solid var(--line);padding:14px 20px;z-index:9}}
header.top h1{{margin:0 0 8px;font-size:17px;font-weight:600}}
header.top .stat{{color:var(--dim);font-size:12px;margin-left:8px}}
input#q{{width:100%;padding:9px 12px;border:1px solid var(--line);border-radius:8px;background:var(--card);color:var(--tx);font-size:14px}}
input#q:focus{{outline:none;border-color:var(--acc)}}
main{{padding:16px 20px 60px;max-width:1400px;margin:0 auto}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px 16px;margin-bottom:16px}}
.card header{{display:flex;align-items:center;gap:10px;margin-bottom:6px}}
.num{{background:var(--acc);color:#fff;border-radius:6px;padding:1px 8px;font-size:12px;font-weight:700}}
.card h2{{margin:0;font-size:15px;font-weight:600;flex:1}}
.cnt{{color:var(--dim);font-size:12px}}
.desc{{margin:0 0 10px;color:var(--dim);font-size:12.5px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:8px}}
.thumb{{display:block;border-radius:8px;overflow:hidden;background:#000;aspect-ratio:4/3}}
.thumb img{{width:100%;height:100%;object-fit:cover;display:block;transition:transform .25s}}
.thumb:hover img{{transform:scale(1.04)}}
.src{{display:inline-block;margin-top:10px;color:var(--acc);font-size:12px;text-decoration:none}}
#lb{{position:fixed;inset:0;background:rgba(0,0,0,.92);display:none;align-items:center;justify-content:center;z-index:99;cursor:zoom-out}}
#lb.on{{display:flex}} #lb img{{max-width:96vw;max-height:94vh;object-fit:contain}}
#lb .cap{{position:absolute;bottom:16px;left:0;right:0;text-align:center;color:#bbb;font-size:13px}}
.hide{{display:none!important}}
</style></head><body>
<header class="top">
  <h1>医院项目图片档案库<span class="stat">{len(projects)} 个项目 / {len(rows)} 张图片</span></h1>
  <input id="q" placeholder="搜索项目名称、医院、城市…">
</header>
<main id="main">{''.join(cards)}</main>
<div id="lb"><img alt=""><div class="cap"></div></div>
<script>
const q=document.getElementById('q'),cards=[...document.querySelectorAll('.card')];
q.oninput=()=>{{const v=q.value.trim().toLowerCase();
  cards.forEach(c=>c.classList.toggle('hide', v&&!c.dataset.name.toLowerCase().includes(v)));}};
const lb=document.getElementById('lb'),lbimg=lb.querySelector('img'),cap=lb.querySelector('.cap');
document.addEventListener('click',e=>{{
  const a=e.target.closest('.thumb');
  if(a){{e.preventDefault();lbimg.src=a.getAttribute('href');cap.textContent=a.dataset.proj;lb.classList.add('on');}}
  else if(lb.classList.contains('on')){{lb.classList.remove('on');lbimg.src='';}}
}});
document.addEventListener('keydown',e=>{{if(e.key==='Escape'){{lb.classList.remove('on')}}}});
</script>
</body></html>"""
(ROOT / "档案库.html").write_text(HTML, encoding="utf-8")
print(f"生成 档案库.html ({len(projects)} 项目 / {len(rows)} 图) 与 档案库.csv")
