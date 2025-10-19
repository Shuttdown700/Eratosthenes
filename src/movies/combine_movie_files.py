import subprocess
import json
from pathlib import Path

# === CONFIGURATION ===
target_width = 1920
target_height = 1080
video_codec = "libx265"
video_crf = "20.5"          # lower = higher quality (typical: 18–28)
audio_codec = "aac"
audio_bitrate = "256k"
audio_channels = "2"
preset = "medium"         # can be ultrafast, veryfast, fast, medium, slow, slower
source_path = Path("R:\Movies\Hitler - A Film From Germany (1977)")
output_path = Path("R:\Temp")
output_name = "Hitler - A Film from Germany (1977).mkv"
filename_concat_list = "concat_list.txt"
filepath_concat_list = Path(output_path / filename_concat_list)
FFMPEG = Path(__file__).resolve().parents[1] / "bin" / "ffmpeg.exe"
FFPROBE = Path(__file__).resolve().parents[1] / "bin" / "ffprobe.exe"

# === STEP 1: INSPECT EACH PART ===
print("\nChecking source dimensions...\n")
files = sorted(source_path.glob("*- pt*.mkv"))

for f in files:
    cmd = [
        str(FFPROBE), "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,codec_name",
        "-of", "json", str(f)
    ]
    data = json.loads(subprocess.check_output(cmd))
    s = data["streams"][0]
    print(f"{f.name}: {s['codec_name']} {s['width']}x{s['height']}")

# === STEP 2: NORMALIZE AND RE-ENCODE ===
print("\nRe-encoding all parts to match target specs...\n")
fixed_files = []

for f in files:
    out = f.with_stem(f.stem + "_fixed")
    fixed_files.append(out)

    cmd = [
        str(FFMPEG), "-y", "-i", str(f),
        "-vf", f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,"
               f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2",
        "-c:v", video_codec, "-preset", preset, "-crf", video_crf,
        "-c:a", audio_codec, "-b:a", audio_bitrate, "-ac", audio_channels,
        "-movflags", "+faststart",
        str(out)
    ]

    print(f"Encoding {f.name} → {out.name}")
    subprocess.run(cmd, check=True)

# === STEP 3: CONCATENATE ALL FIXED FILES ===
print("\nConcatenating all fixed parts...\n")
with open(filename_concat_list, "w") as f:
    for file in fixed_files:
        f.write(f"file '{file.resolve()}'\n")

subprocess.run([
    str(FFMPEG), "-y", "-f", "concat", "-safe", "0",
    "-i", filepath_concat_list, "-c", "copy", str(output_path / output_name)
], check=True)

print(f"\nDone! Output saved as: {str(output_path / output_name)}")
