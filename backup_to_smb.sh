#!/bin/bash

# SMB Backup Script
LOG_FILE="/root/TV_BO/logs/smb_backup.log"
SOURCE_FILE="/root/TV_BO/streams/bo.m3u"

{
    echo "$(date '+%a %b %d %I:%M:%S %p %Z %Y'): Starting SMB backup..."
    
    # Use cat to pipe the file content
    cat "$SOURCE_FILE" | smbclient //10.10.10.34/Backup -A ~/.smb_credentials -c "cd playlist; put - bo.m3u"
    
    if [ $? -eq 0 ]; then
        echo "$(date '+%a %b %d %I:%M:%S %p %Z %Y'): Backup completed successfully"
    else
        echo "$(date '+%a %b %d %I:%M:%S %p %Z %Y'): Backup failed"
    fi
} >> "$LOG_FILE" 2>&1
