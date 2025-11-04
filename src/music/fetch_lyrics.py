import os
import difflib
import pathlib
import lyricsgenius
from mutagen import File
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, USLT, COMM
from mutagen.flac import FLAC
from colorama import init, Fore, Style

import sys
import random
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utilities import read_json  # Adjust if needed

# -------------------------------
# Setup colors
# -------------------------------
init(autoreset=True)
RED, YELLOW, GREEN, BLUE, MAGENTA, RESET, BRIGHT = (
    Fore.RED, Fore.YELLOW, Fore.GREEN, Fore.BLUE, Fore.MAGENTA, Style.RESET_ALL, Style.BRIGHT
)

# -------------------------------
# Global config
# -------------------------------
EXCLUDED_TERMS = ["(Remix)", "(Live)", "(Skit)", "(Instrumental)", "(Remaster)"]
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "output", "music"))
MIN_LYRICS_LENGTH = 50                # Minimum characters for valid lyrics
RECHECK_EXISTING = False              # True to re-fetch even if lyrics exist
VOID_LYRIC_STRINGS = ["www.", ".com", "http://", "https://", 
                      "lyrics powered by", "PMEDIA","Downloaded from"]

# -------------------------------
# Genius API setup
# -------------------------------
BASE_DIR = pathlib.Path(__file__).resolve().parent
config_path = BASE_DIR.parent.parent / "config" / "api.config"
api_config = read_json(config_path)
GENIUS_ACCESS_TOKEN = api_config["genius"]["access_token"]

genius = lyricsgenius.Genius(
    GENIUS_ACCESS_TOKEN,
    skip_non_songs=True,
    excluded_terms=EXCLUDED_TERMS,
    remove_section_headers=True,
    verbose=False,
    timeout=15,
)

# -------------------------------
# Fetch lyrics
# -------------------------------
def fetch_official_lyrics(title: str, artist: str, album: str, genius: lyricsgenius.Genius) -> str:
    """Fetch lyrics from Genius API."""
    query = f"{title} {artist} {album}"
    print(f"{BLUE}{BRIGHT}Searching Genius for:{RESET} {title} by {artist} from {album}{RESET}")

    try:
        song = genius.search_song(title, artist)
        if not song:
            results = genius.search_songs(query)
            best_match = None
            best_score = 0.0
            for hit in results.get("hits", []):
                song_info = hit.get("result", {})
                song_title = song_info.get("title", "").lower()
                song_artist = song_info.get("primary_artist", {}).get("name", "").lower()
                title_score = difflib.SequenceMatcher(None, title.lower(), song_title).ratio()
                artist_score = difflib.SequenceMatcher(None, artist.lower(), song_artist).ratio()
                total_score = 0.6 * title_score + 0.4 * artist_score
                if total_score > best_score and total_score > 0.7:
                    best_match = song_info.get("id")
                    best_score = total_score
            if best_match:
                song = genius.get_song(best_match)
                lyrics = song["song"]["lyrics"] if "song" in song else None
            else:
                lyrics = None
        else:
            lyrics = song.lyrics

        if lyrics:
            lyrics = "\n".join(
                line.strip()
                for line in lyrics.split("\n")
                if line.strip() and not line.startswith("[")
            )
            if len(lyrics) < MIN_LYRICS_LENGTH:
                return ""
            print(f"{GREEN}{BRIGHT}Fetched official lyrics for:{RESET} {title}")
            return lyrics

    except Exception as e:
        print(f"{RED}Error fetching lyrics:{RESET} {e}")
        return None  # <-- distinguish errors from "no lyrics found"

    return ""

# -------------------------------
# Helper functions
# -------------------------------
def is_excluded_title(title: str) -> bool:
    """Return True if the song title contains any excluded term."""
    for term in EXCLUDED_TERMS:
        if term.lower() in title.lower():
            return True
    return False

def has_embedded_lyrics(filepath: str) -> bool:
    """Return True if the file already contains valid lyrics of sufficient length,
    and does NOT contain known void strings (like 'www.' or 'PMEDIA')."""
    try:
        if filepath.lower().endswith(".mp3"):
            audio = MP3(filepath, ID3=ID3)
            if not audio.tags:
                return False

            # Combine all lyric and comment frames
            frames = audio.tags.getall("USLT") + audio.tags.getall("COMM")
            for frame in frames:
                texts = frame.text
                if isinstance(texts, list):
                    for text in texts:
                        if _is_valid_lyric_text(text):
                            return True
                elif isinstance(texts, str) and _is_valid_lyric_text(texts):
                    return True

        elif filepath.lower().endswith(".flac"):
            audio = FLAC(filepath)
            for tag in ["LYRICS", "COMMENT"]:
                if tag in audio:
                    for item in audio[tag]:
                        if _is_valid_lyric_text(item):
                            return True

    except Exception as e:
        print(f"{YELLOW}Error checking lyrics for {filepath}: {e}{RESET}")

    return False

def _is_valid_lyric_text(text: str) -> bool:
    """Helper: check if text is long enough and not containing void strings."""
    if not text:
        return False
    stripped = text.strip()
    if any(void_str.lower() in stripped.lower() for void_str in VOID_LYRIC_STRINGS):
        return False
    return len(stripped) >= MIN_LYRICS_LENGTH


def load_missing_lyrics_log():
    """Load previously logged missing lyrics into a set of tuples."""
    missing_set = set()
    log_file = os.path.join(OUTPUT_DIR, "no_lyrics.txt")
    if os.path.exists(log_file):
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split(" | ")
                if len(parts) == 3:
                    missing_set.add((parts[0], parts[1], parts[2]))
    return missing_set


def log_missing_lyrics(title: str, artist: str, album: str):
    """Log songs that do not have official lyrics."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    log_file = os.path.join(OUTPUT_DIR, "no_lyrics.txt")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"{title} | {artist} | {album}\n")
    print(f"{YELLOW}{BRIGHT}Logged missing lyrics for:{RESET} {title}")


def clear_comments(filepath: str):
    """Remove comment, lyrics, and subtitle frames/tags from MP3 and FLAC files."""
    try:
        if filepath.lower().endswith(".mp3"):
            audio = MP3(filepath, ID3=ID3)
            if audio.tags is None:
                return
            removed = False

            # Remove comment frames
            if audio.tags.getall("COMM"):
                audio.tags.delall("COMM")
                removed = True

            # Remove unsynchronized lyrics/subtitle frames
            if audio.tags.getall("USLT"):
                audio.tags.delall("USLT")
                removed = True

            if removed:
                audio.save(v2_version=3)
                print(f"{YELLOW}{BRIGHT}Cleared COMM and USLT frames for:{RESET} {filepath}")

        elif filepath.lower().endswith(".flac"):
            audio = FLAC(filepath)
            removed = False

            # Remove standard tags
            for tag in ["COMMENT", "LYRICS", "SUBTITLE"]:
                if tag in audio:
                    del audio[tag]
                    removed = True

            if removed:
                audio.save()
                print(f"{YELLOW}{BRIGHT}Cleared COMMENT, LYRICS, and SUBTITLE tags for:{RESET} {filepath}")

    except Exception as e:
        print(f"{RED}Error clearing comments for {filepath}: {e}{RESET}")


# -------------------------------
# Embed lyrics
# -------------------------------
def embed_lyrics(filepath: str, lyrics: str):
    """Embed lyrics into MP3/FLAC metadata."""
    if not lyrics:
        print(f"{YELLOW}No lyrics to embed for {filepath}{RESET}")
        return

    try:
        if filepath.lower().endswith(".mp3"):
            audio = MP3(filepath, ID3=ID3)
            if audio.tags is None:
                audio.add_tags()
            audio.tags.delall("USLT")
            audio.tags.delall("COMM")
            audio.tags.add(USLT(encoding=3, lang="eng", desc="", text=lyrics))
            audio.tags.add(COMM(encoding=3, lang="eng", desc="Lyrics", text=lyrics))
            audio.save(v2_version=3)
            print(f"{MAGENTA}{BRIGHT}Lyrics embedded{RESET} into MP3 metadata for {filepath}")

        elif filepath.lower().endswith(".flac"):
            audio = FLAC(filepath)
            audio["LYRICS"] = lyrics
            audio["COMMENT"] = lyrics
            audio.save()
            print(f"{GREEN}{BRIGHT}Lyrics embedded{RESET} into FLAC metadata for {filepath}")

    except Exception as e:
        print(f"{RED}Error embedding lyrics into {filepath}: {e}{RESET}")


# -------------------------------
# Process directory
# -------------------------------
def process_directory(input_dir: str,
                      bypass_existing: bool = True, 
                      save_to_file: bool = False,
                      missing_lyrics_set: set = None):
    """Recursively process MP3 and FLAC files in randomized order."""
    
    # Step 1: Gather all filepaths
    filepaths = []
    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.lower().endswith((".mp3", ".flac")):
                filepaths.append(os.path.join(root, file))

    # Step 2: Randomize the full list
    random.shuffle(filepaths)

    # Step 3: Process in randomized order
    for filepath in filepaths:
        print(f"\n{BRIGHT}{GREEN}Processing:{RESET} {filepath}")

        try:
            audio = File(filepath)
            title = str(audio.get("TIT2", pathlib.Path(filepath).stem))
            artist = str(audio.get("TPE1", "Unknown Artist"))
            album = str(audio.get("TALB", "Unknown Album"))
        except Exception as e:
            print(f"{YELLOW}Metadata read error ({e}), using filename{RESET}")
            title = pathlib.Path(filepath).stem
            artist = "Unknown Artist"
            album = "Unknown Album"

        # Previously logged missing lyrics
        if not RECHECK_EXISTING and missing_lyrics_set and (title, artist, album) in missing_lyrics_set:
            clear_comments(filepath)
            print(f"{YELLOW}{BRIGHT}Previously logged missing lyrics, cleared comments:{RESET} {title}")
            continue

        # Excluded titles
        if is_excluded_title(title):
            clear_comments(filepath)
            print(f"{YELLOW}{BRIGHT}Skipping excluded song title and cleared comments:{RESET} {title}")
            continue

        # Check if file has invalid/void lyrics (PMEDIA, etc.)
        lyrics_invalid = not has_embedded_lyrics(filepath)
        if bypass_existing and not lyrics_invalid:
            print(f"{YELLOW}{BRIGHT}Lyrics already exist and are valid, skipping:{RESET} {filepath}")
            continue

        if lyrics_invalid:
            clear_comments(filepath)
            print(f"{YELLOW}{BRIGHT}Cleared comments/lyrics with void text for:{RESET} {filepath}")

        # Fetch lyrics
        lyrics = fetch_official_lyrics(title, artist, album, genius)
        if lyrics is None:
            print(f"{RED}{BRIGHT}Fetch error{RESET} for {title}; {YELLOW}{BRIGHT}skipping without logging.{RESET}")
            continue

        if not lyrics:
            log_missing_lyrics(title, artist, album)
            clear_comments(filepath)
            continue

        # Save to file if requested
        if save_to_file:
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            lyrics_path = os.path.join(root, f"{title}_official_lyrics.txt")
            with open(lyrics_path, "w", encoding="utf-8") as f:
                f.write(lyrics)
            print(f"{BLUE}{BRIGHT}Saved lyrics file:{RESET} {lyrics_path}")

        # Embed into metadata
        embed_lyrics(filepath, lyrics)


# -------------------------------
# Main function
# -------------------------------
def main():
    input_dir = r"W:\Music\MP3s_320"
    print(f"{BRIGHT}{GREEN}Starting recursive lyrics fetcher...{RESET}")
    print(f"{BLUE}Scanning directory:{RESET} {input_dir}")

    missing_lyrics_set = load_missing_lyrics_log() if not RECHECK_EXISTING else set()
    
    process_directory(input_dir, 
                      bypass_existing=not RECHECK_EXISTING, 
                      save_to_file=False,
                      missing_lyrics_set=missing_lyrics_set)

    print(f"\n{GREEN}{BRIGHT}All done!{RESET} Official lyrics have been saved, embedded, and missing songs logged.\n")


# -------------------------------
# Entrypoint
# -------------------------------
if __name__ == "__main__":
    main()
