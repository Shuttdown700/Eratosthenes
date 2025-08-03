#!/usr/bin/env python3

import os
import subprocess
os.chdir(os.path.dirname(os.path.abspath(__file__)))

def download_yt_music_playlist(url, output_directory):
    """
    Downloads a YouTube playlist using yt-dlp.
    
    Parameters:
    - url: The URL of the YouTube playlist.
    - sub_directory: The subdirectory where the downloaded files will be saved.
    """
    #     

    # Ensure the output directory exists
    os.makedirs(output_directory, exist_ok=True)

    # Change to yt-dlp binary location
    os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin"))

    # Construct the command with properly quoted arguments
    cmd = [
        "yt-dlp",
        # "--embed-thumbnail",
        "-f", "bestaudio/best",
        "-ciw",
        "-v",
        # "--no-playlist",
        "--extract-audio",
        "--audio-quality", "0",
        "--audio-format", "mp3",
        url,
        "-o", os.path.join(output_directory, "%(title)s.%(ext)s")
    ]
    # Print command for debugging
    print("Running command:", " ".join(f'"{arg}"' if ' ' in arg else arg for arg in cmd))

    # Execute the command
    subprocess.call(cmd)

if __name__ == "__main__":
    url_playlist = ""
    sub_directory = os.path.join("A:", "Temp", "YouTube", "")
    download_yt_music_playlist(url_playlist, sub_directory)     