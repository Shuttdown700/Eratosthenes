#!/usr/bin/env python

import os
import re
import sys
import ctypes

from colorama import init, Fore, Style

# Initialize colorama for Windows compatibility
init(autoreset=True)

def fix_multi_episode_format(root_dir='.', dry_run=True):
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

def add_year_to_filenames(root_dir, dry_run=True):
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
                print(f"Skipping (no episode pattern): {filename}")
                continue

            new_filename = f"{show_name_with_year} {episode_match.group(1)}{ext}"
            src = os.path.join(dirpath, filename)
            dst = os.path.join(dirpath, new_filename)

            if os.path.exists(dst):
                print(f"Skipping (target already exists): {dst}")
                continue

            if dry_run:
                print(f"[DRY RUN] Would rename: {filename} -> {new_filename}")
            else:
                print(f"Renaming: {filename} -> {new_filename}")
                os.rename(src, dst)

def is_hidden(filepath):
    """
    Cross-platform check for hidden files:
    - On Windows, check FILE_ATTRIBUTE_HIDDEN
    - On Unix, check if filename starts with '.'
    """
    if sys.platform.startswith('win'):
        try:
            attrs = ctypes.windll.kernel32.GetFileAttributesW(str(filepath))
            return bool(attrs & 2)  # FILE_ATTRIBUTE_HIDDEN = 0x2
        except Exception as e:
            print(f"Error checking hidden attribute for {filepath}: {e}")
            return False
    else:
        return os.path.basename(filepath).startswith('.')

def delete_hidden_files(root_dir, delete_extensions=None, dry_run=True):
    """
    Deletes hidden files (by attribute or dot-prefix) and files with specific extensions.

    Args:
        root_dir (str): The root directory to search.
        dry_run (bool): If True, only prints what would be deleted.
        delete_extensions (list[str] or None): Extensions (e.g., ['.nfo', '.txt']) to delete regardless of hidden status.
    """
    delete_extensions = [ext.lower() for ext in (delete_extensions or [])]

    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            _, ext = os.path.splitext(filename)
            ext = ext.lower()

            if is_hidden(file_path) or ext in delete_extensions:
                if dry_run:
                    print(f"[DRY RUN] Would delete: {file_path}")
                else:
                    try:
                        os.remove(file_path)
                        print(f"Deleted: {file_path}")
                    except Exception as e:
                        print(f"Failed to delete {file_path}: {e}")

if __name__ == '__main__':
    # fix_multi_episode_format(r'B:\Shows', dry_run=False)

    # dir_to_fix = r'B:\Shows\Teenage Mutant Ninja Turtles (2012)'
    # add_year_to_filenames(dir_to_fix, dry_run=False)
    # delete_hidden_files(dir_to_fix, delete_extensions=[".srt"], dry_run=False)
    pass