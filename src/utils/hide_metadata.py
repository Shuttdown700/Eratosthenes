import argparse
import ctypes
import os
import stat
import sys
from typing import Dict, List, Optional

from pandas import read_json

# --- path setup for local imports ---
# Add the parent directory to sys.path to import from ../utilities.py
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

try:
    from utilities import (
        get_drive_letter,
        read_alexandria,
        read_alexandria_config
    )
except ImportError as e:
    print(f"Error importing from utilities.py: {e}")
    print("Ensure 'utilities.py' exists in the parent directory.")
    sys.exit(1)

# --- Third-party imports ---
try:
    import win32api
    import win32con
    from alive_progress import alive_bar
except ImportError as e:
    print(f"Error: Missing dependency. {e}")
    sys.exit(1)


def set_hidden_attribute(filepath: str, hide: bool) -> None:
    """
    Sets or unsets the Windows hidden file attribute.
    """
    try:
        # GetFileAttributesW returns a bitmask of file attributes
        attrs = ctypes.windll.kernel32.GetFileAttributesW(filepath)
        if attrs == -1:
            return  # File not found or error

        if hide:
            # Check if NOT already hidden
            if not (attrs & win32con.FILE_ATTRIBUTE_HIDDEN):
                print(f'Hiding: {filepath}')
                win32api.SetFileAttributes(
                    filepath, win32con.FILE_ATTRIBUTE_HIDDEN
                )
        else:
            # Check if IS hidden
            if attrs & win32con.FILE_ATTRIBUTE_HIDDEN:
                print(f'Unhiding photo file: {filepath}')
                # Bitwise operation to remove the hidden flag
                ctypes.windll.kernel32.SetFileAttributesW(
                    filepath, attrs & ~win32con.FILE_ATTRIBUTE_HIDDEN
                )
    except Exception as e:
        print(f"Error processing attributes for {filepath}: {e}")


def hide_metadata(
    drive_config: Optional[Dict] = None,
    target_directory: Optional[str] = None
) -> None:
    """
    Hides metadata files (.jpg, .nfo, .png) in drives or a specific directory.
    If files are in /Photos/ or /Courses/, they are unhidden instead.
    """
    extensions_list = ['.jpg', '.nfo', '.png']
    base_directories = []

    # 1. Determine scan targets (Config vs Directory)
    if target_directory:
        if os.path.exists(target_directory):
            base_directories = [target_directory]
        else:
            print(f"Error: Directory '{target_directory}' does not exist.")
            return
    elif drive_config is not None:
        # Unpack the first two return values from the config reader
        primary_drives, backup_drives = read_alexandria_config(drive_config)[:2]

        for key, val in primary_drives.items():
            base_directories.extend(
                [f'{get_drive_letter(v)}:/{key}' for v in val]
            )
        for key, val in backup_drives.items():
            base_directories.extend(
                [f'{get_drive_letter(v)}:/{key}' for v in val]
            )
    else:
        print("Error: Must provide either drive_config or target_directory.")
        return

    # 2. Get file list using the utility function
    filepaths = read_alexandria(base_directories, extensions=extensions_list)

    if not filepaths:
        count = len(base_directories)
        label = "directory" if count == 1 else "directories"
        print(f'No metadata files in any of the {count} {label}!')
        return

    # 3. Process files
    title_text = f'Processing {", ".join(extensions_list)} files'
    with alive_bar(len(filepaths), title=title_text, bar='classic') as bar:
        for filepath in filepaths:
            # Normalize path separators for consistent string matching
            norm_path = filepath.replace('\\', '/')

            # Determine logic: Unhide if Protected, Hide otherwise
            is_protected = '/Photos/' in norm_path or '/Courses/' in norm_path

            if is_protected:
                set_hidden_attribute(filepath, hide=False)
            else:
                set_hidden_attribute(filepath, hide=True)

            bar()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Hide metadata files in specified locations."
    )
    
    # Create a mutually exclusive group (User must choose one, but not both)
    group = parser.add_mutually_exclusive_group(required=True)
    
    group.add_argument(
        '--dir',
        type=str,
        help="A specific directory path to scan."
    )
    group.add_argument(
        '--config',
        action='store_true',
        help="Use the default configuration file to scan drives."
    )

    args = parser.parse_args()

    if args.dir:
        hide_metadata(target_directory=args.dir)
    
    else:
        src_directory = os.path.dirname(os.path.abspath(__file__))
        filepath_drive_hierarchy = os.path.join(src_directory, "..", "..", "config", "alexandria_drives.config")
        drive_config = read_json(filepath_drive_hierarchy)
        hide_metadata(drive_config=drive_config)



        # Note: Since read_alexandria_config takes a dict, you would typically
        # load a JSON/YAML file here. For now, we pass a placeholder or 
        # assume the utility handles the file path if modified.
        # Example: import json; config = json.load(open(args.config))
        print("Config file loading requires specific implementation.")
        # hide_metadata(drive_config=loaded_config_dict)