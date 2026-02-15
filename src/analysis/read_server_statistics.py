#!/usr/bin/env python

import os
import sys

from datetime import datetime
from colorama import Fore, Style, init

init(autoreset=True)

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from utilities import read_json


def read_media_statistics(bool_update=False,
                          bool_print=True
                          ) -> dict:
    """Read and optionally update the media statistics for Alexandria Media Server."""
 
    src_directory = os.path.dirname(os.path.abspath(__file__))

    directory_output = os.path.join(src_directory, "..", "..", "output")
    filepath_statistics = os.path.join(directory_output, "alexandria_media_statistics.json")
    
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
    duration_shows = ",".join(data["TV Shows"]["Total Duration"].split(",")[:-1])
    duration_anime = ",".join(data["Anime"]["Total Duration"].split(",")[:-1])
    duration_bluray_movies = ",".join(data["Movies"]["Total Duration"].split(",")[:-1])
    duration_anime_movies = ",".join(data["Anime Movies"]["Total Duration"].split(",")[:-1])
    duration_4k_movies = ",".join(data["4K Movies"]["Total Duration"].split(",")[:-1])
    duration_course_videos = ",".join(data["Courses"]["Total Duration"].split(",")[:-1])
    duration_music = ",".join(data["Music"]["Total Duration"].split(",")[:-1])

    if bool_print:
        print(f'\n{"#"*10}\n')
        print(f"Media Statistics (CAO {datetime.fromtimestamp(os.stat(filepath_statistics).st_mtime).strftime('%Y-%m-%d')})\n")
        print(f"{Fore.YELLOW}{Style.BRIGHT}Shows: {Style.NORMAL}{num_shows:,} shows, {num_show_episodes:,} episodes | {size_shows} | {duration_shows}")
        print(f"{Fore.CYAN}{Style.BRIGHT}Anime: {Style.NORMAL}{num_anime:,} series, {num_anime_episodes:,} episodes | {size_anime} | {duration_anime}")
        print(f"{Fore.MAGENTA}{Style.BRIGHT}BluRay Movies: {Style.NORMAL}{num_bluray_movies:,} | {size_movies} | {duration_bluray_movies}")
        print(f"{Fore.MAGENTA}{Style.BRIGHT}Anime Movies: {Style.NORMAL}{num_anime_movies:,} | {size_anime_movies} | {duration_anime_movies}")
        print(f"{Fore.MAGENTA}{Style.BRIGHT}4K Movies: {Style.NORMAL}{num_4k_movies:,} | {size_4k_movies} | {duration_4k_movies}")
        print(f"{Fore.GREEN}{Style.BRIGHT}Books: {Style.NORMAL}{num_books:,} books | {size_books}")
        print(f"{Fore.BLUE}{Style.BRIGHT}Music: {Style.NORMAL}{num_songs:,} songs | {size_music} | {duration_music}")
        print(f"{Fore.RED}{Style.BRIGHT}Courses: {Style.NORMAL}{num_course_videos:,} course videos | {size_courses} | {duration_course_videos}")
        print(f'\n{"#"*10}\n')
    
    return data

if __name__ == "__main__":
    read_media_statistics(bool_update=False, bool_print=True)