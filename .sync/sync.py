# -*- coding: utf-8 -*-
"""
档案库 -> GitHub 同步脚本
- 检测到变更: git add -A -> 自动生成提交信息 -> pull --rebase(可选) -> push
- 无变更则跳过
用法:
    python .sync/sync.py                 # 自动提交信息
    python .sync/sync.py -m "手动说明"    # 自定义信息
    python .sync/sync.py --dry-run       # 只看将要提交什么
"""
import argparse, os, pathlib, subprocess, sys, time, datetime, shutil

ROOT = pathlib.Path(__file__).resolve().parent.parent
LOG = ROOT / ".sync" / "sync.log"
LOCK = ROOT / ".sync" / ".lock"

# 后台进程常常拿不到用户 PATH,这里硬解析 git 可执行文件
_GIT_CANDIDATES = [
    r"C:\Users\18811\.workbuddy\binaries\PortableGit\versions\1.2.0\mingw64\bin\git.exe",
    r"C:\Program Files\Git\cmd\git.exe",
    r"C:\Program Files\Git\bin\git.exe",
]


def _find_git():
    g = shutil.which("git")
    if g:
        return g
    for p in _GIT_CANDIDATES:
        if pathlib.Path(p).exists():
            return p
    return "git"


GIT_EXE = _find_git()
GIT = [GIT_EXE]
ENV = os.environ.copy()
ENV["PATH"] = str(pathlib.Path(GIT_EXE).parent) + os.pathsep + ENV.get("PATH", "")
for _k in ("GIT_TERMINAL_PROMPT",):
    ENV[_k] = "0"


def log(msg):
    line = f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def run(args, timeout=600):
    r = subprocess.run(GIT + args, cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=timeout, env=ENV)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def verify():
    """自检:git 可用 / 有远端 / 凭据可推送"""
    code, out = run(["--version"])
    if code != 0:
        return False, f"git 不可用: {out.strip()[:120]}"
    code, out = run(["remote", "get-url", "origin"])
    if code != 0:
        return False, "未配置远端 origin"
    remote = out.strip()
    code, out = run(["ls-remote", "--heads", "origin"], timeout=120)
    if code != 0:
        return False, f"无法访问远端({remote}),请检查 GitHub 登录: {out.strip()[:160]}"
    return True, remote


def portrait():
    """返回 (变更文件列表, 分类计数)"""
    code, out = run(["status", "--porcelain"])
    if code != 0:
        return [], {}
    items = []
    for line in out.splitlines():
        if not line.strip():
            continue
        xy = line[:2].strip()
        path = line[3:].strip().strip('"')
        items.append((xy, path))
    return items, {}


def summarize(items):
    add = mod = dele = 0
    imgs = 0
    dirs = {}
    for xy, path in items:
        p = pathlib.PurePosixPath(path.replace("\\", "/"))
        top = p.parts[0] if p.parts else path
        dirs[top] = dirs.get(top, 0) + 1
        if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".gif"):
            imgs += 1
        if "A" in xy or "?" in xy:
            add += 1
        elif "D" in xy:
            dele += 1
        else:
            mod += 1
    parts = []
    if imgs:
        parts.append(f"图片 {imgs} 张")
    if add - imgs > 0:
        parts.append(f"新增 {add - imgs} 个文件")
    if mod:
        parts.append(f"修改 {mod}")
    if dele:
        parts.append(f"删除 {dele}")
    tops = "、".join(sorted(dirs, key=lambda k: -dirs[k])[:2])
    return f"{tops}: " + "，".join(parts) if parts else "更新", imgs


def ahead():
    """本地领先远端的提交数"""
    code, out = run(["rev-list", "--count", "@{u}..HEAD"])
    if code != 0:
        return 0
    try:
        return int(out.strip().splitlines()[0])
    except Exception:
        return 0


def sync(msg=None, dry=False, pull=True, retries=3):
    items, _ = portrait()
    pending = ahead()
    if not items and pending == 0:
        log("无变更，跳过")
        return 0
    if not items:
        log(f"本地领先远端 {pending} 个提交，直接推送")
    summary, imgs = summarize(items)
    message = msg or f"自动同步 {datetime.datetime.now():%Y-%m-%d %H:%M} · {summary}"
    if dry:
        log(f"[dry-run] 将提交 {len(items)} 项: {summary}")
        for xy, p in items[:20]:
            log(f"    {xy} {p}")
        return 0

    if items:
        run(["add", "-A"])
        code, out = run(["commit", "-m", message])
        if code != 0 and "nothing to commit" not in out:
            log(f"提交失败: {out.strip()[:200]}")
            return 1
        log(f"已提交: {message} ({len(items)} 项)")

    if pull:
        code, out = run(["pull", "--rebase", "--autostash", "--no-tags"])
        if code != 0:
            log(f"pull 失败(继续尝试 push): {out.strip()[:200]}")
            run(["rebase", "--abort"])

    for i in range(retries):
        code, out = run(["push"], timeout=1200)
        if code == 0:
            log("推送成功 ↑")
            return 0
        log(f"推送失败({i+1}/{retries}): {out.strip()[:200]}")
        time.sleep(5 * (i + 1))
    return 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-m", "--message", default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-pull", action="store_true")
    ap.add_argument("--check", action="store_true", help="自检 git/远端/凭据")
    args = ap.parse_args()

    if args.check:
        ok, info = verify()
        log(("自检通过 · 远端 " + info) if ok else ("自检失败 · " + info))
        return 0 if ok else 1

    if LOCK.exists():
        try:
            age = time.time() - LOCK.stat().st_mtime
            if age < 900:
                log(f"已有同步进程运行中(锁 {int(age)}s)，跳过")
                return 0
        except Exception:
            pass
    LOCK.parent.mkdir(exist_ok=True)
    LOCK.write_text(str(os.getpid()), encoding="utf-8")
    try:
        return sync(args.message, args.dry_run, pull=not args.no_pull)
    finally:
        try:
            LOCK.unlink()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
