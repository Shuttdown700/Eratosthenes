#!/usr/bin/env python3
import os
import sys
from pathlib import Path
from typing import Tuple, List, Dict, Any

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from utilities import (
    get_drive_letter,
    read_alexandria_config,
    read_json,
    get_drive_name
)

def map_media_type_to_drives(media: str) -> Tuple[List[str], List[str]]:
    script_dir = Path(__file__).resolve().parent
    config_path = script_dir / ".." / ".." / "config" / "alexandria_drives.config"

    if not config_path.exists():
        print(f"Error: Drive configuration file not found at: {config_path}")
        return [], []

    try:
        drive_config: Dict[str, Any] = read_json(config_path)
    except Exception as e:
        print(f"Error loading configuration file {config_path}: {e}")
        return [], []
        
    normalized_media = media.replace("_"," ").title()
    media_options = list(drive_config.keys())

    if normalized_media not in media_options:
        print(f"Warning: Invalid media type '{media}'. Valid options are: {', '.join(media_options)}")
        return [], []

    try:
        primary_drives_dict, _, _ = read_alexandria_config(drive_config)
    except Exception as e:
        print(f"Error reading alexandria config from loaded data: {e}")
        return [], []

    media_paths: List[str] = primary_drives_dict.get(normalized_media, [])
    
    media_drive_letters: List[str] = [
        get_drive_letter(path) for path in media_paths
    ]
    
    media_drive_names: List[str] = [
        get_drive_name(letter) for letter in media_drive_letters
    ]

    return media_drive_letters, media_drive_names

if __name__ == '__main__':
    media_title = 'music'
    letters, names = map_media_type_to_drives(media_title)
    
    print(f"--- Results for '{media_title.capitalize()}' ---")
    print(f"Drive Letters: {letters}")
    print(f"Drive Names: {names}")
    print("---------------------------------")
    
    print((letters, names),end='\n\n')