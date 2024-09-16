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
        print(f'\n{Back.RED}The following {len(filepaths_excess)} {"file is" if len(filepaths_excess) == 1 else "files are"} not in the primary drives: {Style.RESET_ALL}')
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
            print(f'{Fore.YELLOW}{Style.BRIGHT}Backing up{Style.RESET_ALL} {file_title} {Fore.RED}{Style.BRIGHT}|{Style.RESET_ALL} {Fore.BLUE}{Style.BRIGHT}{get_drive_name(sfile[0])}{Style.RESET_ALL} -> {Fore.GREEN}{Style.BRIGHT}{get_drive_name(dfile[0])}{Style.RESET_ALL}')
            cmd = fr'copy "{sfile}" "{dfile}"'.replace('/','\\')
            subprocess.call(cmd, shell=True, stdout=subprocess.PIPE)

def backup_mapper(media_type, primary_filepaths_dict, backup_drive_letter_dict):
    import os
    # define primary filepaths
    filepaths_primary = primary_filepaths_dict[media_type]
    filepaths_primary_noLetter = [filepath[1:] for filepath in filepaths_primary]
    # define backup filepaths
    backup_paths = [f'{x}:/{media_type}' for x in backup_drive_letter_dict[media_type]]
    [os.makedirs(directory, exist_ok=True) for directory in backup_paths]
    filepaths_backup = read_alexandria(backup_paths,extensions_dict[media_type])
    filepaths_backup_noLetter = [filepath[1:] for filepath in filepaths_backup]
    # determine missing & existing backup filepaths
    tuple_filepaths_missing = []
    tuple_filepaths_existing_backup = []
    for index_primary, primary_filepath in enumerate(filepaths_primary_noLetter):
        if primary_filepath not in filepaths_backup_noLetter:
            sfile = filepaths_primary[index_primary][0]+primary_filepath
            try:
                dfile = filepaths_backup[-1][0]+primary_filepath
            except IndexError:
                dfile = backup_paths[-1][0]+primary_filepath
            backup_tuple = (sfile,dfile)
            tuple_filepaths_missing.append(backup_tuple)
        else:
            sfile = filepaths_primary[index_primary][0]+primary_filepath
            try:
                bfile = filepaths_backup[-1][0]+primary_filepath
            except IndexError:
                bfile = backup_paths[-1][0]+primary_filepath
            backup_tuple = (sfile,bfile)
            tuple_filepaths_existing_backup.append(backup_tuple)
    # determine excess filepaths
    filepaths_excess = []
    for index_backup, backup_filepath in enumerate(filepaths_backup_noLetter):
        if backup_filepath not in filepaths_primary_noLetter:
            filepaths_excess.append(filepaths_backup[index_backup][0]+backup_filepath)
    return tuple_filepaths_missing, filepaths_excess, tuple_filepaths_existing_backup

def backup_integrity():
    # assess if files are the same
    
    # determine which files need to be overwritten
    
    # overwrite backup file with current version
    pass

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
    # define backup drives
    backup_drive_letters = []
    for drive in [x[1] for x in backup_drive_letter_dict.items()]: 
        if '' not in drive: 
            backup_drive_letters += drive
    backup_drive_letters = sorted(list(set(backup_drive_letters)))
    backup_drive_names = [get_drive_name(bdl) for bdl in backup_drive_letters]
    # define media types
    media_types = list(primary_drives_dict.keys())
    # init primary filepaths dict
    primary_filepaths_dict = {}
    # loop through media types
    for media_type in media_types:
        # TEMPORARY CONDITIONAL FOR DEVELOPMENT
        if media_type not in ['Books','Music','Photos','Games','Youtube']: continue
        # loop through backup drives
        for drive_backup_letter in backup_drive_letters:
            # assess if backup drive associates with this media type
            if drive_backup_letter not in backup_drive_letter_dict[media_type]: continue
            # determine backup drive name
            drive_backup_name = get_drive_name(drive_backup_letter)
            # determine primary parent paths for specific media type
            primary_parent_paths = [f'{x}:/{media_type}' for x in primary_drive_letter_dict[media_type]]
            # determine primary filepaths for specific media type
            primary_filepaths = read_alexandria(primary_parent_paths,extensions_dict[media_type])
            # add media-specific primary filepaths to primary filepath dict
            primary_filepaths_dict[media_type] = primary_filepaths
            # map the backup: determine missing and excess files in backup drive
            tuple_filepaths_missing, filepaths_excess, tuple_filepaths_existing_backup = backup_mapper(media_type, primary_filepaths_dict, backup_drive_letter_dict)
            # remove excess files (*requires user action)
            remove_excess_files(filepaths_excess)
            # assess required backup space and remain space on backup drive 
            required_space, remaining_space = assess_backup_feasibility(tuple_filepaths_missing)
            # determine if backup is feasible
            if required_space > remaining_space:
                print(f'\n{Back.RED}{Fore.RESET}The {media_type} backup to the {drive_backup_name} ({drive_backup_letter}) drive is {abs(int(remaining_space-required_space))} GB too large{Style.RESET_ALL}')
            # excecute backup function
            backup_function(tuple_filepaths_missing)
            # determine backup file integrity
            tuple_filepaths_existing_backup(tuple_filepaths_existing_backup)
        

"""

"""


"""
TEMP:
"""

