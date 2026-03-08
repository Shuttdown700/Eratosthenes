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

# Attempt to import a primary directory fetcher; provide a fallback if it doesn't exist yet
try:
    from utilities import get_primary_root_directories
except ImportError:
    def get_primary_root_directories(categories):
        print(f"{Fore.RED}Warning: 'get_primary_root_directories' not found in utilities.py. Sizes for primary-only items may report as 0.{Style.RESET_ALL}")
        return []

# Constants
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
MOVIE_LIST_PATH = os.path.join(OUTPUT_DIR, "movies", "movie_list.txt")
SHOWS_LIST_PATH = os.path.join(OUTPUT_DIR, "series", "show_list.txt")
ANIME_LIST_PATH = os.path.join(OUTPUT_DIR, "series", "anime_list.txt")
ANIME_MOVIE_LIST_PATH = os.path.join(OUTPUT_DIR, "movies", "anime_movie_list.txt")
WHITELIST_FOLDER = os.path.join(PROJECT_ROOT, "config", "series_whitelists", "active")
ALEXANDRIA_CONFIG_PATH = os.path.join(PROJECT_ROOT, "config", "alexandria_drives.config")


def load_alexandria_config():
    """Loads the alexandria drives config."""
    if os.path.exists(ALEXANDRIA_CONFIG_PATH):
        with open(ALEXANDRIA_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def format_size(size_in_bytes):
    """Converts bytes to a human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:
        if size_in_bytes < 1024.0:
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024.0
    return f"{size_in_bytes:.2f} PB"


def get_directory_size(start_path, valid_extensions=None):
    """Calculates total size of a directory by recursively walking its files (handles Season sub-folders)."""
    total_size = 0
    for dirpath, _, filenames in os.walk(start_path):
        for f in filenames:
            if valid_extensions and not f.endswith(valid_extensions):
                continue
            fp = os.path.join(dirpath, f)
            if not os.path.islink(fp):
                try:
                    total_size += os.path.getsize(fp)
                except OSError:
                    pass
    return total_size


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


def _finalize_buckets(buckets, sizes_dict):
    """Internal helper to sort buckets, calculate metadata, and format output."""
    sorted_buckets = OrderedDict()
    for key in sorted(buckets.keys(), key=sort_key):
        # Sort the titles within each bucket alphabetically
        sorted_items = dict(sorted(buckets[key].items()))
        
        # Calculate the total size for all items in this bucket
        total_bytes = sum(sizes_dict.get(title, 0) for title in sorted_items.keys())
        size_str = format_size(total_bytes) if sizes_dict else "N/A"
        
        # Build the requested JSON structure
        sorted_buckets[key] = {
            "Size": size_str,
            "Quantity": len(sorted_items),
            "Media Items": sorted_items
        }
    return sorted_buckets


def organize_into_buckets(backup_locations, all_titles, sizes_dict=None, bool_print_no_backup=True, no_backup_filepath=None):
    """Groups titles into buckets based on number of backups found and exports missing items."""
    if sizes_dict is None:
        sizes_dict = {}
        
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
        print(f"{Fore.RED}{Style.BRIGHT}Titles with NO backups:{Style.RESET_ALL}")
        for title in no_backup_titles:
            print(f"{Fore.YELLOW}{title}{Style.RESET_ALL}")

    # Write missing backups to the specified text file
    if no_backup_filepath:
        os.makedirs(os.path.dirname(no_backup_filepath), exist_ok=True)
        with open(no_backup_filepath, "w", encoding="utf-8") as f:
            if no_backup_titles:
                for title in sorted(no_backup_titles):
                    f.write(f"{title}\n")
            else:
                f.write("") # Clears out old lists if everything is backed up
        
        # Only print the confirmation if there were actually missing titles
        if no_backup_titles:
            print(f"{Fore.RED}Missing backup list{Style.RESET_ALL} saved: {no_backup_filepath}")

    return _finalize_buckets(buckets, sizes_dict)


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
    missing_path = os.path.join(OUTPUT_DIR, "series", "series_configured_missing_backups.txt")
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

    buckets = organize_into_buckets(backup_locations, all_titles, sizes_dict={}, no_backup_filepath=missing_path)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(buckets, f, indent=4, ensure_ascii=False)

    print(f"Detailed {Fore.GREEN}series configured backup summary{Style.RESET_ALL} saved: {output_path}")


def get_series_live_backup_status():
    """Generates summary for Series based on actual file system scan."""
    # We now pull BOTH backup and primary roots to ensure size calculation for all shows
    backup_roots = set(get_backup_root_directories(["Shows", "Anime"]))
    primary_roots = set(get_primary_root_directories(["Shows", "Anime"]))
    all_series_roots = backup_roots | primary_roots
    
    output_path = os.path.join(OUTPUT_DIR, "series", "series_live_backup_summary.json")
    missing_path = os.path.join(OUTPUT_DIR, "series", "series_live_missing_backups.txt")
    all_series = load_list(SHOWS_LIST_PATH) | load_list(ANIME_LIST_PATH)
    
    config = load_alexandria_config()
    primary_drives = set()
    valid_extensions = set()
    for cat in ["Shows", "Anime"]:
        cat_data = config.get(cat, {})
        primary_drives.update(cat_data.get("primary_drives", []))
        valid_extensions.update(cat_data.get("extensions", []))
    valid_extensions = tuple(valid_extensions) if valid_extensions else ('.mp4', '.mkv')
    
    backup_locations = defaultdict(list)
    sizes_dict = {}

    for root in all_series_roots:
        drive_name = get_drive_name(root[0]) 
        is_primary = drive_name in primary_drives
        try:
            for item in os.listdir(root):
                item_path = os.path.join(root, item)
                if os.path.isdir(item_path):
                    title = item.strip()
                    if title in all_series:
                        if not is_primary and backup_locations[title].count(drive_name) < 1:
                            backup_locations[title].append(drive_name)
                        
                        current_size = get_directory_size(item_path, valid_extensions)
                        sizes_dict[title] = max(sizes_dict.get(title, 0), current_size)
        except OSError:
            continue

    detect_same_drive_duplicates(backup_locations)
    buckets = organize_into_buckets(backup_locations, all_series, sizes_dict, bool_print_no_backup=False, no_backup_filepath=missing_path)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(buckets, f, indent=4, ensure_ascii=False)

    print(f"Detailed {Fore.GREEN}series live backup summary{Style.RESET_ALL} saved: {output_path}")


def get_movie_live_backup_status():
    """Generates summary for Movies based on actual file system scan."""
    backup_roots = set(get_backup_root_directories(["Movies", "4K Movies", "Anime Movies"]))
    primary_roots = set(get_primary_root_directories(["Movies", "4K Movies", "Anime Movies"]))
    all_movie_roots = backup_roots | primary_roots
    
    output_path = os.path.join(OUTPUT_DIR, "movies", "movie_live_backup_summary.json")
    missing_path = os.path.join(OUTPUT_DIR, "movies", "movie_live_missing_backups.txt")
    all_movies = load_list(MOVIE_LIST_PATH) | load_list(ANIME_MOVIE_LIST_PATH)
    
    config = load_alexandria_config()
    primary_drives = set()
    valid_extensions = set()
    for cat in ["Movies", "4K Movies", "Anime Movies"]:
        cat_data = config.get(cat, {})
        primary_drives.update(cat_data.get("primary_drives", []))
        valid_extensions.update(cat_data.get("extensions", []))
    valid_extensions = tuple(valid_extensions) if valid_extensions else ('.mp4', '.mkv', '.m4v')

    backup_locations = defaultdict(list)
    sizes_dict = {}

    for root in all_movie_roots:
        drive_name = get_drive_name(root[0]) 
        is_primary = drive_name in primary_drives
        for dirpath, _, files in os.walk(root):
            for file in files:
                if not file.endswith(valid_extensions):
                    continue
                title = os.path.splitext(file)[0].strip()
                if title in all_movies:
                    if not is_primary and backup_locations[title].count(drive_name) < 1:
                        backup_locations[title].append(drive_name)
                    
                    try:
                        file_path = os.path.join(dirpath, file)
                        file_size = os.path.getsize(file_path)
                        sizes_dict[title] = max(sizes_dict.get(title, 0), file_size)
                    except OSError:
                        pass

    detect_same_drive_duplicates(backup_locations)
    buckets = organize_into_buckets(backup_locations, all_movies, sizes_dict, bool_print_no_backup=False, no_backup_filepath=missing_path)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(buckets, f, indent=4, ensure_ascii=False)

    print(f"Detailed {Fore.GREEN}movie live backup summary{Style.RESET_ALL} saved: {output_path}")


def main():
    divider = f'\n{"#" * 20}\n'
    print(divider)
    print(f"{Fore.CYAN}Assessing backup status of all titles...{Style.RESET_ALL}")
    
    update_all_media_lists()
    
    print(divider)
    get_series_configured_backup_status()
    get_series_live_backup_status()
    get_movie_live_backup_status()
    print(divider)


if __name__ == "__main__":
    # main()
    get_series_configured_backup_status()