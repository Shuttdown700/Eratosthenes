#!/usr/bin/env python

import os
import re
from colorama import init, Fore, Style


def find_mp4_files(root_dir):
    mp4_files = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for file in filenames:
            if file.lower().endswith('.mp4'):
                full_path = os.path.join(dirpath, file)
                mp4_files.append(full_path)
    return mp4_files

# Initialize colorama for Windows compatibility
init(autoreset=True)

def fix_episode_format(root_dir='.', dry_run=True):
    """
    Find files ending with 'SxxExx-xx' and rename to 'SxxExx-Exx'.
    If the new name already exists, delete the incorrectly named file.
    
    Args:
        root_dir (str): Directory to scan.
        dry_run (bool): If True, only print actions. If False, apply changes.
    """
    pattern = re.compile(r'(S\d{2}E\d{2})-(\d{2})(\.\w+)$')

    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            match = pattern.search(filename)
            if match:
                base, ep2, ext = match.groups()
                new_name = pattern.sub(rf'{base}-E{ep2}{ext}', filename)
                old_path = os.path.join(dirpath, filename)
                new_path = os.path.join(dirpath, new_name)

                if os.path.exists(new_path):
                    msg = f'DELETE (conflict): {filename} (because {new_name} exists)'
                    print(Fore.RED + ('[DRY RUN] ' if dry_run else '') + msg)
                    if not dry_run:
                        os.remove(old_path)
                else:
                    msg = f'RENAME: {filename} -> {new_name}'
                    color = Fore.YELLOW if dry_run else Fore.GREEN
                    print(color + ('[DRY RUN] ' if dry_run else '') + msg)
                    if not dry_run:
                        os.rename(old_path, new_path)

if __name__ == '__main__':
    # Set dry_run=False to actually rename files
    fix_episode_format(r'B:\Shows', dry_run=False)

    # # Find all .mp4 files in the specified directory and print their paths
    # search_directory = "A:/Anime"  # Replace with the actual directory path
    # mp4_files = find_mp4_files(search_directory)
    # for file in mp4_files:
    #     print(file)