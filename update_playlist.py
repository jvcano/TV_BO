#!/usr/bin/env python3
"""
Dailymotion M3U8 Extractor & M3U Playlist Updater
Extracts streaming URLs from Dailymotion videos and updates M3U playlist files

Usage:
    python3 update_playlist.py
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime

# Configuration
# EDIT THIS SECTION WITH YOUR CHANNELS
CHANNELS = {
    "Unitel bo": "https://unitel.bo/television/vivo",
    "RedUno  bo": "https://www.dailymotion.com/video/x9n2qyk"
}

M3U_FILE = "streams/bo.m3u"  # Path to your M3U file
TIMEOUT = 30  # Seconds to wait for yt-dlp


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


def main():
    """Main execution function"""
    
    print("=" * 60)
    print("Dailymotion M3U8 Extractor & Playlist Updater")
    print("=" * 60)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Check if M3U file exists
    if not Path(M3U_FILE).exists():
        print(f"Error: M3U file not found: {M3U_FILE}")
        print("Please create the M3U file or update M3U_FILE path in script")
        return False
    
    print(f"M3U File: {M3U_FILE}")
    print(f"Channels: {len(CHANNELS)}\n")
    
    # Extract M3U8 URLs for each channel
    print("Extracting M3U8 URLs...")
    print("-" * 60)
    
    channel_updates = {}
    success_count = 0
    
    for channel_name, dailymotion_url in CHANNELS.items():
        print(f"\n{channel_name}")
        print(f"  URL: {dailymotion_url}")
        print(f"  Extracting...", end=" ", flush=True)
        
        m3u8_url = DailymotionExtractor.extract_m3u8_url(dailymotion_url)
        
        if m3u8_url:
            print("✓")
            print(f"  M3U8: {m3u8_url[:80]}..." if len(m3u8_url) > 80 else f"  M3U8: {m3u8_url}")
            channel_updates[channel_name] = m3u8_url
            success_count += 1
        else:
            print("✗")
    
    print("\n" + "-" * 60)
    print(f"Extracted: {success_count}/{len(CHANNELS)} channels\n")
    
    # Update M3U file if we got any URLs
    if channel_updates:
        print("Updating M3U playlist file...")
        if M3UUpdater.update_m3u_file(M3U_FILE, channel_updates):
            print(f"✓ Successfully updated {M3U_FILE}")
            print(f"\nUpdated channels:")
            for channel_name in channel_updates.keys():
                print(f"  • {channel_name}")
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