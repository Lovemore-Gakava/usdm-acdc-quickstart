@echo off
rem Double-click entry for Windows: runs launch.py beside this file with the Python launcher,
rem falling back to python on PATH, and keeps the window open at the end so the report can be read.
setlocal
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 "%~dp0launch.py" %*
) else (
    python "%~dp0launch.py" %*
)
echo.
pause
