# -*- coding: utf-8 -*-
import pathlib, sys, time
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import os
os.chdir(ROOT)
from sync import portrait, ahead
from watch_sync import snapshot

for i in range(3):
    sig, items = snapshot()
    print(f"poll{i}: sig={sig} items={len(items)} ahead={ahead()}")
    time.sleep(3)
