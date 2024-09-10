#!/usr/bin/env python

# define libraries
libraries = [['os']]
from utilities import read_alexandria_config, get_drive_letter, import_libraries
import_libraries(libraries)

from utilities import read_alexandria, read_json

def determine_movie_rating(data_filepath):
    df_movie_ratings = []
    return df_movie_ratings

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
        primary_paths = [f'{x}:/{media_type}' for x in primary_drive_letter_dict[media_type]]
        primary_filepaths = read_alexandria(primary_paths,extensions_dict[media_type])
        primary_filepaths_dict[media_type] = primary_filepaths





"""
SCHEME:
    DONE --- identify primary drives (from config file)
    DONE --- identify backup drives (from config file)
    read the primary files (all at beginning of sequence)
    read backup drives (individually)
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

