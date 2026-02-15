#!/usr/bin/env python

import json
import os
import sys
import shutil

from colorama import Fore, Style

from assess_media_duration import main as assess_media_total_duration
from assess_media_duration import sum_durations
from read_server_statistics import read_media_statistics

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from utilities import (
    get_drive_letter,
    get_file_size,
    read_alexandria,
    read_alexandria_config,
    read_json
)    

def update_server_statistics(bool_update_duration=False, bool_print=False) -> None:
    """Update the server statistics for Alexandria Media Server."""
    src_directory = os.path.dirname(os.path.abspath(__file__))

    directory_output = os.path.join(src_directory, "..", "..", "output")
    filepath_statistics = os.path.join(directory_output, "alexandria_media_statistics.json")
    filepath_drive_config = os.path.join(src_directory, "..", "..", "config", "alexandria_drives.config")

    drive_config = read_json(filepath_drive_config)

    try:
        statistics_dict_current = read_media_statistics(bool_update=False, bool_print=False)
    except KeyError:
        print(f"{Fore.RED}{Style.BRIGHT}Error: Media statistics file not found or incomplete. Please run the update first.{Style.RESET_ALL}")
        return
    except FileNotFoundError:
        print(f"{Fore.RED}{Style.BRIGHT}Error: Media statistics file not found. Please run the update first.{Style.RESET_ALL}")
        return

    # Read drive configuration
    movie_drives_primary = drive_config['Movies']['primary_drives']
    movie_drives_backup = list(drive_config['Movies']['backup_drives'].keys())

    uhd_movie_drives_primary = drive_config['4K Movies']['primary_drives']
    uhd_movie_drives_backup = list(drive_config['4K Movies']['backup_drives'].keys())

    anime_movie_drives_primary = drive_config['Anime Movies']['primary_drives']
    anime_movie_drives_backup = list(drive_config['Anime Movies']['backup_drives'].keys())

    anime_drives_primary = drive_config['Anime']['primary_drives']
    anime_drives_backup = drive_config['Anime']['backup_drives']

    show_drives_primary = drive_config['Shows']['primary_drives']
    show_drives_backup = drive_config['Shows']['backup_drives']

    book_drives_primary = drive_config['Books']['primary_drives']
    book_drives_backup = drive_config['Books']['backup_drives']

    music_drives_primary = drive_config['Music']['primary_drives']
    music_drives_backup = list(drive_config['Music']['backup_drives'].keys())

    # Identify drives
    drive_names = list(set(
        movie_drives_primary + movie_drives_backup +
        uhd_movie_drives_primary + uhd_movie_drives_backup +
        anime_movie_drives_primary + anime_movie_drives_backup +
        anime_drives_primary + anime_drives_backup +
        show_drives_primary + show_drives_backup +
        book_drives_primary + book_drives_backup +
        music_drives_primary + music_drives_backup
    ))
    drive_names = [d for d in drive_names if d]
    drive_letters = [get_drive_letter(d) for d in drive_names]
    drive_letters = [d for d in drive_letters if d]

    # Read Alexandria config
    primary_drives_dict, backup_drives_dict, extensions_dict = read_alexandria_config(drive_config)

    primary_drive_letter_dict = {
        key: [get_drive_letter(x) for x in value]
        for key, value in primary_drives_dict.items()
    }

    primary_parent_paths = []
    primary_extensions = []

    for media_type in drive_config.keys():
        primary_parent_paths.extend(f'{x}:/{media_type}' for x in primary_drive_letter_dict[media_type])
        for _ in primary_drive_letter_dict[media_type]:
            primary_extensions.append(list(extensions_dict[media_type]))

    # Initialize counters
    space_TB_available = 0
    space_TB_used = 0
    space_TB_unused = 0

    for d in drive_letters:
        if not d:
            continue
        disk_obj = shutil.disk_usage(f'{d}:/')
        space_TB_available += int(disk_obj.total / 10**12)
        space_TB_used += int(disk_obj.used / 10**12)
        space_TB_unused += int(disk_obj.free / 10**12)

    primary_filepaths = read_alexandria(primary_parent_paths, primary_extensions)

    # Sort filepaths by media type
    filepaths_movies = []
    filepaths_anime_movies = []
    filepaths_uhd_movies = []
    filepaths_tv_shows = []
    filepaths_anime = []
    filepaths_books = []
    filepaths_youtube = []
    filepaths_music = []

    for f in primary_filepaths:
        if ':/Movies/' in f:
            filepaths_movies.append(f)
        elif ':/Anime Movies/' in f:
            filepaths_anime_movies.append(f)
        elif ':/4K Movies/' in f:
            filepaths_uhd_movies.append(f)
        elif ':/Shows/' in f:
            filepaths_tv_shows.append(f)
        elif ':/Anime/' in f:
            filepaths_anime.append(f)
        elif ':/Books/' in f:
            filepaths_books.append(f)
        elif ':/Music/' in f:
            filepaths_music.append(f)
        elif ':/YouTube/' in f:
            filepaths_youtube.append(f)

    statistics_dict = {}

    # TV Shows
    num_show_files = len(filepaths_tv_shows)
    show_titles = [
        os.path.normpath(path).split(os.sep)[2] if len(os.path.normpath(path).split(os.sep)) > 2 else ""
        for path in filepaths_tv_shows
    ]
    show_titles = [title for title in show_titles if title]  # Remove empty titles
    show_titles = sorted(set(show_titles), key=str.lower)  # Sort and remove duplicates
    num_shows = len(show_titles)
    size_TB_shows = round(sum(get_file_size(f, "TB") for f in filepaths_tv_shows), 2)
    if bool_update_duration:
        duration_shows = assess_media_total_duration(filepaths_tv_shows,print_bool=True)
    else:
        duration_shows = statistics_dict_current["TV Shows"].get("Total Duration", 0)
    statistics_dict["TV Shows"] = {
        "Number of Shows": num_shows,
        "Number of Episodes": num_show_files,
        "Total Size": f"{size_TB_shows:,.2f} TB",
        "Total Duration": duration_shows,
        "Show Titles": show_titles,
        "Primary Filepaths": filepaths_tv_shows
    }

    # Anime
    num_anime_files = len(filepaths_anime)
    anime_titles = [
        os.path.normpath(path).split(os.sep)[2] if len(os.path.normpath(path).split(os.sep)) > 2 else ""
        for path in filepaths_anime
    ]
    anime_titles = [title for title in anime_titles if title]  # Remove empty titles
    anime_titles = sorted(set(anime_titles), key=str.lower)  # Sort and remove duplicates
    num_anime = len(anime_titles)
    size_TB_anime = round(sum(get_file_size(f, "TB") for f in filepaths_anime), 2)
    if bool_update_duration:
        duration_anime = assess_media_total_duration(filepaths_anime,print_bool=True)
    else:
        duration_anime = statistics_dict_current.get("Anime", {}).get("Total Duration", 0)
    statistics_dict["Anime"] = {
        "Number of Anime": num_anime,
        "Number of Episodes": num_anime_files,
        "Total Size": f"{size_TB_anime:,.2f} TB",
        "Total Duration": duration_anime,
        "Anime Titles": anime_titles,
        "Primary Filepaths": filepaths_anime
    }

    # Movies
    num_movie_files = len(filepaths_movies)
    movie_titles = sorted({f.split('/')[2].strip() for f in filepaths_movies}, key=str.lower)
    num_movies = len(movie_titles)
    size_TB_movies = round(sum(get_file_size(f, "TB") for f in filepaths_movies), 2)
    if bool_update_duration:
        duration_movies = assess_media_total_duration(filepaths_movies,print_bool=True)
    else:
        duration_movies = statistics_dict_current.get("Movies", {}).get("Total Duration", 0)
    statistics_dict["Movies"] = {
        "Number of Movies": num_movies,
        "Total Size": f"{size_TB_movies:,.2f} TB",
        "Total Duration": duration_movies,
        "Movie Titles": movie_titles,
        "Primary Filepaths": filepaths_movies
    }

    # Anime Movies
    num_anime_movie_files = len(filepaths_anime_movies)
    anime_movie_titles = sorted({f.split('/')[2].strip() for f in filepaths_anime_movies}, key=str.lower)
    num_anime_movies = len(anime_movie_titles)
    size_GB_anime_movies = round(sum(get_file_size(f, "GB") for f in filepaths_anime_movies), 2)
    if bool_update_duration:
        duration_anime_movies = assess_media_total_duration(filepaths_anime_movies,print_bool=True)
    else:
        duration_anime_movies = statistics_dict_current.get("Anime Movies", {}).get("Total Duration", 0)
    statistics_dict["Anime Movies"] = {
        "Number of Anime Movies": num_anime_movies,
        "Total Size": f"{size_GB_anime_movies:,.2f} GB",
        "Total Duration": duration_anime_movies,
        "Anime Movie Titles": anime_movie_titles,
        "Primary Filepaths": filepaths_anime_movies
    }

    # 4K Movies
    num_uhd_movie_files = len(filepaths_uhd_movies)
    uhd_movie_titles = sorted({f.split('/')[2].strip() for f in filepaths_uhd_movies}, key=str.lower)
    num_uhd_movies = len(uhd_movie_titles)
    size_TB_uhd_movies = round(sum(get_file_size(f, "TB") for f in filepaths_uhd_movies), 2)
    if bool_update_duration:
        duration_uhd_movies = assess_media_total_duration(filepaths_uhd_movies,print_bool=True)
    else:
        duration_uhd_movies = statistics_dict_current.get("4K Movies", {}).get("Total Duration", 0)
    statistics_dict["4K Movies"] = {
        "Number of 4K Movies": num_uhd_movies,
        "Total Size": f"{size_TB_uhd_movies:,.2f} TB",
        "Total Duration": duration_uhd_movies,
        "4K Movie Titles": uhd_movie_titles,
        "Primary Filepaths": filepaths_uhd_movies
    }

    # Books
    num_book_files = len(filepaths_books)
    size_GB_books = round(sum(get_file_size(f, "GB") for f in filepaths_books), 2)
    book_titles = sorted(
        [os.path.splitext(os.path.basename(f))[0] for f in filepaths_books],
        reverse=True,
        key=str.lower
    )
    statistics_dict["Books"] = {
        "Number of Books": num_book_files,
        "Total Size": f"{size_GB_books:,.2f} GB",
        "Book Titles": book_titles,
        "Primary Filepaths": filepaths_books
    }

    # Music
    num_music_files = len(filepaths_music)
    size_GB_music = round(sum(get_file_size(f, "GB") for f in filepaths_music), 2)
    if bool_update_duration:
        duration_music = assess_media_total_duration(filepaths_music,print_bool=True)
    else:
        duration_music = statistics_dict_current.get("Music", {}).get("Total Duration", 0)
    statistics_dict["Music"] = {
        "Number of Songs": num_music_files,
        "Total Size": f"{size_GB_music:,.2f} GB",
        "Total Duration": duration_music,
        "Primary Filepaths": filepaths_music
    }

    # YouTube
    num_course_files = len(filepaths_youtube)
    size_GB_youtube = round(sum(get_file_size(f, "GB") for f in filepaths_youtube), 2)
    if bool_update_duration:
        duration_youtube = assess_media_total_duration(filepaths_youtube,print_bool=True)
    else:
        duration_youtube = statistics_dict_current.get("YouTube", {}).get("Total Duration", 0)
    statistics_dict["YouTube"] = {
        "Number of Course Videos": num_course_files,
        "Total Size": f"{size_GB_youtube:,.2f} GB",
        "Total Duration": duration_youtube,
        "Primary Filepaths": filepaths_youtube
    }

    # Aggregate statistics
    num_total_files = (
        num_show_files + num_anime_files + num_movie_files +
        num_anime_movie_files + num_uhd_movie_files +
        num_book_files + num_course_files
    )
    total_size_TB = (
        size_TB_shows + size_TB_anime + size_TB_movies +
        size_GB_anime_movies / 1000 + size_TB_uhd_movies +
        size_GB_books / 1000 + size_GB_music / 1000 +
        size_GB_youtube / 1000
    )

    durations = [
        duration_shows, duration_anime, duration_movies,
        duration_anime_movies, duration_uhd_movies,
        duration_music, duration_youtube
        ]

    total_duration = sum_durations(durations)

    with open(filepath_statistics, 'w') as json_file:
        json.dump(statistics_dict, json_file, indent=4)

    if bool_print:
        print(f'\n{"#" * 10}\n\n{Fore.YELLOW}{Style.BRIGHT}Server Stats:{Style.RESET_ALL}')
        print(f'Total Available Server Storage: {Fore.BLUE}{Style.BRIGHT}{space_TB_available:,} TB{Style.RESET_ALL}')
        print(f'Used Server Storage: {Fore.RED}{Style.BRIGHT}{space_TB_used:,} TB{Style.RESET_ALL}')
        print(f'Free Server Storage: {Fore.GREEN}{Style.BRIGHT}{space_TB_unused:,} TB{Style.RESET_ALL}\n')
        print(f'{Fore.YELLOW}{Style.BRIGHT}Primary Database Stats:{Style.RESET_ALL}')
        print(f'{num_total_files:,} Primary Media Files ({Fore.GREEN}{Style.BRIGHT}{total_size_TB:,.2f} TB{Style.RESET_ALL}, Duration: {Fore.YELLOW}{total_duration}{Style.RESET_ALL})\n')
        print(f'{Fore.BLUE}{Style.BRIGHT}{num_movie_files:,} BluRay Movies{Style.RESET_ALL} ({size_TB_movies:,} TB, Duration: {Fore.YELLOW}{duration_movies}{Style.RESET_ALL})')
        print(f'{Fore.MAGENTA}{Style.BRIGHT}{num_uhd_movie_files:,} 4K Movies{Style.RESET_ALL} ({size_TB_uhd_movies:,} TB, Duration: {Fore.YELLOW}{duration_uhd_movies}{Style.RESET_ALL})')
        print(f'{Fore.GREEN}{Style.BRIGHT}{num_shows:,} TV Shows{Style.RESET_ALL} ({num_show_files:,} Episodes, {size_TB_shows:,} TB, Duration: {Fore.YELLOW}{duration_shows}{Style.RESET_ALL})')
        print(f'{Fore.RED}{Style.BRIGHT}{num_anime:,} Anime Shows{Style.RESET_ALL} ({num_anime_files:,} Episodes, {size_TB_anime:,} TB, Duration: {Fore.YELLOW}{duration_anime}{Style.RESET_ALL})')
        print(f'{Fore.CYAN}{Style.BRIGHT}{num_book_files:,} Books{Style.RESET_ALL} ({size_GB_books:,} GB)')
        print(f'{Fore.LIGHTGREEN_EX}{Style.BRIGHT}{num_course_files:,} Course Videos{Style.RESET_ALL} ({size_GB_youtube:,} GB, Duration: {Fore.YELLOW}{duration_youtube}{Style.RESET_ALL})')
        print(f'\n{"#" * 10}\n')

if __name__ == "__main__":
    update_server_statistics(
        bool_update_duration=True,
        bool_print=True
        )