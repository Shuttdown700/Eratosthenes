#!/usr/bin/env python3

import json
import os
import shutil
import sys
from pathlib import Path

from colorama import Fore, Style
from tqdm import tqdm

# Append parent directory to sys.path for local imports
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from assess_media_duration import main as assess_media_total_duration
from assess_media_duration import sum_durations
from read_server_statistics import read_media_statistics
from utilities import (
    get_volume_root,
    get_file_size,
    read_alexandria,
    read_alexandria_config,
    read_json
)

# Constants mapping config keys to display names and size units
MEDIA_TYPES = {
    "Shows": {"name": "TV Shows", "unit": "TB", "has_episodes": True},
    "Anime": {"name": "Anime", "unit": "TB", "has_episodes": True},
    "Movies": {"name": "Movies", "unit": "TB", "has_episodes": False},
    "Anime Movies": {"name": "Anime Movies", "unit": "GB", "has_episodes": False},
    "4K Movies": {"name": "4K Movies", "unit": "TB", "has_episodes": False},
    "Books": {"name": "Books", "unit": "GB", "has_episodes": False},
    "Music": {"name": "Music", "unit": "GB", "has_episodes": False},
    "YouTube": {"name": "YouTube", "unit": "GB", "has_episodes": False},
}

# Extensions to ignore when counting files, sizes, and assessing duration
IGNORED_EXTENSIONS = (
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tbn',  # Images
    '.nfo', '.txt',                                            # Metadata
    '.srt', '.sub', '.idx', ".lrc"                             # Subtitles
)


def get_media_title(filepath: str, config_key: str, media_name: str) -> str:
    """Extracts the title of the media based on its category dynamically."""
    if media_name == "Books":
        return os.path.splitext(os.path.basename(filepath))[0]
    
    path_parts = Path(filepath).parts
    try:
        # Dynamically find the root media directory (e.g., "Movies") and take the next folder as the title
        lower_parts = [p.lower() for p in path_parts]
        idx = lower_parts.index(config_key.lower())
        return path_parts[idx + 1].strip()
    except (ValueError, IndexError):
        # Safe fallback if folder structure deviates
        if len(path_parts) >= 2:
            return path_parts[-2].strip()
        return os.path.basename(filepath)


def process_media_category(
    filepaths: list, 
    media_info: dict, 
    config_key: str,
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
    
    total_size = 0.0
    titles = []

    # Combined loop for size calculation and title extraction with tqdm
    if valid_filepaths:
        for f in tqdm(valid_filepaths, desc=f"Processing {media_name}", unit="file", dynamic_ncols=True, leave=False):
            total_size += get_file_size(f, unit)
            titles.append(get_media_title(f, config_key, media_name))
            
    total_size = round(total_size, 2)
    titles = sorted({title for title in titles if title}, key=str.lower)
    
    # Calculate duration
    if update_duration and media_name not in ["Books"]:
        # If assess_media_total_duration prints output, tqdm.write might be needed inside it to prevent display bugs
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

    os.makedirs(directory_output, exist_ok=True)
    drive_config = read_json(filepath_drive_config)

    try:
        current_stats = read_media_statistics(bool_update=False, bool_print=False)
    except (KeyError, FileNotFoundError) as e:
        print(f"{Fore.RED}{Style.BRIGHT}Error: Media statistics file incomplete or not found "
              f"({e}). Please run the update first.{Style.RESET_ALL}")
        current_stats = {}

    # Extract all drives dynamically
    drive_names = set()
    for category in drive_config.values():
        drive_names.update(category.get('primary_drives', []))
        backup = category.get('backup_drives', [])
        drive_names.update(backup.keys() if isinstance(backup, dict) else backup)

    volume_roots = {get_volume_root(d) for d in drive_names if get_volume_root(d)}

    # Calculate storage space
    space_tb_available = 0
    space_tb_used = 0
    space_tb_unused = 0

    for root in volume_roots:
        try:
            disk_obj = shutil.disk_usage(root)
            space_tb_available += int(disk_obj.total / 10**12)
            space_tb_used += int(disk_obj.used / 10**12)
            space_tb_unused += int(disk_obj.free / 10**12)
        except OSError as e:
            print(f"{Fore.YELLOW}Warning: Could not read disk usage for {root} - {e}{Style.RESET_ALL}")

    primary_drives_dict, _, extensions_dict = read_alexandria_config(drive_config)

    # Process all media types independently
    statistics_dict = {}
    durations = []
    total_files = 0
    total_size_tb = 0.0

    print(f"\n{Fore.MAGENTA}{Style.BRIGHT}Scanning and Parsing Media Categories...{Style.RESET_ALL}\n")

    for config_key, media_info in MEDIA_TYPES.items():
        media_name = media_info["name"]
        
        # Build paths specifically for this category
        drive_names_for_type = primary_drives_dict.get(config_key, [])
        roots_for_type = [get_volume_root(name) for name in drive_names_for_type if get_volume_root(name)]
        
        parent_paths = [os.path.join(root, config_key) for root in roots_for_type]
        extensions = list(extensions_dict.get(config_key, []))
        
        filepaths = read_alexandria(parent_paths, extensions)
        total_files += len(filepaths)
        
        stats = process_media_category(filepaths, media_info, config_key, update_duration, current_stats)
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
        
        m_stats  = statistics_dict.get("Movies", {})
        am_stats = statistics_dict.get("Anime Movies", {})
        u_stats  = statistics_dict.get("4K Movies", {})
        t_stats  = statistics_dict.get("TV Shows", {})
        a_stats  = statistics_dict.get("Anime", {})
        mu_stats = statistics_dict.get("Music", {})
        b_stats  = statistics_dict.get("Books", {})
        c_stats  = statistics_dict.get("YouTube", {})

        print(f'{Fore.BLUE}{Style.BRIGHT}{m_stats.get("Number of Movies", 0):,} BluRay Movies{Style.RESET_ALL} '
              f'({m_stats.get("Total Size", "0 TB")}, Duration: {Fore.YELLOW}{m_stats.get("Total Duration", 0)}{Style.RESET_ALL})')
        print(f'{Fore.YELLOW}{Style.BRIGHT}{am_stats.get("Number of Anime Movies", 0):,} Anime Movies{Style.RESET_ALL} '
              f'({am_stats.get("Total Size", "0 GB")}, Duration: {Fore.YELLOW}{am_stats.get("Total Duration", 0)}{Style.RESET_ALL})')
        print(f'{Fore.MAGENTA}{Style.BRIGHT}{u_stats.get("Number of 4K Movies", 0):,} 4K Movies{Style.RESET_ALL} '
              f'({u_stats.get("Total Size", "0 TB")}, Duration: {Fore.YELLOW}{u_stats.get("Total Duration", 0)}{Style.RESET_ALL})')
        print(f'{Fore.GREEN}{Style.BRIGHT}{t_stats.get("Number of Shows", 0):,} TV Shows{Style.RESET_ALL} '
              f'({t_stats.get("Number of Episodes", 0):,} Episodes, {t_stats.get("Total Size", "0 TB")}, Duration: {Fore.YELLOW}{t_stats.get("Total Duration", 0)}{Style.RESET_ALL})')
        print(f'{Fore.RED}{Style.BRIGHT}{a_stats.get("Number of Anime", 0):,} Anime Shows{Style.RESET_ALL} '
              f'({a_stats.get("Number of Episodes", 0):,} Episodes, {a_stats.get("Total Size", "0 TB")}, Duration: {Fore.YELLOW}{a_stats.get("Total Duration", 0)}{Style.RESET_ALL})')
        print(f'{Fore.CYAN}{Style.BRIGHT}{mu_stats.get("Number of Songs", 0):,} Songs{Style.RESET_ALL} ({mu_stats.get("Total Size", "0 GB")}, Duration: {Fore.YELLOW}{mu_stats.get("Total Duration", 0)}{Style.RESET_ALL})')
        print(f'{Fore.LIGHTBLUE_EX}{Style.BRIGHT}{b_stats.get("Number of Books", 0):,} Books{Style.RESET_ALL} ({b_stats.get("Total Size", "0 GB")})')
        print(f'{Fore.LIGHTGREEN_EX}{Style.BRIGHT}{c_stats.get("Number of YouTube Videos", 0):,} YouTube Videos{Style.RESET_ALL} '
              f'({c_stats.get("Total Size", "0 GB")}, Duration: {Fore.YELLOW}{c_stats.get("Total Duration", 0)}{Style.RESET_ALL})')
        print(f'\n{"#" * 10}\n')


if __name__ == "__main__":
    update_server_statistics(update_duration=True, print_stats=True)