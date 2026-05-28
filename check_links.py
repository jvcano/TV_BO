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
    """Returns True if URL returns a valid HLS manifest (HTTP 200 + #EXTM3U or #EXT-X- marker)."""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
        )
        with urllib.request.urlopen(req, timeout=CHECK_TIMEOUT) as resp:
            if resp.status != 200:
                return False
            chunk = resp.read(512)
            return b'#EXTM3U' in chunk or b'#EXT-X-' in chunk
    except Exception:
        return False


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

    current_urls = M3UUpdater.read_stream_urls(M3U_FILE)
    channel_updates = {}
    dead_channels = []
    ok_channels = []
    skipped_channels = []

    for channel in CHANNELS:
        name = channel["name"]
        print(f"\n{name}  [{channel['extractor']}]")

        current_url = current_urls.get(name)
        if not current_url:
            print("  ✗ No URL found in m3u for this channel — skipping")
            skipped_channels.append(name)
            continue

        display = current_url if len(current_url) <= 70 else current_url[:70] + "..."
        print(f"  Current: {display}")
        print(f"  Testing...", end=" ", flush=True)

        if check_stream_url(current_url):
            print("✓ OK — no update needed")
            ok_channels.append(name)
            continue

        dead_channels.append(name)
        print("✗ dead — fetching replacement")
        new_url = fetch_and_test(channel)

        if new_url:
            channel_updates[name] = new_url
            print(f"  ✓ Replacement ready")
        else:
            print(f"  ✗ All {MAX_RETRIES} attempts failed — leaving as-is for review")

    print("\n" + "-" * 60)

    write_ok = True
    if channel_updates:
        print(f"\nUpdating {len(channel_updates)} channel(s) in {M3U_FILE}...")
        if M3UUpdater.update_m3u_file(M3U_FILE, channel_updates):
            print(f"✓ M3U file updated:")
            for name in channel_updates:
                print(f"  • {name}")
        else:
            print("✗ Failed to write M3U file")
            write_ok = False
    elif not dead_channels:
        print("\nAll links OK. No updates needed.")

    failed_channels = [n for n in dead_channels if n not in channel_updates]
    if failed_channels:
        print(f"\n⚠ {len(failed_channels)} channel(s) still dead — review manually:")
        for name in failed_channels:
            print(f"  • {name}")

    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    refreshed_list = ", ".join(channel_updates.keys()) or "-"
    failed_list = ", ".join(failed_channels) or "-"
    print(
        f"\n[{ts}] RESULT: "
        f"ok={len(ok_channels)} "
        f"dead={len(dead_channels)} "
        f"refreshed={len(channel_updates)} "
        f"failed={len(failed_channels)} "
        f"skipped={len(skipped_channels)} "
        f"| refreshed: {refreshed_list} | failed: {failed_list}"
    )

    return write_ok and not failed_channels


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
