#!/usr/bin/env python3
"""
Audio Track Cleaner (Language & Commentary Stripper)
Refactored for PEP 8 compliance and CLI arguments.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple

from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)


class Config:
    """Configuration settings."""
    # Defaults
    STRIP_FOREIGN = True      # Default: Strip non-English (matches your batch)
    STRIP_COMMENTARY = False  # Default: Keep commentary (unless flag used)
    
    # Target Language (ISO 639-2 code)
    TARGET_LANG = "eng"
    
    # Output folder name
    DIR_OUTPUT_NAME = "Filtered"
    OVERWRITE = False
    
    # Extensions to process
    INPUT_EXTENSIONS = {".mkv", ".mp4"}

    @classmethod
    def update_from_args(cls, args):
        """Update config based on CLI arguments."""
        if args.keep_foreign:
            cls.STRIP_FOREIGN = False
            print(f"{Fore.CYAN}Config: Keeping ALL languages.{Style.RESET_ALL}")
        else:
            print(f"{Fore.CYAN}Config: Stripping non-{cls.TARGET_LANG} audio.{Style.RESET_ALL}")

        if args.strip_commentary:
            cls.STRIP_COMMENTARY = True
            print(f"{Fore.CYAN}Config: Stripping commentary tracks.{Style.RESET_ALL}")


class Paths:
    """System paths for dependencies."""
    BASE_DIR = Path(__file__).resolve().parents[1]
    FFMPEG = BASE_DIR / "bin" / "ffmpeg.exe"
    FFPROBE = BASE_DIR / "bin" / "ffprobe.exe"


def check_dependencies() -> None:
    """Verify that FFmpeg binaries exist."""
    if not Paths.FFMPEG.exists() or not Paths.FFPROBE.exists():
        print(f"{Fore.RED}Error: FFmpeg binaries not found at:{Style.RESET_ALL}")
        print(f"  {Paths.FFMPEG}")
        print(f"  {Paths.FFPROBE}")
        sys.exit(1)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_files_in_dir(source_path: Path) -> List[Path]:
    """Return a sorted list of video files in the directory."""
    return sorted(
        [f for f in source_path.glob("*") 
         if f.suffix.lower() in Config.INPUT_EXTENSIONS]
    )


def probe_file(file_path: Path) -> List[Dict[str, Any]]:
    """Return parsed FFprobe output (streams info)."""
    cmd_probe = [
        str(Paths.FFPROBE), "-v", "error",
        "-show_streams", "-of", "json",
        str(file_path)
    ]
    try:
        output = subprocess.check_output(cmd_probe)
        data = json.loads(output)
        return data.get("streams", [])
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        print(f"{Fore.RED}Failed to probe file: {file_path.name}{Style.RESET_ALL}")
        return []


def is_commentary(stream: Dict) -> bool:
    """Check if an audio stream is a commentary track."""
    # Check 1: Disposition (Standard flag)
    disposition = stream.get("disposition", {})
    if disposition.get("comment") == 1:
        return True

    # Check 2: Title (Heuristic)
    tags = stream.get("tags", {})
    title = tags.get("title", "").lower()
    if "commentary" in title:
        return True
    
    return False


def get_stream_map(streams: List[Dict]) -> Tuple[List[str], int]:
    """
    Analyze streams and return a list of map arguments.
    Returns: (map_args, count_of_kept_audio_streams)
    """
    map_args = []
    audio_kept_count = 0

    for stream in streams:
        index = stream.get("index")
        codec_type = stream.get("codec_type")
        
        # ALWAYS Keep Video
        if codec_type == "video":
            map_args.extend(["-map", f"0:{index}"])
            continue

        # ALWAYS Keep Subtitles
        if codec_type == "subtitle":
            map_args.extend(["-map", f"0:{index}"])
            continue

        # FILTER Audio
        if codec_type == "audio":
            tags = stream.get("tags", {})
            lang = tags.get("language", "und").lower()
            
            # 1. Filter by Language
            if Config.STRIP_FOREIGN and lang != Config.TARGET_LANG:
                continue

            # 2. Filter by Commentary
            if Config.STRIP_COMMENTARY and is_commentary(stream):
                continue
            
            # Keep stream
            map_args.extend(["-map", f"0:{index}"])
            audio_kept_count += 1

    return map_args, audio_kept_count


def print_stats(original_file: Path, encoded_file: Path) -> None:
    """Calculate and print file size differences."""
    try:
        orig_size = original_file.stat().st_size
        enc_size = encoded_file.stat().st_size
    except OSError:
        return

    if orig_size == 0:
        return

    diff = orig_size - enc_size
    reduced = diff > 0
    pct = (abs(diff) / orig_size) * 100

    # Human readable size helper
    def to_mb(b): return b / (1024 * 1024)

    color = Fore.GREEN if reduced else Fore.RED
    status = "reduction" if reduced else "increase"

    print(
        f"  {Fore.YELLOW}Size{Style.RESET_ALL}: "
        f"{to_mb(orig_size):.2f} MB → {to_mb(enc_size):.2f} MB "
        f"({color}{pct:.1f}% {status}{Style.RESET_ALL})"
    )


def process_file(input_path: Path, output_dir: Path) -> None:
    """Process a single file."""
    output_file = output_dir / input_path.name

    if output_file.exists() and not Config.OVERWRITE:
        print(f"{Fore.YELLOW}Skipping (exists){Style.RESET_ALL}: {input_path.name}")
        return

    print(f"{Fore.CYAN}Processing{Style.RESET_ALL}: {input_path.name}")

    streams = probe_file(input_path)
    if not streams:
        return

    map_args, audio_count = get_stream_map(streams)

    if audio_count == 0:
        print(f"{Fore.RED}  [WARNING] Filtering would result in NO AUDIO.{Style.RESET_ALL}")
        print(f"  Skipping file to prevent data loss.")
        return

    # Build Command
    cmd = [
        str(Paths.FFMPEG), "-y", "-v", "error",
        "-i", str(input_path)
    ]
    cmd.extend(map_args)
    cmd.extend(["-c", "copy", str(output_file)])

    try:
        subprocess.run(cmd, check=True)
        print(f"{Fore.GREEN}  [OK] Audio Strip Successful{Style.RESET_ALL}")
        # Print the size stats here
        print_stats(input_path, output_file)
        
    except subprocess.CalledProcessError:
        print(f"{Fore.RED}  [FAIL] FFmpeg Error{Style.RESET_ALL}")
        if output_file.exists():
            try: os.remove(output_file)
            except OSError: pass


def process_directory(source_dir: Path) -> None:
    """Process all files in a directory."""
    if not source_dir.exists():
        print(f"{Fore.RED}Directory not found{Style.RESET_ALL}: {source_dir}")
        return

    files = get_files_in_dir(source_dir)
    if not files:
        # print(f"No MKV/MP4 files found in {source_dir}")
        return

    output_dir = source_dir / Config.DIR_OUTPUT_NAME
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{Fore.BLUE}{Style.BRIGHT}Scanning {len(files)} files in: {source_dir}{Style.RESET_ALL}")

    for f in files:
        process_file(f, output_dir)


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    parser = argparse.ArgumentParser(description="Batch Audio/Subtitle Filter")
    
    # Flags
    parser.add_argument("--keep-foreign", action="store_true", 
                        help="Keep non-English audio tracks (Default is to remove them)")
    parser.add_argument("--strip-commentary", action="store_true", 
                        help="Remove commentary tracks (Default is to keep them)")
    
    parser.add_argument("directories", nargs="*", 
                        help="List of directories to process (Optional)")

    args = parser.parse_args()
    
    Config.update_from_args(args)
    check_dependencies()

    # Define directories here if not passed via CLI
    target_directories = args.directories if args.directories else [
        r"T:\Encoding Zone\02 Ready\The Stand (1994) Season 1 S01 + Extras (1080p BluRay x265 HEVC 10bit AAC 2.0 RCVR)"
    ]

    for d in target_directories:
        process_directory(Path(d))

    print(f"\n{Fore.GREEN}{Style.BRIGHT}Batch processing finished.{Style.RESET_ALL}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Fore.RED}Interrupted by user.{Style.RESET_ALL}")

# python .\src\utils\batch_filter_audio_tracks.py --keep-foreign --strip-commentary