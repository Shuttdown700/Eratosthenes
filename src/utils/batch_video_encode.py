#!/usr/bin/env python3
import subprocess
import json
from pathlib import Path

from colorama import Fore, Back, Style

# === COLORS ===
RED = Fore.RED
YELLOW = Fore.YELLOW
GREEN = Fore.GREEN
BLUE = Fore.BLUE
MAGENTA = Fore.MAGENTA
RESET = Style.RESET_ALL
BRIGHT = Style.BRIGHT

# === CONFIGURATION ===
video_codec = "libx265"
video_crf = "20.5"
preset = "medium"

audio_codec = "aac"
bitrate_5_1 = "640k"
bitrate_stereo = "256k"

# *** CONFIGURATION: Set target resolution to 1080p (1920x1080) ***
target_width = 1920
target_height = 1080

overwrite = False

# === FFMPEG/FFPROBE PATHS ===
FFMPEG = Path(__file__).resolve().parents[1] / "bin" / "ffmpeg.exe"
FFPROBE = Path(__file__).resolve().parents[1] / "bin" / "ffprobe.exe"


# ============================================================
# HELPERS
# ============================================================

def gather_files(source_path: Path):
    """Return sorted list of video files in the directory."""
    # Supports .mp4 and .mkv input files
    files = sorted([f for f in source_path.glob("*")
                    if f.suffix.lower() in (".mp4", ".mkv")])
    return files


def probe_streams(file_path: Path):
    """Return parsed FFprobe output (streams info)."""
    cmd_probe = [
        str(FFPROBE), "-v", "error",
        "-show_streams", "-of", "json",
        str(file_path)
    ]
    data = json.loads(subprocess.check_output(cmd_probe))
    streams = data.get("streams", [])
    return streams


def get_video_resolution(streams: list):
    """Return the width and height of the first video stream, or None."""
    video_streams = [s for s in streams if s["codec_type"] == "video"]
    if video_streams:
        v_stream = video_streams[0]
        width = v_stream.get("width")
        height = v_stream.get("height")
        return width, height
    return None, None


def select_audio_settings(audio_streams):
    """Determine output audio channels and bitrate."""
    if audio_streams:
        first_audio = audio_streams[0]
        ch = first_audio.get("channels", 2)
        if ch >= 6:
            return "6", bitrate_5_1
        else:
            return "2", bitrate_stereo
    else:
        return "2", bitrate_stereo


def build_encode_cmd(input_file: Path, output_file: Path, audio_channels: str, audio_bitrate: str,
                     input_width: int, input_height: int):
    """Build ffmpeg command for encoding."""
    vf_filters = []
    
    # *** ADJUSTMENT: Apply scaling filter only if original resolution exceeds target 1080p ***
    if input_width > target_width or input_height > target_height:
        # Robust filter: Prevents upscaling and scales down to fit within 1920x1080
        vf_filters.append(
            f"scale='if(gt(iw,{target_width}),{target_width},-1)':'if(gt(ih,{target_height}),{target_height},-1)':force_original_aspect_ratio=decrease"
        )

    cmd = [
        str(FFMPEG), "-y",
        "-i", str(input_file),

        "-c:v", video_codec,
        "-preset", preset,
        "-crf", str(video_crf),

        "-c:a", audio_codec,
        "-b:a", audio_bitrate,
        "-ac", audio_channels,

        "-map", "0:v?",
        "-map", "0:a?",
        "-map", "0:s?",

        "-c:s", "copy",
        "-movflags", "+faststart",
    ]

    if vf_filters:
        # Insert -vf right after video codec value
        idx = cmd.index("-c:v") + 2
        cmd.insert(idx, "-vf")
        cmd.insert(idx + 1, ",".join(vf_filters))

    cmd.append(str(output_file))
    return cmd


def process_file(f: Path, output_path: Path):
    """Process a single input file."""
    print(f"\n{YELLOW}{BRIGHT}Inspecting{RESET}: {f.name}")

    streams = probe_streams(f)

    # Get video resolution
    in_width, in_height = get_video_resolution(streams)
    print(f"{BLUE}{BRIGHT}Video Resolution{RESET}: {in_width}x{in_height}")

    audio_streams = [s for s in streams if s["codec_type"] == "audio"]
    subtitle_streams = [s for s in streams if s["codec_type"] == "subtitle"]

    # Print audio streams
    for s in audio_streams:
        idx = s.get("index")
        codec = s.get("codec_name", "unknown")
        ch = s.get("channels", "?")
        lang = s.get("tags", {}).get("language", "und")
        title = s.get("tags", {}).get("title", "")
        print(f"{BLUE}{BRIGHT}Audio {idx}{RESET}: {codec.upper()}, {ch}ch, lang={lang.upper()}, title={title.split('@')[0]}")

    # Print subtitle streams
    for s in subtitle_streams:
        idx = s.get("index")
        codec = s.get("codec_name", "unknown")
        lang = s.get("tags", {}).get("language", "und")
        title = s.get("tags", {}).get("title", "")
        print(f"{MAGENTA}{BRIGHT}Subtitle {idx}{RESET}: {codec.upper()}, lang={lang.upper()}, title={title.split('@')[0]}")

    # Audio selection
    audio_channels, audio_bitrate = select_audio_settings(audio_streams)
    print(f"{YELLOW}Selected audio encoding{RESET}: {audio_channels}ch @ {audio_bitrate}")

    # Output file
    # *** ADJUSTMENT: Always output to .mkv container ***
    new_suffix = ".mkv" 

    # Construct the output file path using the original filename stem and the new suffix
    out_file_name = f.stem + new_suffix
    out_file = output_path / out_file_name
    
    if out_file.exists() and not overwrite:
        print(f"{YELLOW}Skipping (already exists){RESET}:", out_file)
        return

    # Build and run command
    print(f"{GREEN}{BRIGHT}Encoding{RESET}: {out_file.name}")
    cmd = build_encode_cmd(f, out_file, audio_channels, audio_bitrate, in_width, in_height)
    
    # Run command and suppress output for clean batch processing
    subprocess.run(cmd, check=True,
                   stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL)
    
    # subprocess.run(cmd, check=True) # For debugging, remove in production

    # Size change
    original_size = f.stat().st_size
    encoded_size = out_file.stat().st_size
    pct = (abs(original_size - encoded_size) / original_size) * 100
    reduced = original_size - encoded_size > 0

    print(
        f"{YELLOW}Size{RESET}: "
        f"{original_size / 1e9:.3f} GB → {encoded_size / 1e9:.3f} GB "
        f"({GREEN if reduced else RED}{pct:.1f}% "
        f"{'reduction' if reduced else 'increase'}{RESET})"
    )


def process_directory(source_path: Path):
    """Process one directory of video files."""
    if not source_path.exists():
        print(f"{RED}Directory not found{RESET}: {source_path}")
        return
    if "Re-Encoded" in source_path.parts:
        print(f"{YELLOW}Skipping (is a Re-Encoded sub-directory){RESET}: {source_path}")
        return
    output_path = source_path / ".." / "Re-Encoded"
    output_path.mkdir(parents=True, exist_ok=True)

    files = gather_files(source_path)
    if not files:
        print(f"{RED}{BRIGHT}No video files found{RESET} in", source_path)
        return

    for f in files:
        process_file(f, output_path)

    print(f"\n{GREEN}{BRIGHT}All files re-encoded to{RESET}: {output_path}")


# ============================================================
# MAIN
# ============================================================

def main(directories: list[str]):
    """Process multiple source directories."""
    for d in directories:
        root = Path(d)
        if not root.exists():
            print(f"{RED}Directory not found{RESET}: {d}")
            continue

        # include the root directory and all subdirectories (recursive)
        dirs_to_check = sorted([root] + [p for p in root.rglob("*") if p.is_dir()])

        for source_path in dirs_to_check:
            # skip output folders to avoid re-processing encoded outputs
            if source_path.name.lower() == "re-encoded":
                continue

            # only process directories that actually contain video files
            if not gather_files(source_path):
                continue

            process_directory(source_path)


if __name__ == "__main__":
    dir_list = [
        r"A:\Temp\Movies\To Re-Encode"
    ]
    main(dir_list)