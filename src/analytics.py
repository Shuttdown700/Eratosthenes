#!/usr/bin/env python

import os
import ffmpeg
import json

from typing import Optional, Dict, Any
from colorama import Fore, Style, init

from utilities import (
    get_drive_name, get_drive_letter,
    read_alexandria, read_alexandria_config,
    read_json, get_file_size
)

# Initialize colorama
init(autoreset=True)

RESET = Style.RESET_ALL
BRIGHT = Style.BRIGHT
RED = Fore.RED
YELLOW = Fore.YELLOW
GREEN = Fore.GREEN

def update_movie_list(primary_drive_letter_dict : dict) -> list:
    # import utility methods
    import os
    from utilities import read_alexandria, write_list_to_txt_file
    # create list of primary movie directories
    primary_movie_drives = [letter+':/Movies/' for letter in primary_drive_letter_dict['Movies']]
    primary_movie_drives += [letter+':/Anime Movies/' for letter in primary_drive_letter_dict['Anime Movies']]
    # determine all primary movie filepaths
    movie_filepaths = read_alexandria(primary_movie_drives)
    # determine all primary movie filenames (without extension)
    movie_titles_with_year = [os.path.splitext(os.path.basename(filepath))[0] for filepath in movie_filepaths]
    # define output filepath
    src_directory = os.path.dirname(os.path.abspath(__file__))
    output_filepath = ("\\".join(src_directory.split('\\')[:-1])+"/output/").replace('\\','/')+'movie_list.txt'
    # write filename list to text file
    write_list_to_txt_file(output_filepath,movie_titles_with_year)
    # return filename list
    return movie_titles_with_year

def suggest_movie_downloads():
    # import utility methods
    import os
    from utilities import read_csv, read_file_as_list, write_list_to_txt_file
    # import API (handler) class
    from api import API
    # instantiate API class
    api_handler = API()
    # define paths
    src_directory = os.path.dirname(os.path.abspath(__file__))
    filepath_movie_list = ("\\".join(src_directory.split('\\')[:-1])+"/output/").replace('\\','/')+'movie_list.txt'
    # read current movie list
    list_movies = read_file_as_list(filepath_movie_list)
    list_movies = [x.lower() for x in list_movies]
    # get top rated movies from TMDb
    data_top_rated = read_csv(api_handler.filepath_tmdb_top_rated_csv)
    list_top_rated_movies = [f"{movie['Title_TMDb'].replace(': ',' - ')} ({movie['Release_Year']})" for movie in data_top_rated]
    # determine what movies are not currently downloaded
    movies_suggested = []
    for movie in list_top_rated_movies:
        if movie.lower() not in list_movies:
            movies_suggested.append(movie)
    # write suggested movie downloads to file
    output_filepath = ("\\".join(src_directory.split('\\')[:-1])+"/output/").replace('\\','/')+'movies_suggested.txt'
    write_list_to_txt_file(output_filepath,movies_suggested)
    return movies_suggested

def update_movie_list(drive_config,output_directory):
    import os
    from utilities import get_drive_letter, read_alexandria, read_alexandria_config, write_list_to_txt_file
    primary_drives_dict, backup_drives_dict, extensions_dict = read_alexandria_config(drive_config)
    primary_drive_letter_dict = {}
    for key,value in primary_drives_dict.items(): primary_drive_letter_dict[key] = [get_drive_letter(x) for x in value]
    primary_parent_paths = []; primary_extensions = []
    media_types = drive_config.keys()
    for media_type in media_types:
        primary_parent_paths += [f'{x}:/{media_type}' for x in primary_drive_letter_dict[media_type]]
        for item in primary_drive_letter_dict[media_type]:
            primary_extensions.append([x for x in extensions_dict[media_type]])
    primary_filepaths = read_alexandria(primary_parent_paths,primary_extensions)
    filepaths_movies = []
    for i,f in enumerate(primary_filepaths):
        if ':/Movies/' in f: filepaths_movies.append(f)
        elif ':/Anime Movies/' in f: filepaths_movies.append(f)
    filepath_movie_list = os.path.join(output_directory,'movie_list.txt')
    movie_titles = sorted(list(set(([filepath_movie.split('/')[2].strip() for filepath_movie in filepaths_movies]))))
    write_list_to_txt_file(filepath_movie_list, movie_titles)
    return movie_titles

def update_server_statistics(drive_config,filepath_statistics,bool_print=False):
    import json, os, shutil
    from colorama import Fore, Back, Style
    from utilities import read_alexandria, read_alexandria_config, get_drive_letter, get_file_size, write_list_to_txt_file
    directory_output = os.path.dirname(filepath_statistics)
    # read Alexandria Config
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
    music_drives_backup = drive_config['Music']['backup_drives']
    # identify drives
    drive_names = list(set(movie_drives_primary+movie_drives_backup+uhd_movie_drives_primary+uhd_movie_drives_backup+anime_movie_drives_primary+anime_movie_drives_backup+anime_drives_primary+anime_drives_backup+show_drives_primary+show_drives_backup+book_drives_primary+book_drives_backup+music_drives_primary+music_drives_backup))
    drive_names = [drive_name for drive_name in drive_names if drive_name != '']
    drive_letters = [get_drive_letter(drive_name) for drive_name in drive_names]
    drive_letters = [d for d in drive_letters if d is not None]
    primary_drives_dict, backup_drives_dict, extensions_dict = read_alexandria_config(drive_config)
    primary_drive_letter_dict = {}; backup_drive_letter_dict = {}
    for key,value in primary_drives_dict.items(): primary_drive_letter_dict[key] = [get_drive_letter(x) for x in value]
    primary_parent_paths = []; primary_extensions = []
    media_types = drive_config.keys()
    for media_type in media_types:
        primary_parent_paths += [f'{x}:/{media_type}' for x in primary_drive_letter_dict[media_type]]
        for item in primary_drive_letter_dict[media_type]:
            primary_extensions.append([x for x in extensions_dict[media_type]])
    # initialize counters
    space_TB_available = 0; space_TB_used = 0; space_TB_unused = 0
    # iterate through drives to determine overall usage
    for d in drive_letters:
        if d == '': continue
        disk_obj = shutil.disk_usage(f'{d}:/')
        space_TB_available += int(disk_obj[0]/10**12)
        space_TB_used += int(disk_obj[1]/10**12)
        space_TB_unused += int(disk_obj[2]/10**12)
    primary_filepaths = read_alexandria(primary_parent_paths,primary_extensions)
    # iterate through primary paths to sort into media type lists
    filepaths_movies = []; filepaths_anime_movies = []; filepaths_uhd_movies = []; filepaths_tv_shows = []
    filepaths_anime = []; filepaths_books = []; filepaths_courses = []; filepaths_music = []
    for i,f in enumerate(primary_filepaths):
        if ':/Movies/' in f: filepaths_movies.append(f)
        elif ':/Anime Movies/' in f: filepaths_anime_movies.append(f)
        elif ':/4K Movies/' in f: filepaths_uhd_movies.append(f)
        elif ':/Shows/' in f: filepaths_tv_shows.append(f)
        elif ':/Anime/' in f: filepaths_anime.append(f)
        elif ':/Books/' in f: filepaths_books.append(f)
        elif ':/Music/' in f: filepaths_music.append(f)
        elif ':/Courses/' in f: filepaths_courses.append(f)
    statistics_dict = {}
    # generate tv show statistics
    num_show_files = len(filepaths_tv_shows)
    show_titles = sorted(list(set(([f.split('/')[2].strip() for f in filepaths_tv_shows]))))
    filepath_show_list = os.path.join(directory_output,'show_list.txt')
    write_list_to_txt_file(filepath_show_list, show_titles)
    num_shows = len(show_titles)
    size_TB_shows = round(sum([get_file_size(filepath_tv_show,"TB") for filepath_tv_show in filepaths_tv_shows]),2)
    dict_show_stats = {"Number of Shows":num_shows,"Number of Episodes":num_show_files,"Total Size":f"{size_TB_shows:,.2f} TB","Show Titles":show_titles,"Primary Filepaths":filepaths_tv_shows}
    statistics_dict["TV Shows"] = dict_show_stats
    # generate anime statistics
    num_anime_files = len(filepaths_anime)
    anime_titles = sorted(list(set(([filepath_anime.split('/')[2].strip() for filepath_anime in filepaths_anime]))))
    filepath_anime_list = os.path.join(directory_output,'anime_list.txt')
    write_list_to_txt_file(filepath_anime_list, anime_titles)
    num_anime = len(anime_titles)
    size_TB_anime = round(sum([get_file_size(filepath_anime,"TB") for filepath_anime in filepaths_anime]),2)
    dict_anime_stats = {"Number of Anime":num_anime,"Number of Episodes":num_anime_files,"Total Size":f"{size_TB_anime:,.2f} TB","Anime Titles":anime_titles,"Primary Filepaths":filepaths_anime}
    statistics_dict["Anime"] = dict_anime_stats
    # generate movie statistics
    num_movie_files = len(filepaths_movies)
    movie_titles = sorted(list(set(([filepath_movie.split('/')[2].strip() for filepath_movie in filepaths_movies]))))
    filepath_movie_list = os.path.join(directory_output,'movie_list.txt')
    write_list_to_txt_file(filepath_movie_list, movie_titles)
    num_movies = len(movie_titles)
    size_TB_movies = round(sum([get_file_size(filepath_movie,"TB") for filepath_movie in filepaths_movies]),2)
    dict_movie_stats = {"Number of Movies":num_movies,"Total Size":f"{size_TB_movies:,.2f} TB","Movie Titles":movie_titles,"Primary Filepaths":filepaths_movies}
    statistics_dict["Movies"] = dict_movie_stats
    # generate anime movie statistics
    num_anime_movie_files = len(filepaths_anime_movies)
    anime_movie_titles = sorted(list(set(([filepath_anime_movie.split('/')[2].strip() for filepath_anime_movie in filepaths_anime_movies]))))
    filepath_anime_movie_list = os.path.join(directory_output,'anime_movie_list.txt')
    write_list_to_txt_file(filepath_anime_movie_list, anime_movie_titles)
    num_anime_movies = len(anime_movie_titles)
    size_GB_anime_movies = round(sum([get_file_size(filepath_anime_movie,"GB") for filepath_anime_movie in filepaths_anime_movies]),2)
    dict_anime_movie_stats = {"Number of Anime Movies":num_anime_movies,"Total Size":f"{size_GB_anime_movies:,.2f} GB","Anime Movie Titles":anime_movie_titles,"Primary Filepaths":filepaths_anime_movies}
    statistics_dict["Anime Movies"] = dict_anime_movie_stats
    # generate 4K movie statistics
    num_uhd_movie_files = len(filepaths_uhd_movies)
    uhd_movie_titles = sorted(list(set(([filepath_uhd_movie.split('/')[2].strip() for filepath_uhd_movie in filepaths_uhd_movies]))))
    num_uhd_movies = len(uhd_movie_titles)
    size_TB_uhd_movies = round(sum([get_file_size(filepath_uhd_movie,"TB") for filepath_uhd_movie in filepaths_uhd_movies]),2)
    dict_uhd_movie_stats = {"Number of 4K Movies":num_uhd_movies,"Total Size":f"{size_TB_uhd_movies:,.2f} TB","4K Movie Titles":uhd_movie_titles,"Primary Filepaths":filepaths_uhd_movies}
    statistics_dict["4K Movies"] = dict_uhd_movie_stats
    # generate book statistics
    num_book_files = len(filepaths_books)
    size_GB_books = round(sum([get_file_size(filepath_book,"GB") for filepath_book in filepaths_books]),2)
    book_titles = sorted([os.path.splitext(os.path.basename(filepath_book))[0] for filepath_book in filepaths_books],reverse=True)
    dict_book_stats = {"Number of Books":num_book_files,"Total Size":f"{size_GB_books:,.2f} GB","Book Titles":book_titles,"Primary Filepaths":filepaths_books}
    statistics_dict["Books"] = dict_book_stats
    # generate music statistics
    num_music_files = len(filepaths_music)
    size_GB_music = round(sum([get_file_size(filepath_music,"GB") for filepath_music in filepaths_music]),2)
    dict_music_stats = {"Number of Songs":num_music_files,"Total Size":f"{size_GB_music:,.2f} GB","Primary Filepaths":filepaths_music}
    statistics_dict["Music"] = dict_music_stats
    # generate course statistics
    num_course_files = len(filepaths_courses)
    size_GB_courses = round(sum([get_file_size(filepath_course,"GB") for filepath_course in filepaths_courses]),2)
    dict_course_stats = {"Number of Course Videos":num_course_files,"Total Size":f"{size_GB_courses:,.2f} GB","Primary Filepaths":filepaths_courses}
    statistics_dict["Courses"] = dict_course_stats
    # aggregate statistics
    num_total_files = num_show_files + num_anime_files + num_movie_files + num_anime_movie_files + num_uhd_movie_files + num_book_files + num_course_files
    total_size_TB = size_TB_shows + size_TB_anime + size_TB_movies + size_GB_anime_movies/1000 + size_TB_uhd_movies + size_GB_books/1000 + size_GB_music/1000 + size_GB_courses/1000
    # save statistics to output file
    with open(filepath_statistics, 'w') as json_file:
        json.dump(statistics_dict, json_file, indent=4)
    # print statistics
    if bool_print: 
        print(f'\n{"#"*10}\n\n{Fore.YELLOW}{Style.BRIGHT}Server Stats:{Style.RESET_ALL}')
        print(f'Total Available Server Storage: {Fore.BLUE}{Style.BRIGHT}{space_TB_available:,} TB{Style.RESET_ALL}\nUsed Server Storage: {Fore.RED}{Style.BRIGHT}{space_TB_used:,} TB{Style.RESET_ALL}\nFree Server Storage: {Fore.GREEN}{Style.BRIGHT}{space_TB_unused:,} TB{Style.RESET_ALL}')
        print(f'\n{Fore.YELLOW}{Style.BRIGHT}Primary Database Stats:{Style.RESET_ALL}')
        print(f'{num_total_files:,} Primary Media Files ({Fore.GREEN}{Style.BRIGHT}{total_size_TB:,.2f} TB{Style.RESET_ALL})\n{Fore.BLUE}{Style.BRIGHT}{num_movie_files:,} BluRay Movies{Style.RESET_ALL} ({size_TB_movies:,} TB)\n{Fore.MAGENTA}{Style.BRIGHT}{num_uhd_movie_files:,} 4K Movies{Style.RESET_ALL} ({size_TB_uhd_movies:,} TB)\n{Fore.GREEN}{Style.BRIGHT}{num_shows:,} TV Shows{Style.RESET_ALL} ({num_show_files:,} TV Show Episodes, {size_TB_shows:,} TB)\n{Fore.RED}{Style.BRIGHT}{num_anime:,} Anime Shows{Style.RESET_ALL} ({num_anime_files:,} Anime Episodes, {size_TB_anime:,} TB)\n{Fore.CYAN}{Style.BRIGHT}{num_book_files:,} Books{Style.RESET_ALL} ({size_GB_books:,} GB)\n{Fore.LIGHTGREEN_EX}{Style.BRIGHT}{num_course_files:,} Course Videos{Style.RESET_ALL} ({size_GB_courses:,} GB)')
        print(f'\n{"#"*10}\n')

def get_video_media_info(filepath):
    src_directory = os.path.dirname(os.path.abspath(__file__))
    filepath_ffprobe = os.path.join(src_directory, 'bin', 'ffprobe.exe')

    if not os.path.exists(filepath):
        raise FileNotFoundError(
            f"The file at {filepath} does not exist or is not accessible."
        )

    print(
        f"{GREEN}{BRIGHT}Downloading media info{RESET} for: "
        f"{YELLOW}{BRIGHT}{os.path.splitext(os.path.basename(filepath))[0]}{RESET}"
    )

    try:
        probe = ffmpeg.probe(filepath, cmd=filepath_ffprobe)
    except ffmpeg.Error as e:
        error_message = e.stderr.decode("utf-8", errors="ignore")
        print(f"{RED}FFmpeg Error:{RESET} {error_message}")
        return {
            'filepath': filepath,
            'file_size_GB': '',
            'video_codec': '',
            'video_minutes': '',
            'video_height': '',
            'video_width': '',
            'audio_codec': '',
            'audio_num_tracks': '',
            'audio_num_channels': '',
            'audio_channel_layout': '',
        }

    # File size
    file_size_gb = round(get_file_size(filepath, "GB"), 3)

    # Video stream
    video_stream = next(
        (stream for stream in probe['streams'] if stream['codec_type'] == 'video'),
        None
    )

    if video_stream:
        video_codec = video_stream.get('codec_name', 'N/A')
        duration = float(video_stream.get('duration', probe['format'].get('duration', 0)))
        video_minutes = round(duration / 60, 2)
        video_height = video_stream.get('height', 'N/A')
        video_width = video_stream.get('width', 'N/A')
    else:
        video_codec = video_minutes = video_height = video_width = 'N/A'

    # Audio streams
    audio_streams = [
        stream for stream in probe['streams'] if stream['codec_type'] == 'audio'
    ]
    audio_num_tracks = len(audio_streams)

    if audio_num_tracks > 0:
        audio_stream = audio_streams[0]
        audio_codec = audio_stream.get('codec_name', 'N/A')
        audio_num_channels = audio_stream.get('channels', 'N/A')
        audio_channel_layout = audio_stream.get('channel_layout', 'N/A')
    else:
        audio_codec = audio_num_channels = audio_channel_layout = 'N/A'

    return {
        'filepath': filepath,
        'file_size_GB': file_size_gb,
        'video_codec': video_codec.upper() if isinstance(video_codec, str) else video_codec,
        'video_minutes': video_minutes,
        'video_height': video_height,
        'video_width': video_width,
        'audio_codec': audio_codec.upper() if isinstance(audio_codec, str) else audio_codec,
        'audio_num_tracks': audio_num_tracks,
        'audio_num_channels': audio_num_channels,
        'audio_channel_layout': audio_channel_layout,
    }

def update_media_file_data(
    drive_config: Dict[str, Any],
    filepath_backup_surface_area: str,
    bool_print: bool = False,
    overwrite_media_data: bool = False,
    reset: Optional[bool] = False
    ) -> None:
    def process_media_type(media_type, primary_drives, backup_drives, extensions, backup_surface_area, backup_surface_area_current, bool_print, overwrite_media_data):
        directories_primary = [f'{get_drive_letter(d)}:/{media_type}/' for d in primary_drives]
        directories_backup = [f'{get_drive_letter(d)}:/{media_type}/' for d in backup_drives]

        filepaths_primary = read_alexandria(directories_primary, extensions)
        filepaths_backup = read_alexandria(directories_backup, extensions)
        filepaths = filepaths_primary + filepaths_backup

        media_dict = backup_surface_area.get(media_type, {})

        for filepath in filepaths:
            title = os.path.splitext(os.path.basename(filepath))[0]
            current_size = os.path.getsize(filepath)
            existing_entry = backup_surface_area_current.get(media_type, {}).get(title)

            should_fetch = (
                overwrite_media_data or
                not existing_entry or
                existing_entry.get("File Size Bytes") != current_size
            )

            if title in media_dict and not should_fetch:
                if bool_print:
                    print(f'{YELLOW}Unchanged backup:{RESET} {title}')
                media_dict[title]["Number of Copies"] += 1
                drive_name = get_drive_name(filepath[0])
                media_dict[title]["Drives (Name)"].append(drive_name)
            else:
                if bool_print:
                    status = "File changed" if existing_entry else "Fetching"
                    print(f'{GREEN}{status} media info:{RESET} {title}')
                media_info = get_video_media_info(filepath)
                media_dict[title] = {
                    "Number of Copies": 1,
                    "Size (GB)": get_file_size(filepath, "GB"),
                    "File Size Bytes": current_size,
                    "Media Type": media_type,
                    "Series Title": filepath.split('/')[2].strip() if media_type in ['Shows', 'Anime'] else 'N/A',
                    "Drives (Name)": [get_drive_name(filepath[0])],
                    "Filepath_noLetter": filepath[1:],
                    "Extension": filepath.split('.')[-1],
                    "Video Codec": media_info['video_codec'],
                    "Audio Codec": media_info['audio_codec'],
                    "Length (min.)": media_info['video_minutes'],
                    "Video Height": media_info['video_height'],
                    "Video Width": media_info['video_width'],
                    "Audio Tracks": media_info['audio_num_tracks'],
                    "Audio Channels": media_info['audio_num_channels'],
                    "Audio Channel Layout": media_info['audio_channel_layout'],
                }

            media_dict[title]["Drives (Name)"] = sorted(set(media_dict[title]["Drives (Name)"]))
        backup_surface_area[media_type] = media_dict
    try:
        backup_surface_area_current = read_json(filepath_backup_surface_area)
        reset_flag = reset is True
        if reset_flag:
            if bool_print:
                print(f"{YELLOW}Resetting existing backup data...{RESET}")
            backup_surface_area_current = {}
    except FileNotFoundError:
        backup_surface_area_current = {}

    extensions_dict = read_alexandria_config(drive_config)[2]
    media_areas = (
        ("Shows", drive_config['Shows']['primary_drives'], drive_config['Shows']['backup_drives']),
        ("Anime", drive_config['Anime']['primary_drives'], drive_config['Anime']['backup_drives']),
        ("Movies", drive_config['Movies']['primary_drives'], drive_config['Movies']['backup_drives']),
        ("Anime Movies", drive_config['Anime Movies']['primary_drives'], drive_config['Anime Movies']['backup_drives']),
        ("4K Movies", drive_config['4K Movies']['primary_drives'], drive_config['4K Movies']['backup_drives']),
    )

    if bool_print:
        print(f'\n{"#"*10}\n\n{BRIGHT}{YELLOW}Starting media file analyzer{RESET}\n\n{"#"*10}\n')

    backup_surface_area = backup_surface_area_current.copy()

    try:
        for media_type, primary_drives, backup_drives in media_areas:
            if bool_print:
                print(f'Analyzing {BRIGHT}{media_type}{RESET}:\n')

            process_media_type(
                media_type, primary_drives, backup_drives,
                extensions_dict[media_type], backup_surface_area,
                backup_surface_area_current, bool_print, overwrite_media_data
            )

            # Save after each media_type batch
            with open(filepath_backup_surface_area, 'w', encoding='utf-8') as json_file:
                json.dump(backup_surface_area, json_file, indent=4)

    except KeyboardInterrupt:
        print(f'{RED}Interrupted by user.{RESET}')
        try:
            with open(filepath_backup_surface_area, 'w', encoding='utf-8') as json_file:
                json.dump(backup_surface_area, json_file, indent=4)
        except (TypeError, ValueError) as e:
            print(f'{RED}Serialization Error:{RESET} {e}')
            # Fallback: trim last key-value from dict
            trimmed_data = dict(list(backup_surface_area.items())[:-1])
            with open(filepath_backup_surface_area, 'w', encoding='utf-8') as json_file:
                json.dump(trimmed_data, json_file, indent=4)

    except Exception as e:
        print(f'{RED}Error:{RESET} {e}')
        try:
            with open(filepath_backup_surface_area, 'w', encoding='utf-8') as json_file:
                json.dump(backup_surface_area, json_file, indent=4)
        except (TypeError, ValueError) as e:
            print(f'{RED}Serialization Error:{RESET} {e}')
            # Fallback: trim last key-value from dict
            trimmed_data = dict(list(backup_surface_area.items())[:-1])
            with open(filepath_backup_surface_area, 'w', encoding='utf-8') as json_file:
                json.dump(trimmed_data, json_file, indent=4)

def read_media_statistics(filepath_statistics,bool_update=False,bool_print=True):
    import os
    from utilities import read_json
    from colorama import Fore, Style, init
    init(autoreset=True)
    if bool_update: 
        src_directory = os.path.dirname(os.path.abspath(__file__))
        drive_hieracrchy_filepath = (src_directory+"/config/alexandria_drives.config").replace('\\','/')
        drive_config = read_json(drive_hieracrchy_filepath)
        update_server_statistics(drive_config, filepath_statistics)
    data = read_json(filepath_statistics)
    num_shows = data["TV Shows"]["Number of Shows"]
    num_show_episodes = data["TV Shows"]["Number of Episodes"]
    num_anime = data["Anime"]["Number of Anime"]
    num_anime_episodes = data["Anime"]["Number of Episodes"]
    num_bluray_movies = data["Movies"]["Number of Movies"]
    num_anime_movies = data["Anime Movies"]["Number of Anime Movies"]
    num_4k_movies = data["4K Movies"]["Number of 4K Movies"]
    num_books = data["Books"]["Number of Books"]
    num_songs = data["Music"]["Number of Songs"]
    num_course_videos = data["Courses"]["Number of Course Videos"]
    size_shows = data["TV Shows"]["Total Size"]
    size_anime = data["Anime"]["Total Size"]
    size_movies = data["Movies"]["Total Size"]
    size_anime_movies = data["Anime Movies"]["Total Size"]
    size_4k_movies = data["4K Movies"]["Total Size"]
    size_books = data["Books"]["Total Size"]
    size_music = data["Music"]["Total Size"]
    size_courses = data["Courses"]["Total Size"]
    if bool_print:
        print(f'\n{"#"*10}\n')
        print("Media Statistics\n")
        print(f"{Fore.YELLOW}{Style.BRIGHT}Shows: {Style.NORMAL}{num_shows:,} shows, {num_show_episodes:,} episodes | {size_shows}")
        print(f"{Fore.CYAN}{Style.BRIGHT}Anime: {Style.NORMAL}{num_anime:,} series, {num_anime_episodes:,} episodes | {size_anime}")
        print(f"{Fore.MAGENTA}{Style.BRIGHT}Movies: {Style.NORMAL}{num_bluray_movies:,} Blu-ray, {num_anime_movies:,} Anime, {num_4k_movies:,} 4K Movies | {size_movies}, {size_anime_movies}, {size_4k_movies}")
        print(f"{Fore.GREEN}{Style.BRIGHT}Books: {Style.NORMAL}{num_books:,} books | {size_books}")
        print(f"{Fore.BLUE}{Style.BRIGHT}Music: {Style.NORMAL}{num_songs:,} songs | {size_music}")
        print(f"{Fore.RED}{Style.BRIGHT}Courses: {Style.NORMAL}{num_course_videos:,} course videos | {size_courses}")
        print(f'\n{"#"*10}\n')
    return data

def get_show_size(show_title_with_year, filepath_alexandria_media_details):
    from utilities import read_json
    data = read_json(filepath_alexandria_media_details)
    show_data = data['Shows']
    if 'Anime' in list(data.keys()): show_data.update(data['Anime'])
    size_GB = 0
    for val in show_data.values():
        if val['Media Type'] in ['Shows','Anime']:
            if show_title_with_year in val['Filepath_noLetter']:
                size_GB += val['Size (GB)']
    return size_GB

def get_media_type_size(media_type, filepath_alexandria_media_details):
    from utilities import read_json
    data = read_json(filepath_alexandria_media_details)
    size_GB = 0; num_files = 0
    media_type_data = data[media_type]
    for val in media_type_data.values():
        if val['Media Type'] == media_type:
            size_GB += val['Size (GB)']
            num_files += 1
    size_TB = size_GB / 1000
    return num_files, size_TB

def read_media_file_data(filepath_alexandria_media_details,bool_update=False,bool_print_backup_data=True):
    import json, os
    from utilities import read_json
    from colorama import Fore, Style, init
    init(autoreset=True)
    src_directory = os.path.dirname(os.path.abspath(__file__))
    if bool_update: 
        drive_hieracrchy_filepath = (src_directory+"/config/alexandria_drives.config").replace('\\','/')
        drive_config = read_json(drive_hieracrchy_filepath)
        update_media_file_data(drive_config, filepath_alexandria_media_details)
    data = read_json(filepath_alexandria_media_details)
    media_order_values = {"Shows":1,"Anime":2,"Movies":3,"Anime Movies":4,"4k Movies":5}
    media_types = sorted(list(set([item[0] for item in data.items()])),key= lambda x: media_order_values.get(x,10))
    backup_count_dict = {media_type: {} for media_type in media_types}
    backup_list_dict = {media_type: {} for media_type in media_types}
    for media_type in media_types:
        media_type_data = data[media_type]
        for idx,item in enumerate(media_type_data.items()):
            media_data = item[1]
            # media_type = media_data["Media Type"]
            num_backups = media_data["Number of Copies"] - 1
            key_string_backup_dict = f'{num_backups} backup copy' if num_backups == 1 else f'{num_backups} backup copies'
            # update backup counters
            if key_string_backup_dict in backup_count_dict[media_type].keys():
                backup_count_dict[media_type][key_string_backup_dict] += 1
            else:
                backup_count_dict[media_type][key_string_backup_dict] = 1
            # update title lists by backup count
            media_name = media_data["Filepath_noLetter"].split('/')[2]
            if key_string_backup_dict in backup_list_dict[media_type].keys():
                backup_list_dict[media_type][key_string_backup_dict].append(media_name)
            else:
                backup_list_dict[media_type][key_string_backup_dict] = [media_name]
    # remove duplicates in the title lists
    for key_media_type, val_backup_list_name in backup_list_dict.items():
        for key_list in val_backup_list_name.keys():
            val_backup_list_name[key_list] = sorted(list(set(val_backup_list_name[key_list])))
    backup_count_dict = {outer_key: dict(sorted(inner_dict.items())) for outer_key, inner_dict in backup_count_dict.items()}
    backup_list_dict = {outer_key: dict(sorted(inner_dict.items())) for outer_key, inner_dict in backup_list_dict.items()}
    if bool_print_backup_data: print(f'\n{"#"*10}\n')
    if bool_print_backup_data: print(f"{Fore.MAGENTA}{Style.BRIGHT}Backup Statistics{Style.RESET_ALL}")
    backup_keys = list(backup_count_dict.keys())
    total_size_TB = sum([get_media_type_size(backup_key, filepath_alexandria_media_details)[-1] for backup_key in backup_keys])
    total_primary_files = sum([get_media_type_size(backup_key, filepath_alexandria_media_details)[0] for backup_key in backup_keys])
    total_copies = 0; total_count_no_backup = 0; total_count_one_backup = 0; total_count_multi_backups = 0
    for backup_key in backup_keys:
        total_copies += sum(list(backup_count_dict[backup_key].values()))
        total_count_no_backup += backup_count_dict[backup_key].get("0 backup copies",0)
        total_count_one_backup += backup_count_dict[backup_key].get("1 backup copy",0)
    total_count_multi_backups += total_copies - total_count_no_backup - total_count_one_backup
    total_prop_no_backups = total_count_no_backup/total_primary_files
    total_prop_one_backup = total_count_one_backup/total_primary_files
    total_prop_multiple_backups = total_count_multi_backups/total_primary_files
    if bool_print_backup_data:
        print(f'\n{Fore.YELLOW}{Style.BRIGHT}Total Dasbase{Style.RESET_ALL}: {total_primary_files:,} total files ({total_size_TB:,.2f} TB)')
        print(f'\t{Fore.RED}{Style.BRIGHT}Without backup{Style.RESET_ALL}: {total_prop_no_backups*100:.1f}% ({total_size_TB*total_prop_no_backups:,.2f} TB, {total_count_no_backup:,} files)')
        print(f'\t{Fore.YELLOW}{Style.BRIGHT}With one backup{Style.RESET_ALL}: {total_prop_one_backup*100:.1f}% ({total_size_TB*total_prop_one_backup:,.2f} TB, {total_count_one_backup:,} files)')
        print(f'\t{Fore.GREEN}{Style.BRIGHT}With multiple backups{Style.RESET_ALL}: {total_prop_multiple_backups*100:.1f}% ({total_size_TB*total_prop_multiple_backups:,.2f} TB, {total_count_multi_backups:,} files)')    
    
    for media_type in media_types:
        backup_count_dict_for_media_type = backup_count_dict[media_type]
        media_type_total_primary_files, media_type_size_TB = get_media_type_size(media_type, filepath_alexandria_media_details)
        # total = sum([count for count in backup_count_dict_for_media_type.values()])
        count_no_backups = backup_count_dict_for_media_type.get("0 backup copies",0)
        count_one_backup = backup_count_dict_for_media_type.get("1 backup copy",0)
        count_multiple_backups = media_type_total_primary_files - count_no_backups - count_one_backup
        prop_no_backups = count_no_backups/media_type_total_primary_files
        prop_one_backup = count_one_backup/media_type_total_primary_files
        prop_multiple_backups = count_multiple_backups/media_type_total_primary_files
        prop_alexandria_files = media_type_total_primary_files/total_primary_files
        prop_alexandria_size = media_type_size_TB/total_size_TB
        if bool_print_backup_data:
            print(f'\n{Fore.YELLOW}{Style.BRIGHT}{media_type}{Style.RESET_ALL}: {media_type_total_primary_files:,} total files ({media_type_size_TB:,.2f} TB) {Fore.MAGENTA}{Style.BRIGHT}[{prop_alexandria_files*100:.1f}% of Alexandria DB files, {prop_alexandria_size*100:.1f}% of Alexandria DB size]{Style.RESET_ALL}')
            print(f'\t{Fore.RED}{Style.BRIGHT}Without backup{Style.RESET_ALL}: {prop_no_backups*100:.1f}% ({media_type_size_TB*prop_no_backups:,.2f} TB, {count_no_backups:,} files)')
            print(f'\t{Fore.YELLOW}{Style.BRIGHT}With one backup{Style.RESET_ALL}: {prop_one_backup*100:.1f}% ({media_type_size_TB*prop_one_backup:,.2f} TB, {count_one_backup:,} files)')
            print(f'\t{Fore.GREEN}{Style.BRIGHT}With multiple backups{Style.RESET_ALL}: {prop_multiple_backups*100:.1f}% ({media_type_size_TB*prop_multiple_backups:,.2f} TB, {count_multiple_backups:,} files)')
        print_line = '\t'; num_titles_per_line = 3
        if "0 backup copies" in backup_list_dict[media_type].keys():
            for idx,title in enumerate(backup_list_dict[media_type]["0 backup copies"]):
                if idx == 0 and bool_print_backup_data: print(f'\n{Fore.RED}{Style.BRIGHT}{media_type} without backups:\n')
                if media_type in ['Shows','Anime']:
                    size_GB = get_show_size(title, filepath_alexandria_media_details)
                    size_print_portion = f'{Fore.GREEN}| {Fore.BLUE}{size_GB:.1f} GB{Style.RESET_ALL}'
                else:
                    try:
                        size_GB = data[title]["Size (GB)"]
                        size_print_portion = f'{Fore.GREEN}| {Fore.BLUE}{size_GB:.1f} GB{Style.RESET_ALL}'
                    except KeyError:
                        size_print_portion = ''
                print_line += f'{Fore.RED}[{idx+1:02}]{Style.RESET_ALL} {title} {size_print_portion}'.strip()
                if idx % num_titles_per_line == 0 and idx != 0:
                    if bool_print_backup_data: print(print_line)
                    print_line = '\t'
                else:
                    print_line += f'{Fore.RED}, {Style.RESET_ALL}'
            if print_line != '\t' and bool_print_backup_data: print(', '.join(print_line.split(',')[:-1]).rstrip())
    if bool_print_backup_data: print(f'\n{"#"*10}\n')
    # save statistics to output file
    output_directory = ("\\".join(src_directory.split('\\')[:-1])+"/output").replace('\\','/')
    filepath_backup_metrics = os.path.join(output_directory,"alexandria_backup_metrics.json").replace('\\','/')
    with open(filepath_backup_metrics, 'w') as json_file:
        json.dump(backup_count_dict, json_file, indent=4)
    filepath_backup_lists = os.path.join(output_directory,"alexandria_backup_lists.json").replace('\\','/')
    with open(filepath_backup_lists, 'w') as json_file:
        json.dump(backup_list_dict, json_file, indent=4)
    return data

def main():
    import os
    from utilities import get_drive_letter, get_file_size, read_alexandria, read_alexandria_config, read_json
    from api import API
    # define paths
    src_directory = os.path.dirname(os.path.abspath(__file__))
    drive_hieracrchy_filepath = (src_directory+"/config/alexandria_drives.config").replace('\\','/')
    output_directory = ("\\".join(src_directory.split('\\')[:-1])+"/output").replace('\\','/')
    filepath_statistics = os.path.join(output_directory,"alexandria_media_statistics.json").replace('\\','/')
    filepath_alexandria_media_details = os.path.join(output_directory,"alexandria_media_details.json").replace('\\','/')
    drive_config = read_json(drive_hieracrchy_filepath)
    # define primary & backup drives
    primary_drives_dict, backup_drives_dict, extensions_dict = read_alexandria_config(drive_config)
    primary_drive_letter_dict = {}; backup_drive_letter_dict = {}
    for key,value in primary_drives_dict.items(): primary_drive_letter_dict[key] = [get_drive_letter(x) for x in value]
    for key,value in backup_drives_dict.items(): backup_drive_letter_dict[key] = [get_drive_letter(x) for x in value]
    # api_handler = API()
    # movie_titles_with_year = update_movie_list(drive_config,output_directory)
    # api_handler.tmdb_movies_fetch()
    # read_media_statistics(filepath_statistics,bool_update=False,bool_print=True)
    read_media_file_data(filepath_alexandria_media_details,bool_update=False,bool_print_backup_data=True)
    # update_server_statistics(drive_config,filepath_statistics)
    # update_media_file_data(drive_config,filepath_alexandria_media_details,bool_print=True, overwrite_media_data=False, reset=False)
    # movies_suggested = suggest_movie_downloads()
    # data_media_statistics = read_media_statistics(filepath_statistics)
    # read_media_file_data(filepath_alexandria_media_details)

if __name__ == '__main__':
    main()


"""
Check to ensure files in media stats still exisits and delete those not in primary drives anymore
"""
