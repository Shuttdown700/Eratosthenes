#!/usr/bin/env python

import os
import re
import sys
import ctypes

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

def fix_multi_episode_format(root_dir: str,
                             dry_run: bool = True):
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
                    msg = f'{RED}{BRIGHT}DELETE (conflict){RESET}: {filename} (because {new_name} exists)'
                    print(('{YELLOW}[DRY RUN]{RESET} ' if dry_run else '') + msg)
                    if not dry_run:
                        os.remove(old_path)
                else:
                    msg = f'{GREEN}{BRIGHT}RENAME{RESET}: {filename} {BLUE}->{RESET} {new_name}'
                    print(('{YELLOW}[DRY RUN]{RESET} ' if dry_run else '') + msg)
                    if not dry_run:
                        os.rename(old_path, new_path)

if __name__ == '__main__':
    dry_run = True
    root_dirs = [r'B:\Shows',r'A:\Anime']
    for root_dir in root_dirs:
        print(f"{MAGENTA}{BRIGHT}Processing directory:{RESET} {root_dir}")
        fix_multi_episode_format(root_dir, dry_run)