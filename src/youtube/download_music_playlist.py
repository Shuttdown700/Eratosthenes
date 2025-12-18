#!/usr/bin/env python3

import os
import subprocess
import sys

# --- Configuration ---
# Assuming yt-dlp is in a 'bin' folder next to where this script is running.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Check for .exe extension if on Windows
PATH_TO_YT_DLP = os.path.join(SCRIPT_DIR, "..", "bin", "yt-dlp" + (".exe" if sys.platform.startswith("win") else "")) 

def download_yt_music_playlist(url, output_directory):
    """
    Downloads a YouTube video, playlist, or channel's audio, extracts it, 
    and adds music metadata.
    
    Parameters:
    - url: The URL of the YouTube video, playlist, or channel.
    - output_directory: The base directory where the downloaded files will be saved.
    """
    
    # Ensure the base output directory exists
    os.makedirs(output_directory, exist_ok=True)

    # Output template optimized for both playlists and channels: 
    # {Base Path}/{Uploader/Channel Name}/{Playlist/Upload Index} - {Track Title}.{Extension}
    # For a channel: %(uploader)s will be the channel name.
    # For a playlist: %(playlist)s will be the playlist name.
    output_template = os.path.join(
        output_directory, 
        "%(uploader)s", 
        "%(playlist_index)s%(upload_date>%Y%m%d,)s - %(title)s.%(ext)s"
    )

    cmd = [
        # 1. Use the full path to the binary
        PATH_TO_YT_DLP, 
        
        # 2. General flags (verbose, continue, ignore errors)
        "-v",
        "-ci", 
        
        # 3. Format selection: best audio only
        "-f", "bestaudio/best",
        
        # 4. Audio extraction and conversion
        # FIX: Use M4A. This forces the compatible container for embedding.
        # It ensures the highest quality while avoiding the .webm error.
        "--extract-audio",
        "--audio-format", "m4a", # <--- Changed to M4A for compatibility
        "--audio-quality", "0", 
        
        # 5. Metadata and art 
        "--add-metadata",
        "--embed-thumbnail",
        
        # 6. Cookies for protected content
        "--cookies-from-browser", "firefox",

        # 7. The URL and Output
        url,
        # The output template ensures the file extension is now .m4a
        "-o", os.path.join(
            output_directory, 
            "%(uploader)s", 
            "%(playlist_index)s%(upload_date>%Y%m%d,)s - %(title)s.%(ext)s"
        )
    ]
    
    # Print command for debugging
    print("Running command:", " ".join(f'"{arg}"' if ' ' in arg else arg for arg in cmd))

    # Execute the command
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error executing yt-dlp: {e}")

if __name__ == "__main__":
    # Example Channel URL: Use the @handle for the most reliable method
    url_channel = "https://www.youtube.com/@juliaplaysgroove/videos" 
    
    sub_directory = os.path.join("A:", "Temp", "YouTube", "Music Downloads") 
    
    download_yt_music_playlist(url_channel, sub_directory)