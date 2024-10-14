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

def update_statistics(drive_config,filepath_statistics):
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
    dict_uhd_movie_stats = {"Number of 4K Movies":num_uhd_movies,"Total Size":f"{size_TB_uhd_movies:,.2f} GB","4K Movie Titles":uhd_movie_titles,"Primary Filepaths":filepaths_uhd_movies}
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

def assess_backup_surface_area_wip(drive_config):
    from utilities import does_drive_exist, get_drive_name
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
    """
    read all filepaths, count (no Letter) paths, save results, print results
    """

def analyze_metadata_wip():
    import pandas as pd
    import collections, math
    import numpy as np
    import matplotlib.pyplot as plt
    from matplotlib.ticker import PercentFormatter 
    print('\n')
    movie_df = pd.read_csv('G:/movie_metadata.csv')
    movie_days = round(sum(movie_df['Duration (min)'].dropna())/60/24,2)
    total_size = round(sum(movie_df['File Size (GB)'].dropna())/1000,2)
    print(f'Cumulative length of Movies: {movie_days} days')
    print(f'Total Size of Movies: {total_size} TB')
    movie_percent_hevc = list(movie_df['Video Codec']).count('HEVC')/len(movie_df['Video Codec'])*100
    print(f'Percent of Movies with HEVC (H.265) encoding: {movie_percent_hevc:.2f}%')
    movie_percent_surround = list(movie_df['Audio Channels']).count(6)/len(movie_df['Channel Layout'])*100
    print(f'Percent of Movies with Surround Sound: {movie_percent_surround:.2f}%')
    c_movies = collections.Counter(list(movie_df['Year']))
    c2_movies = sorted(c_movies.items(), key=lambda x: x[0], reverse=False)
    years_movies = [x[0] for x in c2_movies]
    quantity_movies = [x[1] for x in c2_movies]
    plt.figure()
    plt.bar(years_movies,quantity_movies)
    plt.title(f'Quantity of Movies by Year ({len(movie_df):,} Movies)')
    plt.ylabel('Quantity')
    plt.xlabel('Year')
    plt.show()
    length_in_hours = [round(x/60,2) for x in list(movie_df['Duration (min)'])]
    plt.figure()
    plt.hist(length_in_hours, weights=np.ones(len(length_in_hours)) / len(length_in_hours), bins=50)
    plt.gca().yaxis.set_major_formatter(PercentFormatter(1))
    plt.title(f'Movie Durations ({len(movie_df):,} Movies)')
    plt.ylabel('Frequency (%)')
    plt.xlabel('Hours')
    plt.show()
    ###
    print('\n###\n')
    show_df = pd.read_csv('R:/tv_metadata.csv')
    show_days = round(sum(show_df['Duration (min)'].dropna())/60/24,2)
    total_size = round(sum(show_df['File Size (GB)'].dropna())/1000,2)
    print(f'Cumulative length of Shows: {show_days} days')
    print(f'Total Size of Shows: {total_size} TB')
    show_percent_hevc = list(show_df['Video Codec']).count('HEVC')/len(show_df['Video Codec'])*100
    print(f'Percent of Shows with HEVC (H.265) encoding: {show_percent_hevc:.2f}%')
    show_percent_surround = list(show_df['Audio Channels']).count(6)/len(show_df['Channel Layout'])*100
    print(f'Percent of Shows with Surround Sound: {show_percent_surround:.2f}%')    
    # c_shows = collections.Counter(list(show_df['Year']))
    # c2_shows = sorted(c_shows.items(), key=lambda x: x[0], reverse=False)
    # years_shows = [x[0] for x in c2_shows]
    # quantity_shows = [x[1] for x in c2_shows]
    # plt.figure()
    # plt.bar(years_shows,quantity_shows)
    # plt.title('Quantity of Show Episodes by Year')
    # plt.ylabel('Quantity of Episodes')
    # plt.xlabel('Year')
    # plt.show()
    length_in_mins_shows = sorted([round(x,2) for x in list(show_df['Duration (min)']) if not math.isnan(x)])[:int(-0.051*len(show_df))]
    plt.figure()
    plt.hist(length_in_mins_shows, weights=np.ones(len(length_in_mins_shows)) / len(length_in_mins_shows), bins=100)
    plt.gca().yaxis.set_major_formatter(PercentFormatter(1))
    plt.title(f'TV Show Durations ({len(show_df):,} Show Episodes)')
    plt.ylabel('Frequency (%)')
    plt.xlabel('Minutes')
    plt.show()
    ###
    print('\n###\n')
    anime_df = pd.read_csv('E:/anime_metadata.csv')
    anime_days = round(sum(anime_df['Duration (min)'].dropna())/60/24,2)
    total_size = round(sum(anime_df['File Size (GB)'].dropna())/1000,2)
    print(f'Cumulative length of Anime: {anime_days} days')
    print(f'Total Size of Anime: {total_size} TB')
    anime_percent_hevc = list(anime_df['Video Codec']).count('HEVC')/len(anime_df['Video Codec'])*100
    print(f'Percent of Anime with HEVC (H.265) encoding: {anime_percent_hevc:.2f}%')
    anime_percent_surround = list(anime_df['Audio Channels']).count(6)/len(anime_df['Channel Layout'])*100
    print(f'Percent of Anime with Surround Sound: {anime_percent_surround:.2f}%')
    anime_multi_audio = (len(anime_df['Number of Audio Tracks'])-list(anime_df['Number of Audio Tracks']).count(1))/len(anime_df['Number of Audio Tracks'])*100
    print(f'Percent of Anime with Multiple Audio Tracks: {anime_multi_audio:.2f}%')  
    # c_anime = collections.Counter(list(anime_df['Year']))
    # c2_anime = sorted(c_anime.items(), key=lambda x: x[0], reverse=False)
    # years_anime = [x[0] for x in c2_anime]
    # quantity_anime = [x[1] for x in c2_anime]
    # plt.figure()
    # plt.bar(years_anime,quantity_anime)
    # plt.title('Quantity of Anime Episodes by Year')
    # plt.ylabel('Quantity of Episodes')
    # plt.xlabel('Year')
    # plt.show()
    length_in_hours_anime = sorted([round(x/60,2) for x in list(anime_df['Duration (min)'])  if not math.isnan(x)])[:int(-0.005*len(show_df))]
    plt.figure()
    plt.hist(length_in_hours_anime, weights=np.ones(len(length_in_hours_anime)) / len(length_in_hours_anime), bins=100)
    plt.gca().yaxis.set_major_formatter(PercentFormatter(1))
    plt.title(f'Anime Durations ({len(anime_df):,} Anime Episodes)')
    plt.ylabel('Frequency (%)')
    plt.xlabel('Hours')
    plt.show()
    ###
    with open(r'G:/bluray_price_tracker.txt', mode = 'r', encoding='utf-8') as movie_tracker:
        movie_tracker_data = movie_tracker.readlines()
    video_ratings = []
    audio_ratings = []
    for mtd in movie_tracker_data:
        video_val = mtd.split(',')[-3]
        audio_val = mtd.split(',')[-2]
        if len(video_val) > 0 and float(video_val) > 0:
            video_ratings.append(float(video_val))
        if len(audio_val) > 0 and float(video_val) > 0:
            audio_ratings.append(float(audio_val))
    plt.figure()
    plt.hist(video_ratings, weights=np.ones(len(video_ratings)) / len(video_ratings), bins=30)
    plt.gca().yaxis.set_major_formatter(PercentFormatter(1))
    plt.title(f'Movie Video Quality ({len(movie_tracker_data):,} Movies)')
    plt.ylabel('Frequency (%)')
    plt.xlabel('Quality (out of 5)')
    plt.xticks(np.arange(0, 5, step=0.5))
    plt.show()
    plt.figure()
    plt.hist(audio_ratings, weights=np.ones(len(audio_ratings)) / len(audio_ratings), bins=30)
    plt.gca().yaxis.set_major_formatter(PercentFormatter(1))
    plt.title(f'Movie Audio Quality ({len(movie_tracker_data):,} Movies)')
    plt.ylabel('Frequency (%)')
    plt.xlabel('Quality (out of 5)')
    plt.show()
    min_total_price = 0
    max_total_price = 0
    no_data_movies = 0
    for mtd in movie_tracker_data:
        prices = []
        for index in [-5,-6,-7]:
            p = mtd.split(',')[index]
            if p != '':
                prices.append(float(p.split('$')[-1]))
        if len(prices) > 0:
            min_total_price += min(prices)
            max_total_price += max(prices)
        else:
            no_data_movies += 1
    print(f'\nEstimated (pre-tax, pre-S&H) value of {len(movie_tracker_data):,} bluRay movies: between ${min_total_price:,.2f} & ${max_total_price:,.2f} (with {no_data_movies:,} no-data movies)')
    ###
    with open(r'G:/4K_bluray_price_tracker.txt', mode = 'r', encoding='utf-8') as movie_tracker:
        movie_tracker_data = movie_tracker.readlines()
    video_ratings = []
    audio_ratings = []
    for mtd in movie_tracker_data:
        video_val = mtd.split(',')[-3]
        audio_val = mtd.split(',')[-2]
        if len(video_val) > 0 and float(video_val) > 0:
            video_ratings.append(float(video_val))
        if len(audio_val) > 0 and float(video_val) > 0:
            audio_ratings.append(float(audio_val))
    plt.figure()
    plt.hist(video_ratings, weights=np.ones(len(video_ratings)) / len(video_ratings), bins=30)
    plt.gca().yaxis.set_major_formatter(PercentFormatter(1))
    plt.title(f'Movie Video Quality ({len(movie_tracker_data):,} Movies)')
    plt.ylabel('Frequency (%)')
    plt.xlabel('Quality (out of 5)')
    plt.xticks(np.arange(0, 5, step=0.5))
    plt.show()
    plt.figure()
    plt.hist(audio_ratings, weights=np.ones(len(audio_ratings)) / len(audio_ratings), bins=30)
    plt.gca().yaxis.set_major_formatter(PercentFormatter(1))
    plt.title(f'Movie Audio Quality ({len(movie_tracker_data):,} Movies)')
    plt.ylabel('Frequency (%)')
    plt.xlabel('Quality (out of 5)')
    plt.show()
    min_total_price = 0
    max_total_price = 0
    no_data_movies = 0
    for mtd in movie_tracker_data:
        prices = []
        for index in [-5,-6,-7]:
            p = mtd.split(',')[index]
            if p != '':
                prices.append(float(p.split('$')[-1]))
        if len(prices) > 0:
            min_total_price += min(prices)
            max_total_price += max(prices)
        else:
            no_data_movies += 1
    print(f'\nEstimated (pre-tax, pre-S&H) value of {len(movie_tracker_data):,} 4K movies: between ${min_total_price:,.2f} & ${max_total_price:,.2f} (with {no_data_movies:,} no-data movies)')

def video_metadata_wip(path_list=[],extensions_list=[],metadata_file_name=''):
    import ffmpeg, os
    from alive_progress import alive_bar
    import pandas as pd
    from utilities import read_alexandria
    # file_names, file_paths = read_alexandria(path_list,extensions = extensions_list)   
    # file_names, file_paths = read_alexandria(['G:/Movies/','G:/Anime Movies/'],extensions = ['.mkv','.mp4']); metadata_file_name = 'G:/movie_metadata.csv'
    # file_names, file_paths = read_alexandria(['G:/4K Movies/'],extensions = ['.mkv','.mp4']); metadata_file_name = 'G:/4K_metadata.csv'
    # file_names, file_paths = read_alexandria(['R:/Shows/'],extensions = ['.mkv','.mp4']); metadata_file_name = 'R:/tv_metadata.csv'
    file_names, file_paths = read_alexandria(['A:/Anime/'],extensions = ['.mkv','.mp4']); metadata_file_name = 'A:/anime_metadata.csv'
    df_data = []; columns = ['File','Folder','Year','File Size (GB)','Video Codec','Channel Layout','Duration (min)','Bitrate (kbps)','Width','Height','Audio Codec','Audio Channels','Number of Audio Tracks']
    with alive_bar(len(file_names),ctrl_c=False,dual_line=True,title=f'Collecting {file_paths[0].split("/")[1].strip()} Metadata',bar='classic',spinner='classic') as bar:
        for i,fn in enumerate(file_names):
            num_audio_tracks = 0
            filepath = f'{file_paths[i]}/{fn}'
            # ffmpeg executables need to be in src directory
            try:
                details = ffmpeg.probe(filepath)['streams']
            except:
                continue
            folder = file_paths[i].split('/')[1]
            try:
                if '4K' in file_paths[i]:
                    year = float('nan')
                elif 'Movies' in file_paths[i]:
                    year = int(fn.split('(')[-1][:4])
                else:
                    year = int(file_paths[i].split('/')[-2].split('(')[-1][:4])
            except ValueError:
                year = float('nan')
            for c in range(len(details)):
                if details[c]['codec_type'] == 'video' and details[c]['codec_name'].upper() != 'MJPEG':
                    video_codec = details[c]['codec_name'].upper()
                    try:
                        video_bitrate = int(f"{int(details[c]['bit_rate'])/(1*10**3):.0f}")
                        video_minutes = float(f"{float(details[c]['duration'])/60:.2f}") # in minutes
                        file_size = os.path.getsize(f'{file_paths[i]}/{fn}')/(1*10**9)
                    except KeyError:
                        try:
                            video_bitrate = int(details[c]['tags']['BPS'])//1000
                            duration_array = details[c]['tags']['DURATION'].split('.')[0].split(':')
                            video_minutes = int(duration_array[0])*60+int(duration_array[1])+int(duration_array[2])/60 # in minutes
                            file_size = os.path.getsize(f'{file_paths[i]}/{fn}')/(1*10**9)
                        except:
                            video_bitrate = float('nan')
                            video_minutes = float('nan')
                    video_height = details[c]['coded_height']
                    video_width = details[c]['coded_width']
                elif details[c]['codec_type'] == 'audio': # count number of audio tracks
                    if num_audio_tracks > 0:
                        pass
                    else:
                        audio_codec = details[c]['codec_name'].upper()
                        num_channels = details[c]['channels']
                        channel_layout = details[c]['channel_layout'].upper()
                        if video_bitrate == 'nan':
                            video_minutes = float(f"{float(details[c]['duration'])/60:.2f}") # in minutes
                            video_bitrate = file_size*(1*10**9)*8/(video_minutes*60)/1000
                    num_audio_tracks += 1
            df_data.append([fn,folder,year,round(file_size,2),video_codec,channel_layout,video_minutes,video_bitrate,video_width,video_height,audio_codec,num_channels,num_audio_tracks])
            bar()
        df = pd.DataFrame(df_data,columns=columns).set_index('File',drop=True)
        df.to_csv(metadata_file_name)
        src_directory = os.path.realpath(os.path.dirname(os.path.abspath("__file__")))
        output_directory = "\\".join(src_directory.split('\\')[:-1])+"\\output"
        df.to_csv(rf'{output_directory}\{metadata_file_name.split("/")[-1]}')
        return df

def main():
    import os
    from utilities import get_drive_letter, get_file_size, read_alexandria, read_alexandria_config, read_json
    from api import API
    # define paths
    src_directory = os.path.dirname(os.path.abspath(__file__))
    drive_hieracrchy_filepath = (src_directory+"/config/alexandria_drives.config").replace('\\','/')
    output_directory = ("\\".join(src_directory.split('\\')[:-1])+"/output").replace('\\','/')
    filepath_statistics = os.path.join(output_directory,"alexandria_media_statistics.json").replace('\\','/')
    drive_config = read_json(drive_hieracrchy_filepath)
    # define primary & backup drives
    primary_drives_dict, backup_drives_dict, extensions_dict = read_alexandria_config(drive_config)
    primary_drive_letter_dict = {}; backup_drive_letter_dict = {}
    for key,value in primary_drives_dict.items(): primary_drive_letter_dict[key] = [get_drive_letter(x) for x in value]
    for key,value in backup_drives_dict.items(): backup_drive_letter_dict[key] = [get_drive_letter(x) for x in value]
    # api_handler = API()
    # update_movie_list(primary_drive_letter_dict)
    # api_handler.tmdb_movies_fetch()
    update_statistics(drive_config,filepath_statistics)

    # movie_titles_with_year = update_movie_list(primary_drive_letter_dict)
    # movies_suggested = suggest_movie_downloads()
    
    # update_show_data()

if __name__ == '__main__':
    main()
