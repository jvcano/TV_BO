@echo off
REM Install dependencies if yt-dlp is missing
where yt-dlp >nul 2>&1
if %errorlevel% neq 0 (
    echo yt-dlp not found. Installing...
    pip install -r requirements.txt
)

REM Pass any arguments through (e.g. --check)
python update_playlist.py %*
pause
