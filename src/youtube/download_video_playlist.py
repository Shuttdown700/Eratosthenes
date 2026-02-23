#!/usr/bin/env python3

import os
import subprocess
os.chdir(os.path.dirname(os.path.abspath(__file__)))

PATH_TO_BIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "bin")
PATH_TO_DENO = os.path.join(os.path.expanduser("~"), ".deno", "bin", "deno.exe")
EXT_V = ".mkv"
EXT_A = ".m4a"

def download_yt_video_playlist(url,
                               output_directory):
    
    os.makedirs(output_directory, exist_ok=True)

    # Change to yt-dlp binary location
    os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "bin"))

    # Construct the command with properly quoted arguments
    cmd = [
        "yt-dlp",
        "--sleep-interval", "4",
        "--max-sleep-interval", "10",
        "-vU",
        "-f", 
        # f"bestvideo[ext={EXT_V}][height>=1080]+bestaudio[ext=m4a]/bestvideo[ext={EXT_V}]+bestaudio[ext={EXT_A}]/best",
        "bestvideo+bestaudio/best",
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
    url_playlist = "https://www.youtube.com/watch?v=rO9pOJbvkEA&list=PL8dPuuaLjXtMweg6Yx9MHP01n_yUyaf9H"
    sub_directory = os.path.join("A:","Temp","YouTube","Crash Course - Sex Education")
    download_yt_video_playlist(url_playlist,sub_directory)     