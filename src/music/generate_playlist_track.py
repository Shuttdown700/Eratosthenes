import os
import random
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

# 3. Add utils to sys.path and import custom string generator
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "utils")))
from generate_audio_file_print_string import generate_audio_file_print_string

# 4. Resolve the absolute path to the bin folder (One level up from this script)
BIN_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "bin"))

# 5. INJECT INTO WINDOWS PATH
os.environ["PATH"] += os.pathsep + BIN_DIR

FFMPEG_PATH = os.path.join(BIN_DIR, "ffmpeg.exe")
FFPROBE_PATH = os.path.join(BIN_DIR, "ffprobe.exe")

# 6. Point pydub directly to the executables
AudioSegment.converter = FFMPEG_PATH
AudioSegment.ffprobe = FFPROBE_PATH


def create_continuous_mix(
    playlist_filepath,
    output_dir,
    output_filename="continuous_mix.mp3",
    crossfade_ms=4000,
    overwrite=True,
    randomize=False,
):
    """
    Creates a continuous mix from a list of audio files with crossfading.
    """
    print(f"{Fore.WHITE}=== Starting Playlist Mix Generation ===\n")
    
    # Prepare output paths
    os.makedirs(output_dir, exist_ok=True) 
    final_output_path = os.path.join(output_dir, output_filename)
    
    if os.path.exists(final_output_path):
        if not overwrite:
            print(
                f"{Fore.YELLOW}Mix already exists{Style.RESET_ALL}: {Fore.GREEN}Skipping{Style.RESET_ALL} (overwrite=False): "
                f"{Fore.YELLOW}{output_filename}"
            )
            return
        print(
            f"{Fore.YELLOW}Mix already exists{Style.RESET_ALL}. Preparing to {Fore.RED}overwrite{Style.RESET_ALL}: "
            f"{Fore.CYAN}{output_filename}"
        )

    # Read playlist
    if not os.path.exists(playlist_filepath):
        print(
            f"{Fore.RED}Error{Style.RESET_ALL}: Could not find the playlist file: "
            f"{playlist_filepath}"
        )
        return

    with open(playlist_filepath, "r", encoding="utf-8") as f:
        filepaths = [line.strip() for line in f.readlines() if line.strip()]

    if not filepaths:
        print(f"{Fore.RED}Error{Style.RESET_ALL}: The playlist file is empty.")
        return

    # Randomize the playlist if requested
    if randomize:
        print(f"{Fore.WHITE}\nRandomizing playlist order...")
        random.shuffle(filepaths)

    # Load the first track
    first_track_path = filepaths[0]
    
    if not os.path.exists(first_track_path):
        print(
            f"{Fore.RED}Error{Style.RESET_ALL}: Cannot find the audio file at: "
            f"{first_track_path}"
        )
        return
        
    # Utilize the imported util for metadata printing
    track_print_string = generate_audio_file_print_string(first_track_path)
    print(f"\n{Fore.LIGHTBLUE_EX}Base track{Style.RESET_ALL}: {track_print_string}")

    try:
        combined_audio = AudioSegment.from_file(first_track_path)
    except Exception as e:
        print(f"{Fore.RED}Error loading the first track{Style.RESET_ALL}: {e}")
        return

    # Loop through and crossfade remaining tracks
    for path in filepaths[1:]:
        if not os.path.exists(path):
            print(
                f"{Fore.YELLOW}Warning: File not found. Skipping{Style.RESET_ALL}: "
                f"{os.path.basename(path)}"
            )
            continue
            
        # Utilize the imported util for metadata printing during crossfade loop
        track_print_string = generate_audio_file_print_string(path)
        print(f"{Fore.LIGHTBLUE_EX}Crossfading{Style.RESET_ALL}: {track_print_string}")
        
        try:
            next_track = AudioSegment.from_file(path)
            
            # Ensure crossfade isn't longer than the shortest track
            current_crossfade = min(crossfade_ms, len(combined_audio), len(next_track))
            
            # Append with crossfade
            combined_audio = combined_audio.append(
                next_track, crossfade=current_crossfade
            )
            
        except Exception as e:
            print(
                f"{Fore.RED}Error{Style.RESET_ALL} processing {os.path.basename(path)}: "
                f"{Fore.RED}{e}"
            )

    # Export
    print(
        f"\n{Fore.WHITE}Exporting final mix to: "
        f"{Fore.GREEN}{final_output_path}\n"
    )
    print(f"{Fore.WHITE}This might take a minute depending on playlist length...\n")
    
    try:
        combined_audio.export(final_output_path, format="mp3", bitrate="320k")
        print(f"{Fore.GREEN}{Style.BRIGHT}Export complete! Track saved to{Style.RESET_ALL}: {final_output_path}\n")
    except Exception as e:
        print(f"{Fore.WHITE}Failed to export the mix: {Fore.RED}{e}\n")


if __name__ == "__main__":
    # Define input paths
    INPUT_FOLDER = os.path.join(
        os.path.dirname(__file__), "..", "..", "config", "music_playlist_lists"
    )
    TEXT_FILE_NAME = "test.txt" 
    PLAYLIST_FILE = os.path.join(INPUT_FOLDER, TEXT_FILE_NAME)
    
    # Define output paths
    OUTPUT_DIR = r"W:\Temp\Music" 
    OUTPUT_NAME = "test_mix.mp3"
    
    # Mix settings
    FADE_DURATION = 5000 
    OVERWRITE_EXISTING = True
    RANDOMIZE_PLAYLIST = True 

    create_continuous_mix(
        playlist_filepath=PLAYLIST_FILE, 
        output_dir=OUTPUT_DIR, 
        output_filename=OUTPUT_NAME, 
        crossfade_ms=FADE_DURATION, 
        overwrite=OVERWRITE_EXISTING,
        randomize=RANDOMIZE_PLAYLIST
    )