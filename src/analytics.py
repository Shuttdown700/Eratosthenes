#!/usr/bin/env python

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

def update_movie_file_metadata(drive_config):
    movie_drives_primary = drive_config['Movies']['primary_drives']
    uhd_movie_drives_primar = drive_config['4K Movies']['primary_drives']
    anime_movie_drives_primary = drive_config['Anime Movies']['primary_drives']

def update_show_file_metadata():
    pass

def update_server_statistics(drive_config,filepath_statistics):
    import json, os, shutil
    from colorama import Fore, Back, Style
    from utilities import read_alexandria, read_alexandria_config, get_drive_letter, get_file_size
    # read Alexandria Config
    movie_drives_primary = drive_config['Movies']['primary_drives']
    movie_drives_backup = drive_config['Movies']['backup_drives']
    uhd_movie_drives_primary = drive_config['4K Movies']['primary_drives']
    uhd_movie_drives_backup = drive_config['4K Movies']['backup_drives']
    anime_movie_drives_primary = drive_config['Anime Movies']['primary_drives']
    anime_movie_drives_backup = drive_config['Anime Movies']['backup_drives']
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
    drive_names.remove('')
    drive_letters = [get_drive_letter(drive_name) for drive_name in drive_names]
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
    num_shows = len(show_titles)
    size_TB_shows = round(sum([get_file_size(filepath_tv_show) for filepath_tv_show in filepaths_tv_shows])/10**3,2)
    dict_show_stats = {"Number of Shows":num_shows,"Number of Episodes":num_show_files,"Total Size":f"{size_TB_shows:,.2f} TB","Show Titles":show_titles,"Primary Filepaths":filepaths_tv_shows}
    statistics_dict["TV Shows"] = dict_show_stats
    # generate anime statistics
    num_anime_files = len(filepaths_anime)
    anime_titles = sorted(list(set(([filepath_anime.split('/')[2].strip() for filepath_anime in filepaths_anime]))))
    num_anime = len(anime_titles)
    size_TB_anime = round(sum([get_file_size(filepath_anime) for filepath_anime in filepaths_anime])/10**3,2)
    dict_anime_stats = {"Number of Anime":num_anime,"Number of Episodes":num_anime_files,"Total Size":f"{size_TB_anime:,.2f} TB","Anime Titles":anime_titles,"Primary Filepaths":filepaths_anime}
    statistics_dict["Anime"] = dict_anime_stats
    # generate movie statistics
    num_movie_files = len(filepaths_movies)
    movie_titles = sorted(list(set(([filepath_movie.split('/')[2].strip() for filepath_movie in filepaths_movies]))))
    num_movies = len(movie_titles)
    size_TB_movies = round(sum([get_file_size(filepath_movie) for filepath_movie in filepaths_movies])/10**3,2)
    dict_movie_stats = {"Number of Movies":num_movies,"Total Size":f"{size_TB_movies:,.2f} TB","Movie Titles":movie_titles,"Primary Filepaths":filepaths_movies}
    statistics_dict["Movies"] = dict_movie_stats
    # generate anime movie statistics
    num_anime_movie_files = len(filepaths_anime_movies)
    anime_movie_titles = sorted(list(set(([filepath_anime_movie.split('/')[2].strip() for filepath_anime_movie in filepaths_anime_movies]))))
    num_anime_movies = len(anime_movie_titles)
    size_GB_anime_movies = round(sum([get_file_size(filepath_anime_movie) for filepath_anime_movie in filepaths_anime_movies]),2)
    dict_anime_movie_stats = {"Number of Anime Movies":num_anime_movies,"Total Size":f"{size_GB_anime_movies:,.2f} GB","Anime Movie Titles":anime_movie_titles,"Primary Filepaths":filepaths_anime_movies}
    statistics_dict["Anime Movies"] = dict_anime_movie_stats
    # generate 4K movie statistics
    num_uhd_movie_files = len(filepaths_uhd_movies)
    uhd_movie_titles = sorted(list(set(([filepath_uhd_movie.split('/')[2].strip() for filepath_uhd_movie in filepaths_uhd_movies]))))
    num_uhd_movies = len(uhd_movie_titles)
    size_TB_uhd_movies = round(sum([get_file_size(filepath_uhd_movie) for filepath_uhd_movie in filepaths_uhd_movies])/10**3,2)
    dict_uhd_movie_stats = {"Number of 4K Movies":num_uhd_movies,"Total Size":f"{size_TB_uhd_movies:,.2f} TB","4K Movie Titles":uhd_movie_titles,"Primary Filepaths":filepaths_uhd_movies}
    statistics_dict["4K Movies"] = dict_uhd_movie_stats
    # generate book statistics
    num_book_files = len(filepaths_books)
    size_GB_books = round(sum([get_file_size(filepath_book) for filepath_book in filepaths_books]),2)
    book_titles = sorted([os.path.splitext(os.path.basename(filepath_book))[0] for filepath_book in filepaths_books],reverse=True)
    dict_book_stats = {"Number of Books":num_book_files,"Total Size":f"{size_GB_books:,.2f} GB","Book Titles":book_titles,"Primary Filepaths":filepaths_books}
    statistics_dict["Books"] = dict_book_stats
    # generate music statistics
    num_music_files = len(filepaths_music)
    size_GB_music = round(sum([get_file_size(filepath_music) for filepath_music in filepaths_music]),2)
    dict_music_stats = {"Number of Songs":num_music_files,"Total Size":f"{size_GB_music:,.2f} GB","Primary Filepaths":filepaths_music}
    statistics_dict["Music"] = dict_music_stats
    # generate course statistics
    num_course_files = len(filepaths_courses)
    size_GB_courses = round(sum([get_file_size(filepath_course) for filepath_course in filepaths_courses]),2)
    dict_course_stats = {"Number of Course Videos":num_course_files,"Total Size":f"{size_GB_courses:,.2f} GB","Primary Filepaths":filepaths_courses}
    statistics_dict["Courses"] = dict_course_stats
    # aggregate statistics
    num_total_files = num_show_files + num_anime_files + num_movie_files + num_anime_movie_files + num_uhd_movie_files + num_book_files + num_course_files
    total_size_TB = size_TB_shows + size_TB_anime + size_TB_movies + size_GB_anime_movies/1000 + size_TB_uhd_movies + size_GB_books/1000 + size_GB_music/1000 + size_GB_courses/1000
    # save statistics to output file
    with open(filepath_statistics, 'w') as json_file:
        json.dump(statistics_dict, json_file, indent=4)
    # print statistics
    print(f'\n{"#"*10}\n\n{Fore.YELLOW}{Style.BRIGHT}Server Stats:{Style.RESET_ALL}')
    print(f'Total Available Server Storage: {Fore.BLUE}{Style.BRIGHT}{space_TB_available:,} TB{Style.RESET_ALL}\nUsed Server Storage: {Fore.RED}{Style.BRIGHT}{space_TB_used:,} TB{Style.RESET_ALL}\nFree Server Storage: {Fore.GREEN}{Style.BRIGHT}{space_TB_unused:,} TB{Style.RESET_ALL}')
    print(f'\n{Fore.YELLOW}{Style.BRIGHT}Primary Database Stats:{Style.RESET_ALL}')
    print(f'{num_total_files:,} Primary Media Files ({Fore.GREEN}{Style.BRIGHT}{total_size_TB:,.2f} TB{Style.RESET_ALL})\n{Fore.BLUE}{Style.BRIGHT}{num_movie_files:,} BluRay Movies{Style.RESET_ALL} ({size_TB_movies:,} TB)\n{Fore.MAGENTA}{Style.BRIGHT}{num_uhd_movie_files:,} 4K Movies{Style.RESET_ALL} ({size_TB_uhd_movies:,} TB)\n{Fore.GREEN}{Style.BRIGHT}{num_shows:,} TV Shows{Style.RESET_ALL} ({num_show_files:,} TV Show Episodes, {size_TB_shows:,} TB)\n{Fore.RED}{Style.BRIGHT}{num_anime:,} Anime Shows{Style.RESET_ALL} ({num_anime_files:,} Anime Episodes, {size_TB_anime:,} TB)\n{Fore.CYAN}{Style.BRIGHT}{num_book_files:,} Books{Style.RESET_ALL} ({size_GB_books:,} GB)\n{Fore.LIGHTGREEN_EX}{Style.BRIGHT}{num_course_files:,} Course Videos{Style.RESET_ALL} ({size_GB_courses:,} GB)')
    print(f'\n{"#"*10}\n')

def get_video_media_info(filepath):
    import ffmpeg, os, sys
    RESET = "\033[0m"
    RED = "\033[31m"
    src_directory = os.path.dirname(os.path.abspath(__file__))
    filepath_ffprobe = os.path.join(src_directory,'bin','ffprobe.exe')

    from utilities import get_file_size
    if not os.path.exists(filepath): raise FileNotFoundError(f"The file at {filepath} does not exist or is not accessible.")
    try:
        probe = ffmpeg.probe(filepath,cmd=filepath_ffprobe)
    except:
        print(f'{RED}Error reading media info:{RESET} {filepath}')
        media_info = {
        'filepath' : filepath,
        'file_size_GB': '',
        'video_codec': '',
        'video_bitrate_Mbps': '',
        'video_minutes': '',
        'video_height': '',
        'video_width': '',
        'audio_codec': '',
        'audio_num_tracks': '',
        'audio_num_channels': '',
        'audio_channel_layout': '',
        }
        return media_info
    
    # File size
    file_size_GB = get_file_size(filepath)
    
    # Video stream information
    video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
    if video_stream:
        video_codec = video_stream['codec_name']
        video_bitrate = video_stream.get('bit_rate', 'N/A')
        try:
            video_bitrate_Mbps = float(video_bitrate)/10**6
        except:
            video_bitrate_Mbps = video_bitrate
        video_minutes = float(video_stream['duration']) / 60 if 'duration' in video_stream else 'N/A'
        video_height = video_stream['height']
        video_width = video_stream['width']
    else:
        video_codec = video_bitrate = video_minutes = video_height = video_width = 'N/A'
    
    # Audio stream information
    audio_streams = [stream for stream in probe['streams'] if stream['codec_type'] == 'audio']
    audio_num_tracks = len(audio_streams)
    
    # Assuming the first audio track to get audio properties
    if audio_num_tracks > 0:
        audio_codec = audio_streams[0]['codec_name']
        audio_num_channels = audio_streams[0]['channels']
        audio_channel_layout = audio_streams[0].get('channel_layout', 'N/A')
    else:
        audio_codec = audio_num_channels = audio_channel_layout = 'N/A'
    media_info = {
        'filepath' : filepath,
        'file_size_GB': file_size_GB,
        'video_codec': video_codec.upper() if type(video_codec) is str else video_codec,
        'video_bitrate_Mbps': video_bitrate_Mbps,
        'video_minutes': video_minutes,
        'video_height': video_height,
        'video_width': video_width,
        'audio_codec': audio_codec.upper() if type(audio_codec) is str else audio_codec,
        'audio_num_tracks': audio_num_tracks,
        'audio_num_channels': audio_num_channels,
        'audio_channel_layout': audio_channel_layout,
    }
    return media_info

def update_media_file_data(drive_config,filepath_backup_surface_area,overwrite_media_data=False):
    import json, os
    from utilities import get_drive_name, get_drive_letter, read_alexandria, read_alexandria_config, read_json, get_file_size
    RESET = "\033[0m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    try:
        backup_surface_area_current = read_json(filepath_backup_surface_area)
    except FileNotFoundError:
        backup_surface_area_current = {}
    # read Alexandria Config
    extensions_dict = read_alexandria_config(drive_config)[2]
    movie_drives_primary = drive_config['Movies']['primary_drives']
    movie_drives_backup = drive_config['Movies']['backup_drives']
    uhd_movie_drives_primary = drive_config['4K Movies']['primary_drives']
    uhd_movie_drives_backup = drive_config['4K Movies']['backup_drives']
    anime_movie_drives_primary = drive_config['Anime Movies']['primary_drives']
    anime_movie_drives_backup = drive_config['Anime Movies']['backup_drives']
    anime_drives_primary = drive_config['Anime']['primary_drives']
    anime_drives_backup = drive_config['Anime']['backup_drives']
    show_drives_primary = drive_config['Shows']['primary_drives']
    show_drives_backup = drive_config['Shows']['backup_drives']
    # book_drives_primary = drive_config['Books']['primary_drives']
    # book_drives_backup = drive_config['Books']['backup_drives']
    # music_drives_primary = drive_config['Music']['primary_drives']
    # music_drives_backup = drive_config['Music']['backup_drives']
    # course_drives_primary = drive_config['Courses']['primary_drives']
    # course_drives_backup = drive_config['Courses']['backup_drives']  

    backup_areas = (
        ("Shows",show_drives_primary,show_drives_backup),
        ("Anime",anime_drives_primary,anime_drives_backup),
        ("Movies",movie_drives_primary,movie_drives_backup),
        ("Anime Movies",anime_movie_drives_primary,anime_movie_drives_backup),
        ("4K Movies",uhd_movie_drives_primary,uhd_movie_drives_backup)
    )
    backup_surface_area = {}
    for media_type,primary_drives,backup_drives in backup_areas:
        directories_primary = [f'{get_drive_letter(drive_name)}:/{media_type}/' for drive_name in primary_drives]
        filepaths_primary = read_alexandria(directories_primary,extensions_dict[media_type])
        directories_backup = [f'{get_drive_letter(drive_name)}:/{media_type}/' for drive_name in backup_drives]
        filepaths_backup = read_alexandria(directories_backup,extensions_dict[media_type])
        filepaths = filepaths_primary + filepaths_backup
        for idx,filepath in enumerate(filepaths):
            filepath_noLetter = filepath[1:]
            title = os.path.splitext(os.path.basename(filepath))[0]
            if title in backup_surface_area:
                print(f'{YELLOW}Backup copy:{RESET} {title}')
                backup_surface_area[title]["Number of Copies"] += 1
                backup_surface_area[title]["Drives (Letter)"].append(filepath[0]) 
                backup_surface_area[title]["Drives (Name)"].append(get_drive_name(filepath[0]))
            else:
                if overwrite_media_data or title not in backup_surface_area_current.keys():
                    print(f'{GREEN}Fetching medio info:{RESET} {title}')
                    media_info = get_video_media_info(filepath)
                    backup_surface_area.update(
                        {
                            title: {
                                "Number of Copies":1,
                                "Size (GB)": get_file_size(filepath),
                                "Media Type": media_type,
                                "Drives (Letter)": [filepath[0]],
                                "Drives (Name)": [get_drive_name(filepath[0])],
                                "Filepath_noLetter": filepath_noLetter,
                                "Extension": filepath_noLetter.split('.')[-1],
                                "Video Codec": media_info['video_codec'],
                                "Audio Codec": media_info['audio_codec'],
                                "Length (min.)": media_info['video_minutes'],
                                "Bitrate (Mbps)": media_info['video_bitrate_Mbps'],
                                "Video Height": media_info['video_height'],
                                "Video Width": media_info['video_width'],
                                "Audio Tracks": media_info['audio_num_tracks'],
                                "Audio Channels": media_info['audio_num_channels'],
                                "Audio Channel Layout": media_info['audio_channel_layout']
                            }
                        }
                    )
                else:
                    print(f'{GREEN}Medio info already exisits:{RESET} {title}')
                    entry = backup_surface_area_current[title]
                    entry['Number of Copies'] = 1
                    entry['Size (GB)'] = get_file_size(filepath)
                    entry['Drives (Letter)'] = [filepath[0]]
                    entry['Drives (Name)'] = [get_drive_name(filepath[0])]
                    backup_surface_area[title] = entry
    with open(filepath_backup_surface_area, 'w') as json_file:
        json.dump(backup_surface_area, json_file, indent=4)

def read_media_file_data(filepath_alexandria_media_details,bool_update=False,bool_print=True):
    pass

def read_media_statistics(filepath_statistics,bool_update=False,bool_print=True):
    from utilities import read_json
    from colorama import Fore, Style, init
    init(autoreset=True)
    if bool_update: update_server_statistics(filepath_statistics)
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
    # movie_titles_with_year = update_movie_list(primary_drive_letter_dict)
    # api_handler.tmdb_movies_fetch()
    # update_server_statistics(drive_config,filepath_statistics)
    # update_media_file_data(drive_config,filepath_alexandria_media_details)
    # movies_suggested = suggest_movie_downloads()
    read_media_statistics(filepath_statistics)

if __name__ == '__main__':
    main()
