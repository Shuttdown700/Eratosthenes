import argparse
import ctypes
import os
import sys
from pathlib import Path
from typing import Dict, Optional

from colorama import Fore, Style, init
from tqdm import tqdm

# Initialize colorama
init(autoreset=True)

# --- path setup for local imports ---
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

try:
    from utilities import (
        get_volume_root,
        read_alexandria,
        read_alexandria_config,
        read_json
    )
except ImportError as e:
    print(f"{Fore.RED}Error importing from utilities.py: {e}{Style.RESET_ALL}")
    sys.exit(1)


# OS Detection and Windows constants
IS_WINDOWS = sys.platform.startswith('win')
FILE_ATTRIBUTE_HIDDEN = 0x02


def set_hidden_attribute(filepath: str, hide: bool) -> None:
    """Sets or unsets the Windows hidden file attribute using native ctypes."""
    if not IS_WINDOWS:
        return

    try:
        attrs = ctypes.windll.kernel32.GetFileAttributesW(filepath)
        if attrs == -1:
            return  # File not found or error

        if hide:
            # Hide if not already hidden
            if not (attrs & FILE_ATTRIBUTE_HIDDEN):
                ctypes.windll.kernel32.SetFileAttributesW(filepath, attrs | FILE_ATTRIBUTE_HIDDEN)
        else:
            # Unhide if it is hidden
            if attrs & FILE_ATTRIBUTE_HIDDEN:
                ctypes.windll.kernel32.SetFileAttributesW(filepath, attrs & ~FILE_ATTRIBUTE_HIDDEN)
                
    except Exception as e:
        # Using tqdm.write prevents the print statement from breaking the progress bar visually
        tqdm.write(f"{Fore.RED}Error processing attributes for {filepath}: {e}{Style.RESET_ALL}")


def hide_metadata(
    drive_config: Optional[Dict] = None,
    target_directory: Optional[str] = None
) -> None:
    """
    Hides metadata files (.jpg, .nfo, .png) in drives or a specific directory.
    Only applies to Windows file properties. Will skip execution on Linux.
    """
    if not IS_WINDOWS:
        print(f"{Fore.YELLOW}Notice: Metadata hiding is configured for Windows only. Skipping process on this OS.{Style.RESET_ALL}")
        return

    extensions_list = ['.jpg', '.nfo', '.png']
    base_directories = []

    # 1. Determine scan targets (Config vs Directory)
    if target_directory:
        if os.path.exists(target_directory):
            base_directories = [target_directory]
        else:
            print(f"{Fore.RED}Error: Directory '{target_directory}' does not exist.{Style.RESET_ALL}")
            return
    elif drive_config is not None:
        primary_drives, backup_drives, _ = read_alexandria_config(drive_config)

        for key, val in primary_drives.items():
            base_directories.extend(
                [os.path.join(get_volume_root(v), key) for v in val if get_volume_root(v)]
            )
        for key, val in backup_drives.items():
            base_directories.extend(
                [os.path.join(get_volume_root(v), key) for v in val if get_volume_root(v)]
            )
    else:
        print(f"{Fore.RED}Error: Must provide either drive_config or target_directory.{Style.RESET_ALL}")
        return

    # 2. Get file list using the utility function
    filepaths = read_alexandria(base_directories, extensions=extensions_list)

    if not filepaths:
        count = len(base_directories)
        label = "directory" if count == 1 else "directories"
        print(f'{Fore.GREEN}No metadata files found in any of the {count} {label}!{Style.RESET_ALL}')
        return

    # 3. Process files using tqdm
    title_text = f'Processing {", ".join(extensions_list)} files'
    
    for filepath in tqdm(filepaths, desc=title_text, unit="file", dynamic_ncols=True):
        path_obj = Path(filepath)

        # Determine logic: Unhide if Protected, Hide otherwise
        is_protected = "Photos" in path_obj.parts or "Courses" in path_obj.parts

        if is_protected:
            set_hidden_attribute(filepath, hide=False)
        else:
            set_hidden_attribute(filepath, hide=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Hide metadata files in specified locations (Windows Only)."
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--dir', type=str, help="A specific directory path to scan.")
    group.add_argument('--config', action='store_true', help="Use the default configuration file to scan drives.")

    args = parser.parse_args()

    if args.dir:
        hide_metadata(target_directory=args.dir)
    else:
        src_directory = os.path.dirname(os.path.abspath(__file__))
        filepath_drive_hierarchy = os.path.join(src_directory, "..", "..", "config", "alexandria_drives.config")
        
        if not os.path.exists(filepath_drive_hierarchy):
            print(f"{Fore.RED}Error: Config file not found at {filepath_drive_hierarchy}{Style.RESET_ALL}")
            sys.exit(1)
            
        drive_config = read_json(filepath_drive_hierarchy)
        hide_metadata(drive_config=drive_config)