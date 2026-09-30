// 微信图片页抓取器：真实 Chrome（持久化 profile 保留验证 cookie），遇验证等待人工处理
// 用法: node wx_fetch.js <url1> <url2> ...   或   node wx_fetch.js --links links.txt
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright-core');

const CHROME = 'C:/Users/18811/.agent-browser/browsers/chrome-154.0.8037.92/chrome.exe';
const PROFILE = 'C:/Users/18811/.agent-browser/wx_profile';
const OUT = path.join(__dirname, '_pages');
fs.mkdirSync(OUT, { recursive: true });

function isBlocked(url, html) {
  return /wappoc_appmsgcaptcha/.test(url) || /环境异常/.test(html) || /去验证/.test(html);
}

(async () => {
  let args = process.argv.slice(2);
  let urls = [];
  if (args[0] === '--links') {
    urls = fs.readFileSync(path.join(__dirname, args[1]), 'utf8')
      .split('\n').map(s => s.trim()).filter(s => s.startsWith('http'));
  } else {
    urls = args.filter(s => s.startsWith('http'));
  }
  if (!urls.length) { console.log('NO_URL'); process.exit(1); }

  const ctx = await chromium.launchPersistentContext(PROFILE, {
    executablePath: CHROME,
    headless: false,
    viewport: { width: 1280, height: 900 },
    args: ['--disable-blink-features=AutomationControlled'],
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
  });
  const page = ctx.pages()[0] || await ctx.newPage();

  for (const url of urls) {
    console.log('>>> ' + url.slice(0, 90));
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 }).catch(e => console.log('  goto:' + e.message));
    let html = '';
    let needHuman = false;
    for (let i = 0; i < 60; i++) {          // 最多等 5 分钟人工验证
      await page.waitForTimeout(3000);
      html = await page.content().catch(() => '');
      const u = page.url();
      if (isBlocked(u, html)) {
        if (!needHuman) {
          console.log('  [!] 需要人工完成滑块验证（浏览器窗口已打开），等待中...');
          needHuman = true;
        }
        continue;
      }
      if (/mmbiz\.qpic\.cn/.test(html)) { console.log('  [ok] 页面就绪'); break; }
    }
    const ts = Date.now();
    const file = path.join(OUT, 'page_' + ts + '.html');
    fs.writeFileSync(file, html, 'utf8');
    let title = await page.title().catch(() => '');
    const aTitle = await page.evaluate(() => {
      const el = document.querySelector('#activity-name');
      return el ? el.innerText.trim() : '';
    }).catch(() => '');
    if (aTitle) title = aTitle;
    title = title.replace(/\s*[-|]\s*微信公众号.*$/, '').trim();
    const desc = await page.evaluate(() => window.desc || '').catch(() => '');
    // 图集页: cgiDataNew.picture_page_info_list
    let imgs = await page.evaluate(() => {
      const l = (window.cgiDataNew && window.cgiDataNew.picture_page_info_list) || [];
      return l.map(x => x.cdn_url).filter(u => u && /mmbiz\.qpic\.cn/.test(u));
    }).catch(() => []);
    let kind = 'album';
    // 普通图文: #js_content 内 img[data-src]
    if (!imgs.length) {
      imgs = await page.evaluate(() => {
        const box = document.querySelector('#js_content, .rich_media_content, #img-content');
        if (!box) return [];
        const out = [];
        box.querySelectorAll('img').forEach(im => {
          const u = im.getAttribute('data-src') || im.getAttribute('src') || '';
          if (/mmbiz\.qpic\.cn/.test(u)) out.push(u.startsWith('//') ? 'https:' + u : u);
        });
        return out;
      }).catch(() => []);
      if (imgs.length) kind = 'article';
    }
    fs.writeFileSync(path.join(OUT, 'page_' + ts + '.json'),
      JSON.stringify({ url, title, desc, imgs, ts, kind }, null, 2), 'utf8');
    console.log('  HTML: ' + file);
    console.log('  TITLE: ' + title);
    console.log('  DESC: ' + desc.slice(0, 100));
    console.log('  IMGS: ' + imgs.length);
    if (isBlocked(page.url(), html)) { console.log('  [FAIL] 仍未通过验证: ' + url); continue; }
  }

  await ctx.close();
  console.log('DONE');
})();
