# -*- coding: utf-8 -*-
"""
Git push 的兜底通道:走 GitHub REST API(api.github.com)直接建树+提交+更新分支。
用于直连 github.com 被代理拦截(502)时的应急同步。

做法:比较【本地 HEAD 树】与【远端分支树】的差异,只上传差异 blob,
内容与本地仓库对象一致(LFS 文件会正确上传指针文件而非原图)。
用法: python .sync/push_api.py [-m "提交信息"]
"""
import base64, json, pathlib, subprocess, sys, time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from sync import run, log, ROOT, ENV

OWNER = "hszzhua2"
REPO = "hospital-project-archive"
BRANCH = "master"
API = f"/repos/{OWNER}/{REPO}"


def gh(method, endpoint, payload=None, timeout=300):
    cmd = ["gh", "api", "-X", method, endpoint]
    if payload is not None:
        r = subprocess.run(cmd + ["--input", "-"], input=json.dumps(payload, ensure_ascii=False),
                           capture_output=True, text=True, encoding="utf-8", timeout=timeout, env=ENV)
    else:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                           timeout=timeout, env=ENV)
    out = (r.stdout or "").strip()
    if r.returncode != 0:
        raise RuntimeError(f"gh api {endpoint} 失败: {(r.stderr or out)[:300]}")
    return json.loads(out) if out else {}


def local_tree():
    """{path: (mode, blob_sha)} —— 关闭 quotepath,避免中文被转义"""
    code, out = run(["-c", "core.quotepath=false", "ls-tree", "-r", "HEAD"], timeout=300)
    if code != 0:
        raise RuntimeError(out.strip()[:200])
    tree = {}
    for line in out.splitlines():
        if not line.strip():
            continue
        meta, path = line.split("\t", 1)
        mode, typ, sha = meta.split()
        if typ != "blob":
            continue
        tree[path.strip()] = (mode, sha)
    return tree


def remote_tree(sha):
    """{path: blob_sha}"""
    data = gh("GET", f"{API}/git/trees/{sha}?recursive=1")
    out = {}
    for item in data.get("tree", []):
        if item.get("type") == "blob":
            out[item["path"]] = item["sha"]
    return out


def blob_content(sha):
    code, out = run(["cat-file", "blob", sha], timeout=300)
    if code != 0:
        raise RuntimeError(f"读取 blob {sha} 失败")
    # subprocess 文本模式会破坏二进制,改用二进制读取
    r = subprocess.run([__import__("sync").GIT_EXE, "cat-file", "blob", sha],
                       cwd=ROOT, capture_output=True, env=ENV)
    return r.stdout


def main(message=None):
    ref = gh("GET", f"{API}/git/ref/heads/{BRANCH}")
    base_sha = ref["object"]["sha"]
    lt, rt = local_tree(), remote_tree(base_sha)

    adds, dels = [], []
    for path, (mode, sha) in lt.items():
        if rt.get(path) != sha:
            adds.append((path, mode, sha))
    for path in rt:
        if path not in lt:
            dels.append(path)

    if not adds and not dels:
        log("API 通道:本地与远端一致,无需同步")
        return 0

    log(f"API 通道:新增/更新 {len(adds)} 个,删除 {len(dels)} 个")
    entries = []
    for path, mode, sha in adds:
        blob = gh("POST", f"{API}/git/blobs",
                  {"content": base64.b64encode(blob_content(sha)).decode(),
                   "encoding": "base64"})
        entries.append({"path": path, "mode": mode, "type": "blob", "sha": blob["sha"]})
    for path in dels:
        entries.append({"path": path, "mode": "100644", "type": "blob", "sha": None})

    if not message:
        code, logtxt = run(["log", "--format=%s", "-1"], timeout=120)
        message = (logtxt.strip() or "同步更新")[:200]

    tree = gh("POST", f"{API}/git/trees", {"base_tree": base_sha, "tree": entries})
    commit = gh("POST", f"{API}/git/commits",
                {"message": message, "tree": tree["sha"], "parents": [base_sha]})
    gh("PATCH", f"{API}/git/refs/heads/{BRANCH}", {"sha": commit["sha"]})
    log(f"API 推送成功 ↑ {commit['sha'][:8]}")

    # 本地对齐远端(内容一致,仅 SHA 不同)
    run(["update-ref", f"refs/remotes/origin/{BRANCH}", commit["sha"]])
    code, _ = run(["fetch", "origin", BRANCH], timeout=180)
    if code == 0:
        run(["reset", "--soft", commit["sha"]])
        log("本地 HEAD 已对齐远端")
    else:
        log("远端引用已更新(fetch 不可用,本地历史保持独立,后续靠 API 通道同步)")
    return 0


if __name__ == "__main__":
    msg = None
    args = sys.argv[1:]
    if "-m" in args:
        msg = args[args.index("-m") + 1]
    try:
        sys.exit(main(msg))
    except Exception as e:
        log(f"API 推送失败: {e}")
        sys.exit(1)
