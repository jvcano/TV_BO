#!/usr/bin/env python3.12
"""
M3U8 Extractor & M3U Playlist Updater
Extracts streaming URLs from various sources and updates M3U playlist files

Usage:
    python3 update_playlist.py
"""

import argparse
import subprocess
import sys
from pathlib import Path
from datetime import datetime

# Configuration
# extractor "unitel"     → permanent mdstrm HLS URL from stream_url field
# extractor "dailymotion"→ yt-dlp extracts a fresh CDN .m3u8 each run
MDSTRM = "https://mdstrm.com/live-stream-playlist/{}.m3u8"

CHANNELS = [
    {
        "name":       "Unitel bo - Santa Cruz",
        "extractor":  "unitel",
        "stream_url": MDSTRM.format("692b7e7ac84183fcf9e3462d"),
        "tvg_id":     "UnitelSCZ.bo@Web",
        "tvg_logo":   "https://cdn.theorg.com/0f6b491c-9b22-43e4-ae72-d0138aa10870_thumb.jpg",
        "group":      "Unitel BO",
    },
    {
        "name":       "Unitel bo - La Paz",
        "extractor":  "unitel",
        "stream_url": MDSTRM.format("6928b14aaa768aad947bf65d"),
        "tvg_id":     "UnitelLPZ.bo@Web",
        "tvg_logo":   "https://cdn.theorg.com/0f6b491c-9b22-43e4-ae72-d0138aa10870_thumb.jpg",
        "group":      "Unitel BO",
    },
    {
        "name":       "Unitel bo - Cochabamba",
        "extractor":  "unitel",
        "stream_url": MDSTRM.format("691f2aeb5ac95d286c49af8d"),
        "tvg_id":     "UnitelCBBA.bo@Web",
        "tvg_logo":   "https://cdn.theorg.com/0f6b491c-9b22-43e4-ae72-d0138aa10870_thumb.jpg",
        "group":      "Unitel BO",
    },
    {
        "name":       "RedUno  bo",
        "url":        "https://www.dailymotion.com/video/x9n2qyk",
        "extractor":  "dailymotion",
        "tvg_id":     "RedUno.bo@Web",
        "tvg_logo":   "https://upload.wikimedia.org/wikipedia/commons/thumb/2/27/Uno_logo.svg/200px-Uno_logo.svg.png",
        "group":      "TV BO",
    },
    {
        "name":       "RedUno bo - La Paz",
        "url":        "https://www.dailymotion.com/video/xa0fwio",
        "extractor":  "dailymotion",
        "tvg_id":     "RedUnoLaPaz.bo@Web",
        "tvg_logo":   "https://upload.wikimedia.org/wikipedia/commons/thumb/2/27/Uno_logo.svg/200px-Uno_logo.svg.png",
        "group":      "TV BO",
    },
    {
        "name":       "Bolivia tv- La Paz",
        "url":        "https://www.dailymotion.com/video/x9nzqpo",
        "extractor":  "dailymotion",
        "tvg_id":     "BoliviaTV.bo@Web",
        "tvg_logo":   "https://www.boliviatv.bo/principal/images/logos/btv-nuevo.png",
        "group":      "TV BO",
    },
]

M3U_FILE = "streams/bo.m3u"  # Path to your M3U file
TIMEOUT = 30  # Seconds to wait for yt-dlp


class UnitelExtractor:
    """Returns the permanent HLS URL stored in the channel config.

    mdstrm.com exposes /live-stream-playlist/{id}.m3u8 for all hosted channels.
    No signed tokens, no expiry, no yt-dlp needed — URL lives in CHANNELS.
    """

    @staticmethod
    def extract_stream_url(channel):
        return channel["stream_url"]


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


def extract_url(channel):
    if channel["extractor"] == "unitel":
        return UnitelExtractor.extract_stream_url(channel)
    elif channel["extractor"] == "dailymotion":
        return DailymotionExtractor.extract_m3u8_url(channel["url"])
    else:
        print(f"  ✗ Unknown extractor: {channel['extractor']}")
        return None


def main():
    parser = argparse.ArgumentParser(description="M3U8 Extractor & Playlist Updater")
    parser.add_argument("--check", action="store_true",
                        help="Extract and print URLs without updating the M3U file")
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
        source = channel.get('url') or channel.get('stream_url', '')
        print(f"\n{name}  [{channel['extractor']}]")
        print(f"  Source: {source}")
        print(f"  Extracting...", end=" ", flush=True)

        url = extract_url(channel)

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