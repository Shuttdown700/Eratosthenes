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

def update_show_list():
    pass

def update_movie_file_metadata():
    movie_drives_primary = drive_config['Movies']['primary_drives']
    uhd_movie_drives_primar = drive_config['4K Movies']['primary_drives']
    anime_movie_drives_primary = drive_config['Anime Movies']['primary_drives']

def update_show_file_metadata():
    pass

def update_all_statistics(drive_config):
    import os, shutil
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
    filepaths_anime = []; filepaths_books = []; filepaths_games = []; filepaths_youtube = []; filepaths_photos = []
    for i,f in enumerate(primary_filepaths):
        if ':/Movies/' in f: filepaths_movies.append(f)
        elif ':/Anime Movies/' in f: filepaths_anime_movies.append(f)
        elif ':/4K Movies/' in f: filepaths_uhd_movies.append(f)
        elif ':/Shows' in f: filepaths_tv_shows.append(f)
        elif ':/Anime' in f: filepaths_anime.append(f)
        elif ':/Books/' in f: filepaths_books.append(f)
        elif ':/Games/' in f: filepaths_games.append(f)
        elif ':/Music/' in f: filepaths_youtube.append(f)
        elif ':/Photos/' in f: filepaths_photos.append(f)
    
    # need to save statistics to json file

    num_show_files = len(tv_shows)
    num_shows = len(list(set(([f.split('/')[2].strip() for f in tv_shows]))))
    size_shows = round(sum([get_file_size(show) for show in tv_shows])/10**3,2)
    num_anime_files = len(anime)
    num_animes = len(list(set(([f.split('/')[2].strip() for f in anime]))))
    size_animes = round(sum([get_file_size(anime) for anime in anime])/10**3,2)
    num_movie_files = len(movies)
    size_movies = round(sum([get_file_size(movie) for movie in movies])/10**3,2)
    num_4k_movie_files = len(uhd_movies)
    size_4k_movies = round(sum([get_file_size(movie) for movie in uhd_movies])/10**3,2)
    num_book_files = len(books)
    size_books = round(sum([get_file_size(book) for book in books])/10**3,2)
    num_total_files = num_show_files + num_anime_files + num_movie_files + num_4k_movie_files + num_book_files
    total_size = size_shows + size_animes + size_movies + size_4k_movies + size_books
    print(f'{Fore.YELLOW}{Style.BRIGHT}Server Stats:{Style.RESET_ALL}')
    print(f'Total Available Server Storage: {total_available_space:,.2f} TB\nUsed Server Storage: {used_space:,.2f} TB\nFree Server Storage: {unused_space:,.2f} TB')
    print(f'\n{Fore.YELLOW}{Style.BRIGHT}Database Stats:{Style.RESET_ALL}')
    print(f'{num_total_files:,} Total Media Files ({total_size:,.2f} TB)\n{num_movie_files:,} HD Movies ({size_movies:,} TB)\n{num_4k_movie_files:,} 4K Movies ({size_4k_movies:,} TB)\n{num_shows:,} TV Shows ({num_show_files:,} TV Show Episodes, {size_shows:,} TB)\n{num_animes:,} Anime Shows ({num_anime_files:,} Anime Episodes, {size_animes:,} TB)\n{num_book_files:,} Books ({num_book_files:,} Books, {size_books*1000:,} GB)')
    

def update_figures():
    pass

def assess_backup_surface_area():
    pass

if __name__ == '__main__':
    import os
    from utilities import get_drive_letter, get_file_size, read_alexandria, read_alexandria_config, read_json
    from api import API
    from colorama import Fore, Back, Style
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
    # api_handler = API()
    # update_movie_list(primary_drive_letter_dict)
    # api_handler.tmdb_movies_fetch()
    update_all_statistics(drive_config)

    # movie_titles_with_year = update_movie_list(primary_drive_letter_dict)
    # movies_suggested = suggest_movie_downloads()
    
    # update_show_data()
