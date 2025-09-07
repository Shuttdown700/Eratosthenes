#!/usr/bin/env python

import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utilities import is_hidden

def delete_hidden_files(root_dir: str, 
                        delete_extensions: list = [], 
                        dry_run: bool = True):
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
    dir_to_clean = r'B:\Spongebob Squarepants (1999)\Season 2'
    delete_hidden_files(dir_to_clean, 
                        delete_extensions=[".nfo",".jpg",".jpeg",".png"], 
                        dry_run=False)