#!/bin/bash

# Check Links Script Wrapper
LOG_FILE="/root/TV_BO/logs/check.log"

{
    echo "$(date '+%a %b %d %I:%M:%S %p %Z %Y'): Running check_links.py..."
    cd /root/TV_BO
    python3 check_links.py
    
    if [ $? -eq 0 ]; then
        echo "$(date '+%a %b %d %I:%M:%S %p %Z %Y'): check_links.py completed successfully"
    else
        echo "$(date '+%a %b %d %I:%M:%S %p %Z %Y'): check_links.py failed"
    fi
} >> "$LOG_FILE" 2>&1
