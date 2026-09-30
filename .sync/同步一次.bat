@echo off
chcp 65001 >nul
set "GITDIR=C:\Users\18811\.workbuddy\binaries\PortableGit\versions\1.2.0\mingw64\bin"
set "PY=C:\Users\18811\.workbuddy\binaries\python\envs\default\Scripts\python.exe"
set "PATH=%GITDIR%;%PATH%"
cd /d "C:\Users\18811\WorkBuddy\2026-09-30-16-56-05"
"%PY%" ".sync\sync.py" %*
echo.
echo 同步完成，按任意键关闭…
pause >nul
