#! /usr/bin/env python3

import os
from colorama import init, Fore, Style

# Initialize colorama
init(autoreset=True)

VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv', '.webm', '.mpg', '.mpeg'}

def is_video_file(filename: str) -> bool:
    _, ext = os.path.splitext(filename)
    return ext.lower() in VIDEO_EXTENSIONS

def detect_video_clusters(root_dir: str, threshold: int = 2) -> None:
    """
    Recursively searches subdirectories under root_dir for more than `threshold` video files.
    Prints results using colorama.
    """
    if not os.path.isdir(root_dir):
        print(Fore.RED + f"Provided path '{root_dir}' is not a valid directory.")
        return

    print(Fore.CYAN + f"Scanning '{root_dir}' for directories with more than {threshold} video files...\n")

    for dirpath, dirnames, filenames in os.walk(root_dir):
        video_files = [f for f in filenames if is_video_file(f)]
        if len(video_files) > threshold:
            print(Fore.GREEN + f"[FOUND] {len(video_files)} video files in: {dirpath}")
            for vf in video_files:
                print(Fore.YELLOW + f"  - {vf}")
            print()

    print(Fore.GREEN + "Scan complete.")

# Example usage
if __name__ == "__main__":
    # You can call this function with any path and threshold

    root_dirs = [
        r"R:\Movies",
        r"A:\Anime Movies",
        r"A:\4K Movies"
    ]
    for root_dir in root_dirs:
        print(Fore.MAGENTA + f"Checking directory: {root_dir}")
        detect_video_clusters(root_dir, threshold=2)
