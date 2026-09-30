"""把 _dupes/ 里的图片按原目录恢复回 images/,用于回滚误判的去重结果"""
import shutil, pathlib

ROOT = pathlib.Path(__file__).resolve().parent
IMG = ROOT / "images"
DUP = ROOT / "_dupes"

n = 0
for p in sorted(DUP.glob("*")):
    if p.suffix.lower() not in (".jpg", ".jpeg", ".png", ".gif"):
        continue
    stem = p.stem                      # 形如 01_项目名__05
    if "__" not in stem:
        continue
    proj, name = stem.rsplit("__", 1)
    tgt_dir = IMG / proj
    tgt_dir.mkdir(parents=True, exist_ok=True)
    tgt = tgt_dir / (name + p.suffix)
    k = 1
    while tgt.exists():
        tgt = tgt_dir / f"{name}_{k}{p.suffix}"
        k += 1
    shutil.move(str(p), str(tgt))
    n += 1
print(f"已恢复 {n} 张回 images/")
