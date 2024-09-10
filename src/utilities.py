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

def read_alexandria(parent_dirs,extensions = ['.mp4','.mkv','.pdf','.mp3']) -> list[list[str], list[str]]:
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



def read_json(filepath):
    import json
    with open(filepath, 'r', encoding='utf8') as json_file:
        json_data = json.load(json_file)
    return json_data

def write_to_csv(output_filepath,data_array,header):
    import csv
    # Writing to CSV file
    with open(output_filepath, mode='w', newline='', encoding='utf8') as file:
        writer = csv.writer(file)
        # Write the headers
        writer.writerow(header)
        # Write the data
        writer.writerows(data_array)
        
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


