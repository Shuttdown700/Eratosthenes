import os
import sys

CURR_DIR = os.path.dirname(os.path.abspath(__file__))

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from utilities import (
    read_alexandria,
    write_list_to_txt_file,
    get_drive_letter,
    read_alexandria_config,
    read_json,
)

sys.path.append(os.path.join(os.path.dirname(__file__), "..","utils"))

from map_media_type_to_drives import map_media_type_to_drives

from colorama import Fore, Style, init
init(autoreset=True)

RED = Fore.RED
YELLOW = Fore.YELLOW
GREEN = Fore.GREEN
BRIGHT = Style.BRIGHT
RESET = Style.RESET_ALL

MEDIA_TYPE_OPTIONS = [
    "movies",
    "anime_movies",
    "4k_movies",
    "shows",
    "anime",
    "books"
]


def update_media_list(media_type: str) -> list:
    """Update the media list based on primary drive configuration."""


    media_key = media_type.replace("_", " ").title()
    media_drive_letters, _ = map_media_type_to_drives(media_key)
    media_dirs = [
        f"{letter}:/{media_key}/"
        for letter in media_drive_letters
    ]

    if not media_dirs:
        print(f"{RED}{BRIGHT}No directories found for media type:{RESET} {media_type}")
        return

    # Read all media file paths
    media_filepaths = read_alexandria(media_dirs)

    if media_key in ["Shows", "Anime"]:
        # Filter out directories and keep only files
        # Extract the second directory from each file path (e.g., /Drive/Shows/Series/Episode -> 'Series')
        data = [
            os.path.normpath(path).split(os.sep)[2] if len(os.path.normpath(path).split(os.sep)) > 2 else ""
            for path in media_filepaths
        ]
        data = [title for title in data if title]  # Remove empty titles
        data = sorted(set(data), key=str.lower)  # Sort and remove duplicates

    else:
        # For movies, anime movies, 4K movies, and books, extract the title from the file name
        data = [
            os.path.splitext(os.path.basename(path))[0] for path in media_filepaths
        ]
        data = sorted(set(data), key=str.lower)

    # Define output path
    dirname = media_type.replace(" ", "_").lower() if media_type != "anime_movies" else "movies"
    output_dir = os.path.join(
        CURR_DIR, "..", "..", "output", dirname
    )
    os.makedirs(output_dir, exist_ok=True)

    output_filepath = os.path.join(
        output_dir, f"{media_type.replace(' ', '_').lower()}_list.txt"
    )

    # Write titles to file
    write_list_to_txt_file(output_filepath, data)
    # Print the last two directories and the filename from the output path
    parts = os.path.normpath(output_filepath).split(os.sep)
    to_print = os.sep.join(parts[-3:]) if len(parts) >= 3 else output_filepath
    print(f"{GREEN}{BRIGHT}{media_type.replace('_',' ').title()} list updated:{RESET} {to_print}")
    return data

def update_all_media_lists() -> None:
    """Update all media lists."""
    for media_type in MEDIA_TYPE_OPTIONS:
        update_media_list(media_type)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        media_type_arg = sys.argv[1].replace(" ","_").lower()
        if media_type_arg not in MEDIA_TYPE_OPTIONS:
            print(f"{RED}Invalid media type:{RESET} {media_type_arg}.")
            sys.exit(1)
        update_media_list(media_type_arg)
    else:
        print("Usage: python update_media_list.py <media_type>")
        print(f"{YELLOW}No media type provided{RESET} | Updating all media lists: {', '.join(MEDIA_TYPE_OPTIONS)}.")
        update_all_media_lists()

    
