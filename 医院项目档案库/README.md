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
