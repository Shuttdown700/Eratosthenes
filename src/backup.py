#!/usr/bin/env python

# define libraries
libraries = [['os']]
from utilities import import_libraries
import_libraries(libraries)

from utilities import read_alexandria, read_json

def determine_primary_drives(drive_hieracrchy):
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
    primary_drives_dict = {}; backup_drives_dict = {}
    for media_type in drive_hieracrchy:
        primary_drives = drive_hieracrchy[media_type]['primary_drives']
        primary_drives_dict.update({media_type:primary_drives})
        backup_drives = drive_hieracrchy[media_type]['backup_drives']
        backup_drives_dict.update({media_type:backup_drives})
    return primary_drives_dict, backup_drives_dict

if __name__ == '__main__':
    import os
    
    # define paths
    src_directory = os.path.dirname(os.path.abspath(__file__))
    drive_hieracrchy_filepath = (src_directory+"/config/alexandria_drive_hierarchy.json").replace('\\','/')
    output_directory = ("\\".join(src_directory.split('\\')[:-1])+"/output").replace('\\','/')
    # define variables
    
    
    
    
    
    
    drive_hieracrchy = read_json(drive_hieracrchy_filepath)
    primary_drives_dict, backup_drives_dict = determine_primary_drives(drive_hieracrchy)





"""
SCHEME:
    identify primary drives (from config file)
    identify backup drives (from config file)
    identify what to backup (type-by-drive, from config file)
    read primary drives (all at beginning)
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

