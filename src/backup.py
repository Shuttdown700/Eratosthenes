#!/usr/bin/env python

# define libraries
libraries = [['os']]
from utilities import read_alexandria_config, get_drive_letter, get_drive_name, get_file_size, get_space_remaining, import_libraries
import_libraries(libraries)

from colorama import Fore, Back, Style
from utilities import read_alexandria, read_json

def determine_movie_rating(data_filepath):
    df_movie_ratings = []
    return df_movie_ratings

def assess_backup_feasibility(tuple_filepaths_missing):
    drives_backup = list(set([x[1][0] for x in tuple_filepaths_missing]))
    remaining_space = 0
    for drive in drives_backup:
        remaining_space = get_space_remaining(drive)
    required_space = 0
    for filepath in tuple_filepaths_missing:
        required_space += get_file_size(filepath[0])
    return required_space, remaining_space

def remove_excess_files(filepaths_excess):
    ui = ''
    if len(filepaths_excess) > 0:
        print(f'\n{Back.RED}The following {len(filepaths_excess):,.2f} files are not in the primary drives:')
        for excess_file in filepaths_excess:
            print(excess_file[1:])
        ui = ''
        while ui != 'n' and ui != 'y':
            if len(filepaths_excess) > 1:
                ui = input(f'\nDo you want to delete these {len(filepaths_excess)} items? [Y/N] {Style.RESET_ALL}').lower()
            else:
                ui = input(f'\nDo you want to delete this item? [Y/N] {Style.RESET_ALL}').lower()
    if ui.lower() == 'y':
        for excess_file in filepaths_excess:
            print(f'Deleting: {excess_file}')
            os.remove(excess_file)

def backup_function(backup_tuples):
    """
    Batch back-up function

    Parameters
    ----------
    backup_tuples : tuple
        Tuple of backup pairs. Format: (src,dest)

    Returns
    -------
    None.

    """
    # import libraries
    import os, subprocess
    # loop through backup tuples 
    for bt in backup_tuples:
        # reading backup tuple
        sfile = fr'{bt[0]}'
        dfile = fr'{bt[1]}'
        file_title = sfile.split('/')[-1][:-4].strip()
        # ensure source file exisits (reduces errors)
        if os.path.isfile(sfile):
            dpath = os.path.dirname(dfile)
            if not os.path.exists(dpath):
                os.makedirs(dpath)
            # backup the missing file
            print(f'{Fore.YELLOW}{Style.BRIGHT}Backing up{Style.RESET_ALL} {file_title} from {Fore.BLUE}{Style.BRIGHT}{get_drive_name(sfile[0])}{Style.RESET_ALL} to {Fore.GREEN}{Style.BRIGHT}{get_drive_name(dfile[0])}{Style.RESET_ALL}')
            cmd = fr'copy "{sfile}" "{dfile}"'.replace('/','\\')
            subprocess.call(cmd, shell=True, stdout=subprocess.PIPE)

def backup(media_type, primary_filepaths_dict, backup_drive_letter_dict):
    # define primary filepaths
    filepaths_primary = primary_filepaths_dict[media_type]
    filepaths_primary_noLetter = [filepath[1:] for filepath in filepaths_primary]
    # define backup filepaths
    backup_paths = [f'{x}:/{media_type}' for x in backup_drive_letter_dict[media_type]]
    filepaths_backup = read_alexandria(backup_paths,extensions_dict[media_type])
    filepaths_backup_noLetter = [filepath[1:] for filepath in filepaths_backup]
    # determine missing filepaths
    tuple_filepaths_missing = []
    for index_primary, primary_filepath in enumerate(filepaths_primary_noLetter):
        if primary_filepath not in filepaths_backup_noLetter:
            sfile = filepaths_primary[index_primary][0]+primary_filepath
            dfile = filepaths_backup[-1][0]+primary_filepath
            backup_tuple = (sfile,dfile)
            tuple_filepaths_missing.append(backup_tuple)
    # determine excess filepaths
    filepaths_excess = []
    for index_backup, backup_filepath in enumerate(filepaths_backup_noLetter):
        if backup_filepath not in filepaths_primary_noLetter:
            filepaths_excess.append(filepaths_backup[index_backup][0]+backup_filepath)
    return tuple_filepaths_missing, filepaths_excess

if __name__ == '__main__':
    import os
    # define paths
    src_directory = os.path.dirname(os.path.abspath(__file__))
    drive_hieracrchy_filepath = (src_directory+"/config/alexandria_drives.config").replace('\\','/')
    output_directory = ("\\".join(src_directory.split('\\')[:-1])+"/output").replace('\\','/')
    drive_config = read_json(drive_hieracrchy_filepath)
    # define primary & backup drives
    primary_drives_dict, backup_drives_dict, extensions_dict = read_alexandria_config(drive_config)
    primary_drive_letter_dict = {}; backup_drive_letter_dict = {}
    for key,value in primary_drives_dict.items(): primary_drive_letter_dict[key] = [get_drive_letter(x) for x in value]
    for key,value in backup_drives_dict.items(): backup_drive_letter_dict[key] = [get_drive_letter(x) for x in value]
    # define media types
    media_types = list(primary_drives_dict.keys())
    # define primary filepaths
    primary_filepaths_dict = {}
    for media_type in media_types:
        
        " Need to loop through each identified backup drive one their own"
        
        
        if media_type not in ["Books","Music","4K Movies","Movies","Anime Movies"]: continue
        primary_paths = [f'{x}:/{media_type}' for x in primary_drive_letter_dict[media_type]]
        primary_filepaths = read_alexandria(primary_paths,extensions_dict[media_type])
        primary_filepaths_dict[media_type] = primary_filepaths
        tuple_filepaths_missing, filepaths_excess = backup(media_type, primary_filepaths_dict, backup_drive_letter_dict)
        remove_excess_files(filepaths_excess)
        required_space, remaining_space = assess_backup_feasibility(tuple_filepaths_missing)
        backup_function(tuple_filepaths_missing)
        

"""
SCHEME:
    DONE --- identify primary drives (from config file)
    DONE --- identify backup drives (from config file)
    DONE --- read the primary files (all at beginning of sequence)
    DONE --- read backup drives (individually)
    identify missing files
    assess backup feasibility
    backup missing files
    identify updated files
    assess update feasibility
    replace updated files
    loop to next drive / conclude

"""


"""
TEMP:
"""

