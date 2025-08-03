#!/usr/bin/env python3

import os
import subprocess
os.chdir(os.path.dirname(os.path.abspath(__file__)))

def download_yt_video_playlist(url,
                               output_directory):
    
    os.makedirs(output_directory, exist_ok=True)

    # Change to yt-dlp binary location
    os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin"))

    # Construct the command with properly quoted arguments
    cmd = [
        "yt-dlp",
        "-vU",
        "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--embed-thumbnail",
        url,
        "-o", os.path.join(output_directory, "%(title)s.%(ext)s"),
         "--cookies-from-browser", "firefox"
    ]

    # Print command for debugging
    print("Running command:", " ".join(f'"{arg}"' if ' ' in arg else arg for arg in cmd))

    # Execute the command
    subprocess.call(cmd)

if __name__ == "__main__":
    url_playlist = "https://www.youtube.com/watch?v=Q0BrP8bqj0c&list=PLH0Szn1yYNecanpQqdixWAm3zHdhY2kPR&ab_channel=BibleProject"
    sub_directory = os.path.join("A:","Temp","YouTube","Bible Project - New Testament")
    download_yt_video_playlist(url_playlist,sub_directory)     