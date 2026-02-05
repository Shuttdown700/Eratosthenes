import subprocess
import sys
import shutil
from colorama import Fore, Style, init
from pathlib import Path

# Initialize colorama
init()

# === COLORS ===
C_ERR = Fore.RED + Style.BRIGHT
C_WARN = Fore.YELLOW + Style.BRIGHT
C_OK = Fore.GREEN + Style.BRIGHT
C_INFO = Fore.BLUE + Style.BRIGHT
RESET = Style.RESET_ALL

# ==========================================
# CONFIGURATION
# ==========================================
ROOT_DIRECTORY = Path(r"K:\Temp\ALF Complete Series (S01 - S04) 1080p x264 Phun Psyz")

# 1. Define what you want to create
TARGET_FORMAT = ".mkv"

# 2. Define what files to look for (case insensitive)
if TARGET_FORMAT == ".mkv":
    SOURCE_EXTENSIONS = [".mp4", ".mov", ".avi"]
elif TARGET_FORMAT == ".mp3":
    SOURCE_EXTENSIONS = [".m4a", ".m4b", ".wav", ".flac"]

# 3. Operations
DELETE_ORIGINAL = True
DRY_RUN = False

# ==========================================
# FFMPEG SETUP
# ==========================================
SCRIPT_DIR = Path(__file__).resolve().parent
LOCAL_FFMPEG = SCRIPT_DIR.parent / "bin" / "ffmpeg.exe"

if LOCAL_FFMPEG.exists():
    FFMPEG_BIN = str(LOCAL_FFMPEG)
elif shutil.which("ffmpeg"):
    FFMPEG_BIN = "ffmpeg"
else:
    print(f"{C_ERR}[CRITICAL] FFmpeg not found.{RESET}")
    sys.exit(1)

# ==========================================
# LOGIC
# ==========================================

def get_ffmpeg_args(input_path: Path, target_ext: str) -> list:
    """
    Returns the appropriate FFmpeg arguments based on the target extension.
    Now supports preserving Cover Art for Audio->Audio conversions
    and avoids mapping unsupported Data tracks for Video->Video.
    """
    target_ext = target_ext.lower()
    input_ext = input_path.suffix.lower()

    # Define known video formats
    VIDEO_EXTS = ['.mp4', '.mkv', '.mov', '.avi', '.webm', '.m4v', '.wmv']
    is_video_source = input_ext in VIDEO_EXTS

    # --- LOGIC: VIDEO CONTAINER SWAP (.mkv, .mp4, .mov) ---
    if target_ext in ['.mkv', '.mp4', '.mov', '.avi']:
        return [
            # CHANGED: Use specific maps instead of '-map 0' to avoid copying
            # unsupported data/timecode tracks which cause the "Invalid Argument" error.
            '-map', '0:v',         # Grab all Video streams
            '-map', '0:a',         # Grab all Audio streams
            '-map', '0:s?',        # Grab all Subtitle streams (if they exist)
            
            '-c:v', 'copy',        # Copy Video
            '-c:a', 'copy',        # Copy Audio
            '-c:s', 'srt' if target_ext == '.mkv' else 'mov_text',
            '-y'
        ]

    # --- LOGIC: AUDIO TRANSCODE (.mp3) ---
    elif target_ext == '.mp3':
        args = [
            '-c:a', 'libmp3lame',
            '-q:a', '2',             # VBR Quality ~190kbps
            '-id3v2_version', '3',   # Crucial for Windows Thumbnail compatibility
        ]
        
        if is_video_source:
            args.append('-vn')
        else:
            # If source is audio, attempt to copy attached pictures (Cover Art)
            args.extend(['-map', '0:a', '-map', '0:v?', '-c:v', 'copy'])

        args.append('-y')
        return args

    # --- LOGIC: AUDIO LOSSLESS (.flac) ---
    elif target_ext == '.flac':
        args = [
            '-c:a', 'flac',
            '-compression_level', '5'
        ]

        if is_video_source:
            args.append('-vn')
        else:
            args.extend(['-map', '0:a', '-map', '0:v?', '-c:v', 'copy'])

        args.append('-y')
        return args

    # --- GENERIC FALLBACK ---
    else:
        return ['-vn', '-y'] if is_video_source else ['-y']

def process_file(input_path: Path):
    # Ensure strict lower case comparison for safety
    if input_path.suffix.lower() == TARGET_FORMAT.lower():
        return

    output_path = input_path.with_suffix(TARGET_FORMAT)

    if output_path.exists():
        print(f"{C_WARN}[SKIP]{RESET} Target exists: {output_path.name}")
        return

    if DRY_RUN:
        print(f"{C_WARN}[DRY RUN]{RESET} Convert: {input_path.name} -> {output_path.name}")
        if DELETE_ORIGINAL:
            print(f"{C_WARN}[DRY RUN]{RESET} Delete:  {input_path.name}")
        return

    # Construct Command
    args = get_ffmpeg_args(input_path, TARGET_FORMAT)
    cmd = [FFMPEG_BIN, '-i', str(input_path)] + args + ['-loglevel', 'error', str(output_path)]

    print(f"{C_WARN}[CONVERTING]{RESET} {input_path.name}...")

    try:
        subprocess.run(cmd, check=True)
        print(f"{C_OK}[SUCCESS]{RESET} Created: {output_path.name}")

        if DELETE_ORIGINAL:
            try:
                input_path.unlink()
                print(f"{C_OK}[DELETED]{RESET} Original: {input_path.name}")
            except OSError as e:
                print(f"{C_ERR}[ERROR]{RESET} Could not delete original: {e}")

    except subprocess.CalledProcessError as e:
        print(f"{C_ERR}[FAILURE]{RESET} FFmpeg error on {input_path.name}: {e}")
        if output_path.exists():
            output_path.unlink()

def main():
    print(f"{C_INFO}--- Universal Converter ---{RESET}")
    print(f"Directory:  {ROOT_DIRECTORY}")
    print(f"Target:     {TARGET_FORMAT}")
    print(f"Sources:    {SOURCE_EXTENSIONS}")
    print(f"Delete Org: {DELETE_ORIGINAL}")
    print("---------------------------")

    if not ROOT_DIRECTORY.exists():
        print(f"{C_ERR}[ERROR]{RESET} Directory not found.")
        return

    # Find all matching files recursively
    files_found = []
    for ext in SOURCE_EXTENSIONS:
        # rglob is case-insensitive on Windows, case-sensitive on Linux
        files_found.extend(ROOT_DIRECTORY.rglob(f"*{ext}"))

    # Remove duplicates (in case SOURCE_EXTENSIONS has overlaps) and sort
    files_found = sorted(list(set(files_found)))
    
    # Filter out files that are already the target format (sanity check)
    files_to_process = [f for f in files_found if f.suffix.lower() != TARGET_FORMAT.lower()]

    if not files_to_process:
        print(f"{C_WARN}No matching source files found.{RESET}")
        return

    for file_path in files_to_process:
        process_file(file_path)

    print("---------------------------")
    print(f"{C_OK}Processing complete.{RESET} Processed {len(files_to_process)} files.")

if __name__ == "__main__":
    main()