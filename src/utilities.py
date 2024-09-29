#!/usr/bin/env python

def import_libraries(libraries):
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

def read_alexandria(parent_dirs : list,extensions = ['.mp4','.mkv','.pdf','.mp3']) -> list[list[str], list[str]]:
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
    for p in parent_dirs:
        walk = sorted(list([x for x in os.walk(p) if x[2] != []]))
        for w in walk:
            # identify parent dir in filepath
            parent_path = w[0]
            # correct hanging slash error
            if parent_path[-1] == '/' or parent_path[-1] == '\\': parent_path = parent_path[:-1]
            # generate file list of specific extensions
            file_list = [f for f in w[-1] if '.'+f.split('.')[-1] in extensions]
            # generate list of filepaths
            for i,f in enumerate(file_list):
                all_filepaths.append((parent_path+'/'+f).replace('\\','/'))
    return all_filepaths

def files_are_identical(file1 : str, file2 : str) -> bool:
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

def read_json(filepath):
    import json
    with open(filepath, 'r', encoding='utf8') as json_file:
        json_data = json.load(json_file)
    return json_data

def get_json_file_list(directory):
    import os
    list_json_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.json'):
                list_json_files.append(os.path.join(root, file))
    return list_json_files

def write_to_csv(output_filepath,data_array,header):
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
        
def read_alexandria_config(drive_hieracrchy):
    """
    Returns dictionarys identifying primary and backup drives by media type

    Parameters
    ----------
    drive_hieracrchy : dict
        Drive hierarchy dictionary item.

    Returns
    -------
    primary_drives_dict : dict
        Primary drives by media type.
    backup_drives_dict : dict
        Backup drives by media type.

    """
    primary_drives_dict = {}; backup_drives_dict = {}; extensions_dict = {}
    for media_type in drive_hieracrchy:
        primary_drives = drive_hieracrchy[media_type]['primary_drives']
        primary_drives_dict.update({media_type:primary_drives})
        backup_drives = drive_hieracrchy[media_type]['backup_drives']
        backup_drives_dict.update({media_type:backup_drives})
        extensions = drive_hieracrchy[media_type]['extensions']
        extensions_dict.update({media_type:extensions})
    return primary_drives_dict, backup_drives_dict, extensions_dict

def get_drive_name(letter):
    """
    Gets drive name from letter.

    Parameters
    ----------
    letter : str
        Drive letter [A-Z] (Windows).

    Returns
    -------
    str
        Returns name of the drive, as displayed in file explorer.

    """
    import win32api
    if does_drive_exist(letter): 
        return win32api.GetVolumeInformation(f"{letter}:/")[0]
    else: 
        return "None"

def does_drive_exist(letter):
    """
    Checks if a drive exists. 

    Parameters
    ----------
    letter : str
        Drive letter [A-Z] (Windows).

    Returns
    -------
    bool
        Returns TRUE if drive exists, otherwise returns FALSE.
        
    """
    import win32api
    try: 
        win32api.GetVolumeInformation(f"{letter}:/")
        return True
    except:
        return False

def get_drive_letter(drive_name):
    """
    Gets drive letter from drive name.

    Parameters
    ----------
    drive_name : str
        Drive name.

    Returns
    -------
    d : str
        Drive letter [A-Z] (Windows).

    """
    import win32api
    drives = [drive[0] for drive in win32api.GetLogicalDriveStrings().split('\000')[:-1] if does_drive_exist(drive[0])]
    for d in drives:
        if get_drive_name(d) == drive_name:
            return d
    return ''

def get_drive_size(letter):
    """
    Gets size of drive.

    Parameters
    ----------
    letter : str
        Drive letter [A-Z] (Windows).

    Returns
    -------
    float
        Size of drive in GB.

    """
    import shutil
    return shutil.disk_usage(f'{letter}:/')[0]/10**9

def get_time():
    """
    Returns current time.
    
    Returns
    -------
    curr_time: str
        Time in 'TTTT on DDMMMYYYY' format.
        
    """
    import time
    time_dict = {'dotw':time.ctime().split()[0],'month':time.ctime().split()[1],'day':time.ctime().split()[2],
                 'hour_24_clock':time.ctime().split()[3].split(':')[0],'minute':time.ctime().split()[3].split(':')[1],
                 'second':time.ctime().split()[3].split(':')[2],'year':time.ctime().split()[4]}
    if len(time_dict["minute"]) < 2: time_dict['minute'] = '0'+time.ctime().split()[3].split(':')[1]
    if len(time_dict["day"]) < 2: time_dict['day'] = '0'+time.ctime().split()[2]
    curr_time = f'{time_dict["hour_24_clock"]}{time_dict["minute"]} on {time_dict["day"]}{time_dict["month"].upper()}{time_dict["year"][2:]}'
    return curr_time

def get_time_elapsed(start_time):
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

def order_file_contents(file_path, numeric=False):
    # Read the file content
    with open(file_path, 'r') as file:
        lines = file.readlines()
    # Remove any leading/trailing whitespace from each line (including newlines)
    lines = [line.strip() for line in lines]
    # Sort the lines numerically or alphabetically
    if numeric:
        lines.sort(key=lambda x: float(x) if x.replace('.', '', 1).isdigit() else x)
    else:
        lines.sort()
    # Write the sorted content back to the file
    with open(file_path, 'w') as file:
        for line in lines:
            file.write(f"{line}\n")
    print(f"Contents of '{file_path}' have been ordered.")

def get_space_remaining(drive):
    import shutil
    disk_obj = shutil.disk_usage(f'{drive}:/')
    gb_remaining = int(disk_obj[2]/10**9)
    return gb_remaining

def get_file_size(file_with_path):
    import os
    return os.path.getsize(file_with_path)/10**9

def write_list_to_txt_file(file_path, items, bool_append = False):
    flag = 'a' if bool_append else 'w'
    with open(file_path, flag,encoding='utf-8') as file:
        for i, item in enumerate(items):
            if i < len(items) - 1:
                file.write(f"{item}\n")
            else:
                file.write(f"{item}")

def read_file_as_list(file_path):
    with open(file_path, 'r') as file:
        lines = file.readlines()
    return [line.strip() for line in lines]

def remove_empty_folders(directories):
    import os
    for directory in directories:
        # Walk through all subdirectories and delete any that are empty
        for root, dirs, files in os.walk(directory, topdown=False):
            for dir in dirs:
                subdirectory_path = os.path.join(root, dir)
                if not os.listdir(subdirectory_path):  # Check if the directory is empty
                    os.rmdir(subdirectory_path)
                    print(f"Deleted empty subdirectory: {subdirectory_path}")