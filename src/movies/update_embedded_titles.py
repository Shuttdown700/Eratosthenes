#!/usr/bin/env python3
import subprocess
import json
from pathlib import Path
from typing import Optional

from colorama import Fore, Back, Style

# === COLORS ===
RED = Fore.RED
BRIGHT_RED = Fore.RED + Style.BRIGHT
YELLOW = Fore.YELLOW
BRIGHT_YELLOW = Fore.YELLOW + Style.BRIGHT
GREEN = Fore.GREEN
BRIGHT_GREEN = Fore.GREEN + Style.BRIGHT
BLUE = Fore.BLUE
MAGENTA = Fore.MAGENTA
BRIGHT_MAGENTA = Fore.MAGENTA + Style.BRIGHT
RESET = Style.RESET_ALL
BRIGHT = Style.BRIGHT

# === Settings ===
TARGET_EXTS = [".mkv", ".mp4"]

# Locate binaries relative to script directory
SCRIPT_DIR = Path(__file__).resolve().parent
FFMPEG = SCRIPT_DIR / "../bin/ffmpeg.exe"
FFPROBE = SCRIPT_DIR / "../bin/ffprobe.exe"
MKVPROPEDIT = SCRIPT_DIR / "../bin/mkvpropedit.exe"


# ---------------------------------------------------------
# Metadata reading
# ---------------------------------------------------------
def get_embedded_title(filepath: Path) -> Optional[str]:
    """Read the embedded title via ffprobe."""
    cmd = [
        str(FFPROBE),
        "-v", "quiet",
        "-print_format", "json",
        "-show_entries", "format_tags=title",
        str(filepath)
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
    except Exception as e:
        print(f"{BRIGHT_RED}ERROR{RESET}: ffprobe failed for {filepath}: {e}")
        return None

    if result.returncode != 0:
        return None

    try:
        data = json.loads(result.stdout)
        return data.get("format", {}).get("tags", {}).get("title")
    except json.JSONDecodeError:
        return None


# ---------------------------------------------------------
# MKV metadata writing (fast, no rewrite)
# ---------------------------------------------------------
def set_title_mkv(filepath: Path, title: str, silent: bool) -> bool:
    """Set title for MKV using mkvpropedit (no remux)."""
    cmd = [
        str(MKVPROPEDIT),
        str(filepath),
        "--edit", "info",
        "--set", f"title={title}"
    ]

    try:
        subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.DEVNULL if silent else None,
            stderr=subprocess.DEVNULL if silent else None,
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"{BRIGHT_RED}ERROR{RESET}: mkvpropedit failed on {filepath}: {e}")
        return False


# ---------------------------------------------------------
# MP4 metadata writing (ffmpeg, requires remux)
# ---------------------------------------------------------
def set_title_mp4(filepath: Path, title: str, silent: bool) -> bool:
    tmp = filepath.with_suffix(filepath.suffix + ".tmp")

    cmd = [
        str(FFMPEG),
        "-i", str(filepath),
        "-metadata", f"title={title}",
        "-codec", "copy",
        str(tmp)
    ]

    try:
        subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.DEVNULL if silent else None,
            stderr=subprocess.DEVNULL if silent else None,
        )
        tmp.replace(filepath)
        return True
    except subprocess.CalledProcessError as e:
        print(f"{BRIGHT_RED}ERROR{RESET}: ffmpeg failed on {filepath}: {e}")
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        return False


# ---------------------------------------------------------
# Main logic
# ---------------------------------------------------------
def sync_titles(
    directories: list[str | Path],
    dry_run: bool,
    silent: bool
) -> None:

    for directory in directories:
        root = Path(directory)

        if not root.exists():
            print(f"{YELLOW}Skipping non-existent directory{RESET}: {root}")
            continue

        for file in root.rglob("*"):
            if not file.is_file():
                continue

            ext = file.suffix.lower()
            if ext not in TARGET_EXTS:
                continue

            expected_title = file.stem
            current_title = get_embedded_title(file)

            # Already correct → skip
            if current_title == expected_title:
                # print(f"{YELLOW}OK{RESET}: {file.name} (title already correct)")
                continue

            # Not correct → update
            print(f"{BRIGHT_YELLOW}Needs update{RESET}: {file.name}")
            # print(f"  current: {current_title!r}")
            # print(f"  expected: {expected_title!r}")

            if dry_run:
                print(f"{BRIGHT_MAGENTA}[DRY RUN]{RESET} Would update title for {file}")
                continue

            # Choose correct writer
            if ext == ".mkv":
                success = set_title_mkv(file, expected_title, silent)
            else:
                success = set_title_mp4(file, expected_title, silent)

            if success:
                print(f"{BRIGHT_GREEN}Updated{RESET}: {file}")
            else:
                print(f"{BRIGHT_RED}FAILED to update{RESET}: {file}")


# ---------------------------------------------------------
def main():
    dirs_to_scan = [
        r"R:\Movies\3 Women (1977)"
    ]

    sync_titles(
        directories=dirs_to_scan,
        dry_run=False,
        silent=True
    )


if __name__ == "__main__":
    main()
