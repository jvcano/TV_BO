#!/bin/bash
set -e

# Install dependencies if yt-dlp is missing
if ! command -v yt-dlp &>/dev/null; then
    echo "yt-dlp not found. Installing..."
    pip install -r requirements.txt
fi

# Pass any arguments through (e.g. --check)
python3 update_playlist.py "$@"
