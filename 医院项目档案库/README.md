# 医院项目图片档案库

来源：微信公众号「吴昭辉医师」图集（国家区域医疗中心项目合集）

## 目录结构
```
医院项目档案库/
├─ 档案库.html      可视化档案库（双击打开，可搜索、点图看大图）
├─ 档案库.csv       图片索引（项目 / 描述 / 文件 / 来源链接）
├─ images/          按项目分文件夹存放的原图
├─ _dupes/          同一张图的重复 CDN 版本（已剔除，可删）
├─ _pages/          抓取的页面源码与元数据
├─ links.txt        待抓取的微信图片消息链接（每行一条）
└─ *.py / *.js      抓取与归档脚本
```

## 加新项目的流程（三步）
1. 微信里打开该图集图片 → 右上角「…」→ 复制链接，粘贴到 `links.txt`（每行一条，可一次贴很多条）
2. 抓取页面：
   ```bash
   NODE_PATH=C:/Users/18811/.workbuddy/binaries/node/workspace/node_modules \
   C:/Users/18811/.workbuddy/binaries/node/versions/22.22.2-3/node.exe wx_fetch.js --links links.txt
   ```
   若弹出「环境异常」滑块验证，在浏览器窗口里手动拖一下，脚本会自动继续
3. 归档并重建档案库：
   ```bash
   C:/Users/18811/.workbuddy/binaries/python/versions/3.13.12/python.exe build_archive.py
   C:/Users/18811/.workbuddy/binaries/python/envs/default/Scripts/python.exe dedupe.py
   C:/Users/18811/.workbuddy/binaries/python/versions/3.13.12/python.exe make_gallery.py
   ```

说明：`build_archive.py` 按 md5 跳过已下载图片，重复执行安全；`dedupe.py` 用感知哈希剔除同一张图的 sz_/mmbiz 双版本。

## 在线分享（GitHub Pages）
**分享链接：https://hszzhua2.github.io/hospital-project-archive/**

手机/电脑浏览器直接打开，无需登录，适合发给同行看。站点由 `docs/` 目录发布，
图片是**真实文件副本**（不走 LFS，因为 GitHub Pages 不解析 LFS 指针）。

新增项目后，跑完归档流程再执行 `make_gallery.py`，它会同时更新本地 `档案库.html` 和 `docs/index.html`，
随后自动同步流会把站点推上线（约 1 分钟生效）。

## GitHub 自动同步
仓库：https://github.com/hszzhua2/hospital-project-archive （公开，图片走 Git LFS）

工作区任一文件变化后，后台监听会在文件稳定 8 秒后自动提交并推送，无需手动操作。

- 手动同步一次：双击 `.sync/同步一次.bat`，或 `python .sync/sync.py -m "说明"`
- 看将要提交什么：`.sync/sync.py --dry-run`
- 自检（git / 远端 / 凭据是否可用）：`.sync/sync.py --check`
- 查看日志：`.sync/sync.log`
- 后台监听：登录即启动（启动项 `HospitalArchiveGitSync`），默认 15 秒轮询 / 8 秒稳定等待
- 立即启动监听：双击 `.sync/start_watch.bat`（窗口会自动最小化，进程名 `pythonw.exe`）
- 停止监听：任务管理器结束 `pythonw.exe`
- 监听日志每 5 分钟写一条「心跳」，可据此判断进程是否还活着

排除在仓库外：`_pages/`（大体积页面源码）、`_dupes/`（重复图）、`.workbuddy/`（会话记忆）。
