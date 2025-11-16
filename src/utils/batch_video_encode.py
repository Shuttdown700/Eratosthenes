#!/usr/bin/env python3
import subprocess
import json
from pathlib import Path

from colorama import Fore, Back, Style

RED = Fore.RED
YELLOW = Fore.YELLOW
GREEN = Fore.GREEN
BLUE = Fore.BLUE
MAGENTA = Fore.MAGENTA
RESET = Style.RESET_ALL
BRIGHT = Style.BRIGHT

# === CONFIGURATION ===
video_codec = "libx265"         # HEVC
video_crf = "20.5"              # 18–28 typical
preset = "medium"               # ultrafast, veryfast, fast, medium, slow, slower
audio_codec = "aac"             # audio re-encode codec
bitrate_5_1 = "640k"
bitrate_stereo = "256k"
target_width = None             # e.g., 1920 (None keeps source)
target_height = None            # e.g., 1080 (None keeps source)
overwrite = False                # overwrite output files if exist

# === PATHS ===
source_path = Path(r"R:\Temp\To Re-Encode")
output_path = source_path.parent / "Re-Encoded"
output_path.mkdir(parents=True, exist_ok=True)

FFMPEG = Path(__file__).resolve().parents[1] / "bin" / "ffmpeg.exe"
FFPROBE = Path(__file__).resolve().parents[1] / "bin" / "ffprobe.exe"

# === FILE GATHERING ===
files = sorted([f for f in source_path.glob("*") if f.suffix.lower() in (".mp4", ".mkv")])
if not files:
    print("{RED}{BRIGHT}No video files found{RESET} in", source_path)
    exit(1)

# === PROCESS EACH FILE ===
for f in files:
    print(f"\n{YELLOW}{BRIGHT}Inspecting{RESET}: {f.name}")
    cmd_probe = [
        str(FFPROBE), "-v", "error",
        "-show_streams", "-of", "json",
        str(f)
    ]
    data = json.loads(subprocess.check_output(cmd_probe))
    streams = data.get("streams", [])

    audio_streams = [s for s in streams if s["codec_type"] == "audio"]
    subtitle_streams = [s for s in streams if s["codec_type"] == "subtitle"]

    # === PRINT AUDIO STREAM INFO ===
    for s in audio_streams:
        idx = s.get("index")
        codec = s.get("codec_name", "unknown")
        ch = s.get("channels", "?")
        lang = s.get("tags", {}).get("language", "und")
        title = s.get("tags", {}).get("title", "")
        print(f"{BLUE}{BRIGHT}Audio {idx}{RESET}: {codec.upper()}, {ch} channel, lang={lang.upper()}, title={title.split("@")[0]}")

    # === PRINT SUBTITLE INFO ===
    for s in subtitle_streams:
        idx = s.get("index")
        codec = s.get("codec_name", "unknown")
        lang = s.get("tags", {}).get("language", "und")
        title = s.get("tags", {}).get("title", "")
        print(f"{MAGENTA}{BRIGHT}Subtitle {idx}{RESET}: {codec.upper()}, lang={lang.upper()}, title={title.split('@')[0]}")

    # === AUDIO BITRATE DECISION BASED ON FIRST TRACK ===
    if audio_streams:
        first_audio = audio_streams[0]
        ch = first_audio.get("channels", 2)
        if ch >= 6:
            audio_bitrate = bitrate_5_1
            audio_channels = "6"
        else:
            audio_bitrate = bitrate_stereo
            audio_channels = "2"
    else:
        audio_bitrate = bitrate_stereo
        audio_channels = "2"

    print(f"{YELLOW}Selected audio encoding{RESET}: {audio_channels}ch @ {audio_bitrate}")

    # === OUTPUT FILE ===
    out_file = output_path / f.name
    if out_file.exists() and not overwrite:
        print(f"{YELLOW}Skipping (already exists){RESET}:", out_file)
        continue

    # === BUILD SCALE FILTER IF REQUESTED ===
    vf_filters = []
    if target_width and target_height:
        vf_filters.append(
            f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,"
            f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2"
        )

    # === FFMPEG COMMAND ===
    cmd_encode = [
        str(FFMPEG), "-y", "-i", str(f),
        "-c:v", video_codec,
        "-preset", preset,
        "-crf", str(video_crf),
        "-c:a", audio_codec,
        "-b:a", audio_bitrate,
        "-ac", audio_channels,
        "-map", "0",                     # include all streams (audio, subs, metadata)
        "-movflags", "+faststart"
    ]

    if vf_filters:
        cmd_encode.insert(cmd_encode.index("-c:v") + 2, "-vf")
        cmd_encode.insert(cmd_encode.index("-c:v") + 3, ",".join(vf_filters))

    cmd_encode.append(str(out_file))

    print(f"{GREEN}{BRIGHT}Encoding{RESET}: {out_file.name}")

    # === RUN SILENTLY ===
    subprocess.run(cmd_encode, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

print(f"\n{GREEN}{BRIGHT}All files re-encoded to{RESET}: {output_path}")
