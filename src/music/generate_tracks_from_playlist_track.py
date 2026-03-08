import os
import re
import sys
import warnings

from colorama import Fore, Style, init

# 1. Initialize colorama for auto-resetting colors
init(autoreset=True)

# 2. Suppress the false-positive pydub warnings BEFORE importing AudioSegment
warnings.filterwarnings(
    "ignore", category=RuntimeWarning, message="Couldn't find ffmpeg or avconv"
)
warnings.filterwarnings(
    "ignore", category=RuntimeWarning, message="Couldn't find ffprobe or avprobe"
)

from pydub import AudioSegment

# 3. Resolve the absolute path to the bin folder (One level up from this script)
BIN_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "bin"))

# 4. INJECT INTO WINDOWS PATH
os.environ["PATH"] += os.pathsep + BIN_DIR

FFMPEG_PATH = os.path.join(BIN_DIR, "ffmpeg.exe")
FFPROBE_PATH = os.path.join(BIN_DIR, "ffprobe.exe")

# 5. Point pydub directly to the executables
AudioSegment.converter = FFMPEG_PATH
AudioSegment.ffprobe = FFPROBE_PATH


def time_to_ms(time_str):
    """Converts a timestamp string (MM:SS or HH:MM:SS) to milliseconds."""
    parts = time_str.split(':')
    if len(parts) == 2:  # MM:SS
        m, s = parts
        return (int(m) * 60 + int(s)) * 1000
    elif len(parts) == 3:  # HH:MM:SS
        h, m, s = parts
        return (int(h) * 3600 + int(m) * 60 + int(s)) * 1000
    return 0


def sanitize_filename(name):
    """Removes invalid characters from a string to make it safe for a filename."""
    return re.sub(r'[\\/*?:"<>|]', "", name)


def split_playlist(input_filepath, output_dir, breakpoints):
    """
    Splits a single audio file into multiple tracks based on provided breakpoints.
    """
    print(f"{Fore.WHITE}=== Starting Playlist Splitter ===\n")
    
    # Check if input file exists
    if not os.path.exists(input_filepath):
        print(f"{Fore.RED}Error{Style.RESET_ALL}: Could not find the input file at: \n{input_filepath}")
        return

    # Prepare output directory
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"{Fore.CYAN}Loading audio file... this might take a moment depending on size.{Style.RESET_ALL}")
    
    try:
        # Load the large audio file
        full_audio = AudioSegment.from_file(input_filepath)
        total_length_ms = len(full_audio)
        print(f"{Fore.GREEN}Audio loaded successfully! Total length: {total_length_ms / 1000:.2f} seconds.\n")
    except Exception as e:
        print(f"{Fore.RED}Error loading audio{Style.RESET_ALL}: {e}")
        return

    # Process each breakpoint
    for i, (start_time, track_name) in enumerate(breakpoints):
        safe_track_name = sanitize_filename(track_name)
        track_number = i + 1
        output_filename = f"{track_number:02d} - {safe_track_name}.mp3"
        output_filepath = os.path.join(output_dir, output_filename)
        
        start_ms = time_to_ms(start_time)
        
        # Determine end time (either the start of the next track, or the end of the file)
        if i + 1 < len(breakpoints):
            next_start_time = breakpoints[i + 1][0]
            end_ms = time_to_ms(next_start_time)
        else:
            end_ms = total_length_ms
            
        print(f"{Fore.LIGHTBLUE_EX}Cutting Track {track_number}{Style.RESET_ALL}: {track_name} ({start_time} -> {end_ms/1000:.2f}s)")
        
        try:
            # Slice the audio array
            track_audio = full_audio[start_ms:end_ms]
            
            # Export the individual track with metadata tags
            track_audio.export(
                output_filepath, 
                format="mp3", 
                bitrate="320k",
                tags={
                    "title": track_name
                }
            )
            print(f"  {Fore.GREEN}Saved{Style.RESET_ALL}: {output_filename}")
        except Exception as e:
            print(f"  {Fore.RED}Error exporting {track_name}{Style.RESET_ALL}: {e}")

    print(f"\n{Fore.GREEN}{Style.BRIGHT}Splitting complete! All tracks saved to:{Style.RESET_ALL} {output_dir}\n")


if __name__ == "__main__":
    # --- Configuration ---
    
    INPUT_FILE = r"T:\ShuttFlix-Temp\YouTube\Music\INDIE ONLY\NA20260125, - tired of trying to feel something. [indie playlist].m4a"
    OUTPUT_FOLDER = r"T:\ShuttFlix-Temp\Music"
    
    # Format: [("MM:SS" or "HH:MM:SS", "Track Name")]
    # The end time of one track is automatically the start time of the next.
    TRACK_BREAKPOINTS = [
        ("00:00", "And It's Crazy"),
        ("03:58", "1995"),
        ("10:09", "Lease Inside Your Heart"),
        ("16:29", "Text You From The Afterlife"),
        ("21:01", "Keep The Light On")
    ]

    # --- Execution ---
    split_playlist(
        input_filepath=INPUT_FILE,
        output_dir=OUTPUT_FOLDER,
        breakpoints=TRACK_BREAKPOINTS
    )