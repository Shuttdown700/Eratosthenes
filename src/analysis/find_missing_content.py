#!/usr/bin/env python3

import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api import API
from utilities import (
    get_drive_letter, 
    read_alexandria_config, 
    read_json
)

from colorama import Fore, Back, Style
import re

RED = Fore.RED + Style.BRIGHT
YELLOW = Fore.YELLOW + Style.BRIGHT
GREEN = Fore.GREEN + Style.BRIGHT
RESET = Style.RESET_ALL

def check_if_file_exists(
        series_drives: list,
        series_title: str, 
        year: str, 
        season: str, 
        episode: str
    ) -> bool:
    """
    Check if a file exists at the given filepath.
    
    Args:
        filepath (str): Path to the file.
    
    Returns:
        bool: True if file exists, False otherwise.
    """
    root_paths = ["Shows", "Anime"]
    extensions = [".mkv", ".mp4"]
    candidate_filepaths = []
    if (len(season) > 1 and season[0] == '0'): 
        season_num_dir = season[1:]
    else:
        season_num_dir = season
    for drive in series_drives:
        for root_path in root_paths:
            for extension in extensions:

                filepath_01 = os.path.join(f"{drive}:", root_path, f"{series_title} ({year})", f"Season {season_num_dir}", f"{series_title} S{season}E{episode}{extension}")
                filepath_02 = os.path.join(f"{drive}:", root_path, f"{series_title} ({year})", f"Season {season_num_dir}", f"{series_title} ({series_year}) S{season}E{episode}{extension}")
                filepath_03 = os.path.join(f"{drive}:", root_path, f"{series_title} ({year})", f"Season {season_num_dir}", f"{series_title} S{season}E{episode}-E{int(episode)+1:02}{extension}")
                filepath_04 = os.path.join(f"{drive}:", root_path, f"{series_title} ({year})", f"Season {season_num_dir}", f"{series_title} S{season}E{int(episode)-1:02}-E{episode}{extension}")

                candidate_filepaths.append(filepath_01)
                candidate_filepaths.append(filepath_02)
                candidate_filepaths.append(filepath_03)
                candidate_filepaths.append(filepath_04)

    for filepath in candidate_filepaths:
        if os.path.exists(filepath):
            print(f"{GREEN}File found: {filepath}{RESET}")
            return True
        else:
            print(f"{RED}File not found: {filepath}{RESET}")
    return False


if __name__ == "__main__":
    bool_update_series_data = True
    bool_check_special_episodes = False

    api_handler = API()
    drive_config = read_json(api_handler.drive_hieracrchy_filepath)
    primary_drives_dict, backup_drives_dict, extensions_dict = read_alexandria_config(drive_config)
    primary_drive_letter_dict = {}
    for key,value in primary_drives_dict.items(): primary_drive_letter_dict[key] = [get_drive_letter(x) for x in value]
    # series_drives = primary_drive_letter_dict["Shows"] + primary_drive_letter_dict["Anime"]
    series_drives = primary_drive_letter_dict["Shows"]
    if bool_update_series_data: 
        series_data = api_handler.update_series_data()
    else:
        series_data = read_json(api_handler.filepath_series_data)
    for series_id, series_info in series_data.items():
        series_title = series_info.get("Series Title", "Unknown Series")
        series_year = series_info.get("Series First Aired", "Unknown Year")[:4]
        series_episodes = series_info.get("Series Episodes", {})
        for series_episode, series_episode_info in series_episodes.items():
            
            match = re.match(r"S(\d{2})E(\d{2})", series_episode.split()[-1])
            if match:
                season_number = match.group(1)
                episode_number = match.group(2)
            else:
                season_number = None
                episode_number = None
            if int(season_number) == 0 and not bool_check_special_episodes: 
                continue
            if check_if_file_exists(series_drives, series_title, series_year, season_number, episode_number):
                pass
            else:
                print(f"{YELLOW}Missing content for {series_title} S{season_number}E{episode_number}{RESET}")
                pass
                # Here you can add logic to handle missing content, e.g., logging or notifying the user

