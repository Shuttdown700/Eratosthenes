
import os, subprocess
os.chdir(os.path.dirname(os.path.abspath(__file__)))

def download_yt_video_playlist(url,output_directory):
    
    os.makedirs(output_directory, exist_ok=True)

    # Change to yt-dlp binary location
    os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin"))

    # Construct the command with properly quoted arguments
    cmd = [
        "yt-dlp",
        "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--embed-thumbnail",
        url,
        "-o", os.path.join(output_directory, "%(title)s.%(ext)s")
    ]

    # Print command for debugging
    print("Running command:", " ".join(f'"{arg}"' if ' ' in arg else arg for arg in cmd))

    # Execute the command
    subprocess.call(cmd)

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
        "--audio-format", "m4a",
        url,
        "-o", os.path.join(output_directory, "%(title)s.%(ext)s")
    ]
    # Print command for debugging
    print("Running command:", " ".join(f'"{arg}"' if ' ' in arg else arg for arg in cmd))

    # Execute the command
    subprocess.call(cmd)

url_playlist = "https://www.youtube.com/watch?v=ZiIjLL9wq4Q&list=PLWVo2tank-zwgDMAZhAp4_pT0NZ6YwVCc&ab_channel=ChildishGambino-Topic"
sub_directory = os.path.join("W:","Temp","YouTube")
download_yt_music_playlist(url_playlist,sub_directory)              