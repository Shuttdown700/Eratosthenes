import os
import sys
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from mutagen.id3 import ID3, USLT, COMM, ID3NoHeaderError
from colorama import Fore, Style, init

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'utils')))
from generate_audio_file_print_string import generate_audio_file_print_string

# Initialize Colorama
init(autoreset=True)

# Constants for Colors
RED = Fore.RED
YELLOW = Fore.YELLOW
GREEN = Fore.GREEN
BLUE = Fore.BLUE
MAGENTA = Fore.MAGENTA
RESET = Style.RESET_ALL
BRIGHT = Style.BRIGHT

# Configuration Constants
EXCLUDED_TERMS = ["(Remix)", "(Live)", "(Skit)", "(Instrumental)", "(Remaster)"]
MIN_LYRICS_LENGTH = 30
VOID_LYRIC_STRINGS = [
    "www.", ".com", "http://", "https://",
    "lyrics powered by", "PMEDIA", "Downloaded from"
]


def embed_lyrics(filepath: str, lyrics: str):
    """
    Embed lyrics into MP3 (USLT frame) or FLAC (LYRICS tag) metadata.
    """
    if not lyrics:
        print(f"{YELLOW}No lyrics to embed for {filepath}{RESET}")
        return

    try:
        if filepath.lower().endswith(".mp3"):
            try:
                audio = MP3(filepath, ID3=ID3)
            except ID3NoHeaderError:
                audio = MP3(filepath)
                audio.add_tags()

            if audio.tags is None:
                audio.add_tags()

            # Remove existing lyrics/comments to prevent duplicates
            audio.tags.delall("USLT")
            audio.tags.delall("COMM")

            # Add new frames
            audio.tags.add(USLT(encoding=3, lang="eng", desc="", text=lyrics))
            audio.tags.add(COMM(encoding=3, lang="eng", desc="Lyrics", text=lyrics))
            audio.save(v2_version=3)
            print(f"{MAGENTA}{BRIGHT}Lyrics embedded{RESET} into {YELLOW}{BRIGHT}MP3{RESET} metadata for: {generate_audio_file_print_string(filepath)}")

        elif filepath.lower().endswith(".flac"):
            audio = FLAC(filepath)
            audio["LYRICS"] = lyrics
            audio["COMMENT"] = lyrics
            audio.save()
            print(f"{GREEN}{BRIGHT}Lyrics embedded{RESET} into {YELLOW}{BRIGHT}FLAC{RESET} metadata for: {generate_audio_file_print_string(filepath)}")

    except Exception as e:
        print(f"{RED}Error embedding lyrics into {filepath}: {e}{RESET}")


def is_excluded_title(title: str) -> bool:
    """Return True if the song title contains any excluded term."""
    for term in EXCLUDED_TERMS:
        if term.lower() in title.lower():
            return True
    return False


def clear_comments(filepath: str):
    """
    Remove comment, lyrics, and subtitle frames/tags from MP3 and FLAC files.
    """
    try:
        if filepath.lower().endswith(".mp3"):
            try:
                audio = MP3(filepath, ID3=ID3)
            except ID3NoHeaderError:
                return  # No tags to clear

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
            for tag in ["COMMENT", "LYRICS", "SUBTITLE"]:
                if tag in audio:
                    del audio[tag]
                    removed = True

            if removed:
                audio.save()
                print(f"{YELLOW}{BRIGHT}Cleared tags for:{RESET} {filepath}")

    except Exception as e:
        print(f"{RED}Error clearing comments for {filepath}: {e}{RESET}")


def _is_valid_lyric_text(text: str) -> bool:
    """Helper: check if text is long enough and not containing void strings."""
    if not text:
        return False
    stripped = text.strip()
    if any(void_str.lower() in stripped.lower() for void_str in VOID_LYRIC_STRINGS):
        return False
    return len(stripped) >= MIN_LYRICS_LENGTH


def has_embedded_plain_lyrics(filepath: str) -> bool:
    """
    Return True if the file already contains valid lyrics of sufficient length,
    and does NOT contain known void strings.
    """
    try:
        if filepath.lower().endswith(".mp3"):
            try:
                audio = MP3(filepath, ID3=ID3)
            except ID3NoHeaderError:
                return False

            if not audio.tags:
                return False

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