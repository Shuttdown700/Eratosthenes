#!/usr/bin/env python

def update_movie_list(primary_drive_letter_dict : dict) -> list:
    # import utility methods
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
    from utilities import read_csv, read_file_as_list, write_list_to_txt_file
    from api import API
    api_handler = API()
    src_directory = os.path.dirname(os.path.abspath(__file__))
    filepath_movie_list = ("\\".join(src_directory.split('\\')[:-1])+"/output/").replace('\\','/')+'movie_list.txt'
    list_movies = read_file_as_list(filepath_movie_list)
    list_movies = [x.lower() for x in list_movies]
    data_top_rated = read_csv(api_handler.filepath_tmdb_top_rated_csv)
    list_top_rated_movies = [f"{movie['Title_TMDb'].replace(': ',' - ')} ({movie['Release_Year']})" for movie in data_top_rated]
    movies_suggested = []
    for movie in list_top_rated_movies:
        if movie.lower() not in list_movies:
            movies_suggested.append(movie)
    output_filepath = ("\\".join(src_directory.split('\\')[:-1])+"/output/").replace('\\','/')+'movies_suggested.txt'
    write_list_to_txt_file(output_filepath,movies_suggested)
    return movies_suggested

def update_movie_data():
    pass

def update_show_data():
    pass

if __name__ == '__main__':
    import os
    from utilities import get_drive_letter, read_alexandria_config, read_json
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

    

    # movie_titles_with_year = update_movie_list(primary_drive_letter_dict)
    # movies_suggested = suggest_movie_downloads()
    # update_movie_data()
    # update_show_data()
