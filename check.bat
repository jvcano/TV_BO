@echo off
where yt-dlp >nul 2>&1
if %errorlevel% neq 0 (
    echo yt-dlp not found. Installing...
    pip install -r requirements.txt
)

python check_links.py %*
pause
