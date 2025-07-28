import os
import re
import subprocess
from typing import List

# Define path to ffprobe (relative to this script's location)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FFPROBE_PATH = os.path.join(SCRIPT_DIR, "..", "bin", "ffprobe.exe")


def get_video_duration(filepath: str) -> float:
    """Return the duration of a video file in seconds."""
    try:
        result = subprocess.run(
            [
                FFPROBE_PATH, "-v", "error", "-show_entries",
                "format=duration", "-of",
                "default=noprint_wrappers=1:nokey=1", filepath
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        return float(result.stdout.strip())
    except Exception as e:
        print(f"[ERROR] Could not get duration for {filepath}: {e}")
        return 0.0


def get_total_duration(filepaths: List[str], print_bool: bool) -> float:
    """Return total duration of all video files in seconds."""
    total_seconds = 0.0
    for path in filepaths:
        print(f"Getting duration for: {os.path.basename(path)}")
        duration = get_video_duration(path)
        total_seconds += duration
    return total_seconds


def format_duration(seconds: float) -> str:
    """Format seconds into Y years, D days, HH:MM:SS string."""
    seconds = int(seconds)

    years = seconds // (365 * 24 * 3600)
    seconds %= (365 * 24 * 3600)

    days = seconds // (24 * 3600)
    seconds %= (24 * 3600)

    hours = seconds // 3600
    seconds %= 3600

    minutes = seconds // 60
    secs = seconds % 60

    parts = []
    if years:
        parts.append(f"{years} year{'s' if years != 1 else ''}")
    if days:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    parts.append(f"{hours:02}:{minutes:02}:{secs:02}")

    return ', '.join(parts)


def parse_duration(duration_str: str) -> int:
    """
    Parse a duration string like '1 year, 2 days, 03:04:05' into total seconds.
    """
    years = days = hours = minutes = seconds = 0

    # Extract time (HH:MM:SS)
    time_match = re.search(r'(\d{2}):(\d{2}):(\d{2})$', duration_str)
    if time_match:
        hours, minutes, seconds = map(int, time_match.groups())

    # Extract years and days using keywords
    if 'year' in duration_str:
        year_match = re.search(r'(\d+)\s+year', duration_str)
        if year_match:
            years = int(year_match.group(1))

    if 'day' in duration_str:
        day_match = re.search(r'(\d+)\s+day', duration_str)
        if day_match:
            days = int(day_match.group(1))

    total_seconds = (
        years * 365 * 24 * 3600 +
        days * 24 * 3600 +
        hours * 3600 +
        minutes * 60 +
        seconds
    )

    return total_seconds


def sum_durations(duration_strings: list[str]) -> str:
    """
    Takes a list of duration strings and returns the formatted total.
    """
    total_seconds = sum(parse_duration(s) for s in duration_strings)
    return format_duration(total_seconds)



def main(video_filepaths: List[str],print_bool=False) -> None:
    """Main function to calculate and print total video duration."""
    total_seconds = get_total_duration(video_filepaths,print_bool)
    formatted_duration = format_duration(total_seconds)
    if print_bool: print(f"Total Duration: {formatted_duration}")
    return formatted_duration

# Example usage
if __name__ == "__main__":
    video_filepaths = [
        r"G:\Movies\[REC] (2007)\[REC] (2007).mkv"
    ]

    main(video_filepaths)
