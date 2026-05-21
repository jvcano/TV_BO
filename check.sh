#!/bin/bash
set -e

if ! command -v yt-dlp &>/dev/null; then
    echo "yt-dlp not found. Installing..."
    pip install -r requirements.txt
fi

python3 check_links.py "$@"
