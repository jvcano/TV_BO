#!/usr/bin/env python3.12
"""
Stream Link Checker & Auto-Refresher
Tests stream links in bo.m3u. If a link is dead, extracts a fresh one,
tests it, and updates the file. Retries up to MAX_RETRIES times before
leaving the dead link as-is for manual review.

Usage:
    python3 check_links.py
"""

import sys
import time
import urllib.request
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from update_playlist import CHANNELS, M3U_FILE, M3UUpdater, extract_url

MAX_RETRIES = 3
CHECK_TIMEOUT = 10  # seconds for each HTTP check
RETRY_WAIT = 10     # seconds between retry attempts


def check_stream_url(url):
    """Returns True if URL responds with data (HTTP 200 + non-empty body)."""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
        )
        with urllib.request.urlopen(req, timeout=CHECK_TIMEOUT) as resp:
            if resp.status != 200:
                return False
            return len(resp.read(512)) > 0
    except Exception:
        return False


def get_current_url(channel_name):
    """Return the current stream URL for a channel from the m3u file."""
    lines = M3UUpdater.read_m3u(M3U_FILE)
    if not lines:
        return None
    for i, line in enumerate(lines):
        if "#EXTINF" in line and "," in line:
            name = line.split(",", 1)[1].strip()
            if name == channel_name and i + 1 < len(lines):
                url = lines[i + 1].strip()
                if url and not url.startswith("#"):
                    return url
    return None


def fetch_and_test(channel):
    """
    Try to extract a new working URL for the channel.
    Retries up to MAX_RETRIES times. Returns the URL on success, None otherwise.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        print(f"    [{attempt}/{MAX_RETRIES}] Extracting new URL...", end=" ", flush=True)
        new_url = extract_url(channel)

        if not new_url:
            print("extraction failed")
        else:
            print(f"got URL")
            print(f"           {new_url}")
            print(f"           Testing...", end=" ", flush=True)
            if check_stream_url(new_url):
                print("✓ works")
                return new_url
            else:
                print("✗ not responding")

        if attempt < MAX_RETRIES:
            print(f"    Waiting {RETRY_WAIT}s before next attempt...")
            time.sleep(RETRY_WAIT)

    return None


def main():
    print("=" * 60)
    print("Stream Link Checker & Auto-Refresher")
    print("=" * 60)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    if not Path(M3U_FILE).exists():
        print(f"Error: M3U file not found: {M3U_FILE}")
        return False

    channel_updates = {}

    for channel in CHANNELS:
        name = channel["name"]
        print(f"\n{name}  [{channel['extractor']}]")

        current_url = get_current_url(name)
        if not current_url:
            print("  ✗ No URL found in m3u for this channel — skipping")
            continue

        display = current_url if len(current_url) <= 70 else current_url[:70] + "..."
        print(f"  Current: {display}")
        print(f"  Testing...", end=" ", flush=True)

        if check_stream_url(current_url):
            print("✓ OK — no update needed")
            continue

        print("✗ dead — fetching replacement")
        new_url = fetch_and_test(channel)

        if new_url:
            channel_updates[name] = new_url
            print(f"  ✓ Replacement ready")
        else:
            print(f"  ✗ All {MAX_RETRIES} attempts failed — leaving as-is for review")

    print("\n" + "-" * 60)

    if not channel_updates:
        print("\nAll links OK. No updates needed.")
        return True

    print(f"\nUpdating {len(channel_updates)} channel(s) in {M3U_FILE}...")
    if M3UUpdater.update_m3u_file(M3U_FILE, channel_updates):
        print(f"✓ M3U file updated:")
        for name in channel_updates:
            print(f"  • {name}")
        return True
    else:
        print("✗ Failed to write M3U file")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
