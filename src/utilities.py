#!/usr/bin/env python

import csv
import ctypes
import json
import os
import shutil
import stat
import sys
import time
import filecmp
from pathlib import Path
from typing import Optional, Dict, List, Tuple

from alive_progress import alive_bar
from colorama import init, Fore, Style

# Initialize colorama
init(autoreset=True)
RED, YELLOW, GREEN, BLUE, MAGENTA, RESET, BRIGHT = (
    Fore.RED, Fore.YELLOW, Fore.GREEN, Fore.BLUE, Fore.MAGENTA, 
    Style.RESET_ALL, Style.BRIGHT
)

# OS Detection for Cross-Platform compatibility
IS_WINDOWS = sys.platform.startswith('win')

def read_alexandria(
    parent_dirs: List[str],
    extensions: List[str] = ['.mp4', '.mkv', '.m4v', '.pdf', '.mp3', '.flac']
) -> List[str]:
    """Returns all files of a given extension from a list of parent directories."""
    assert isinstance(parent_dirs, list) and isinstance(extensions, list), \
        "Arguments must be lists."
    
    all_filepaths = []
    for idx_p, p in enumerate(parent_dirs):
        for root, _, files in os.walk(p):
            # Handle variable extensions per parent dir if passed as nested list
            if isinstance(extensions[0], list) and len(extensions) >= idx_p + 1:
                extension_list = extensions[idx_p]
            else:
                extension_list = extensions
            
            for file in files:
                _, ext = os.path.splitext(file)
                if ext.lower() in extension_list:
                    all_filepaths.append(os.path.join(root, file))
                    
    return all_filepaths


def files_are_identical(file1: str, file2: str, method: str = "size") -> bool:
    """Determines if two files are exactly the same."""
    if method == "size":
        if os.path.getsize(file1) != os.path.getsize(file2):
            return False
        return True
    elif method == "content":
        # Use built-in filecmp for actual content verification
        return filecmp.cmp(file1, file2, shallow=False)
    else:
        raise ValueError("Invalid method. Must be 'size' or 'content'.")
    return filecmp.cmp(file1, file2, shallow=False)


def read_json(filepath: str | Path, default: dict = None) -> dict:
    """Read JSON file safely, returning default if it fails."""
    try:
        with open(filepath, "r", encoding='utf8') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return default if default is not None else {}


def write_json(filepath: str | Path, data: dict) -> None:
    """Write dictionary to JSON file with proper formatting and UTF-8."""
    try:
        with open(filepath, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error writing to {filepath}: {e}")


def get_json_file_list(directory: str) -> List[str]:
    """Returns a list of all JSON files in a directory tree."""
    list_json_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.json'):
                list_json_files.append(os.path.join(root, file))
    return list_json_files


def write_to_csv(output_filepath: str, data_array: list, header: list) -> None:
    """Writes an array of data to a CSV file."""
    with open(output_filepath, mode='w', newline='', encoding='utf8') as file:
        writer = csv.writer(file)
        writer.writerow(header)
        writer.writerows(data_array)


def read_csv(file_path: str) -> List[dict]:
    """Reads a CSV file into a list of dictionary rows."""
    try:
        with open(file_path, mode='r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            return [row for row in reader]
    except FileNotFoundError:
        return []


def read_alexandria_config(drive_hierarchy: dict) -> Tuple[dict, dict, dict]:
    """Returns dictionaries identifying primary and backup drives by media type."""
    primary_drives_dict = {}
    backup_drives_dict = {}
    extensions_dict = {}
    
    for media_type, config in drive_hierarchy.items():
        primary_drives_dict[media_type] = config['primary_drives']
        
        backup_config = config['backup_drives']
        if isinstance(backup_config, dict):
            backup_drives_dict[media_type] = sorted(backup_config.keys())
        else:
            backup_drives_dict[media_type] = backup_config
            
        extensions_dict[media_type] = config['extensions']
        
    return primary_drives_dict, backup_drives_dict, extensions_dict


def does_volume_exist(path: str) -> bool:
    """Checks if a drive or mount path is accessible."""
    try:
        os.stat(path)
        return True
    except OSError:
        return False


def get_volume_root(volume_name: str) -> Optional[str]:
    """
    Cross-platform: Gets drive letter (Windows) or mount path (Linux) 
    from a volume name.
    """
    if IS_WINDOWS:
        # Windows: Check A-Z drives
        drives = [f"{chr(i)}:\\" for i in range(65, 91) if does_volume_exist(f"{chr(i)}:\\")]
        for drive in drives:
            vol_name_buf = ctypes.create_unicode_buffer(260)
            result = ctypes.windll.kernel32.GetVolumeInformationW(
                drive, vol_name_buf, 260, None, None, None, None, 0
            )
            if result != 0 and vol_name_buf.value.strip().lower() == volume_name.lower():
                return drive.rstrip('\\') # Returns 'C:'
        return None
    else:
        # Linux: Check common mount directories for the volume name
        common_mounts = [
            f"/mnt/{volume_name}",
            f"/media/{os.environ.get('USER', 'root')}/{volume_name}",
            f"/run/media/{os.environ.get('USER', 'root')}/{volume_name}"
        ]
        for mount in common_mounts:
            if os.path.ismount(mount) or os.path.exists(mount):
                return mount
        return None


def get_drive_name(letter: str) -> Optional[str]:
    """[LEGACY, NEEDS SUBBED-OUT] Gets drive name from letter."""
    import ctypes, os
    # Normalize drive letter to format like 'C:\\'
    letter = letter.strip(':\\').upper() + ':\\'
    try:
        if not does_drive_exist(letter):
            return None
        volume_name = ctypes.create_unicode_buffer(260)
        result = ctypes.windll.kernel32.GetVolumeInformationW(
            letter,
            volume_name,
            260,
            None, None, None, None, 0
        )
        if result == 0:
            error = ctypes.get_last_error()
            # print(f"[DEBUG] Failed to get volume name for {letter}: Error {error}")
            return None
        volume = volume_name.value.strip()
        # print(f"[DEBUG] Drive {letter} has volume name: '{volume}'")
        return volume if volume else None
    except OSError as e:
        # print(f"[DEBUG] Error accessing drive {letter}: {e}")
        return None


def does_drive_exist(letter: str) -> bool:
    """Checks if a drive exists."""
    import os
    letter = letter.strip(':\\').upper() + ':\\'
    try:
        os.stat(letter)
        # print(f"[DEBUG] Drive {letter} is accessible")
        return True
    except OSError as e:
        # print(f"[DEBUG] Drive {letter} inaccessible: {e}")
        return False


def get_drive_letter(drive_name: str) -> Optional[str]:
    """Gets drive letter from drive name."""
    import ctypes, os
    # print(f"[DEBUG] Searching for drive with name: '{drive_name}'")
    try:
        # Generate drive letters A-Z and filter valid ones
        drives = [f"{chr(i)}:\\" for i in range(65, 91) if does_drive_exist(chr(i))]
        # print(f"[DEBUG] Found drives: {drives}")
        for drive in drives:
            volume_name = get_drive_name(drive)
            if volume_name and volume_name.lower() == drive_name.lower():
                # print(f"[DEBUG] Match found: {drive} -> {volume_name}")
                return drive.rstrip(':\\')
        # print(f"[DEBUG] No drive found with name '{drive_name}'")
        return None
    except Exception as e:
        # print(f"[DEBUG] Error listing drives: {e}")
        return None

def get_drive_size(volume_root: str) -> float:
    """Gets total size of drive/mount in GB."""
    return shutil.disk_usage(volume_root)[0] / 10**9


def get_primary_root_directories(media_types: List[str]) -> List[str]:
    """Returns a list of root directories for primary drives."""
    src_directory = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(src_directory, "..", "config", "alexandria_drives.config")
    drive_config = read_json(filepath)
    primary_drives_dict, _, _ = read_alexandria_config(drive_config)
    
    root_directories = []
    for media_type in media_types:
        for drive_name in primary_drives_dict.get(media_type, []):
            vol_root = get_volume_root(drive_name)
            if vol_root:
                root_directories.append(os.path.join(vol_root, media_type.capitalize()))
    return root_directories


def get_backup_root_directories(media_types: List[str]) -> List[str]:
    """Returns a list of root directories for backup drives."""
    src_directory = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(src_directory, "..", "config", "alexandria_drives.config")
    drive_config = read_json(filepath)
    _, backup_drives_dict, _ = read_alexandria_config(drive_config)
    
    root_directories = []
    for media_type in media_types:
        for drive_name in backup_drives_dict.get(media_type, []):
            vol_root = get_volume_root(drive_name)
            if vol_root:
                root_directories.append(os.path.join(vol_root, media_type.capitalize()))
    return root_directories


def get_time() -> str:
    """Returns current time in 'HHMM on DDMMMYY' format."""
    t = time.localtime()
    hour = time.strftime('%H', t)
    minute = time.strftime('%M', t)
    day = time.strftime('%d', t)
    month = time.strftime('%b', t).upper()
    year = time.strftime('%y', t)
    return f"{hour}{minute} on {day}{month}{year}"


def get_time_elapsed(start_time: float) -> None:
    """Prints the elapsed time since the input time."""
    t_sec = round(time.time() - start_time)
    t_min, t_sec = divmod(t_sec, 60)
    t_hour, t_min = divmod(t_min, 60)
    
    hour_name = 'hour' if t_hour == 1 else 'hours'
    min_name = 'minute' if t_min == 1 else 'minutes'
    sec_name = 'second' if t_sec == 1 else 'seconds'
    
    print(f"\nThis process took: {t_hour} {hour_name}, {t_min} {min_name}, and {t_sec} {sec_name}")


def order_file_contents(file_path: str, numeric: bool = False) -> None:
    """Orders the contents of a file alphabetically or numerically."""
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = [line.strip() for line in file if line.strip()]
        
    if numeric:
        lines.sort(key=lambda x: float(x) if x.replace('.', '', 1).isdigit() else x)
    else:
        lines.sort(key=lambda x: x.lower())
        
    with open(file_path, 'w', encoding='utf-8') as file:
        for line in lines:
            file.write(f"{line}\n")


def get_space_remaining(volume_root: str, unit: str = "GB") -> float:
    """Returns the remaining space on a drive in the specified unit."""
    unit = unit.upper()
    units = {'B': 1, 'KB': 10**3, 'MB': 10**6, 'GB': 10**9, 'TB': 10**12}
    
    if unit not in units:
        raise ValueError(f"Invalid unit '{unit}'. Choose from {list(units.keys())}")

    disk_obj = shutil.disk_usage(volume_root)
    return disk_obj.free / units[unit]


def get_file_size(file_with_path: str, unit: str = "GB") -> float:
    """Returns the size of a file in the specified unit."""
    if not os.path.exists(file_with_path):
        return 0.0
        
    size_bytes = os.path.getsize(file_with_path)
    unit = unit.upper()
    units = {'B': 1, 'KB': 10**3, 'MB': 10**6, 'GB': 10**9, 'TB': 10**12}
    
    if unit not in units:
        raise ValueError(f"Invalid unit '{unit}'. Choose from {list(units.keys())}")
        
    return size_bytes / units[unit]


def format_file_size(size_bytes: float) -> str:
    """Convert file size in bytes to a human-readable string."""
    if size_bytes < 0:
        raise ValueError("Size must be non-negative")

    units = ['bytes', 'kB', 'MB', 'GB', 'TB']
    index = 0
    while size_bytes >= 1024 and index < len(units) - 1:
        size_bytes /= 1024.0
        index += 1
    return f"{size_bytes:.2f} {units[index]}"


def write_list_to_txt_file(
    file_path: str, 
    items: list, 
    bool_append: bool = False,
    bool_sort: bool = False
) -> None:
    """Writes a list of items to a text file."""
    flag = 'a' if bool_append else 'w'
    if bool_sort:
        items = sorted(items, key=lambda x: str(x).lower())
        
    with open(file_path, flag, encoding='utf-8') as file:
        file.write("\n".join(str(item) for item in items))


def read_file_as_list(file_path: str) -> List[str]:
    """Reads a file and returns its contents as a list."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return [line.strip() for line in file if line.strip()]
    except FileNotFoundError:
        return []


def remove_empty_folders(
    directories: List[str],
    print_line_prefix: str = "",
    print_header: str = ""
) -> None:
    """Remove empty subdirectories from a list of directories."""
    if not isinstance(directories, list) or not all(isinstance(d, str) for d in directories):
        raise ValueError("'directories' must be a list of directory paths as strings.")
    
    num_directories_removed = 0

    for directory in directories:
        base_path = Path(directory)
        if not base_path.exists() or not base_path.is_dir():
            continue

        for root, dirs, _ in os.walk(directory, topdown=False):
            for dir_name in dirs:
                try:
                    sub_path = Path(root) / dir_name
                    if not any(sub_path.iterdir()):
                        # Using os.path.sep to be OS-agnostic instead of hardcoded slashes
                        if f"{os.path.sep}Games{os.path.sep}" not in str(sub_path):
                            sub_path.rmdir()
                            if num_directories_removed == 0 and print_header:
                                print(print_header)
                            print(f"{print_line_prefix}{RED}{BRIGHT}Deleted empty subdirectory:{RESET} {sub_path}")
                            num_directories_removed += 1
                except Exception as e:
                    print(f"{print_line_prefix}{YELLOW}Warning: Failed to delete {sub_path}: {e}{RESET}")


def is_hidden(filepath: str | Path) -> bool:
    """Cross-platform check for hidden files."""
    if IS_WINDOWS:
        try:
            attrs = ctypes.windll.kernel32.GetFileAttributesW(str(filepath))
            return bool(attrs & 2)  # FILE_ATTRIBUTE_HIDDEN = 0x2
        except Exception:
            return False
    else:
        return os.path.basename(filepath).startswith('.')


def hide_metadata(drive_config: dict) -> None:
    """Hides metadata files cross-platform."""
    extensions_list = ['.jpg', '.nfo', '.png']
    primary_drives_dict, backup_drives_dict, _ = read_alexandria_config(drive_config)
    
    dirs_base_all = []
    for key, val in primary_drives_dict.items():
        dirs_base_all += [os.path.join(get_volume_root(v), key) for v in val if get_volume_root(v)]
    for key, val in backup_drives_dict.items():
        dirs_base_all += [os.path.join(get_volume_root(v), key) for v in val if get_volume_root(v)]    
        
    filepaths = read_alexandria(dirs_base_all, extensions=extensions_list)
    
    if not filepaths:
        print(f'No {", ".join(extensions_list)} files found!')
        return

    with alive_bar(len(filepaths), title=f'Hiding {", ".join(extensions_list)} files', bar='classic') as bar:
        for filepath in filepaths:
            path_obj = Path(filepath)
            
            # Cross platform path check for /Photos/ or /Courses/
            is_exempt = "Photos" in path_obj.parts or "Courses" in path_obj.parts
            
            if not is_exempt:
                if is_hidden(filepath):
                    bar()
                    continue
                
                print(f'Hiding: {filepath}')
                if IS_WINDOWS:
                    # Windows: Set hidden attribute natively without pywin32
                    attrs = ctypes.windll.kernel32.GetFileAttributesW(str(filepath))
                    ctypes.windll.kernel32.SetFileAttributesW(str(filepath), attrs | 2)
                else:
                    # Linux: Rename file to start with '.'
                    new_path = path_obj.with_name(f".{path_obj.name}")
                    path_obj.rename(new_path)
            else:
                if is_hidden(filepath):
                    print(f'Unhiding file: {filepath}')
                    if IS_WINDOWS:
                        attrs = ctypes.windll.kernel32.GetFileAttributesW(str(filepath))
                        ctypes.windll.kernel32.SetFileAttributesW(str(filepath), attrs & ~2)
                    else:
                        # Linux: Remove the leading '.'
                        if path_obj.name.startswith('.'):
                            new_path = path_obj.with_name(path_obj.name[1:])
                            path_obj.rename(new_path)
            bar()


def rewrite_whitelists_with_year(directory_whitelist: str, primary_drives_dict: dict) -> None:
    """Rewrites all whitelist files with the year in the show title."""
    filepaths_whitelists = [
        os.path.join(directory_whitelist, f) 
        for f in os.listdir(directory_whitelist) 
        if f.endswith(".txt") and 'whitelist' in f.lower()
    ]
    
    primary_shows_dirs = list(set([os.path.join(get_volume_root(x), 'Shows') for x in primary_drives_dict.get('Shows', []) if get_volume_root(x)]))
    show_list = sorted(list(set([Path(fp).parts[-2] for fp in read_alexandria(primary_shows_dirs)])))
    
    primary_anime_dirs = list(set([os.path.join(get_volume_root(x), 'Anime') for x in primary_drives_dict.get('Anime', []) if get_volume_root(x)]))
    anime_list = sorted(list(set([Path(fp).parts[-2] for fp in read_alexandria(primary_anime_dirs)])))
    
    for filepath in filepaths_whitelists:
        whitelist = read_file_as_list(filepath)
        whitelist_items = set()
        
        for wl_item in whitelist:
            for anime in anime_list:
                if wl_item in anime:
                    whitelist_items.add(anime.strip())
            for show in show_list:
                if wl_item in show:
                    whitelist_items.add(show.strip())
                    
        write_list_to_txt_file(filepath, list(whitelist_items), bool_sort=True)


def delete_metadata_wip(volume_root: str, file_extensions: List[str] = ['.jpg', '.nfo', '.png', '.jpeg', '.info', '.srt']) -> None:
    """Deletes metadata files from a drive/mount."""
    directories = [
        os.path.join(volume_root, 'Movies'),
        os.path.join(volume_root, 'Shows'),
        os.path.join(volume_root, 'Anime'),
        os.path.join(volume_root, '4K Movies')
    ]
    
    filepaths = read_alexandria(directories, extensions=file_extensions)
    
    if filepaths:
        with alive_bar(len(filepaths), title='Deleting files', bar='classic') as bar:
            for fp in filepaths:
                try:
                    os.remove(fp)
                except OSError as e:
                    print(f"Error deleting {fp}: {e}")
                bar()
    else:
        print(f'No matching metadata files found in {volume_root}!')


def delete_empty_dirs(root_dir: str, approved_extensions: list, dry_run: bool = False, confirm_deletion: bool = True) -> None:
    """Delete directories that do not contain files with approved extensions."""
    dirs_to_delete = []
    
    for dirpath, _, filenames in os.walk(root_dir, topdown=False):
        has_approved_files = any(
            os.path.splitext(filename)[1].lower() in approved_extensions 
            for filename in filenames
        )
        if not has_approved_files and dirpath != root_dir:
            dirs_to_delete.append(dirpath)
            
    if dry_run:
        print("Dry run mode: The following directories would be deleted:")
        for dirpath in dirs_to_delete:
            print(dirpath)
        return
        
    for dirpath in dirs_to_delete:
        if confirm_deletion:
            while True:
                response = input(f"Delete directory: {dirpath}? (y/n): ").strip().lower()
                if response == 'n':
                    print(f"Skipping: {dirpath}")
                    break
                elif response == 'y':
                    print(f"Deleting: {dirpath}")
                    shutil.rmtree(dirpath)
                    break
                print('\nInvalid response\n')
        else:
            shutil.rmtree(dirpath)


def human_readable_size(size_in_gb: float) -> Tuple[float, str]:
    """Converts gigabytes into standard scaled readable formats."""
    size_in_bytes = size_in_gb * (1024 ** 3)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_in_bytes < 1024:
            return size_in_bytes, unit
        size_in_bytes /= 1024
    return size_in_bytes, "TB"
