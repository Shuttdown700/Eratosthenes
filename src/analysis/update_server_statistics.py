#!/usr/bin/env python3

import json
import os
import shutil
import sys

from colorama import Fore, Style

# Append parent directory to sys.path for local imports
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from assess_media_duration import main as assess_media_total_duration
from assess_media_duration import sum_durations
from read_server_statistics import read_media_statistics
from utilities import (
    get_drive_letter,
    get_file_size,
    read_alexandria,
    read_alexandria_config,
    read_json
)

# Constants for mapping path identifiers to their display names and size units
MEDIA_TYPES = {
    ":/Shows/": {"name": "TV Shows", "unit": "TB", "has_episodes": True},
    ":/Anime/": {"name": "Anime", "unit": "TB", "has_episodes": True},
    ":/Movies/": {"name": "Movies", "unit": "TB", "has_episodes": False},
    ":/Anime Movies/": {"name": "Anime Movies", "unit": "GB", "has_episodes": False},
    ":/4K Movies/": {"name": "4K Movies", "unit": "TB", "has_episodes": False},
    ":/Books/": {"name": "Books", "unit": "GB", "has_episodes": False},
    ":/Music/MP3s_320": {"name": "Music", "unit": "GB", "has_episodes": False},
    ":/YouTube/": {"name": "YouTube", "unit": "GB", "has_episodes": False},
}

# Extensions to ignore when counting files, sizes, and assessing duration
IGNORED_EXTENSIONS = (
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tbn',  # Images
    '.nfo', '.txt',                                            # Metadata
    '.srt', '.sub', '.idx', ".lrc"                             # Subtitles
)

def get_media_title(filepath: str, media_name: str) -> str:
    """Extracts the title of the media based on its category."""
    if media_name == "Books":
        return os.path.splitext(os.path.basename(filepath))[0]
    
    # For TV Shows, Movies, etc., we assume the title is the parent directory
    # e.g., 'D:/Movies/Avatar/Avatar.mkv' -> 'Avatar'
    path_parts = filepath.replace('\\', '/').split('/')
    if len(path_parts) > 2:
        return path_parts[2].strip()
    return ""


def process_media_category(
    filepaths: list, 
    media_info: dict, 
    update_duration: bool, 
    current_stats: dict
) -> dict:
    """Calculates statistics (size, duration, counts) for a specific media category."""
    media_name = media_info["name"]
    unit = media_info["unit"]
    
    # Filter out artwork, metadata, and subtitle files
    valid_filepaths = [
        f for f in filepaths 
        if not f.lower().endswith(IGNORED_EXTENSIONS)
    ]
    
    num_files = len(valid_filepaths)
    total_size = round(sum(get_file_size(f, unit) for f in valid_filepaths), 2)
    
    # Extract and clean titles using only valid media files
    titles = [get_media_title(f, media_name) for f in valid_filepaths]
    titles = sorted({title for title in titles if title}, key=str.lower)
    
    # Calculate duration
    if update_duration and media_name not in ["Books"]:
        total_duration = assess_media_total_duration(valid_filepaths, print_bool=True)
    elif media_name not in ["Books"]:
        total_duration = current_stats.get(media_name, {}).get("Total Duration", 0)
    else:
        total_duration = 0

    # Build the category dictionary
    stats = {
            "Total Size": f"{total_size:,.2f} {unit}",
            "Primary Filepaths": valid_filepaths
    }
    
    # Override specific keys to match the original JSON schema exactly
    title_key = "Show Titles" if media_name == "TV Shows" else f"{media_name} Titles"
    count_key = "Number of Shows" if media_name == "TV Shows" else f"Number of {media_name}"
    
    if media_name not in ["Music", "YouTube"]:
        stats[title_key] = titles
        
    if media_info["has_episodes"]:
        stats[count_key] = len(titles)
        stats["Number of Episodes"] = num_files
    elif media_name == "Music":
        stats["Number of Songs"] = num_files
    elif media_name == "YouTube":
        stats["Number of YouTube Videos"] = num_files
    else:
        stats[count_key] = len(titles) if titles else num_files

    if media_name not in ["Books"]:
        stats["Total Duration"] = total_duration

    return stats

def update_server_statistics(update_duration: bool = False, print_stats: bool = False) -> None:
    """Update and output the server statistics for Alexandria Media Server."""
    src_directory = os.path.dirname(os.path.abspath(__file__))
    directory_output = os.path.join(src_directory, "..", "..", "output")
    filepath_statistics = os.path.join(directory_output, "alexandria_media_statistics.json")
    filepath_drive_config = os.path.join(src_directory, "..", "..", "config", "alexandria_drives.config")

    drive_config = read_json(filepath_drive_config)

    try:
        current_stats = read_media_statistics(bool_update=False, bool_print=False)
    except (KeyError, FileNotFoundError) as e:
        print(f"{Fore.RED}{Style.BRIGHT}Error: Media statistics file incomplete or not found "
              f"({e}). Please run the update first.{Style.RESET_ALL}")
        return

    # Extract all drives dynamically
    drive_names = set()
    for category in drive_config.values():
        drive_names.update(category.get('primary_drives', []))
        # Handle dict keys or lists for backup drives
        backup = category.get('backup_drives', [])
        drive_names.update(backup.keys() if isinstance(backup, dict) else backup)

    drive_letters = {get_drive_letter(d) for d in drive_names if d}
    drive_letters.discard(None)

    # Calculate storage space
    space_tb_available = 0
    space_tb_used = 0
    space_tb_unused = 0

    for drive in drive_letters:
        disk_obj = shutil.disk_usage(f'{drive}:/')
        space_tb_available += int(disk_obj.total / 10**12)
        space_tb_used += int(disk_obj.used / 10**12)
        space_tb_unused += int(disk_obj.free / 10**12)

    # Read Alexandria config
    primary_drives_dict, _, extensions_dict = read_alexandria_config(drive_config)
    
    primary_parent_paths = []
    primary_extensions = []

    for media_type in drive_config.keys():
        drive_letters_for_type = [get_drive_letter(x) for x in primary_drives_dict.get(media_type, [])]
        primary_parent_paths.extend(f'{letter}:/{media_type}' for letter in drive_letters_for_type)
        for _ in drive_letters_for_type:
            primary_extensions.extend(list(extensions_dict.get(media_type, [])))

    primary_filepaths = read_alexandria(primary_parent_paths, primary_extensions)

    # Categorize filepaths
    categorized_filepaths = {key: [] for key in MEDIA_TYPES.keys()}
    for filepath in primary_filepaths:
        for path_key in MEDIA_TYPES.keys():
            if path_key in filepath:
                categorized_filepaths[path_key].append(filepath)
                break

    # Process all media types
    statistics_dict = {}
    durations = []
    total_files = len(primary_filepaths)
    total_size_tb = 0.0

    for path_key, media_info in MEDIA_TYPES.items():
        media_name = media_info["name"]
        paths = categorized_filepaths[path_key]
        
        stats = process_media_category(paths, media_info, update_duration, current_stats)
        statistics_dict[media_name] = stats
        
        if "Total Duration" in stats:
            durations.append(stats["Total Duration"])
            
        # Add to total size, converting GB to TB where necessary
        size_val = float(stats["Total Size"].split()[0].replace(',', ''))
        total_size_tb += size_val if media_info["unit"] == "TB" else size_val / 1000

    total_duration = sum_durations(durations)

    # Save to JSON
    with open(filepath_statistics, 'w', encoding='utf-8') as json_file:
        json.dump(statistics_dict, json_file, indent=4)

    # Terminal Output
    if print_stats:
        print(f'\n{"#" * 10}\n\n{Fore.YELLOW}{Style.BRIGHT}Server Stats:{Style.RESET_ALL}')
        print(f'Total Available Server Storage: {Fore.BLUE}{Style.BRIGHT}{space_tb_available:,} TB{Style.RESET_ALL}')
        print(f'Used Server Storage: {Fore.RED}{Style.BRIGHT}{space_tb_used:,} TB{Style.RESET_ALL}')
        print(f'Free Server Storage: {Fore.GREEN}{Style.BRIGHT}{space_tb_unused:,} TB{Style.RESET_ALL}\n')
        
        print(f'{Fore.YELLOW}{Style.BRIGHT}Primary Database Stats:{Style.RESET_ALL}')
        print(f'{total_files:,} Primary Media Files ({Fore.GREEN}{Style.BRIGHT}{total_size_tb:,.2f} TB{Style.RESET_ALL}, '
              f'Duration: {Fore.YELLOW}{total_duration}{Style.RESET_ALL})\n')
        
        # Helper string formatters for clean printing
        m_stats = statistics_dict.get("Movies", {})
        u_stats = statistics_dict.get("4K Movies", {})
        t_stats = statistics_dict.get("TV Shows", {})
        a_stats = statistics_dict.get("Anime", {})
        b_stats = statistics_dict.get("Books", {})
        c_stats = statistics_dict.get("YouTube", {})

        print(f'{Fore.BLUE}{Style.BRIGHT}{m_stats.get("Number of Movies", 0):,} BluRay Movies{Style.RESET_ALL} '
              f'({m_stats.get("Total Size", "0 TB")}, Duration: {Fore.YELLOW}{m_stats.get("Total Duration", 0)}{Style.RESET_ALL})')
        print(f'{Fore.YELLOW}{Style.BRIGHT}{a_stats.get("Number of Anime Movies", 0):,} Anime Movies{Style.RESET_ALL} '
              f'({a_stats.get("Total Size", "0 GB")}, Duration: {Fore.YELLOW}{a_stats.get("Total Duration", 0)}{Style.RESET_ALL})')
        print(f'{Fore.MAGENTA}{Style.BRIGHT}{u_stats.get("Number of 4K Movies", 0):,} 4K Movies{Style.RESET_ALL} '
              f'({u_stats.get("Total Size", "0 TB")}, Duration: {Fore.YELLOW}{u_stats.get("Total Duration", 0)}{Style.RESET_ALL})')
        print(f'{Fore.GREEN}{Style.BRIGHT}{t_stats.get("Number of Shows", 0):,} TV Shows{Style.RESET_ALL} '
              f'({t_stats.get("Number of Episodes", 0):,} Episodes, {t_stats.get("Total Size", "0 TB")}, Duration: {Fore.YELLOW}{t_stats.get("Total Duration", 0)}{Style.RESET_ALL})')
        print(f'{Fore.RED}{Style.BRIGHT}{a_stats.get("Number of Anime", 0):,} Anime Shows{Style.RESET_ALL} '
              f'({a_stats.get("Number of Episodes", 0):,} Episodes, {a_stats.get("Total Size", "0 TB")}, Duration: {Fore.YELLOW}{a_stats.get("Total Duration", 0)}{Style.RESET_ALL})')
        print(f'{Fore.RED}{Style.BRIGHT}{a_stats.get("Music", {}).get("Number of Songs", 0):,} Songs{Style.RESET_ALL} '
              f'({a_stats.get("Music", {}).get("Total Size", "0 GB")})')
        print(f'{Fore.CYAN}{Style.BRIGHT}{b_stats.get("Number of Books", 0):,} Books{Style.RESET_ALL} ({b_stats.get("Total Size", "0 GB")})')
        print(f'{Fore.LIGHTGREEN_EX}{Style.BRIGHT}{c_stats.get("Number of YouTube Videos", 0):,} YouTube Videos{Style.RESET_ALL} '
              f'({c_stats.get("Total Size", "0 GB")}, Duration: {Fore.YELLOW}{c_stats.get("Total Duration", 0)}{Style.RESET_ALL})')
        print(f'\n{"#" * 10}\n')

if __name__ == "__main__":
    update_server_statistics(update_duration=True, print_stats=True)