#!/usr/bin/env python

import os
import re

from colorama import init, Fore, Style

init(autoreset=True)

# Define terminal color shortcuts
RED = Fore.RED
YELLOW = Fore.YELLOW
GREEN = Fore.GREEN
BLUE = Fore.BLUE
MAGENTA = Fore.MAGENTA
RESET = Style.RESET_ALL
BRIGHT = Style.BRIGHT

def add_year_to_filenames(root_dir: str,
                          dry_run: bool = True):
    """
    Renames episode files to include the year from the show folder name (e.g., "The Office (2005)").
    Skips files that already include the year.

    Args:
        root_dir (str): Path to the root show folder (e.g., "/path/The Office (2005)").
        dry_run (bool): If True, only prints planned renames; does not change any files.
    """
    # Extract show name and year from folder name
    basename = os.path.basename(root_dir)
    match = re.search(r'(.*?)\s*\((\d{4})\)', basename)
    if not match:
        raise ValueError("Folder name must include show title and year in format: Show Name (YYYY)")

    show_name = match.group(1).strip()
    year = match.group(2)
    show_name_with_year = f"{show_name} ({year})"

    video_extensions = ['.mkv', '.mp4', '.avi', '.mov']

    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            name, ext = os.path.splitext(filename)
            if ext.lower() not in video_extensions:
                continue

            # Skip if filename already contains year in any format (e.g., The Office (2005))
            if f"({year})" in filename:
                continue

            # Look for episode pattern
            episode_match = re.search(r'(S\d{2}E\d{2}(?:-E\d{2})?)', filename, re.IGNORECASE)
            if not episode_match:
                print(f"{RED}{BRIGHT}Skipping (no episode pattern){RESET}: {filename}")
                continue

            new_filename = f"{show_name_with_year} {episode_match.group(1)}{ext}"
            src = os.path.join(dirpath, filename)
            dst = os.path.join(dirpath, new_filename)

            if os.path.exists(dst):
                print(f"{YELLOW}Skipping (target already exists){RESET}: {dst}")
                continue

            if dry_run:
                print(f"{GREEN}{BRIGHT}[DRY RUN] Would rename{RESET}: {filename} {BLUE}{BRIGHT}->{RESET} {new_filename}")
            else:
                print(f"{GREEN}{BRIGHT}Renaming{RESET}: {filename} {BLUE}{BRIGHT}->{RESET} {new_filename}")
                os.rename(src, dst)

if __name__ == '__main__':
    dir_to_fix = r'D:\Shows\Spongebob Squarepants (1999)'
    add_year_to_filenames(dir_to_fix, 
                          dry_run=False)
