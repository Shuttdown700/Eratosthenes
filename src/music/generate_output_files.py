import os
import json
from mutagen import File
from collections import defaultdict
from tqdm import tqdm
from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)

# === COLORS ===
RED = Fore.RED
YELLOW = Fore.YELLOW
GREEN = Fore.GREEN
BLUE = Fore.BLUE
MAGENTA = Fore.MAGENTA
RESET = Style.RESET_ALL
BRIGHT = Style.BRIGHT


def extract_metadata(filepath):
    """Extract metadata from an audio file using mutagen."""
    try:
        audio = File(filepath, easy=True)
        if not audio:
            return None

        artist = audio.get('artist', ['Unknown Artist'])[0]
        album_artist = audio.get('albumartist', [artist])[0]
        album = audio.get('album', ['Unknown Album'])[0]
        title = audio.get('title', [os.path.basename(filepath)])[0]

        return {
            'artist': artist.strip(),
            'album_artist': album_artist.strip(),
            'album': album.strip(),
            'title': title.strip()
        }
    except Exception as e:
        print(f"{RED}{BRIGHT}Error reading {filepath}:{RESET} {e}")
        return None


def collect_music_data(base_dir, skip_dirs=None):
    """Recursively collect artist, album, and track info from .mp3 and .flac files."""
    if skip_dirs is None:
        skip_dirs = []

    music_data = defaultdict(lambda: defaultdict(list))
    all_artists = set()
    all_album_artists = set()

    print(f"{BLUE}{BRIGHT}Scanning directory:{RESET} {base_dir}")

    # Count total files for progress bar
    total_files = sum(
        len([f for f in files if f.lower().endswith((".mp3", ".flac"))])
        for _, _, files in os.walk(base_dir)
    )

    with tqdm(total=total_files, desc="Processing files", ncols=90, colour="cyan") as pbar:
        for root, dirs, files in os.walk(base_dir):
            # Skip unwanted directories
            dirs[:] = [d for d in dirs if os.path.join(root, d) not in skip_dirs]

            for file in files:
                if not file.lower().endswith((".mp3", ".flac")):
                    continue

                filepath = os.path.join(root, file)
                metadata = extract_metadata(filepath)
                pbar.update(1)

                if not metadata:
                    continue

                artist = metadata['artist']
                album_artist = metadata['album_artist']
                album = metadata['album']
                title = metadata['title']

                all_artists.add(artist)
                all_album_artists.add(album_artist)
                music_data[artist][album].append(title)

    print(f"{GREEN}{BRIGHT}Scan complete.{RESET}")
    print(f"{YELLOW}Artists: {len(all_artists)}")
    print(f"Albums: {sum(len(a) for a in music_data.values())}")
    print(f"Tracks: {sum(len(t) for a in music_data.values() for t in a.values())}{RESET}")

    return music_data, sorted(all_artists), sorted(all_album_artists)


def write_text_file(filename, items):
    """Write a sorted list of strings to a text file."""
    with open(filename, 'w', encoding='utf-8') as f:
        for item in sorted(items):
            f.write(f"{item}\n")
    print(f"{GREEN}Wrote {len(items)} entries → {filename}{RESET}")


def write_json_file(filename, data):
    """Write nested dictionary as formatted JSON."""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print(f"{GREEN}Wrote JSON data → {filename}{RESET}")


if __name__ == "__main__":
    # === CONFIGURATION ===
    base_directory = r"W:\Music\MP3s_320"  # Directory to scan
    
    output_directory = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', '..', 'output', 'music')
    )
    skip_directories = [
        os.path.join(base_directory, "_playlists")
    ]

    # Create output directory if missing
    os.makedirs(output_directory, exist_ok=True)

    # === EXECUTION ===
    music_data, artists, album_artists = collect_music_data(base_directory, skip_directories)

    # Define output filepaths
    artists_file = os.path.join(output_directory, "artists.txt")
    album_artists_file = os.path.join(output_directory, "album_artists.txt")
    json_file = os.path.join(output_directory, "music_library.json")

    # Write output files
    write_text_file(artists_file, artists)
    write_text_file(album_artists_file, album_artists)
    write_json_file(json_file, music_data)

    print(f"{BLUE}{BRIGHT}All output saved in:{RESET} {output_directory}")
