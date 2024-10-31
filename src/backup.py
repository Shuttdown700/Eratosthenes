#!/usr/bin/env python

# define libraries
libraries = [['os']]
from utilities import import_libraries
import_libraries(libraries)

from colorama import Fore, Back, Style
from utilities import files_are_identical, read_alexandria, read_alexandria_config, read_csv, read_json
from utilities import get_drive_letter, get_drive_name, get_file_size, get_space_remaining, remove_empty_folders

def apply_movie_backup_filters(drive_config: dict,media_type: str,backup_filepaths: list): # type: ignore
    """
    Function to filter movie backups using IMDb rating and blocked keywords

    Parameters
    ----------
    drive_config : dict
        Alexandria backup configuration.
    media_type : str
        Media type for this backup
    backup_filepaths : list
        List of missing backup filepath tuples. Format: [(primary,backup),(primary,backup),...]

    Returns
    -------
    tuple_filepaths_missing_adjusted : list
        List of adjusted backup filepath tuples. Format: [(primary,backup),(primary,backup),...]
    """
    import ast, os
    # initialize variables
    tuple_filepaths_missing_adjusted = []
    num_filtered_by_keyword = 0
    num_filtered_by_imdb = 0
    num_not_in_tmdb = 0
    num_filtered_by_lack_of_tmbd_data = 0
    num_exceptions_by_keyword = 0
    if len(backup_filepaths) == 0: return backup_filepaths
    if type(backup_filepaths) == list and type(backup_filepaths[0]) == tuple:
        # determine the various backup drive letters
        drives_backup = list(set([x[1][0] for x in backup_filepaths]))
        bool_assess_current_backup = False
    elif type(backup_filepaths) == list and type(backup_filepaths[0]) == str:
        # determine the various backup drive letters
        drives_backup = list(set([x[0] for x in backup_filepaths]))    # initialize IMDb minimums from config
        bool_assess_current_backup = True
    imdb_mins = {}; backup_unknown_imdbs = {}; exclude_strings = {}; exclude_strings_exceptions = {}
    # loop through backup drive letters
    for drive in drives_backup:
        # determine and save the drive's minimum IMDb rating
        try:
            imdb_min = float(drive_config[media_type]["backup_drive_imdb_minimums"][drive_config[media_type]["backup_drives"].index(get_drive_name(drive))])
        except ValueError as e:
            print(f'{Fore.RED}Error in filter function:{Style.RESET_ALL} {e}')
            imdb_min = 10
        imdb_mins[drive] = imdb_min
        # determine and save the drive's backup action if the IMDb rating is not found
        backup_unknown_imdb = ast.literal_eval(drive_config[media_type]["backup_unknown_imdb_scores"][drive_config[media_type]["backup_drives"].index(get_drive_name(drive))])
        backup_unknown_imdbs[drive] = backup_unknown_imdb
        # determine and save the drive's excluded string list
        exclude_string_list = drive_config[media_type]["backup_drive_exclude_strings"][drive_config[media_type]["backup_drives"].index(get_drive_name(drive))]
        exclude_strings[drive] = exclude_string_list
        # determine and save the drive's excluded string list
        exclude_string_exceptions_list = drive_config[media_type]["backup_drive_exclude_strings_exceptions"][drive_config[media_type]["backup_drives"].index(get_drive_name(drive))]
        exclude_strings_exceptions[drive] = exclude_string_exceptions_list
    # read the previously saved TMDb data
    tmdb_filepath = ("\\".join(os.path.dirname(os.path.abspath(__file__)).split('\\')[:-1])+"/output/").replace('\\','/')+'tmdb.csv'
    tmdb_data = read_csv(tmdb_filepath)
    # loop through the missing filepath tuples
    num_total_movie_backup_candidates = len(backup_filepaths)
    if num_total_movie_backup_candidates == 0: return backup_filepaths
    filepaths_blocked = []
    for filepaths in backup_filepaths:
        # define all file variables
        if not bool_assess_current_backup:
            file_src = filepaths[0]
            file_dst = filepaths[1]
        else:
            file_src = file_dst = filepaths
        movie_with_year = os.path.splitext(os.path.basename(file_src))[0]
        bool_found = False
        # loop through TMDb data
        for index, item in enumerate(tmdb_data):
            # if a movie match is found 
            if item.get('Title_Alexandria') == movie_with_year:
                tmdb_data_index = index
                bool_found = True
                break
        # if an exception strings exist in the movie title, bypass filtering
        bool_exception = False
        if True in [True if x.lower() in movie_with_year.lower() else False for x in exclude_strings_exceptions[file_dst[0]]]: 
            num_exceptions_by_keyword += 1
            bool_exception = True
        if not bool_found and not bool_exception:
            # print(f'{movie_with_year} not found in TMDb pull!')
            num_not_in_tmdb += 1
            if not backup_unknown_imdbs[file_dst[0]]: filepaths_blocked.append(file_dst); num_filtered_by_lack_of_tmbd_data += 1; continue
        elif bool_found and not bool_exception:
            # determine the movie rating
            movie_rating = float(tmdb_data[tmdb_data_index]['Rating'])
            # compare movie rating with minimum rating allowed
            if movie_rating < imdb_mins[file_dst[0]]:
                # if lower than threshold, continue to next filepath
                num_filtered_by_imdb += 1
                filepaths_blocked.append(file_dst)
                continue
        # if an excluded strings exist in the movie title, skip it
        if True in [True if x.lower() in movie_with_year.lower() else False for x in exclude_strings[file_dst[0]]] and not bool_exception: 
            num_filtered_by_keyword += 1
            filepaths_blocked.append(file_dst)
            continue
        # if not filterd, append to adjusted filepath tuple list
        tuple_filepaths_missing_adjusted.append(filepaths)
    if bool_assess_current_backup and len(filepaths_blocked) > 0:
        num_files_deleted = remove_excess_files(filepaths_blocked, True)
        if num_files_deleted > 0:
             return "Backup Files Removed"
        return []
    # # determine the percent of movies that were filtered
    # percent_filtered = 100 - round(len(tuple_filepaths_missing_adjusted)/len(backup_filepaths),4)*100
    # percent_in_tmdb = 100 - round(num_not_in_tmdb/len(backup_filepaths),4)*100
    # print(f'\n{Fore.GREEN}{Style.BRIGHT}{percent_in_tmdb:.2f}%{Style.RESET_ALL} of candidate movie backups ({len(backup_filepaths)}) are in the local TMDb database')
    # if len(tuple_filepaths_missing_adjusted) > 0:
    #     print(f'{Fore.RED}{Style.BRIGHT}{percent_filtered:.2f}%{Style.RESET_ALL} of candidate movie backups ({int(len(tuple_filepaths_missing_adjusted))}) were filtered: {Fore.RED}{Style.BRIGHT}{num_filtered_by_imdb}{Style.RESET_ALL} due to low IMDb score, {Fore.RED}{Style.BRIGHT}{num_filtered_by_keyword}{Style.RESET_ALL} by blocked keywords, and {Fore.RED}{Style.BRIGHT}{num_filtered_by_lack_of_tmbd_data}{Style.RESET_ALL} due to no TMDb data')
    return tuple_filepaths_missing_adjusted

def apply_show_backup_filters(drive_config: dict,media_type: str,backup_filepaths: list):
    """
    Function to filter movie backups using IMDb rating and blocked keywords

    Parameters
    ----------
    drive_config : dict
        Alexandria backup configuration.
    media_type : str
        Media type for this backup
    backup_filepaths : list
        List of missing backup filepath tuples. Format: [(primary,backup),(primary,backup),...]

    Returns
    -------
    tuple_filepaths_missing_adjusted : list
        List of adjusted backup filepath tuples. Format: [(primary,backup),(primary,backup),...]
    """
    # import libraries & methods
    import os
    from utilities import get_drive_name, read_file_as_list
    # initialize counters & lists
    tuple_filepaths_missing_adjusted = []; filepaths_blocked = []; drive_show_whitelists = {}
    # return empty backup filepath list
    if len(backup_filepaths) == 0: return backup_filepaths
    # if filtering proposed backup (list of tuples), determine backup drives
    if type(backup_filepaths) == list and type(backup_filepaths[0]) == tuple:
        drives_backup = list(set([x[1][0] for x in backup_filepaths]))
        bool_assess_current_backup = False
    # if filtering existing backup (list of strings), determine backup drives
    elif type(backup_filepaths) == list and type(backup_filepaths[0]) == str:
        drives_backup = list(set([x[0] for x in backup_filepaths]))
        bool_assess_current_backup = True
    src_directory = os.path.dirname(os.path.abspath(__file__))
    # load the backup drives' whitelist
    for drive_letter in drives_backup:
        filepath_drive_show_whitelist = (src_directory+f"/config/show_whitelists/{get_drive_name(drive_letter).replace(' ','_')}_whitelist.txt").replace('\\','/')
        show_whitelist = read_file_as_list(filepath_drive_show_whitelist)
        drive_show_whitelists[drive_letter] = show_whitelist
    # iterate through the filepath list
    for filepaths in backup_filepaths:
        if not bool_assess_current_backup:
            file_src = filepaths[0]
            file_dst = filepaths[1]
        else:
            file_src = file_dst = filepaths
        show_with_year = file_src.split('/')[2]
        show_filename = os.path.basename(file_src)
        # if the show is not in the whitelist, add the filepath to the blocked list
        if True not in [True if x.lower() in show_with_year.lower() or x.lower() in show_filename.lower() else False for x in drive_show_whitelists[file_dst[0]]]: 
            filepaths_blocked.append(file_dst)
        # if show is in the whitelist, add the filepath to the adjusted list
        else:
            tuple_filepaths_missing_adjusted.append(filepaths)
    if bool_assess_current_backup and len(filepaths_blocked) > 0:
        num_files_deleted = remove_excess_files(filepaths_blocked, updated_block_list = True)
        if num_files_deleted > 0:
             return False
        return tuple_filepaths_missing_adjusted
    return tuple_filepaths_missing_adjusted

def assess_backup_feasibility(tuple_filepaths_missing,tuple_filepaths_modified):
    """
    Function to determine the feasibility of a backup

    Parameters
    ----------
    tuple_filepaths_missing : list
        List of excess file tuples. Format: [(primary,backup),(primary,backup),...]
    tuple_filepaths_modified : list
        List of excess file tuples. Format: [(primary,backup),(primary,backup),...]

    Returns
    -------
    required_space: float
        GBs in space required for the backup
    remaining_space : float
        GBs in remaining space on the backup drive
    """
    # determine list of backup drive letters
    drives_backup = list(set([x[1][0] for x in tuple_filepaths_missing])) + list(set([x[1][0] for x in tuple_filepaths_modified]))
    remaining_space = 0
    # loop through backup drives (should be one in SEP-2024 build)
    for drive in drives_backup:
        remaining_space = get_space_remaining(drive)
    required_space = 0
    # loop through missing filepaths to determine required space
    for filepath in tuple_filepaths_missing:
        required_space += get_file_size(filepath[0])
    # loop through filepaths that have been recently modified
    for tuple_filepath in tuple_filepaths_modified:
        filepath_primary = tuple_filepath[0]
        filepath_backup = tuple_filepath[1]
        # add older version of file to available space
        remaining_space += get_file_size(filepath_backup)
        # add newer version of file to required backup space
        required_space += get_file_size(filepath_primary)
    return required_space, remaining_space

def remove_excess_files(filepaths_backup_excess, updated_block_list=False):
    """
    Function to remove excess files in the backup drives

    Parameters
    ----------
    filepaths_excess : list
        List of excess file tuples. Format: [(primary,backup),(primary,backup),...]

    Returns
    -------
    None.
    """
    import os
    num_files_deleted = 0; size_GB_files_excess = 0
    # assess if there are excess files
    if len(filepaths_backup_excess) > 0:
        if not updated_block_list:
            print(f'\n{Back.RED}The following {len(filepaths_backup_excess)} {"file is" if len(filepaths_backup_excess) == 1 else "files are"} not in the primary drives:{Style.RESET_ALL}')
        else:
            print(f'\n{Back.RED}The following {len(filepaths_backup_excess)} {"file is" if len(filepaths_backup_excess) == 1 else "files are"} blocked with the updated backup config:{Style.RESET_ALL}')
        # loop through excess filepaths
        for filepath_excess in filepaths_backup_excess:
            print(filepath_excess)
            size_GB_files_excess += get_file_size(filepath_excess)
        # initialize user interaction value
        ui = ''
        # wait until there's a valid user response
        while ui != 'n' and ui != 'y':
            if len(filepaths_backup_excess) > 1:
                ui = input(f'\nDo you want to delete these {Fore.RED}{Style.BRIGHT}{len(filepaths_backup_excess):,} items ({int(size_GB_files_excess):,} GB){Style.RESET_ALL}? [Y/N] {Style.RESET_ALL}').lower()
            else:
                ui = input(f'\nDo you want to delete this item? [Y/N] {Style.RESET_ALL}').lower()
        # assess if the user wishes to delete excess files
        if ui.lower() == 'y':
            # delete all excess filepaths
            for excess_file in filepaths_backup_excess:
                if '$Recycle' in excess_file: continue
                print(f'{Fore.RED}{Style.BRIGHT}Deleting:{Style.RESET_ALL} {excess_file}')
                try:
                    os.remove(excess_file)
                except Exception as e:
                    print(f'{Fore.YELLOW}Error:{Style.RESET_ALL} {e}')
                num_files_deleted += 1
            return num_files_deleted
        return 0
    return 0

def backup_function(backup_tuples,modified_tuples):
    """
    Batch back-up function

    Parameters
    ----------
    backup_tuples : list
        List of backup file tuples. Format: [(src,dest),(src,dest),...]
    modified_tuples : list
        List of modified file tuples. Format: [(src,dest),(src,dest),...]

    Returns
    -------
    None.

    """
    # import libraries
    import os, subprocess
    # loop through backup tuples 
    if len(backup_tuples) > 0:
        size_GB_backup = sum([get_file_size(x[0]) for x in backup_tuples])
        size_GB_remaining = get_space_remaining(backup_tuples[0][1][0]) - size_GB_backup
        print(f'\n\t\tBacking up {Fore.RED}{Style.BRIGHT}{len(backup_tuples):,} {"files" if len(backup_tuples) != 1 else "file"}{Style.RESET_ALL} ({Fore.YELLOW}{Style.BRIGHT}{int(size_GB_backup):,} GB backup{Style.RESET_ALL}, {Fore.GREEN}{Style.BRIGHT}{int(size_GB_remaining):,} GB of space will remain{Style.RESET_ALL}):')
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
            print(f'{Fore.YELLOW}{Style.BRIGHT}\t\tBacking up{Style.RESET_ALL} {file_title} {Fore.RED}{Style.BRIGHT}|{Style.RESET_ALL} {Fore.BLUE}{Style.BRIGHT}{get_drive_name(sfile[0])}{Style.RESET_ALL} -> {Fore.GREEN}{Style.BRIGHT}{get_drive_name(dfile[0])}{Style.RESET_ALL}')
            cmd = fr'copy "{sfile}" "{dfile}"'.replace('/','\\')
            subprocess.call(cmd, shell=True, stdout=subprocess.PIPE)
    if len(modified_tuples) > 0: print(f'\n\t\tUpdating {Fore.RED}{Style.BRIGHT}{len(modified_tuples)}{Style.RESET_ALL} {"files" if len(modified_tuples) != 1 else "file"}:')
    for mt in modified_tuples:
        # reading backup tuple
        sfile = fr'{mt[0]}'
        dfile = fr'{mt[1]}'
        file_title = sfile.split('/')[-1][:-4].strip()
        # ensure source file exisits (reduces errors)
        if os.path.isfile(sfile):
            dpath = os.path.dirname(dfile)
            if not os.path.exists(dpath):
                os.makedirs(dpath)
            # backup the missing file
            print(f'{Fore.YELLOW}{Style.BRIGHT}\t\tUpdating File{Style.RESET_ALL} {file_title} {Fore.RED}{Style.BRIGHT}|{Style.RESET_ALL} {Fore.BLUE}{Style.BRIGHT}{get_drive_name(sfile[0])}{Style.RESET_ALL} -> {Fore.GREEN}{Style.BRIGHT}{get_drive_name(dfile[0])}{Style.RESET_ALL}')
            cmd = fr'copy "{sfile}" "{dfile}"'.replace('/','\\')
            subprocess.call(cmd, shell=True, stdout=subprocess.PIPE)

def backup_integrity(tuple_filepaths_existing_backup):
    """
    Function to determine integrity of current backup

    Parameters
    ----------
    tuple_filepaths_existing_backup : list
        List of existing backup file tuples. Format: [(primary,backup),(primary,backup),...]

    Returns
    -------
    tuple_filepaths_modified : list
        List of adjusted existing backup file tuples. Format: [(primary,backup),(primary,backup),...]
    """
    import os
    tuple_filepaths_modified = []
    # loop through existing backup filepaths
    for idx,filepath_tuple in enumerate(tuple_filepaths_existing_backup):
        file_primary = filepath_tuple[0]
        file_backup = filepath_tuple[1]
        if not os.path.isfile(file_primary) or not os.path.isfile(file_backup): continue
        # determine if primary & backup filepaths are different
        if not files_are_identical(file_primary,file_backup):
            # append modified filepaths where backup is outdated
            tuple_filepaths_modified.append((file_primary,file_backup))
    return tuple_filepaths_modified

def backup_mapper(media_type:str,drive_backup_letter:str,primary_filepaths_dict:dict, drive_config,bool_recurssive=False):
    """
    Function to filter movie backups using IMDb rating

    Parameters
    ----------
    media_type : str
        Media type for this backup
    tuple_filepaths_missing : list
        List of missing backup filepath tuples. Format: [(primary,backup),(primary,backup),...]
    primary_filepaths_dict : dict
        Primary filepaths of all primary files, grouped by media type
    drive_config : dict
        Alexandria backup configuration.

    Returns
    -------
    tuple_filepaths_missing : list
        List of backup filepath tuples. Format: [(primary,backup),(primary,backup),...]
    filepaths_backup_excess : list
        List of excess filepaths.
    filepaths_backup_current : list
        List of current filepaths.
    tuple_filepaths_modified : list
        List of modified backup filepath tuples. Format: [(primary,backup),(primary,backup),...]
    """
    import os
    # define primary filepaths
    filepaths_primary = primary_filepaths_dict[media_type]
    filepaths_primary_noLetter = [filepath[1:] for filepath in filepaths_primary]
    # define backup filepaths
    backup_path = f'{drive_backup_letter}:/{media_type}'
    os.makedirs(backup_path, exist_ok=True)
    extensions_dict = read_alexandria_config(drive_config)[2]
    filepaths_backup = read_alexandria([backup_path],extensions_dict[media_type])
    filepaths_backup_noLetter = [filepath[1:] for filepath in filepaths_backup]
    # determine missing & existing backup filepaths
    tuple_filepaths_missing = []
    tuple_filepaths_existing_backup = []
    # iterate through primary filepaths
    for index_primary, primary_filepath_noLetter in enumerate(filepaths_primary_noLetter):
        # if backup file does not exist, append to missing backup tuple
        if primary_filepath_noLetter not in filepaths_backup_noLetter:
            sfile = filepaths_primary[index_primary][0]+primary_filepath_noLetter
            try:
                dfile = filepaths_backup[-1][0]+primary_filepath_noLetter
            except IndexError:
                dfile = backup_path[0]+primary_filepath_noLetter
            backup_tuple = (sfile,dfile)
            tuple_filepaths_missing.append(backup_tuple)
        # if backup file already exists, append tuple to exisiting backup list
        else:
            sfile = filepaths_primary[index_primary][0]+primary_filepath_noLetter
            index_backup = filepaths_backup_noLetter.index(primary_filepath_noLetter)
            bfile = drive_backup_letter+filepaths_backup_noLetter[index_backup]
            backup_tuple = (sfile,bfile)
            tuple_filepaths_existing_backup.append(backup_tuple)
    # if the media type is a movie, filter existing & missing filepaths by rating & keywords
    if media_type.lower() in ['movies', 'anime movies']:
        # filter existing backups by passing the existing backup filepaths list
        message_current_backups = apply_movie_backup_filters(drive_config,media_type,filepaths_backup)
        # if files were removed from the existing backup and function not on recurssion, re-map the backup
        if message_current_backups == "Backup Files Removed" and not bool_recurssive:
            backup_mapper(media_type, drive_backup_letter, primary_filepaths_dict, drive_config,bool_recurssive=True)
        # print("Assessing the candidate backup files:")
        tuple_filepaths_missing = apply_movie_backup_filters(drive_config,media_type,tuple_filepaths_missing)
    if media_type.lower() in ['shows','anime']:
        # filter existing backups by passing the existing backup filepaths list
        if not bool_recurssive: 
            filepaths_backup_current = apply_show_backup_filters(drive_config,media_type,filepaths_backup)
            # if files were removed from the existing backup, re-map the backup
            if not isinstance(filepaths_backup_current,list) and not bool_recurssive:
                backup_mapper(media_type, drive_backup_letter, primary_filepaths_dict, drive_config,bool_recurssive=True)
        # filter proposed backups filepaths
        tuple_filepaths_missing = apply_show_backup_filters(drive_config,media_type,tuple_filepaths_missing)
    # determine current and excess backup filepaths
    filepaths_backup_excess = []; filepaths_backup_current = []
    # iterate through backup filepaths
    for index_backup, backup_filepath_noLetter in enumerate(filepaths_backup_noLetter):
        # determine if backup file is not in primary drive
        if backup_filepath_noLetter not in filepaths_primary_noLetter:
            filepaths_backup_excess.append(filepaths_backup[index_backup][0]+backup_filepath_noLetter)
        else:
            filepaths_backup_current.append(filepaths_backup[index_backup][0]+backup_filepath_noLetter)
    # remove excess backup filespaths
    num_files_deleted = remove_excess_files(filepaths_backup_excess)
    # if files were deleted, re-map the backup
    if num_files_deleted > 0:
        backup_mapper(media_type, drive_backup_letter, primary_filepaths_dict, drive_config,bool_recurssive=True)
    # determine which primary files were modified since last backed-up
    tuple_filepaths_modified = backup_integrity(tuple_filepaths_existing_backup)
    return tuple_filepaths_missing, tuple_filepaths_modified, filepaths_backup_current, filepaths_backup_excess

def main():
    import os
    from analytics import read_media_statistics, read_media_file_data
    print(f'\n{"#"*10}\n\n{Fore.MAGENTA}{Style.BRIGHT}Initiating Alexandria Backup...{Style.RESET_ALL}\n\n{"#"*10}')
    # define paths
    src_directory = os.path.dirname(os.path.abspath(__file__))
    drive_hieracrchy_filepath = (src_directory+"/config/alexandria_drives.config").replace('\\','/')
    output_directory = ("\\".join(src_directory.split('\\')[:-1])+"/output").replace('\\','/')
    filepath_statistics = os.path.join(output_directory,"alexandria_media_statistics.json")
    filepath_alexandria_media_details = os.path.join(output_directory,"alexandria_media_details.json").replace('\\','/')
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
    primary_filepaths_dict = {}; drive_stats_dict = {}
    # loop through backup drives
    """
    Do I want to query the online DBs for update metadata? No, have that be a feature seperate from backups
    
    """
    for drive_backup_letter in backup_drive_letters:
        drive_backup_name = get_drive_name(drive_backup_letter)
        print(f'\n### {Fore.GREEN}{Style.BRIGHT}{drive_backup_name} ({drive_backup_letter.upper()} drive){Style.RESET_ALL} ###')
        # loop through media types
        for media_type in media_types:
            # assess if backup drive associates with this media type
            if drive_backup_letter not in backup_drive_letter_dict[media_type] and drive_backup_letter not in primary_drive_letter_dict[media_type]:
                # detect non-directed backups
                root_path = f'{drive_backup_letter}:/{media_type}'
                undirected_backup_filepaths = read_alexandria([root_path],extensions_dict[media_type])
                if len(undirected_backup_filepaths) == 0: continue
                num_files_deleted = remove_excess_files(undirected_backup_filepaths)
                remove_empty_folders([root_path])
                continue
            if drive_backup_letter in primary_drive_letter_dict[media_type]: continue
            print(f'\n\tAssessing {Fore.YELLOW}{Style.BRIGHT}{media_type}{Style.RESET_ALL} in backup drive: {Fore.GREEN}{Style.BRIGHT}{drive_backup_name} ({drive_backup_letter.upper()} drive){Style.RESET_ALL}')
            # determine primary parent paths for specific media type
            primary_parent_paths = [f'{x}:/{media_type}' for x in primary_drive_letter_dict[media_type]]
            # determine space remaining on primary drive(s)
            for drive_letter in primary_drive_letter_dict[media_type]: drive_stats_dict.update({get_drive_name(drive_letter): {"Space Remaining (TB)": get_space_remaining(drive_letter)/1000}})
            # determine primary filepaths for specific media type
            primary_filepaths = read_alexandria(primary_parent_paths,extensions_dict[media_type])
            # add media-specific primary filepaths to primary filepath dict
            primary_filepaths_dict[media_type] = primary_filepaths
            # map the backup: determine missing and excess files in backup drive
            tuple_filepaths_missing, tuple_filepaths_modified, filepaths_backup_current, filepaths_backup_excess = backup_mapper(media_type, drive_backup_letter, primary_filepaths_dict, drive_config)
            # assess required backup space and remain space on backup drive 
            required_space, remaining_space = assess_backup_feasibility(tuple_filepaths_missing, tuple_filepaths_modified)
            # determine if backup is feasible
            if required_space > remaining_space:
                print(f'\n{Back.RED}{Style.BRIGHT}{Fore.RESET}The {Fore.YELLOW}{media_type}{Fore.RESET} backup to the {Fore.YELLOW}{drive_backup_name} ({drive_backup_letter}) drive{Fore.RESET} is {abs(int(remaining_space-required_space))} GB too large{Style.RESET_ALL}')
            else:
                # excecute backup function
                backup_function(tuple_filepaths_missing, tuple_filepaths_modified)
            # remove empty sub-directories
            remove_empty_folders(primary_parent_paths+[f'{drive_backup_letter}:/{media_type}'])
        space_remaining_TB = get_space_remaining(drive_backup_letter)/1000
        drive_stats_dict.update({
            drive_backup_name: {
                "Space Remaining (TB)": space_remaining_TB
            }
        })
        print(f'\n{Fore.MAGENTA}{Style.BRIGHT}Space remaining{Style.RESET_ALL} in {Fore.GREEN}{Style.BRIGHT}{drive_backup_name} ({drive_backup_letter.upper()} drive){Style.RESET_ALL}: {Fore.BLUE}{Style.BRIGHT}{space_remaining_TB:,.2f} TB{Style.RESET_ALL}')
    drive_stats_dict = dict(sorted(drive_stats_dict.items(), key=lambda item: item[0].title()))
    read_media_statistics(filepath_statistics,bool_update=True)
    read_media_file_data(filepath_alexandria_media_details,bool_update=True)
    for idx,item in enumerate(drive_stats_dict.items()):
        if idx == 0: print(f'{Fore.MAGENTA}{Style.BRIGHT}Space Remaining on Drives{Style.RESET_ALL}\n')
        print(f'{Fore.GREEN}{Style.BRIGHT}{item[0]}:{Style.RESET_ALL} {item[1]["Space Remaining (TB)"]:,.2f} TB')
    print(f'\n{"#"*10}\n\n{Fore.GREEN}{Style.BRIGHT}Alexandria Backup Complete{Style.RESET_ALL}\n\n{"#"*10}\n')

if __name__ == '__main__':
    main()