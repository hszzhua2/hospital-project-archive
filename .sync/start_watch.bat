@echo off
chcp 65001 >nul
set "GITDIR=C:\Users\18811\.workbuddy\binaries\PortableGit\versions\1.2.0\mingw64\bin"
set "PYW=C:\Users\18811\.workbuddy\binaries\python\envs\default\Scripts\pythonw.exe"
set "PATH=%GITDIR%;%PATH%"
cd /d "C:\Users\18811\WorkBuddy\2026-09-30-16-56-05"
start "" /min "%PYW%" ".sync\watch_sync.py" --interval 15 --debounce 8
