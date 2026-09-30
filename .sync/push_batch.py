# -*- coding: utf-8 -*-
"""
大批量文件分批提交推送。
单次 push 体积过大(数百 MB)会被代理/服务端 408 断开,
这里把待提交文件切成若干批,每批单独 commit + push。
用法: python push_batch.py -m "提交说明" [--batch 30]
"""
import argparse, pathlib, subprocess, sys, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
GIT = r"C:/Users/18811/.workbuddy/binaries/PortableGit/versions/1.2.0/mingw64/bin/git.exe"
if not pathlib.Path(GIT).exists():
    GIT = "git"


def run(args, timeout=1800, quiet=True):
    r = subprocess.run([GIT, "-c", "core.quotepath=false"] + args, cwd=ROOT,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=timeout)
    out = (r.stdout or "") + (r.stderr or "")
    if not quiet:
        print(out[-800:])
    return r.returncode, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-m", default="批量更新")
    ap.add_argument("--batch", type=int, default=25, help="每批项目目录数")
    args = ap.parse_args()

    run(["config", "http.postBuffer", "524288000"])
    # 撤销上一次未推送成功的提交,保留工作区内容
    code, out = run(["log", "--oneline", "-1"])
    head_msg = out.strip()
    run(["reset", "--mixed", "HEAD~1"])

    code, out = run(["status", "--porcelain"])
    pending = [l[3:].strip().strip('"') for l in out.splitlines() if l.strip()]
    if not pending:
        print("无待提交文件")
        return 0
    print(f"待提交 {len(pending)} 个文件: {head_msg}")

    docs_img = sorted({p.split("/")[2] for p in pending
                       if p.startswith("docs/") and p.count("/") >= 3})
    others = [p for p in pending if not p.startswith("docs/images/")
              and not p.startswith("docs/thumbs/")]
    print(f"docs 项目目录 {len(docs_img)} 个,其余文件 {len(others)} 个")

    batches = []
    if others:
        batches.append(("元数据/脚本/档案", others))
    for i in range(0, len(docs_img), args.batch):
        chunk = docs_img[i:i + args.batch]
        files = [p for p in pending
                 if any(f"/{c}/" in p or p.startswith(f"docs/images/{c}/")
                        or p.startswith(f"docs/thumbs/{c}/") for c in chunk)]
        batches.append((f"站点图片 {i+1}-{min(i+args.batch, len(docs_img))}", files))

    for bi, (label, files) in enumerate(batches, 1):
        if not files:
            continue
        idx = ROOT / ".sync" / f"_batch_{bi}.lst"
        idx.write_text("\n".join(files), encoding="utf-8")
        run(["add", "-A", "--", *files])
        code, out = run(["commit", "-m", f"{args.m} [{bi}/{len(batches)}] {label}"])
        if code != 0 and "nothing to commit" in out:
            print(f"  批次 {bi} 无变更,跳过")
            continue
        for attempt in range(3):
            code, out = run(["push"])
            if code == 0:
                print(f"  批次 {bi}/{len(batches)} {label} 推送成功 ({len(files)} 文件)")
                break
            print(f"  批次 {bi} 推送失败({attempt+1}/3): {out.strip()[-160:]}")
            time.sleep(15)
        else:
            print(f"  批次 {bi} 三次失败,中止剩余批次")
            return 1
        idx.unlink(missing_ok=True)
    print("全部分批推送完成")
    return 0


if __name__ == "__main__":
    sys.exit(main())
