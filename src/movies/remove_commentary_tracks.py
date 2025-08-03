#! /usr/bin/env python3

import os
import subprocess
import sys

from tqdm import tqdm
from typing import List
from colorama import init, Fore, Style

# Initialize Colorama
init(autoreset=True)

BIN_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "bin"))
FFPROBE_BIN = os.path.join(BIN_DIR, "ffprobe.exe")
FFMPEG_BIN = os.path.join(BIN_DIR, "ffmpeg.exe")


def find_mkv_files_with_commentary(root_dir: str) -> List[str]:
    """Recursively find .mkv files with commentary audio tracks."""
    mkv_files_with_commentary = []
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.lower().endswith(".mkv"):
                full_path = os.path.join(dirpath, filename)
                if has_commentary_track(full_path):
                    mkv_files_with_commentary.append(full_path)
    return mkv_files_with_commentary

def has_commentary_track(file_path: str) -> bool:
    """Check if the MKV file has a commentary audio track."""
    try:
        result = subprocess.run(
            [FFPROBE_BIN, "-v", "error", "-show_entries", "stream=index:stream_tags=title", "-of", "csv=p=0", file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",  # 👈 Use this
            errors="replace"   # 👈 Silently replace invalid characters
        )
        if result.stdout is None:
            print(Fore.RED + f"ffprobe failed or returned no output for {file_path}")
            return False

        for line in result.stdout.splitlines():
            if "commentary" in line.lower():
                return True
        return False
    except Exception as e:
        print(Fore.RED + f"Error checking {file_path}: {e}")
        return False

def remove_commentary_track(file_path: str, dry_run: bool = True) -> None:
    """Remove commentary audio track from an MKV file in-place."""
    try:
        # Get stream metadata
        result = subprocess.run(
            [FFPROBE_BIN, "-v", "error", "-show_streams", "-print_format", "json", file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors="replace"
        )

        import json
        streams = json.loads(result.stdout)["streams"]
        non_commentary_maps = []

        for s in streams:
            idx = s.get("index")
            codec_type = s.get("codec_type")
            title = s.get("tags", {}).get("title", "").lower()

            if codec_type == "audio" and "commentary" in title:
                continue  # Skip commentary audio
            non_commentary_maps.extend(["-map", f"0:{idx}"])


        if not non_commentary_maps:
            print(Fore.YELLOW + f"No eligible streams to include for {file_path}")
            return

        temp_file_path = file_path + ".__tmp.mkv"
        cmd = [FFMPEG_BIN, "-i", file_path] + non_commentary_maps + ["-c", "copy", temp_file_path]

        if dry_run:
            print(Fore.CYAN + f"[Dry Run] Would run: {' '.join(cmd)}")
        else:
            print(Fore.GREEN + f"Removing commentary from: {file_path}")
            subprocess.run(cmd, check=True)
            os.replace(temp_file_path, file_path)
            print(Fore.BLUE + f"Updated in-place: {file_path}")

    except Exception as e:
        print(Fore.RED + f"Error processing {file_path}: {e}")


def process_directory(root_dir: str, dry_run: bool = True):
    """Main driver function with progress bar."""
    mkv_files = find_mkv_files_with_commentary(root_dir)
    total = len(mkv_files)
    if total == 0:
        print(Fore.YELLOW + "No .mkv files with commentary found.")
        return

    print(Fore.MAGENTA + f"Processing {total} .mkv files with commentary...\n")

    for mkv_file in tqdm(mkv_files, desc="Removing commentary", unit="file", ncols=80, colour="cyan"):
        tqdm.write(Fore.GREEN + f"Processing: {mkv_file}")
        remove_commentary_track(mkv_file, dry_run=dry_run)

if __name__ == "__main__":
    # Example usage
    root_directory = r"R:\Movies"
    dry_run_mode = True  # Set to False to actually remove commentary tracks
    print(Fore.YELLOW + f"Starting process in {'dry run' if dry_run_mode else 'live mode'}...")
    process_directory(root_directory, dry_run=dry_run_mode)
