// 试探:在图片页滚动加载瀑布流,收集同公众号其他"图片消息"的链接
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright-core');

const CHROME = 'C:/Users/18811/.agent-browser/browsers/chrome-154.0.8037.92/chrome.exe';
const PROFILE = 'C:/Users/18811/.agent-browser/wx_profile';
const SEED = process.argv[2] || fs.readFileSync(path.join(__dirname, 'links.txt'), 'utf8')
  .split('\n').map(s => s.trim()).filter(s => s.startsWith('http'))[0];

(async () => {
  const ctx = await chromium.launchPersistentContext(PROFILE, {
    executablePath: CHROME, headless: false, viewport: { width: 1280, height: 900 },
    args: ['--disable-blink-features=AutomationControlled'],
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
  });
  const page = ctx.pages()[0] || await ctx.newPage();
  await page.goto(SEED, { waitUntil: 'domcontentloaded', timeout: 60000 }).catch(e => console.log('goto:' + e.message));
  await page.waitForTimeout(4000);

  const found = new Set();
  for (let i = 0; i < 12; i++) {
    const links = await page.evaluate(() => {
      const out = [];
      document.querySelectorAll('a[href]').forEach(a => out.push(a.href));
      return out;
    }).catch(() => []);
    links.forEach(l => { if (/mp\.weixin\.qq\.com\/s\?/.test(l) && /sn=/.test(l)) found.add(l); });
    await page.mouse.wheel(0, 2500);
    await page.waitForTimeout(1500);
  }
  // 页面源码里的标题/链接
  const html = await page.content().catch(() => '');
  for (const m of html.matchAll(/https?:\/\/mp\.weixin\.qq\.com\/s\?[^"'\s<>\\]*?sn=[0-9a-f]{16,}/g)) {
    found.add(m[0].replace(/&amp;/g, '&'));
  }
  console.log('发现图片消息链接: ' + found.size);
  [...found].forEach(u => console.log('  ' + u.slice(0, 150)));
  fs.writeFileSync(path.join(__dirname, 'discovered.txt'), [...found].join('\n'), 'utf8');
  await ctx.close();
  console.log('已写入 discovered.txt');
})();
