#!/usr/bin/env python3

libraries = [['alive_progress',['alive_bar']],['colorama',['Fore','Style']],
             ['glob'],['os'],['pandas'],['shutil'],['sys'],['subprocess'],
             ['time'],['win32api'],['matplotlib.pyplot']]

import_libraries(libraries)
import alive_progress
import colorama
import os
import pandas as pd
import shutil
import sys
import subprocess
import time
import win32api

from alive_progress import alive_bar
from colorama import Fore, Style, Back
# from alexandria_utilities import get_shows_not_on_drive

def get_show_files(show):
    file_names, file_paths = read_alexandria([show_dir,anime_dir])
    show_files_with_path1 = [file_paths[i]+'/'+file_names[i] for i in range(len(file_paths)) if 'Movies' not in file_paths[i]]
    show_files_with_path2 = [sfwp for sfwp in show_files_with_path1 if show == sfwp.split('/')[2].split('(')[0].strip()]
    return show_files_with_path2

def get_show_size(show_files_with_path):
    if isinstance(show_files_with_path, str): show_files_with_path = get_show_files(show_files_with_path)
    show_size = 0
    for sfwp in show_files_with_path: show_size += get_file_size(sfwp)  
    return round(show_size,2)

def get_shows_list(drive):
    all_titles, all_paths = read_alexandria([f'{drive}:\\Shows\\',f'{drive}:\\Anime\\'])
    return sorted(list(set([' '.join(at.split()[:-1]) for at in all_titles])))

def write_all_shows_to_whitelist(primary_drive,target_drive):
    target_drive_name = get_drive_name(target_drive)
    file_names, file_paths = read_alexandria([f'{target_drive}:/Shows/',f'{target_drive}:/Anime/'])
    shows = list(set([' '.join(f.strip().split()[:-1]) for i,f in enumerate(file_names) if file_paths[i] != f'{primary_drive}:/Movies']))
    # shows = sorted([' '.join(s.split()[:-1]) for s in shows])
    with open(f'{os.path.dirname(__file__)}\\Show Lists\\{"_".join(target_drive_name.split())}_whitelist.txt',mode='r',encoding='utf-8') as whitelist:
        wl = list(set([w.strip() for w in whitelist.readlines()]))
    shows = sorted(list(set(shows + wl)))
    with open(f'{os.path.dirname(__file__)}\\Show Lists\\{"_".join(target_drive_name.split())}_whitelist.txt',mode='w',encoding='utf-8') as whitelist:
        whitelist.seek(0)
        for s in shows:
            whitelist.write(s+'\n')

### BACKUP FUNCTIONS ###

def read_whitelist(drive_name):
    os.chdir(rf'{os.path.dirname(__file__)}\Show Lists')
    whitelist_file_name = '_'.join(drive_name.split())+'_whitelist.txt'
    with open (whitelist_file_name,mode='r',encoding='utf-8') as file:
        return [w.strip() for w in file.readlines()]
     
### ANALYTICS FUNCTIONS ###

def write_show_catalog():
    shows_only_paths = list(set([p.split('/')[-2] for p in primary_paths if 'Shows' in p]))
    year_sorted = sorted(shows_only_paths,key = lambda x: (x.split()[-1],' '.join(x.split()[:-1])),reverse=(True))
    with open(rf'{os.path.dirname(__file__)}\year_sorted_shows.txt', mode='w',encoding='utf-8') as file:
        file.seek(0)
        for p in year_sorted:
            file.write(p+'\n')

def find_duplicates_and_show_data():
    write_show_catalog()
    print('\nSearching for duplicate files...')
    are_there_duplicates = False
    cleared_duplciates = ['Shaun the Sheep S03E10','Shaun the Sheep S05E07',
                          'Naruto S05E39','Dragon Ball Super S05E35']
    duplicates = []
    file_names_with_path = [primary_paths[i]+'/'+primary_titles[i] for i in range(len(primary_paths)) if 'Music' not in primary_paths[i] and 'Movie' not in primary_paths[i]]
    show_files = {}
    show_sizes = {}
    for fnwp in file_names_with_path:
        file_path_list = []
        show_name = ' '.join(fnwp.split('/')[2].split()[:-1]).strip()
        for fnwp2 in file_names_with_path:
            if show_name+' (' and show_name+' S' in fnwp2:
                file_path_list.append(fnwp2)
        show_files.update({show_name:file_path_list})
    shows = list(show_files.keys())
    os.chdir(rf'{os.path.dirname(__file__)}')
    with open('show_menu.txt', mode = 'w', encoding = 'utf-8') as menu_file:
        for s in shows:
            total_size_in_gb = 0
            episode_sizes = []
            show_episode_files = show_files[s]
            if len(show_episode_files) == 0: continue
            show_seasons = []
            for sef in show_episode_files:
                size_in_gb = get_file_size(sef)
                episode_sizes.append(size_in_gb)
                total_size_in_gb += size_in_gb
                show_seasons.append(f'{sef.split("/")[3].strip()}')
            show_seasons = list(set(show_seasons))
            year = show_episode_files[0].split('/')[2].split()[-1][1:-1]
            menu_file.write(f'{s}, {year}, {len(show_seasons)} {"Seasons" if len(show_seasons) != 1 else "Season"}, {len(show_episode_files)} Episodes, {total_size_in_gb:,.2f} GB\n')
            for i, es in enumerate(episode_sizes):
                 if episode_sizes.count(es) > 1:
                    ep_file = '.'.join(show_episode_files[i].split("/")[-1].split(".")[:-1])
                    if ep_file not in cleared_duplciates:
                        print(f'{Fore.RED}{Style.BRIGHT}Match{Style.RESET_ALL}: {ep_file} is {es} GB')
                        are_there_duplicates = True
                        duplicates.append(ep_file)
            show_sizes.update({s:total_size_in_gb})
    show_sizes = dict(sorted(show_sizes.items(), key=lambda item: (item[1],item[0]),reverse=True))
    os.chdir(rf'{os.path.dirname(__file__)}')
    with open('show_sizes.txt', mode = 'w', encoding = 'utf-8') as size_file:
        size_file.seek(0)
        for s in list(show_sizes.keys()):
            percent = round(show_sizes[s]/sum(list(show_sizes.values()))*100,2)
            size_file.write(f'{s}: {round(show_sizes[s],2)} GB ({percent}%)\n')
    if not are_there_duplicates:
        print(f'\n{Back.GREEN}No Duplicates found.{Style.RESET_ALL}')
        return None
    else:
        print(f'\n{Back.RED}Duplicates found{Style.RESET_ALL}')
        with open('duplicate_shows.txt', mode = 'w', encoding = 'utf-8') as duplicates_file:
            duplicates_file.seek(0)
            for d in duplicates:
                # print(d)
                duplicates_file.write(d+'\n')
        return duplicates

def check_backup_surface_area(drives):
    connected_drives = []
    mp4_tracker = {}; show_tracker = {}
    for d in drives:
        if not does_drive_exist(d): continue
        connected_drives.append(d)
        file_names, file_paths = read_alexandria([f'{d}:/Movies/',f'{d}:/Shows/',f'{d}:/Anime/',f'{d}:/Anime Movies/',f'{d}:/4K Movies',f'{d}:/Music',f'{d}:/Books'])
        files = [[file_paths[i][3:]+'/'+file_names[i],file_paths[i][0]] for i in range(len(file_names))]
        for f in files:
            try:
                mp4_tracker[f[0]][0] += 1
                mp4_tracker[f[0]][1].append(f[1])
            except KeyError:
                mp4_tracker.update({f[0]:[1,[f[1]]]})
    connected_drives = sorted(connected_drives,key=lambda x: get_drive_name(x))
    one_count_list = []; two_count_list = []; threePlus_count_list = []
    mp4_keys = list(mp4_tracker.keys())
    for m in mp4_keys:
        count = mp4_tracker[m][0]
        drive_list = ', '.join(mp4_tracker[m][1]).strip()
        if m not in list(show_tracker.keys()) and 'Movies' not in m: show_tracker.update({' '.join(m.split('/')[1].split()[:-1]):(count,drive_list)})
        media_type = m.split('/')[0].strip()
        if 'Anime' in media_type and 'Movie' in media_type:
            parent_drive = anime_movie_dir[0]
        elif 'Anime' in media_type:
            parent_drive = anime_dir[0]
        elif 'Shows' in media_type:
            parent_drive = show_dir[0]    
        elif '4K' in media_type:
            parent_drive = uhd_movie_dir[0]
        elif 'Books' in media_type:
            parent_drive = book_dir[0]  
        elif 'Music' in media_type:
            parent_drive = music_dir[0]           
        elif 'Movie' in media_type: 
            parent_drive = movie_dir[0]
        else:
            continue
        if count == 1:
            one_count_list.append(f'{parent_drive}:/{m}')
        elif count == 2:
            two_count_list.append(f'{parent_drive}:/{m}')
        elif count >= 3:
            threePlus_count_list.append(f'{parent_drive}:/{m}')
    with open('not_backed_up_files.txt',mode='w',encoding='utf-8') as file:
        file.seek(0)
        ocls = []
        refined_show_list = list(set([' '.join(o.split('/')[-1].split()[:-1]) for o in one_count_list if 'Movies' not in o.split('/')[1] and 'Books' not in o.split('/')[1] and 'Music' not in o.split('/')[1]]))
        for i,ocl in enumerate(sorted(refined_show_list)):
            if i == 0: print(f'\n{Back.YELLOW}The following shows are not backed up:{Style.RESET_ALL}')
            show_size = get_show_size(get_show_files(ocl))
            ocls.append(ocl)
            file.write(f'{ocl}: {show_size} GB\n')
            print(f'{Style.BRIGHT}{ocl}{Style.RESET_ALL}: {show_size} GB')
    drive_string = ''
    for c in connected_drives:
        drive_string += f'{drive_colors[c]}{Style.BRIGHT}{get_drive_name(c)}{Style.RESET_ALL}, '
    print(f'\nAssessing backup surface area across {drive_string.rstrip()[:-1]}...')
    show_tracker = dict(sorted(show_tracker.items(), key=lambda item: (item[1][0],item[0])))
    with open(rf"{os.path.dirname(__file__)}\show_backup_tracker.txt",mode='w',encoding='utf-8') as file:
        file.seek(0)
        for st in list(show_tracker.keys()):
            file.write(f'{show_tracker[st][0]}: {st} [{show_tracker[st][1]}] ({get_show_size(get_show_files(st))} GB)\n')
    total = len(one_count_list)+len(two_count_list)+len(threePlus_count_list)
    singleCountPercent = len(one_count_list)/total*100
    doubleCountPercent = len(two_count_list)/total*100
    triplePlusCountPercent = len(threePlus_count_list)/total*100
    singleData = 0; doubleData = 0; triplePlusData = 0
    for ocl in one_count_list:
        try:
            singleData += get_file_size(ocl)
        except FileNotFoundError:
            print(f'File not found: {ocl}')
            continue
    for tcl in two_count_list:
        try:
            doubleData += get_file_size(tcl)
        except FileNotFoundError:
            print(f'File not found: {tcl}')
            continue
    for tpcl in threePlus_count_list:
        try:
            triplePlusData += get_file_size(tpcl)
        except FileNotFoundError:
            print(f'File not found: {tpcl}')
            continue  
    totalData = sum([singleData,doubleData,triplePlusData])
    # print(f'\nAcross the {len(connected_drives)} connected drives: {", ".join(sorted([str({drive_colors[c]}{Style.BRIGHT}{get_drive_name(c)}{Style.RESET_ALL}) for c in connected_drives]))}\n')
    print(f'\nAcross the {len(connected_drives)} connected drives: '+drive_string.rstrip()[:-1])
    print(f'{(singleData/totalData)*100:.2f}% of data ({singleData/1000:,.2f} TB) is not backed up')
    print(f'{singleCountPercent:.2f}% of files are not backed up\n###')    
    print(f'{(doubleData/totalData)*100:.2f}% of data ({doubleData/1000:,.2f} TB) is backed up once')
    print(f'{doubleCountPercent:.2f}% of files are backed up once\n###')
    print(f'{(triplePlusData/totalData)*100:.2f}% of data ({triplePlusData/1000:,.2f} TB) is backed up more than once')
    print(f'{triplePlusCountPercent:.2f}% of files are backed up more than once')

def get_stats(drives):
    total_available_space = 0; used_space = 0; unused_space = 0
    for d in drives:
        disk_obj = shutil.disk_usage(f'{d}:/')
        total_available_space += int(disk_obj[0]/10**12)
        used_space += int(disk_obj[1]/10**12)
        unused_space += int(disk_obj[2]/10**12)
    movies = []; tv_shows = []; animes = []; uhd_movies = []; books = []
    for i,f in enumerate(primary_paths):
        if 'Movies' in f and '4K' not in f:
            movies.append(f+'/'+primary_titles[i])
        elif ':/Shows' in f:
            tv_shows.append(f+'/'+primary_titles[i])
        elif ':/Anime' in f:
            animes.append(f+'/'+primary_titles[i])
        elif ':/4K Movies/' in f:
            uhd_movies.append(f+'/'+primary_titles[i])
        elif ':/Books/' in f:
            books.append(f+'/'+primary_titles[i])
    num_show_files = len(tv_shows)
    num_shows = len(list(set(([f.split('/')[2].strip() for f in tv_shows]))))
    size_shows = round(sum([get_file_size(show) for show in tv_shows])/10**3,2)
    num_anime_files = len(animes)
    num_animes = len(list(set(([f.split('/')[2].strip() for f in animes]))))
    size_animes = round(sum([get_file_size(anime) for anime in animes])/10**3,2)
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
    
### MAIN FUNCTION ###

def main(backup_drive,no_movie_drives,uhd_movie_drives,music_drives,book_drives):
    if does_drive_exist(movie_dir[0]): print(f'Movie Drive: {drive_colors[movie_dir[0]]}{Style.BRIGHT}{get_drive_name(movie_dir[0])} ({movie_dir[0]} drive){Style.RESET_ALL}')
    if does_drive_exist(show_dir[0]): print(f'TV Show Drive: {drive_colors[show_dir[0]]}{Style.BRIGHT}{get_drive_name(show_dir[0])} ({show_dir[0]} drive){Style.RESET_ALL}')
    if does_drive_exist(anime_dir[0]): print(f'Anime Drive: {drive_colors[anime_dir[0]]}{Style.BRIGHT}{get_drive_name(anime_dir[0])} ({anime_dir[0]} drive){Style.RESET_ALL}')
    if does_drive_exist(music_dir[0]): print(f'Music Drive: {drive_colors[music_dir[0]]}{Style.BRIGHT}{get_drive_name(music_dir[0])} ({music_dir[0]} drive){Style.RESET_ALL}')
    if does_drive_exist(book_dir[0]): print(f'Book Drive: {drive_colors[book_dir[0]]}{Style.BRIGHT}{get_drive_name(book_dir[0])} ({book_dir[0]} drive){Style.RESET_ALL}')
    if does_drive_exist(backup_drive[0]): print(f'Assessing: {drive_colors[backup_drive]}{Style.BRIGHT}{get_drive_name(backup_drive)} ({backup_drive} drive){Style.RESET_ALL}')
    ###
    # try:
    feasible = determine_backup_feasibility(backup_drive,no_movie_drives,uhd_movie_drives,music_drives,book_drives)
    # except:
    #     feasible = False; print('Failure while determining backup feasibility...')
    if feasible:
        backup(backup_drive,no_movie_drives,uhd_movie_drives,music_drives,book_drives)
    ###
    get_space_remaining(backup_drive)
    # get_shows_not_on_drive(backup_drive)


def set_color_scheme(drives):
    """
    Defines global variable drive_colors in support of print statements

    Parameters
    ----------
    drives : list
        List of backup drive letters.

    Returns
    -------
    None.

    """
    global drive_colors; drive_colors = {}
    reserved_colors = {'Rex':Fore.BLUE,'Echo':Fore.CYAN,'Cody':Fore.YELLOW,'Fives':Fore.LIGHTBLUE_EX,'Gree':Fore.GREEN,'Wolffe':Fore.MAGENTA}
    possible_colors = [Fore.RED]
    for i,d in enumerate(drives):
        if get_drive_name(d) in list(reserved_colors.keys()):
            drive_color = f'{reserved_colors[get_drive_name(d)]}{Style.BRIGHT}'
            drive_colors.update({d:drive_color})
        else:
            drive_colors.update({d:possible_colors[i % len(possible_colors)]})

global os_drive; os_drive = 'C'
global movie_dir; movie_dir = "G:/Movies/"
if not does_drive_exist(movie_dir[0]): movie_drive_name = 'Gree'; movie_dir = f'{get_drive_letter(movie_drive_name)}:/Movies/'
global uhd_movie_dir; uhd_movie_dir = "G:/4K Movies/"
if not does_drive_exist(uhd_movie_dir[0]): uhd_movie_drive_name = 'Gree'; uhd_movie_dir = f'{get_drive_letter(uhd_movie_drive_name)}:/4K Movies/'
global show_dir; show_dir = 'R:/Shows/'
if not does_drive_exist(show_dir[0]): show_drive_name = 'Rex'; show_dir = f'{get_drive_letter(show_drive_name)}:/Shows/'
global anime_dir; anime_dir = 'A:/Anime/'
if not does_drive_exist(anime_dir[0]): anime_drive_name = 'Appo'; anime_dir = f'{get_drive_letter(anime_drive_name)}:/Anime/'
global anime_movie_dir; anime_movie_dir = 'G:/Anime Movies/'
if not does_drive_exist(anime_movie_dir[0]): anime_movie_drive_name = 'Gree'; anime_movie_dir = f'{get_drive_letter(anime_movie_drive_name)}:/Anime Movies/'
global anime_movies; anime_movies = [m[:-4] for m in read_alexandria([anime_movie_dir])[0]]
global music_dir; music_dir = 'W:/Music/MP3s_320/'
if not does_drive_exist(music_dir[0]): music_drive_name = 'Wolffe'; music_dir = f'{get_drive_letter(music_drive_name)}:/Music/'
global book_dir; book_dir = 'W:/Books/'
if not does_drive_exist(book_dir[0]): book_drive_name = 'Wolffe'; music_dir = f'{get_drive_letter(book_drive_name)}:/Books/'
if __name__ == '__main__':
     # starts time
    start_time = time.time()
    # prints time the script starts
    print(f'\nMain process initiated at {get_time()}...\n\n#################################\n')
    # sets global variables & define the primary directory for each media genre
    global primary_titles; global primary_paths; primary_titles, primary_paths = read_alexandria([movie_dir,show_dir,anime_dir,anime_movie_dir,uhd_movie_dir,book_dir,music_dir])
    global backup_titles; global backup_paths
    global imdb_min
    deactivated_drives = []
    # Writes Shows & Anime to their drive's whitelist
    if does_drive_exist(show_dir[0]):
        write_all_shows_to_whitelist(show_dir[0],show_dir[0])
    else:
        deactivated_drives.append(show_dir[0])
    if does_drive_exist(anime_dir[0]):
        write_all_shows_to_whitelist(anime_dir[0],anime_dir[0])
    else:
        deactivated_drives.append(anime_dir[0])
    if not does_drive_exist(movie_dir[0]): deactivated_drives.append(movie_dir[0])
    if not does_drive_exist(anime_movie_dir[0]): deactivated_drives.append(anime_movie_dir[0])
    # define the drives to NOT backup into
    drive_blacklist = [os_drive,'T'] + deactivated_drives
    # searches for backup drives
    drives = [drive[0] for drive in win32api.GetLogicalDriveStrings().split('\000')[:-1] if drive[0] not in drive_blacklist and does_drive_exist(drive[0])]
    # sets color scheme for print statements relating to drives
    set_color_scheme(drives)
    # defines drives that should not backup movies (from <drive>:/Movies directory)
    global no_movie_drives; no_movie_drives = list(set(['R2D2','Wolffe','Appo','Keeli','Lindsay_Movie_HHD',get_drive_name(movie_dir[0]),get_drive_name(anime_movie_dir[0]),get_drive_name(show_dir[0]),get_drive_name(anime_dir[0])])) # drives with no movies
    global uhd_movie_drives; uhd_movie_drives = ['Wolffe','Vaughn',get_drive_name(uhd_movie_dir[0])] # drives with 4K/UHD movies
    global music_drives; music_drives = ['Wolffe',get_drive_name(music_dir[0])] # drives with music 
    global book_drives; book_drives = ['Wolffe','Vaughn',"B's Movies",get_drive_name(music_dir[0])] # drives with books
    for bd in drives:
        imdb_min = get_imdb_minimum(bd)
        backup_titles, backup_paths = read_alexandria([f'{bd}:/Movies/',f'{bd}:/Shows/',f'{bd}:/Anime/',f'{bd}:/Anime Movies',f'{bd}:/4K Movies',f'{bd}:/Books',f'{bd}:/Music'])
        try:
            main(bd,no_movie_drives,uhd_movie_drives,music_drives,book_drives)
        except OSError as e:
            print(f'OS Error: {e}\n')
        print('\n#################################\n')
    # searches for duplicate files within shows in the primary drive
    # duplicates = find_duplicates_and_show_data()
    time.sleep(0.1)
    # determines what percentage of files are backed up at different levels
    # check_backup_surface_area(drives)
    time.sleep(0.1)
    # fetches file stats for the primary drive
    get_stats(drives)
    txt_doc_list = [rf'{os.path.dirname(__file__)}\Show Lists\anime_shows.txt',
                    rf"{os.path.dirname(__file__)}\Show Lists\B's_Movies_whitelist.txt",
                    rf'{os.path.dirname(__file__)}\Show Lists\Alexandria_2_whitelist.txt',
                    rf'{os.path.dirname(__file__)}\Show Lists\Fives_whitelist.txt',
                    rf"{os.path.dirname(__file__)}\Show Lists\Dani's_Movies_whitelist.txt",
                    rf"{os.path.dirname(__file__)}\Show Lists\Mike's_Movies_whitelist.txt",
                    rf"{os.path.dirname(__file__)}\Show Lists\Cody_whitelist.txt",
                    rf"{os.path.dirname(__file__)}\Show Lists\Echo_whitelist.txt",
                    rf"{os.path.dirname(__file__)}\Show Lists\Wolffe_whitelist.txt",
                    rf"{os.path.dirname(__file__)}\Show Lists\McGugh_Movies_whitelist.txt",
                    rf"{os.path.dirname(__file__)}\Show Lists\Vaughn_whitelist.txt",
                    rf"{os.path.dirname(__file__)}\Show Lists\Vaughn_missing_shows.txt",
                    rf"{os.path.dirname(__file__)}\Show Lists\Gree_whitelist.txt",
                    rf"{os.path.dirname(__file__)}\Show Lists\Lindsay_Movie_HHD_whitelist.txt"]
    for tdl in txt_doc_list:
        order_txt_doc(tdl)
    print('\n#################################')
    print(f'\nMain process completed at {get_time()}.')
    get_time_elapsed(start_time)
    if sys.stdin and sys.stdin.isatty(): time.sleep(100)


   
