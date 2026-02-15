import os
import pathlib
import random
import requests
import re
import sys
import time
from mutagen import File
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, ID3NoHeaderError
from mutagen.flac import FLAC
from colorama import Fore, Style, init

from utilities_music import (
    embed_lyrics,
    is_excluded_title,
    clear_comments,
    has_embedded_plain_lyrics
)

# Initialize Colorama
init(autoreset=True)
RED = Fore.RED
YELLOW = Fore.YELLOW
GREEN = Fore.GREEN
BLUE = Fore.BLUE
MAGENTA = Fore.MAGENTA
RESET = Style.RESET_ALL
BRIGHT = Style.BRIGHT

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MISSING_LOG_PATH = os.path.join(SCRIPT_DIR, "..", "..", "output", "music", "missing_LRCLib_lyrics.txt")
if not os.path.exists(os.path.dirname(MISSING_LOG_PATH)):
    os.makedirs(os.path.dirname(MISSING_LOG_PATH))

def get_lyrics_LRCLib(track_name, artist_name, album_name, duration):
    """
    Fetches lyrics from LRCLib based on track signature.
    Duration must be in seconds and within ±2 seconds of the database record.
    """
    base_url = "https://lrclib.net/api/get"

    params = {
        "track_name": track_name,
        "artist_name": artist_name,
        "album_name": album_name,
        "duration": duration
    }

    try:
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as err:
        # 404 is common if lyrics aren't found; suppress verbose error for it
        if response.status_code != 404:
            return f"HTTP Error: {err}"
        return None
    except Exception as e:
        return f"An error occurred: {e}"


def process_directory(input_dir: str,
                      bypass_existing_synced: bool = True,
                      bypass_existing_plain: bool = True,
                      bypass_logged_missing: bool = True,
                      randomized_list: bool = False,
                      max_lyrics_fetched: int = None):
    """Recursively process MP3 and FLAC files."""

    filepaths = []
    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.lower().endswith((".mp3", ".flac")):
                filepaths.append(os.path.join(root, file))

    logged_missing_set = _load_logged_missing_lyrics() if bypass_logged_missing else None

    num_lyrics_fetched = 0
    if randomized_list:
        random.shuffle(filepaths)
    for idx, filepath in enumerate(filepaths):
        if max_lyrics_fetched and num_lyrics_fetched >= max_lyrics_fetched:
             print(f"{YELLOW}{BRIGHT}\nReached max lyrics fetched limit of {max_lyrics_fetched}, stopping processing.{RESET}")
             break
        print(f"\n{BRIGHT}{GREEN}Processing {idx+1:,}:{RESET} {filepath}")

        # --- Metadata Extraction ---
        try:
            audio = File(filepath)
            # Default to filename if title tag is missing
            filename_stem = pathlib.Path(filepath).stem
            
            title = str(audio.get("TIT2", filename_stem))
            # Mutagen's easy wrapper might return lists; handle raw ID3 vs EasyID3
            if isinstance(title, list):
                title = title[0]
            
            artist = str(audio.get("TPE1", "Unknown Artist"))
            if isinstance(artist, list):
                artist = artist[0]

            album = str(audio.get("TALB", "Unknown Album"))
            if isinstance(album, list):
                album = album[0]

            duration = int(audio.info.length) if audio and audio.info else 0

        except Exception as e:
            print(f"{YELLOW}Metadata read error ({e}), using filename{RESET}")
            title = pathlib.Path(filepath).stem
            artist = "Unknown Artist"
            album = "Unknown Album"
            duration = 0

        print(f"{BLUE}Track:{RESET} {title} | {BLUE}Artist:{RESET} {artist} | "
              f"{BLUE}Album:{RESET} {album} | {BLUE}Duration:{RESET} {duration}s")

        # --- Check Existing Lyrics ---
        
        # Check for sidecar .lrc file or embedded synced lyrics
        has_synced = _has_saved_synced_lyrics(filepath) or _has_embedded_synced_lyrics(filepath)
        has_plain = has_embedded_plain_lyrics(filepath)

        # Excluded titles
        if is_excluded_title(title):
            clear_comments(filepath)
            print(f"{YELLOW}{BRIGHT}Skipping excluded title:{RESET} {title}")
            continue

        # Skip if synced exists (and bypass is on)
        if bypass_existing_synced and has_synced:
            print(f"{YELLOW}{BRIGHT}Synced lyrics exist (file or embedded), skipping:{RESET} {filepath}")
            continue
        
        item_tuple = (artist,album,title)
        if bypass_logged_missing and logged_missing_set and item_tuple in logged_missing_set:
            clear_comments(filepath)
            print(f"{YELLOW}{BRIGHT}Previously logged missing lyrics, skipping fetch and cleared comments:{RESET} {title}")
            continue

        # Skip if plain exists (and bypass is on) - ONLY if we don't care about upgrading to synced
        # Typically, if we want synced, we shouldn't skip just because plain exists.
        # But per your logic:
        if bypass_existing_plain and has_plain and not has_synced:
             print(f"{YELLOW}{BRIGHT}Plain lyrics exist, skipping:{RESET} {filepath}")
             continue

        # Duration validation
        if duration == 0:
            print(f"{YELLOW}{BRIGHT}Duration is 0, skipping fetch for:{RESET} {filepath}")
            continue

        # --- Fetching ---
        
        # If we are here, we are fetching. Clean old junk if we are forcing an update.
        if not has_synced and not has_plain:
            # Only clear if we are starting fresh/empty, or logic dictates
            pass 

        results = get_lyrics_LRCLib(title, artist, album, duration)
        
        if not isinstance(results, dict):
            # Handle error strings or None
            if results is None:
                print(f"{RED}No lyrics found.{RESET}")
                _log_missing_lyrics(title, artist, album)
            else:
                print(f"{RED}{results}{RESET}")
            continue

        lyrics_plain = results.get('plainLyrics')
        lyrics_synced = results.get('syncedLyrics')

        lyrics_to_embed = lyrics_synced if lyrics_synced else lyrics_plain
        
        if lyrics_to_embed:
            if lyrics_synced:
                 print(f"{GREEN}{BRIGHT}Fetched and embedding {YELLOW}synced{GREEN} lyrics{RESET}")
            else:
                 print(f"{GREEN}{BRIGHT}Fetched and embedding {YELLOW}plain{GREEN} lyrics{RESET}")
            
            embed_lyrics(filepath, lyrics_to_embed)
        else:
             print(f"{RED}API returned entry but lyrics fields were empty.{RESET}")
             _log_missing_lyrics(title, artist, album)

        _save_lyrics_in_target_directory(filepath, lyrics_plain, lyrics_synced)

        time.sleep(random.uniform(1, 5))
        num_lyrics_fetched += 1




# -------------------------------
# Helper functions
# -------------------------------

def _has_embedded_synced_lyrics(filepath: str) -> bool:
    """
    Checks if the file has embedded lyrics that contain LRC timestamps.
    """
    # Regex for LRC timestamp: [mm:ss.xx]
    timestamp_pattern = re.compile(r'\[\d{2}:\d{2}\.\d{2}\]')
    
    try:
        if filepath.lower().endswith(".mp3"):
            try:
                audio = MP3(filepath, ID3=ID3)
            except ID3NoHeaderError:
                return False
            
            if not audio.tags:
                return False

            # Check USLT frames for timestamps
            for frame in audio.tags.getall("USLT"):
                if timestamp_pattern.search(str(frame)):
                    return True

        elif filepath.lower().endswith(".flac"):
            audio = FLAC(filepath)
            if "LYRICS" in audio:
                for text in audio["LYRICS"]:
                    if timestamp_pattern.search(text):
                        return True
    except Exception:
        pass
        
    return False


def _has_saved_synced_lyrics(filepath: str) -> bool:
    """Check if a corresponding .lrc file exists."""
    lrc_path = os.path.splitext(filepath)[0] + ".lrc"
    return os.path.exists(lrc_path)


def _log_missing_lyrics(title: str, artist: str, album: str):
    """Log missing tracks to a file."""
    try:
        with open(MISSING_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"{artist} | {album} | {title}\n")
    except Exception as e:
        print(f"{RED}Could not write to log file: {e}{RESET}")


def _save_lyrics_in_target_directory(filepath: str, plain_lyrics: str, synced_lyrics: str):
    """Save plain (.txt) and synced (.lrc) lyrics to the file's directory."""
    if not plain_lyrics and not synced_lyrics:
        return

    try:
        target_dir = os.path.dirname(filepath)
        filename_no_ext = os.path.splitext(os.path.basename(filepath))[0]
        
        # Save Synced (.lrc)
        if synced_lyrics:
            lrc_path = os.path.join(target_dir, f"{filename_no_ext}.lrc")
            with open(lrc_path, "w", encoding="utf-8") as f:
                f.write(synced_lyrics)
            print(f"Saved {MAGENTA}{BRIGHT}.lrc file{RESET} to {os.path.dirname(filepath)}")

        # Save Plain (.txt) - Optional, mostly for backup
        if plain_lyrics and not synced_lyrics:
            txt_path = os.path.join(target_dir, f"{filename_no_ext}.txt")
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(plain_lyrics)
            print(f"Saved {MAGENTA}{BRIGHT}.txt file{RESET} to {os.path.dirname(filepath)}")

    except Exception as e:
        print(f"{RED}Error saving lyrics files for {filepath}: {e}{RESET}")

def _load_logged_missing_lyrics():
    """Load previously logged missing lyrics into a set of tuples."""
    missing_set = set()
    if os.path.exists(MISSING_LOG_PATH):
        try:
            with open(MISSING_LOG_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split(" | ")
                    if len(parts) == 3:
                        artist = parts[0].strip()
                        album = parts[1].strip()
                        title = parts[2].strip()
                        missing_set.add((artist, album, title))
        except Exception as e:
            print(f"{RED}Could not read log file: {e}{RESET}")
    return missing_set


if __name__ == "__main__":
    # Example input directory
    input_dir = r"W:\Music\MP3s_320"
    
    if os.path.exists(input_dir):
        process_directory(
            input_dir,
            bypass_existing_synced=True,
            bypass_existing_plain=False,
            bypass_logged_missing=True,
            randomized_list=False,
            max_lyrics_fetched=20_000
        )
    else:
        print(f"{RED}Directory not found: {input_dir}{RESET}")