#!/usr/bin/env python

import os
import re
import sys
import ctypes

from colorama import init, Fore, Style

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utilities import get_drive_letter, read_alexandria_config, read_json

init(autoreset=True)

# Define terminal color shortcuts
RED = Fore.RED
YELLOW = Fore.YELLOW
GREEN = Fore.GREEN
BLUE = Fore.BLUE
MAGENTA = Fore.MAGENTA
RESET = Style.RESET_ALL
BRIGHT = Style.BRIGHT

def fix_multi_episode_format(root_dir: str, dry_run: bool = True):
    """
    Finds files with 'SxxExx-xx' or 'SxxExxExx' and renames them to 'SxxExx-Exx'.
    """
    # Regex Breakdown:
    # 1. ^(.*S\d+E\d+)  -> Capture everything up to the first episode (e.g., "Show S01E01")
    # 2. (?:E|-)        -> Match either 'E' or '-' as the separator (don't capture it)
    # 3. (\d+)          -> Capture the second episode number (e.g., "02")
    # 4. (\.\w+)$       -> Capture the file extension (e.g., ".mkv")
    pattern = re.compile(r'^(.*S\d+E\d+)(?:E|-)(\d+)(\.\w+)$', re.IGNORECASE)

    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            match = pattern.search(filename)
            if match:
                # Unpack the 3 capturing groups
                base_part, episode_num, extension = match.groups()
                
                # Rebuild: "Show S01E01" + "-E" + "02" + ".mkv"
                new_name = f"{base_part}-E{episode_num}{extension}"
                
                old_path = os.path.join(dirpath, filename)
                new_path = os.path.join(dirpath, new_name)

                # Skip if the file is already named correctly
                if filename == new_name:
                    continue

                if os.path.exists(new_path):
                    msg = f"DELETE (conflict): {filename} (because {new_name} exists)"
                    print(('[DRY RUN] ' if dry_run else '') + msg)
                    if not dry_run:
                        os.remove(old_path)
                else:
                    msg = f"RENAME: {filename} -> {new_name}"
                    print(('[DRY RUN] ' if dry_run else '') + msg)
                    if not dry_run:
                        os.rename(old_path, new_path)

if __name__ == '__main__':
    # === CONFIGURATION ===
    src_directory = os.path.dirname(os.path.abspath(__file__))
    filepath_drive_hierarchy = os.path.join(src_directory, "..", "..", "config", "alexandria_drives.config")
    drive_config = read_json(filepath_drive_hierarchy)
    primary_drives_name_dict, backup_drives_name_dict, extensions_dict = read_alexandria_config(drive_config)
    media_type1 = "Shows"; media_type2 = "Anime"
    drive_names1 = primary_drives_name_dict[media_type1]; drive_names2 = primary_drives_name_dict[media_type2]
    drive_letters1 = [get_drive_letter(name) for name in drive_names1 if get_drive_letter(name) is not None]
    drive_letters2 = [get_drive_letter(name) for name in drive_names2 if get_drive_letter(name) is not None]
    # === FUNCTION INPUTS ===
    root_dirs1 = [rf"{letter}:\{media_type1}" for letter in drive_letters1]
    root_dirs2 = [rf"{letter}:\{media_type2}" for letter in drive_letters2]
    dry_run = False
    for root_dir in root_dirs1 + root_dirs2:
        print(f"{MAGENTA}{BRIGHT}Processing directory:{RESET} {root_dir}")
        fix_multi_episode_format(root_dir, dry_run)
