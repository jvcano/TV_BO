#!/usr/bin/env python3
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

# Configuration
# extractor: "unitel" = scrape mdstrm iframe, "dailymotion" = yt-dlp
CHANNELS = [
    {"name": "Unitel bo",  "url": "https://unitel.bo/television/vivo",         "extractor": "unitel"},
    {"name": "RedUno  bo", "url": "https://www.dailymotion.com/video/x9n2qyk", "extractor": "dailymotion"},
]

M3U_FILE = "streams/bo.m3u"  # Path to your M3U file
TIMEOUT = 30  # Seconds to wait for yt-dlp


class UnitelExtractor:
    """Extract stream URL from Unitel Bolivia website iframe"""

    @staticmethod
    def extract_stream_url(page_url):
        try:
            req = urllib.request.Request(
                page_url,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            )
            with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
                html = response.read().decode('utf-8', errors='ignore')

            match = re.search(r'<iframe[^>]+src="(https://mdstrm\.com/live-stream/[^"?]+)', html)
            if match:
                return match.group(1)

            print("  ✗ No mdstrm.com iframe found on page")
            return None

        except Exception as e:
            print(f"  ✗ Error: {e}")
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
    """Update M3U playlist files with new URLs"""
    
    @staticmethod
    def read_m3u(filepath):
        """Read M3U file and return lines"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.readlines()
        except FileNotFoundError:
            print(f"Error: M3U file not found: {filepath}")
            return None
        except Exception as e:
            print(f"Error reading M3U file: {e}")
            return None
    
    @staticmethod
    def write_m3u(filepath, lines):
        """Write updated lines to M3U file"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            return True
        except Exception as e:
            print(f"Error writing M3U file: {e}")
            return False
    
    @staticmethod
    def update_m3u_file(m3u_file_path, channel_updates):
        """
        Update M3U file with new URLs
        
        Args:
            m3u_file_path (str): Path to M3U file
            channel_updates (dict): Channel name -> new URL mapping
            
        Returns:
            bool: True if update successful
        """
        
        # Read existing M3U file
        lines = M3UUpdater.read_m3u(m3u_file_path)
        if lines is None:
            return False
        
        # Process lines
        updated_lines = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # Check if this is an EXTINF line (channel info)
            if '#EXTINF' in line:
                updated_lines.append(line)
                
                # Extract channel name from EXTINF line
                # Format: #EXTINF:-1 tvg-logo="..." group-title="...", Channel Name
                if ',' in line:
                    channel_name = line.split(',', 1)[1].strip()
                    
                    # Check if this channel needs updating
                    if channel_name in channel_updates:
                        # Skip the old URL line
                        if i + 1 < len(lines):
                            i += 1
                        
                        # Add new URL
                        new_url = channel_updates[channel_name]
                        updated_lines.append(f"{new_url}\n")
                        i += 1
                        continue
            
            updated_lines.append(line)
            i += 1
        
        # Write updated file
        if M3UUpdater.write_m3u(m3u_file_path, updated_lines):
            return True
        return False


def extract_url(channel):
    if channel["extractor"] == "unitel":
        return UnitelExtractor.extract_stream_url(channel["url"])
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
        print(f"\n{name}  [{channel['extractor']}]")
        print(f"  Source: {channel['url']}")
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