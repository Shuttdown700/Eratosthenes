#!/usr/bin/env python3
"""
Video Batch Encoder Script
Refactored for PEP 8 compliance and CLI arguments.
"""

import argparse
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utilities import format_file_size

from colorama import Fore, Style, init

# Initialize colorama for Windows support
init(autoreset=True)


class Config:
    """Configuration settings for the encoding process."""
    # Defaults (can be overridden by CLI args)
    VIDEO_CODEC = "hevc_nvenc"  # Default to GPU
    PRESET = "p6"
    VIDEO_QUALITY = "24"
    TUNE = "hq"
    
    PIX_FMT = "yuv420p"
    RC_MODE = "vbr"
    SPATIAL_AQ = "1"

    # Audio
    AUDIO_CODEC = "aac"
    BITRATE_5_1 = "640k"
    BITRATE_STEREO = "256k"

    # Resolution
    TARGET_WIDTH = 1920
    TARGET_HEIGHT = 1080

    # File Handling
    DIR_OUTPUT_NAME = "Re-Encoded"
    OVERWRITE = False
    INPUT_EXTENSIONS = {".mp4", ".mkv"}

    @classmethod
    def set_encoder(cls, mode: str):
        """Update encoder settings based on mode ('cpu' or 'gpu')."""
        if mode == "cpu":
            cls.VIDEO_CODEC = "libx265"
            cls.PRESET = "medium"
            cls.VIDEO_QUALITY = "20.5"  # CRF for CPU
            cls.TUNE = None
            print(f"{Fore.CYAN}Mode set to CPU (libx265, CRF {cls.VIDEO_QUALITY}){Style.RESET_ALL}")
        else:
            cls.VIDEO_CODEC = "hevc_nvenc"
            cls.PRESET = "p6"
            cls.VIDEO_QUALITY = "26"    # CQ for GPU
            cls.TUNE = "hq"
            print(f"{Fore.CYAN}Mode set to GPU (hevc_nvenc, CQ {cls.VIDEO_QUALITY}){Style.RESET_ALL}")


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


def get_video_resolution(streams: List[Dict]) -> Tuple[Optional[int], Optional[int]]:
    """Return the width and height of the first video stream."""
    video_streams = [s for s in streams if s["codec_type"] == "video"]
    if video_streams:
        v_stream = video_streams[0]
        return v_stream.get("width"), v_stream.get("height")
    return None, None


def determine_audio_settings(streams: List[Dict]) -> Tuple[str, str]:
    """Determine output audio channels and bitrate based on input."""
    audio_streams = [s for s in streams if s["codec_type"] == "audio"]
    
    if audio_streams:
        first_audio = audio_streams[0]
        channels = first_audio.get("channels", 2)
        if channels >= 6:
            return "6", Config.BITRATE_5_1
    
    return "2", Config.BITRATE_STEREO


def determine_subtitle_strategy(streams: List[Dict]) -> str:
    """Determine subtitle codec. Convert 'mov_text' to 'srt'."""
    subtitle_streams = [s for s in streams if s["codec_type"] == "subtitle"]
    target_codec = "copy"

    for sub in subtitle_streams:
        codec = sub.get("codec_name", "unknown")
        if codec == "mov_text":
            target_codec = "srt"

    return target_codec


def print_stream_info(streams: List[Dict]) -> None:
    """Print formatted information about audio and subtitle streams."""
    audio_streams = [s for s in streams if s["codec_type"] == "audio"]
    subtitle_streams = [s for s in streams if s["codec_type"] == "subtitle"]

    for s in audio_streams:
        idx = s.get("index")
        codec = s.get("codec_name", "unknown")
        ch = s.get("channels", "?")
        lang = s.get("tags", {}).get("language", "und")
        title = s.get("tags", {}).get("title", "").split('@')[0]
        print(f"{Fore.BLUE}{Style.BRIGHT}Audio {idx}{Style.RESET_ALL}: "
              f"{codec.upper()}, {ch}ch, lang={lang.upper()}, title={title}")

    for s in subtitle_streams:
        idx = s.get("index")
        codec = s.get("codec_name", "unknown")
        lang = s.get("tags", {}).get("language", "und")
        title = s.get("tags", {}).get("title", "").split('@')[0]
        print(f"{Fore.MAGENTA}{Style.BRIGHT}Subtitle {idx}{Style.RESET_ALL}: "
              f"{codec.upper()}, lang={lang.upper()}, title={title}")


def build_ffmpeg_cmd(input_file: Path, output_file: Path, 
                     audio_channels: str, audio_bitrate: str,
                     input_dims: Tuple[int, int], sub_codec: str, 
                     use_trim: bool = False) -> List[str]:
    """Construct the FFmpeg command list."""
    
    in_w, in_h = input_dims
    vf_filters = []

    # Resolution scaling logic
    if in_w and in_h and (in_w > Config.TARGET_WIDTH or in_h > Config.TARGET_HEIGHT):
        scale_filter = (
            f"scale='if(gt(iw,{Config.TARGET_WIDTH}),{Config.TARGET_WIDTH},-1)':"
            f"'if(gt(ih,{Config.TARGET_HEIGHT}),{Config.TARGET_HEIGHT},-1)':"
            "force_original_aspect_ratio=decrease"
        )
        vf_filters.append(scale_filter)

    cmd = [str(Paths.FFMPEG), "-y", "-err_detect", "ignore_err"]

    if use_trim:
        cmd.extend(['-ss', '0.5'])

    cmd.extend(["-i", str(input_file)])

    # Video Encoder Args
    if Config.VIDEO_CODEC == "hevc_nvenc":
        video_args = [
            "-c:v", "hevc_nvenc",
            "-preset", Config.PRESET,
            "-rc:v", Config.RC_MODE,
            "-cq:v", Config.VIDEO_QUALITY,
            "-spatial-aq", Config.SPATIAL_AQ,
            "-tune", Config.TUNE
        ]
    else:
        video_args = [
            "-c:v", "libx265",
            "-preset", Config.PRESET,
            "-crf", Config.VIDEO_QUALITY
        ]

    if vf_filters:
        video_args.extend(["-vf", ",".join(vf_filters)])

    cmd.extend(video_args)

    # Audio, Subtitle, and Map Args
    cmd.extend([
        '-pix_fmt', Config.PIX_FMT,
        "-c:a", Config.AUDIO_CODEC,
        "-b:a", audio_bitrate,
        "-ac", audio_channels,
        "-map", "0:v?",
        "-map", "0:a?",
        "-map", "0:s?",
        "-c:s", sub_codec,
        str(output_file)
    ])

    return cmd


def print_stats(original_file: Path, encoded_file: Path) -> None:
    """Calculate and print file size differences."""
    try:
        orig_size = original_file.stat().st_size
        enc_size = encoded_file.stat().st_size
    except OSError:
        return

    if orig_size == 0:
        return

    diff = original_file.stat().st_size - encoded_file.stat().st_size
    reduced = diff > 0
    filesize_diff_string = format_file_size(abs(diff))
    pct = (abs(diff) / orig_size) * 100

    color = Fore.GREEN if reduced else Fore.RED
    status = "reduction" if reduced else "increase"

    print(
        f"{Fore.YELLOW}Size{Style.RESET_ALL}: "
        f"{format_file_size(orig_size)} → {format_file_size(enc_size)} "
        f"({color}{pct:.1f}% [{filesize_diff_string}] {status}{Style.RESET_ALL})"
    )


# ============================================================
# PROCESS LOGIC
# ============================================================

def process_single_file(input_path: Path, output_dir: Path) -> None:
    """Analyze and encode a single video file."""
    print(f"\n{Style.BRIGHT}Time{Style.RESET_ALL}: "
          f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{Fore.YELLOW}{Style.BRIGHT}Inspecting{Style.RESET_ALL}: {input_path.name}")

    streams = probe_file(input_path)
    if not streams:
        return

    width, height = get_video_resolution(streams)
    print_stream_info(streams)

    sub_codec = determine_subtitle_strategy(streams)
    a_ch, a_bit = determine_audio_settings(streams)
    print(f"{Fore.YELLOW}Audio Settings{Style.RESET_ALL}: {a_ch} channels @ {a_bit} bitrate")

    output_file = output_dir / (input_path.stem + ".mkv")

    if output_file.exists() and not Config.OVERWRITE:
        print(f"{Fore.YELLOW}Skipping (already exists){Style.RESET_ALL}: {output_file.name}")
        return

    # Attempt 1: Standard Encode
    print(f"{Fore.GREEN}{Style.BRIGHT}Encoding ({Config.VIDEO_CODEC} @ {Config.VIDEO_QUALITY if Config.VIDEO_CODEC == 'libx265' else Config.PRESET}){Style.RESET_ALL}: {output_file.name}")
    
    dims = (width or 0, height or 0)
    cmd = build_ffmpeg_cmd(input_path, output_file, a_ch, a_bit, dims, sub_codec, use_trim=False)
    
    success = False
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        success = True
    except subprocess.CalledProcessError:
        print(f"{Fore.RED}{Style.BRIGHT}[FAIL]{Style.RESET_ALL} Standard encoding failed. Attempting trim fix...")
        if output_file.exists():
            try: os.remove(output_file)
            except OSError: pass

        # Attempt 2: Trimmed Encode
        cmd_trim = build_ffmpeg_cmd(input_path, output_file, a_ch, a_bit, dims, sub_codec, use_trim=True)
        try:
            subprocess.run(cmd_trim, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            success = True
            print(f"{Fore.GREEN}[SUCCESS] Trimmed encoding worked.{Style.RESET_ALL}")
        except subprocess.CalledProcessError as e:
            print(f"{Fore.RED}[FAILURE] Both encoding attempts failed!{Style.RESET_ALL}")
            if output_file.exists():
                try: os.remove(output_file)
                except OSError: pass
            return

    if success:
        print_stats(input_path, output_file)
        print(f"{Style.BRIGHT}Time{Style.RESET_ALL}: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


def process_directory_tree(root_dir_str: str) -> None:
    """Recursively process a directory tree."""
    root = Path(root_dir_str)
    if not root.exists():
        print(f"{Fore.RED}Directory not found{Style.RESET_ALL}: {root_dir_str}")
        return

    dirs_to_process = []
    
    # Walk top-down
    for dir_path in [root] + list(root.rglob("*")):
        if not dir_path.is_dir(): continue
        if dir_path.name == Config.DIR_OUTPUT_NAME: continue
        
        if get_files_in_dir(dir_path):
            dirs_to_process.append(dir_path)

    for source_path in sorted(dirs_to_process):
        output_path = source_path / Config.DIR_OUTPUT_NAME
        output_path.mkdir(parents=True, exist_ok=True)
        
        files = get_files_in_dir(source_path)
        if not files: continue

        print(f"\n{Fore.CYAN}{Style.BRIGHT}>>> Processing Directory: {source_path}{Style.RESET_ALL}")
        
        for video_file in files:
            process_single_file(video_file, output_path)

        print(f"\n{Fore.GREEN}{Style.BRIGHT}Directory finished.{Style.RESET_ALL}")


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    """Main execution point."""
    
    # CLI Argument Parsing
    parser = argparse.ArgumentParser(description="Batch Video Encoder (FFmpeg wrapper)")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--cpu", action="store_true", help="Force CPU encoding (libx265)")
    group.add_argument("--gpu", action="store_true", help="Force GPU encoding (hevc_nvenc)")
    
    # You can also pass directory args here if you want to remove the hardcoded list later
    # parser.add_argument("directories", nargs="*", help="List of directories to process")

    args = parser.parse_args()

    # Determine Encoder Mode
    if args.cpu:
        Config.set_encoder("cpu")
    else:
        # Default is GPU if --cpu is not specified
        Config.set_encoder("gpu")

    check_dependencies()
    
    # Hardcoded target directories (as requested in original script)
    # Could be replaced by args.directories if desired
    target_directories = [
        r"T:\Encoding Zone\02 Ready",
    ]
    
    for d in target_directories:
        process_directory_tree(d)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Fore.RED}Process interrupted by user.{Style.RESET_ALL}")
        sys.exit(0)