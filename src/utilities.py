#!/usr/bin/env python

from typing import Optional

def import_libraries(libraries: list) -> None:
    """
    Helps load/install required libraries when running from cmd prompt

    Parameters
    ----------
    libraries : list
        List of libraries.

    Returns
    -------
    None.

    """
    import subprocess
    import warnings
    warnings.filterwarnings("ignore")
    exec('warnings.filterwarnings("ignore")')
    aliases = {'numpy':'np','pandas':'pd','matplotlib.pyplot':'plt'}
    for s in libraries:
        try:
            exec(f"import {s[0]} as {aliases[s[0]]}") if s[0] in list(aliases.keys()) else exec(f"import {s[0]}")
        except ImportError:
            print(f'Installing... {s[0].split(".")[0]}')
            cmd = f'python -m pip install {s[0].split(".")[0]}'
            subprocess.call(cmd, shell=True, stdout=subprocess.PIPE)
        if len(s) == 1: continue
        for sl in s[1]:
            exec(f'from {s[0]} import {sl}')

def read_alexandria(parent_dirs : list,extensions: list[str] = ['.mp4','.mkv','.pdf','.mp3']) -> list:
    """
    Returns all files of a given extension from a list of parent directories

    Parameters
    ----------
    parent_dirs : list
        Parent directories to be searched through.
    extensions : list, optional
        Extensions to search for. The defaults are '.mp4' & '.mkv'.

    Returns
    -------
    all_titles : list
        A list of all filenames, excluding the extension.
    all_paths : list
        A list of all paths to corresponding files.
        
    """
    # import libraries
    import os
    # assert correction arguments
    assert isinstance(parent_dirs,list) and isinstance(extensions,list), "One or more arguments are not in list type."
    all_filepaths = []
    for idx_p,p in enumerate(parent_dirs):
        walk = sorted(list([x for x in os.walk(p) if x[2] != []]))
        for w in walk:
            # identify parent dir in filepath
            parent_path = w[0]
            # correct hanging slash error
            if parent_path[-1] == '/' or parent_path[-1] == '\\': parent_path = parent_path[:-1]
            # generate file list of specific extensions
            if isinstance(extensions[0],list) and len(extensions) >= idx_p+1:
                extension_list = extensions[idx_p]
            else:
                extension_list = extensions
            file_list = [f for f in w[-1] if '.'+f.split('.')[-1] in extension_list]
            # generate list of filepaths
            for idx_f,f in enumerate(file_list):
                all_filepaths.append((parent_path+'/'+f).replace('\\','/'))
    return all_filepaths

def files_are_identical(file1 : str, file2: str) -> bool:
    """
    Determines if two files are the same

    Parameters
    ----------
    file1 : str
        Filepath to file 1.
    file2 : str
        Filepath to file 2.

    Returns
    -------
    bool
        Returns TRUE if the input files are identical.

    """
    import os
    # Check if the file sizes are different
    if os.path.getsize(file1) != os.path.getsize(file2):
        return False # files are different
    else:
        return True # files are identical

def read_json(filepath: str) -> dict:
    import json
    with open(filepath, 'r', encoding='utf8') as json_file:
        json_data = json.load(json_file)
    return json_data

def get_json_file_list(directory: str) -> list:
    import os
    list_json_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.json'):
                list_json_files.append(os.path.join(root, file))
    return list_json_files

def write_to_csv(output_filepath: str,data_array: list,header: str) -> None:
    import csv
    # Writing to CSV file
    with open(output_filepath, mode='w', newline='', encoding='utf8') as file:
        writer = csv.writer(file)
        # Write the headers
        writer.writerow(header)
        # Write the data
        writer.writerows(data_array)

def read_csv(file_path: str) -> list[dict]:
    """
    Reads a csv file

    Parameters
    ----------
    file_path : str
        File path to csv file.

    Returns
    -------
    csv_data : list of dict rows
        list of rows, with each row in dict form.

    """
    import csv
    try:
        with open(file_path, mode='r', newline='',encoding='utf-8') as file:
            reader = csv.DictReader(file)
            csv_data = [row for row in reader]
    except FileNotFoundError:
        return []
    return csv_data

def read_alexandria_config(drive_hieracrchy: dict) -> tuple[dict,dict,dict]:
    """Returns dictionarys identifying primary and backup drives by media type."""
    primary_drives_dict = {}; backup_drives_dict = {}; extensions_dict = {}
    for media_type in drive_hieracrchy:
        primary_drives = drive_hieracrchy[media_type]['primary_drives']
        primary_drives_dict.update({media_type:primary_drives})
        try:
            backup_drives = sorted(drive_hieracrchy[media_type]['backup_drives'].keys())
        except AttributeError:
            backup_drives = drive_hieracrchy[media_type]['backup_drives']
        backup_drives_dict.update({media_type:backup_drives})
        extensions = drive_hieracrchy[media_type]['extensions']
        extensions_dict.update({media_type:extensions})
    return primary_drives_dict, backup_drives_dict, extensions_dict

def get_drive_name(letter: str) -> Optional[str]:
    """Gets drive name from letter."""
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

def get_drive_size(letter: str) -> float:
    """Gets size of drive."""
    import shutil
    return shutil.disk_usage(f'{letter}:/')[0]/10**9

def get_time() -> str:
    """Returns current time in 'TTTT on DDMMMYYYY' format."""
    import time
    time_dict = {'dotw':time.ctime().split()[0],'month':time.ctime().split()[1],'day':time.ctime().split()[2],
                 'hour_24_clock':time.ctime().split()[3].split(':')[0],'minute':time.ctime().split()[3].split(':')[1],
                 'second':time.ctime().split()[3].split(':')[2],'year':time.ctime().split()[4]}
    if len(time_dict["minute"]) < 2: time_dict['minute'] = '0'+time.ctime().split()[3].split(':')[1]
    if len(time_dict["day"]) < 2: time_dict['day'] = '0'+time.ctime().split()[2]
    curr_time = f'{time_dict["hour_24_clock"]}{time_dict["minute"]} on {time_dict["day"]}{time_dict["month"].upper()}{time_dict["year"][2:]}'
    return curr_time

def get_time_elapsed(start_time: float) -> None:
    """
    Prints the elapsed time since the input time.
    
    Parameters
    ----------
    start_time : float
        Time as a floating pouint number in seconds.

    Returns
    -------
    None.
    
    """
    import time
    hour_name, min_name, sec_name = 'hours', 'minutes', 'seconds'
    t_sec = round(time.time() - start_time)
    (t_min, t_sec) = divmod(t_sec,60)
    (t_hour,t_min) = divmod(t_min,60)
    if t_hour == 1: hour_name = 'hour'
    if t_min == 1: min_name = 'msinute'
    if t_sec == 1: sec_name = 'second'
    print(f'\nThis process took: {t_hour} {hour_name}, {t_min} {min_name}, and {t_sec} {sec_name}')

def order_file_contents(file_path: str, numeric=False) -> None:
    """Orders the contents of a file alphabetically or numerically."""
    # Read the file content
    with open(file_path, 'r') as file:
        lines = file.readlines()
    # Remove any leading/trailing whitespace from each line (including newlines)
    lines = [line.strip() for line in lines if line.strip()]
    # Sort the lines numerically or alphabetically
    if numeric:
        lines.sort(key=lambda x: float(x) if x.replace('.', '', 1).isdigit() else x)
    else:
        lines.sort()
    # Write the sorted content back to the file
    with open(file_path, 'w') as file:
        for line in lines:
            file.write(f"{line}\n")
    # print(f"Contents of '{file_path}' have been ordered.")

def get_space_remaining(drive: str, unit: str = "GB") -> float:
    """
    Returns the remaining space on a drive in the specified unit.
    """
    import shutil
    unit = unit.upper()
    units = {
        'B': 1,
        'KB': 10**3,
        'MB': 10**6,
        'GB': 10**9,
        'TB': 10**12
    }
    if unit not in units:
        raise ValueError(f"Invalid unit '{unit}'. Choose from {list(units.keys())}")

    disk_obj = shutil.disk_usage(f'{drive}:/')
    remaining = disk_obj.free / units[unit]
    return remaining

def get_file_size(file_with_path: str, unit: str = "GB") -> float:
    """
    Returns the size of a file in the specified unit.
    """
    import os
    if not os.path.exists(file_with_path):
        return 0.0
    size_bytes = os.path.getsize(file_with_path)
    unit = unit.upper()
    units = {
        'B': 1,
        'KB': 10**3,
        'MB': 10**6,
        'GB': 10**9,
        'TB': 10**12
    }
    if unit not in units:
        raise ValueError(f"Invalid unit '{unit}'. Choose from {list(units.keys())}")
    return size_bytes / units[unit]

def format_file_size(size_bytes):
    """Convert file size in bytes to a human-readable string."""
    if size_bytes < 0:
        raise ValueError("Size must be non-negative")

    units = ['bytes', 'kB', 'MB', 'GB', 'TB']
    index = 0
    while size_bytes >= 1024 and index < len(units) - 1:
        size_bytes /= 1024.0
        index += 1
    return f"{size_bytes:.2f} {units[index]}"

def write_list_to_txt_file(file_path: str, items: list, bool_append: bool = False) -> None:
    """Writes a list of items to a text file."""
    flag = 'a' if bool_append else 'w'
    with open(file_path, flag,encoding='utf-8') as file:
        for i, item in enumerate(items):
            if i < len(items) - 1:
                file.write(f"{item}\n")
            else:
                file.write(f"{item}")

def read_file_as_list(file_path: str) -> list:
    """Reads a file and returns its contents as a list."""
    with open(file_path, 'r',encoding='utf-8') as file:
        lines = file.readlines()
    return [line.strip() for line in lines]

def remove_empty_folders(
    directories: list[str],
    print_line_prefix: str = "",
    print_header: str = ""
) -> None:
    """
    Remove empty subdirectories from a list of directories.

    Args:
        directories (List[str]): List of directory paths to scan.
        print_line_prefix (str, optional): Prefix for printed messages.
        print_header (str, optional): Header to print before the first deletion message.

    Raises:
        ValueError: If 'directories' is not a list of strings.
    """
    import os
    from pathlib import Path
    from colorama import Fore, Style
    # Validate input
    if not isinstance(directories, list) or not all(isinstance(d, str) for d in directories):
        raise ValueError("'directories' must be a list of directory paths as strings.")
    
    num_directories_removed = 0

    for directory in directories:
        base_path = Path(directory)
        if not base_path.exists() or not base_path.is_dir():
            # print(f"{print_line_prefix}{Fore.YELLOW}Warning: Directory not found or not a directory:{Style.RESET_ALL} {directory}")
            continue

        # Walk from bottom up
        for root, dirs, _ in os.walk(directory, topdown=False):
            for dir_name in dirs:
                try:
                    sub_path = Path(root) / dir_name
                    if not any(sub_path.iterdir()):  # Check if empty
                        if '/Games/' not in str(sub_path).replace("\\", "/"):
                            sub_path.rmdir()
                            if num_directories_removed == 0 and print_header:
                                print(print_header)
                            print(f"{print_line_prefix}{Fore.RED}{Style.BRIGHT}Deleted empty subdirectory:{Style.RESET_ALL} {sub_path}")
                            num_directories_removed += 1
                except Exception as e:
                    print(f"{print_line_prefix}{Fore.YELLOW}Warning: Failed to delete {sub_path}: {e}{Style.RESET_ALL}")

    if num_directories_removed == 0:
        print(f"{print_line_prefix}{Fore.GREEN}No empty directories found.{Style.RESET_ALL}")

def hide_metadata(drive_config: dict) -> None:
    """Hides metadata files in the specified drives."""
    import ctypes, os, stat, win32con, win32api
    from alive_progress import alive_bar
    extensions_list = ['.jpg','.nfo','.png']
    primary_drives_dict, backup_drives_dict = read_alexandria_config(drive_config)[:2]
    dirs_base_all = []
    for key,val in primary_drives_dict.items():
        dirs_base_all += [f'{get_drive_letter(v)}:/{key}' for v in val]
    for key,val in backup_drives_dict.items():
        dirs_base_all += [f'{get_drive_letter(v)}:/{key}' for v in val]    
    filepaths = read_alexandria(dirs_base_all,extensions=extensions_list)
    if len(filepaths) > 0:
        with alive_bar(len(filepaths),ctrl_c=False,dual_line=False,title=f'Hiding {", ".join(extensions_list)} files',bar='classic',spinner='classic') as bar:
            for filepath in filepaths:
                if '/Photos/' not in filepath.replace('\\','/') and '/Courses/' not in filepath.replace('\\','/'): # if not in /Photos/
                    fa = os.stat(filepath).st_file_attributes
                    if bool(fa & stat.FILE_ATTRIBUTE_HIDDEN): # if hidden, skip
                        bar()
                        continue
                    print(f'Hiding: {filepath}')
                    win32api.SetFileAttributes(filepath,win32con.FILE_ATTRIBUTE_HIDDEN)
                    bar()
                else: # if in /Photos/ or /Courses/
                    if ctypes.windll.kernel32.GetFileAttributesW(filepath) & 2: # if hidden, unhide it
                        print(f'Unhiding photo file: {filepath}')
                        attrs = ctypes.windll.kernel32.GetFileAttributesW(filepath)
                        ctypes.windll.kernel32.SetFileAttributesW(filepath, attrs & ~2)
                        bar()
                        continue
                    bar()
    else:
        print(f'No {", ".join(extensions_list)} files in any of the {len(dirs_base_all)} {"drive" if len(dirs_base_all) == 1 else "drives"}!')

def rewrite_whitelists_with_year(directory_whitelist: str,primary_drives_dict: dict) -> None:
    """Rewrites all whitelist files with the year in the show title."""
    import os
    filepaths_whitelists = []
    # Iterate through all files in the directory
    primary_drives_shows = list(set([f'{get_drive_letter(x)}:/Shows/' for x in primary_drives_dict['Shows']]))
    show_list = sorted(list(set([filepath.split('/')[2] for filepath in read_alexandria(primary_drives_shows)])))
    primary_drives_anime = list(set([f'{get_drive_letter(x)}:/Anime/' for x in primary_drives_dict['Anime']]))
    anime_list = sorted(list(set([filepath.split('/')[2] for filepath in read_alexandria(primary_drives_anime)])))
    for file_name in os.listdir(directory_whitelist):
        if file_name.endswith(".txt") and 'whitelist' in file_name.lower():
            filepaths_whitelists.append(os.path.join(directory_whitelist,file_name).replace('\\','/'))
    for filepath_whitelist in filepaths_whitelists:
        whitelist_items = []
        whitelist = read_file_as_list(filepath_whitelist)
        for wl_item in whitelist:
            for anime in anime_list:
                if wl_item in anime:
                    whitelist_items.append(anime.strip())
            for show in show_list:
                if wl_item in show:
                    whitelist_items.append(show.strip())
        whitelist_items = sorted(list(set(whitelist_items)))
        write_list_to_txt_file(filepath_whitelist,whitelist_items)

def delete_metadata_wip(drive: str,file_extensions: list[str] = ['.jpg','.nfo','.png','.jpeg','.info','.srt']) -> None:
    """Deletes metadata files from a drive."""
    import os
    from alive_progress import alive_bar
    for e in file_extensions:
        file_names, file_paths = read_alexandria([f'{drive}:/Movies/',f'{drive}:/Shows/',f'{drive}:/Anime/',f'{drive}:/4K Movies/'],extensions = [e])
        file_names_with_path = [file_paths[i]+'/'+file_names[i] for i in range(len(file_paths))]
        if len(file_names_with_path) > 0:
            with alive_bar(len(file_names_with_path),ctrl_c=False,dual_line=False,title=f'Deleting {e} files',bar='classic',spinner='classic') as bar:
                for fnwp in file_names_with_path:
                    os.remove(fnwp)
                    bar()
        else:
            print(f'No {e} files in {drive} drive!')

def delete_empty_dirs(root_dir: str, approved_extensions: list, dry_run: bool = False, confirm_deletion: bool = True) -> None:
    """Delete directories that do not contain files with approved extensions."""
    import os, shutil
    dirs_to_delete = []
    # Traverse the directory tree from the bottom up to safely remove directories
    for dirpath, dirnames, filenames in os.walk(root_dir, topdown=False):
        # Check if there are files with approved extensions
        has_approved_files = any(
            os.path.splitext(filename)[1].lower() in approved_extensions 
            for filename in filenames
        )
        # If no approved files are found and the directory is not the root, add to the list
        if not has_approved_files and dirpath != root_dir:
            dirs_to_delete.append(dirpath)
    if dry_run:
        print("Dry run mode: The following directories would be deleted:")
        for dirpath in dirs_to_delete:
            print(dirpath)
        return
    # If not dry run, proceed with deletion (with optional confirmation)
    for dirpath in dirs_to_delete:
        if confirm_deletion:
            response = ''
            while True:
                response = input(f"Do you want to delete the directory: {dirpath}? (y/n): ").strip().lower()
                if response == 'n':
                    print(f"Skipping directory: {dirpath}")
                    break
                elif response == 'y':
                    print(f"Deleting directory: {dirpath}")
                    shutil.rmtree(dirpath)
                    break
                print('\nInvalid response\n')

def human_readable_size(size_in_gb):
    size_in_bytes = size_in_gb * (1024 ** 3)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_in_bytes < 1024:
            return size_in_bytes, unit
        size_in_bytes /= 1024
    return size_in_bytes, "TB"

def main() -> None:
    """Main function to run the utility functions."""      
    # define paths
    # import os
    # src_directory = os.path.dirname(os.path.abspath(__file__))
    # drive_hieracrchy_filepath = (src_directory+"/config/alexandria_drives.config").replace('\\','/')
    # output_directory = ("\\".join(src_directory.split('\\')[:-1])+"/output").replace('\\','/')
    # key_directory = ("\\".join(src_directory.split('\\')[:-1])+"/keys").replace('\\','/')
    # directory_whitelist = (src_directory+"/config/show_whitelists").replace('\\','/')
    # drive_config = read_json(drive_hieracrchy_filepath)
    # primary_drives_dict, backup_drives_dict = read_alexandria_config(drive_config)[:2]
    # dirs_base_all = []; dirs_base_primary = []; dirs_base_backup = []
    # for key,val in primary_drives_dict.items():
    #     dirs_base_primary += [f'{get_drive_letter(v)}:/{key}' for v in val]
    # for key,val in backup_drives_dict.items():
    #     dirs_base_backup += [f'{get_drive_letter(v)}:/{key}' for v in val]
    # dirs_base_all = dirs_base_primary + dirs_base_backup
    # # rewrite_whitelists_with_year(directory_whitelist,primary_drives_dict)
    # hide_metadata(drive_config)
    # remove_empty_folders(dirs_base_all)
    # generate_ssl_key_and_cert(key_directory)
    # Test the functions
    print(does_drive_exist('C'))

if __name__ == '__main__':
    main()
