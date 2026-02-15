import json
import os
import sys
from collections import OrderedDict, defaultdict

from colorama import Fore, Style, init

# Local imports
from batch_update_media_list import update_all_media_lists

# Initialize Colorama
init(autoreset=True)

# Path Setup
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "../.."))

# Append path for utilities
sys.path.append(os.path.abspath(os.path.join(SCRIPT_DIR, '..')))
from utilities import (
    get_backup_root_directories, get_drive_name
)

# Constants
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
MOVIE_LIST_PATH = os.path.join(OUTPUT_DIR, "movies", "movie_list.txt")
SHOWS_LIST_PATH = os.path.join(OUTPUT_DIR, "series", "show_list.txt")
ANIME_LIST_PATH = os.path.join(OUTPUT_DIR, "series", "anime_list.txt")
ANIME_MOVIE_LIST_PATH = os.path.join(OUTPUT_DIR, "movies", "anime_movie_list.txt")
WHITELIST_FOLDER = os.path.join(PROJECT_ROOT, "config", "series_whitelists", "active")


def sort_key(label):
    """Sorts keys numerically based on the leading integer."""
    try:
        return int(label.split()[0])
    except (ValueError, IndexError):
        return 0


def load_list(path):
    """Reads a text file and returns a set of non-empty lines."""
    if not os.path.exists(path):
        return set()
    with open(path, encoding='utf-8') as f:
        return {line.strip() for line in f if line.strip()}


def _finalize_buckets(buckets):
    """Internal helper to sort buckets numerically and titles alphabetically."""
    sorted_buckets = OrderedDict()
    for key in sorted(buckets.keys(), key=sort_key):
        # Sort the titles within each bucket alphabetically
        sorted_buckets[key] = dict(sorted(buckets[key].items()))
    return sorted_buckets


def organize_into_buckets(backup_locations, all_titles, bool_print_no_backup=True):
    """Groups titles into buckets based on number of backups found."""
    buckets = defaultdict(dict)
    no_backup_titles = []

    for title in all_titles:
        drives = backup_locations.get(title, [])
        count = len(drives)
        
        bucket_key = f"{count} backup" if count == 1 else f"{count} backups"
        buckets[bucket_key][title] = drives
        
        if count == 0:
            no_backup_titles.append(title)

    if bool_print_no_backup and no_backup_titles:
        print(f"\n{Fore.RED}{Style.BRIGHT}Titles with NO backups:{Style.RESET_ALL}")
        for title in no_backup_titles:
            print(f"{Fore.YELLOW}{title}{Style.RESET_ALL}")

    return _finalize_buckets(buckets)


def detect_same_drive_duplicates(backup_locations):
    """Identifies titles that appear multiple times on the same drive."""
    duplicates_found = False
    for title, drives in backup_locations.items():
        seen = set()
        dupes = {d for d in drives if d in seen or seen.add(d)}
        
        if dupes:
            if not duplicates_found:
                print(f"\n{Fore.RED}{Style.BRIGHT}Potential same-drive duplicates:{Style.RESET_ALL}")
                duplicates_found = True
            for d in dupes:
                print(f"{Fore.YELLOW}{title} on {d}{Style.RESET_ALL}")


def get_series_configured_backup_status():
    """Generates summary for Series based on whitelist configuration."""
    output_path = os.path.join(OUTPUT_DIR, "series", "series_configured_backup_summary.json")
    all_titles = load_list(SHOWS_LIST_PATH) | load_list(ANIME_LIST_PATH)
    backup_locations = defaultdict(list)

    if os.path.exists(WHITELIST_FOLDER):
        for filename in os.listdir(WHITELIST_FOLDER):
            if "_whitelist" in filename:
                drive_name = filename.replace("_whitelist", "").split('.')[0]
                path = os.path.join(WHITELIST_FOLDER, filename)
                
                with open(path, encoding='utf-8') as f:
                    for line in f:
                        title = line.strip()
                        if title:
                            backup_locations[title].append(drive_name)

    buckets = organize_into_buckets(backup_locations, all_titles)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(buckets, f, indent=4, ensure_ascii=False)

    print(f"Detailed {Fore.GREEN}series backup summary{Style.RESET_ALL} saved: {output_path}")


def get_movie_live_backup_status():
    """Generates summary for Movies based on actual file system scan."""
    movie_roots = set(get_backup_root_directories(["Movies", "Anime Movies"]))
    output_path = os.path.join(OUTPUT_DIR, "movies", "movie_live_backup_summary.json")
    all_movies = load_list(MOVIE_LIST_PATH) | load_list(ANIME_MOVIE_LIST_PATH)
    
    backup_locations = defaultdict(list)

    for root in movie_roots:
        # Optimization: Use a single drive name lookup per root
        drive_letter = get_drive_name(root[0]) 
        for _, _, files in os.walk(root):
            for file in files:
                title = os.path.splitext(file)[0].strip()
                if title in all_movies:
                    backup_locations[title].append(drive_letter)

    detect_same_drive_duplicates(backup_locations)
    buckets = organize_into_buckets(backup_locations, all_movies, bool_print_no_backup=False)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(buckets, f, indent=4, ensure_ascii=False)

    print(f"Detailed {Fore.GREEN}movie backup summary{Style.RESET_ALL} saved: {output_path}")


def main():
    divider = f'\n{"#" * 20}\n'
    print(divider)
    print(f"{Fore.CYAN}Assessing backup status of all titles...{Style.RESET_ALL}")
    
    update_all_media_lists()
    
    print(divider)
    get_series_configured_backup_status()
    get_movie_live_backup_status()
    print(divider)


if __name__ == "__main__":
    main()