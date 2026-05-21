#!/usr/bin/env python3.12
"""
M3U8 Extractor & M3U Playlist Updater
Extracts streaming URLs from various sources and updates M3U playlist files

Usage:
    python3 update_playlist.py
"""

import argparse
import re
import subprocess
import sys
import urllib.request
from pathlib import Path
from datetime import datetime


def git_push(filepath):
    """Commit and push the updated m3u file to GitHub."""
    try:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        subprocess.run(["git", "add", filepath], check=True)
        subprocess.run(["git", "commit", "-m", f"chore: update stream URLs [{ts}]"], check=True)
        subprocess.run(["git", "push"], check=True)
        print("✓ Pushed to GitHub")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Git push failed: {e}")
        return False

# Configuration
# extractor: "unitel" = scrape mdstrm iframe + yt-dlp, "dailymotion" = yt-dlp
CHANNELS = [
    {
        "name":     "Unitel bo",
        "url":      "https://unitel.bo/television/vivo",
        "extractor":"unitel",
        "tvg_id":   "Unitel.bo@Web",
        "tvg_logo": "https://cdn.theorg.com/0f6b491c-9b22-43e4-ae72-d0138aa10870_thumb.jpg",
        "group":    "TV BO",
    },
    {
        "name":     "RedUno  bo",
        "url":      "https://www.dailymotion.com/video/x9n2qyk",
        "extractor":"dailymotion",
        "tvg_id":   "RedUno.bo@Web",
        "tvg_logo": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/27/Uno_logo.svg/200px-Uno_logo.svg.png",
        "group":    "TV BO",
    },
]

M3U_FILE = "streams/bo.m3u"  # Path to your M3U file
TIMEOUT = 30  # Seconds to wait for yt-dlp


UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'


class UnitelExtractor:
    """Extract HLS stream URL from Unitel Bolivia.

    Search order:
      1. Fetch unitel.bo page  → find mdstrm stream ID → yt-dlp on player URL
      2. If yt-dlp fails       → fetch the mdstrm #document and grep for .m3u8
    """

    @staticmethod
    def _fetch(url):
        req = urllib.request.Request(url, headers={'User-Agent': UA})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.read().decode('utf-8', errors='ignore')

    @staticmethod
    def _ytdlp(url):
        try:
            result = subprocess.run(
                ['yt-dlp', '-f', 'best', '-g', '--no-warnings', url],
                capture_output=True, text=True, timeout=TIMEOUT
            )
            if result.returncode == 0:
                return result.stdout.strip()
            print(f"  ✗ yt-dlp: {result.stderr.strip()}")
        except subprocess.TimeoutExpired:
            print("  ✗ yt-dlp timed out")
        except FileNotFoundError:
            print("  ✗ yt-dlp not found — pip install yt-dlp")
        except Exception as e:
            print(f"  ✗ yt-dlp error: {e}")
        return None

    @staticmethod
    def extract_stream_url(page_url, debug=False):
        # ── Search 1: find mdstrm stream ID in the Unitel page ──────────────
        try:
            html = UnitelExtractor._fetch(page_url)
        except Exception as e:
            print(f"  ✗ Could not fetch page: {e}")
            return None

        if debug:
            print(f"\n  [DEBUG] Fetched {len(html)} chars from {page_url}")
            print(f"  [DEBUG] Contains 'mdstrm': {'mdstrm' in html}")
            print(f"  [DEBUG] Contains 'iframe': {'iframe' in html}")
            print(f"  [DEBUG] Contains 'player': {'player' in html.lower()}")
            # Show any line that contains mdstrm
            hits = [l.strip() for l in html.splitlines() if 'mdstrm' in l]
            if hits:
                print(f"  [DEBUG] Lines with 'mdstrm':")
                for h in hits[:5]:
                    print(f"    {h[:200]}")
            else:
                print(f"  [DEBUG] No lines contain 'mdstrm' — page is likely JS-rendered")
                print(f"  [DEBUG] First 500 chars of HTML:")
                print(f"    {html[:500]}")

        match = re.search(r'mdstrm\.com/live-stream/([a-zA-Z0-9]+)', html)
        if not match:
            print("  ✗ No mdstrm.com stream ID found on page")
            return None

        stream_id  = match.group(1)
        player_url = f'https://mdstrm.com/live-stream/{stream_id}'
        print(f"\n  Player: {player_url}")

        # ── yt-dlp on the player URL ─────────────────────────────────────────
        hls = UnitelExtractor._ytdlp(player_url)
        if hls:
            return hls

        # ── Search 2: fetch the mdstrm #document and grep for .m3u8 ─────────
        print("  Trying secondary search inside mdstrm player page...")
        try:
            player_html = UnitelExtractor._fetch(player_url)
            m3u8 = re.search(r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)', player_html)
            if m3u8:
                print("  ✓ Found m3u8 in player page")
                return m3u8.group(1)
            print("  ✗ No .m3u8 found in player page")
        except Exception as e:
            print(f"  ✗ Could not fetch player page: {e}")

        return None


class DailymotionExtractor:
    """Extract M3U8 URLs from Dailymotion videos"""
    
    @staticmethod
    def extract_m3u8_url(dailymotion_url):
        """
        Extract M3U8 streaming URL from Dailymotion video
        
        Args:
            dailymotion_url (str): Full Dailymotion video URL
            
        Returns:
            str: M3U8 URL or None if extraction fails
        """
        
        try:
            command = [
                'yt-dlp',
                '-f', 'best',           # Best quality format
                '-g',                   # Get URL only (don't download)
                '--no-warnings',        # Suppress warnings
                dailymotion_url
            ]
            
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=TIMEOUT
            )
            
            if result.returncode == 0:
                m3u8_url = result.stdout.strip()
                return m3u8_url
            else:
                print(f"  ✗ Error: {result.stderr.strip()}")
                return None
                
        except subprocess.TimeoutExpired:
            print(f"  ✗ Timeout: Extraction took too long ({TIMEOUT}s)")
            return None
        except FileNotFoundError:
            print("  ✗ Error: yt-dlp not found")
            print("    Install with: pip install yt-dlp")
            return None
        except Exception as e:
            print(f"  ✗ Error: {e}")
            return None


class M3UUpdater:
    """Write and update M3U playlist files"""

    @staticmethod
    def read_stream_urls(filepath):
        """Read current stream URL for each channel name from an existing m3u file."""
        urls = {}
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = [l.rstrip('\r\n') for l in f.readlines()]
            for i, line in enumerate(lines):
                if '#EXTINF' in line and ',' in line:
                    name = line.split(',', 1)[1].strip()
                    if i + 1 < len(lines):
                        url = lines[i + 1].strip()
                        if url and not url.startswith('#'):
                            urls[name] = url
        except Exception:
            pass
        return urls

    @staticmethod
    def write_m3u(filepath, channels, url_map):
        """
        Write a clean M3U file from scratch following standard IPTV format:
          #EXTM3U
          [blank]
          #EXTINF:-1 tvg-id="..." tvg-logo="..." group-title="...",Name
          stream-url
          [blank]
          ...
        """
        try:
            with open(filepath, 'w', encoding='utf-8', newline='\n') as f:
                f.write('#EXTM3U\n')
                for ch in channels:
                    url = url_map.get(ch['name'])
                    if not url:
                        continue
                    f.write(
                        f'#EXTINF:-1 '
                        f'tvg-id="{ch["tvg_id"]}" '
                        f'tvg-name="{ch["name"]}" '
                        f'tvg-logo="{ch["tvg_logo"]}" '
                        f'group-title="{ch["group"]}",{ch["name"]}\n'
                    )
                    f.write(f'{url}\n')
            return True
        except Exception as e:
            print(f"Error writing M3U file: {e}")
            return False

    @staticmethod
    def update_m3u_file(m3u_file_path, channel_updates):
        """
        Merge new URLs with existing ones and write a clean file.
        Channels that failed extraction keep their previous URL.
        """
        existing = M3UUpdater.read_stream_urls(m3u_file_path)
        merged   = {**existing, **channel_updates}   # new URLs override old
        return M3UUpdater.write_m3u(m3u_file_path, CHANNELS, merged)


def extract_url(channel, debug=False):
    if channel["extractor"] == "unitel":
        return UnitelExtractor.extract_stream_url(channel["url"], debug=debug)
    elif channel["extractor"] == "dailymotion":
        return DailymotionExtractor.extract_m3u8_url(channel["url"])
    else:
        print(f"  ✗ Unknown extractor: {channel['extractor']}")
        return None


def main():
    parser = argparse.ArgumentParser(description="M3U8 Extractor & Playlist Updater")
    parser.add_argument("--check", action="store_true",
                        help="Extract and print URLs without updating the M3U file")
    parser.add_argument("--debug", action="store_true",
                        help="Print raw HTML diagnostics for failed extractions")
    args = parser.parse_args()

    print("=" * 60)
    print("M3U8 Extractor & Playlist Updater")
    if args.check:
        print("  MODE: check only (no file will be written)")
    print("=" * 60)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    if not args.check and not Path(M3U_FILE).exists():
        print(f"Error: M3U file not found: {M3U_FILE}")
        return False

    print(f"M3U File: {M3U_FILE}")
    print(f"Channels: {len(CHANNELS)}\n")

    print("Extracting URLs...")
    print("-" * 60)

    channel_updates = {}
    success_count = 0

    for channel in CHANNELS:
        name = channel["name"]
        print(f"\n{name}  [{channel['extractor']}]")
        print(f"  Source: {channel['url']}")
        print(f"  Extracting...", end=" ", flush=True)

        url = extract_url(channel, debug=args.debug)

        if url:
            print("✓")
            print(f"  Stream: {url}")
            channel_updates[name] = url
            success_count += 1
        else:
            print("✗")

    print("\n" + "-" * 60)
    print(f"Extracted: {success_count}/{len(CHANNELS)} channels\n")

    if args.check:
        print("Check complete. Run without --check to update the M3U file.")
        return success_count > 0

    if channel_updates:
        print("Updating M3U playlist file...")
        if M3UUpdater.update_m3u_file(M3U_FILE, channel_updates):
            print(f"✓ Successfully updated {M3U_FILE}")
            for name in channel_updates:
                print(f"  • {name}")
            return True
        else:
            print(f"✗ Failed to update {M3U_FILE}")
            return False
    else:
        print("✗ No URLs extracted, M3U file not updated")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)