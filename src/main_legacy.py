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

def get_time():
    """
    Returns current time.
    
    Returns
    -------
    curr_time: str
        Time in 'TTTT on DDMMMYYYY' format.
        
    """
    time_dict = {'dotw':time.ctime().split()[0],'month':time.ctime().split()[1],'day':time.ctime().split()[2],
                 'hour_24_clock':time.ctime().split()[3].split(':')[0],'minute':time.ctime().split()[3].split(':')[1],
                 'second':time.ctime().split()[3].split(':')[2],'year':time.ctime().split()[4]}
    if len(time_dict["minute"]) < 2: time_dict['minute'] = '0'+time.ctime().split()[3].split(':')[1]
    if len(time_dict["day"]) < 2: time_dict['day'] = '0'+time.ctime().split()[2]
    curr_time = f'{time_dict["hour_24_clock"]}{time_dict["minute"]} on {time_dict["day"]}{time_dict["month"].upper()}{time_dict["year"][2:]}'
    return curr_time

def get_time_elapsed(start_time):
    """
    Prints the elapsed time since the input time.
    
    Parameters
    ----------
    start_time : float
        Time as a floating pouint number in seconds.

    Returns
    -------
    None.
    
    """
    hour_name, min_name, sec_name = 'hours', 'minutes', 'seconds'
    t_sec = round(time.time() - start_time)
    (t_min, t_sec) = divmod(t_sec,60)
    (t_hour,t_min) = divmod(t_min,60)
    if t_hour == 1: hour_name = 'hour'
    if t_min == 1: min_name = 'minute'
    if t_sec == 1: sec_name = 'second'
    print(f'\nThis process took: {t_hour} {hour_name}, {t_min} {min_name}, and {t_sec} {sec_name}')

def does_drive_exist(letter):
    """
    Checks if a drive exists. 

    Parameters
    ----------
    letter : str
        Drive letter [A-Z] (Windows).

    Returns
    -------
    bool
        Returns TRUE if drive exists, otherwise returns FALSE.
        
    """
    try: 
        win32api.GetVolumeInformation(f"{letter}:/")
        return True
        # return (win32file.GetLogicalDrives() >> (ord(letter.upper()) - 65) & 1) != 0
    except:
        return False

def get_drive_name(letter):
    """
    Gets drive name from letter.

    Parameters
    ----------
    letter : str
        Drive letter [A-Z] (Windows).

    Returns
    -------
    str
        Returns name of the drive, as displayed in file explorer.

    """
    if does_drive_exist(letter): 
        return win32api.GetVolumeInformation(f"{letter}:/")[0]
    else: 
        return "None"

def get_drive_letter(drive_name):
    """
    Gets drive letter from drive name.

    Parameters
    ----------
    drive_name : str
        Drive name.

    Returns
    -------
    d : str
        Drive letter [A-Z] (Windows).

    """
    drives = [drive[0] for drive in win32api.GetLogicalDriveStrings().split('\000')[:-1] if does_drive_exist(drive[0])]
    for d in drives:
        if get_drive_name(d) == drive_name:
            return d

def get_drive_size(letter):
    """
    Gets size of drive.

    Parameters
    ----------
    letter : str
        Drive letter [A-Z] (Windows).

    Returns
    -------
    float
        Size of drive in GB.

    """
    return shutil.disk_usage(f'{letter}:/')[0]/10**9

def get_file_size(file_with_path):
    try:
        if file_with_path[-4] == '.': return os.path.getsize(file_with_path)/10**9
        else: 
            try:
                return os.path.getsize(file_with_path+'.mp4')/10**9
            except:
                return os.path.getsize(file_with_path+'.mkv')/10**9
    except FileNotFoundError:
        if file_with_path[-4] == '.': return os.path.getsize(file_with_path[:-4]+'.mkv')/10**9
        else: return os.path.getsize(file_with_path)/10**9

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

def get_space_remaining(drive):
    drives = [movie_dir[0],show_dir[0],anime_dir[0]]
    if drive not in drives: drives.append(drive)
    for i,d in enumerate(drives):
        disk_obj = shutil.disk_usage(f'{d}:/')
        gb_remaining = int(disk_obj[2]/10**9)
        if i == 0: print(f'\n{gb_remaining:,} GB of space left on {drive_colors[d]}{Style.BRIGHT}{get_drive_name(d)}{Style.RESET_ALL}...')    
        else: print(f'{gb_remaining:,} GB of space left on {drive_colors[d]}{Style.BRIGHT}{get_drive_name(d)}{Style.RESET_ALL}...')  

def get_shows_list(drive):
    all_titles, all_paths = read_alexandria([f'{drive}:\\Shows\\',f'{drive}:\\Anime\\'])
    return sorted(list(set([' '.join(at.split()[:-1]) for at in all_titles])))

def get_imdb_minimum(drive):
    """
    Returns the IMDb minimum rating for a movie
    
    Parameters
    ----------
    drive : string
        Letter of backup drive.

    Returns
    -------
    float
        Returns the minimum IMDB rating of movies to be backed up on the drive.

    """
    imdb_min_path = rf'{os.path.dirname(__file__)}\imdb_drive_minimums.txt'
    with open(imdb_min_path,mode='r',encoding='utf-8') as imdb_file:
        lines = imdb_file.readlines()
    imdb_dict = {}
    for l in lines:
        imdb_dict.update({l.split('|')[0].strip():float(l.split('|')[1].strip())})
    return imdb_dict.get(get_drive_name(drive),5.99)

def order_txt_doc(txt_file):
    try:
        if txt_file[-4:] != '.txt': txt_file += '.txt'
        with open(txt_file,mode='r') as file: items = sorted(list(set([l.strip() for l in file.readlines()])), key = lambda x: x.lower())
        with open(txt_file,mode='w') as file: 
            file.seek(0)
            for item in items:
                if item.strip() != '': file.write(item+'\n')
    except FileNotFoundError:
        pass

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

def movie_score_filter(threshold):
    df_tmdb = pd.read_csv(rf'{movie_dir[0]}:\tmdb.csv')
    df_bad = df_tmdb[df_tmdb['Rating'] < threshold].reset_index(drop=True)
    df_good = df_tmdb[df_tmdb['Rating'] >= threshold].reset_index(drop=True)
    bad_movies = [f"{df_bad.loc[i,'Title']} ({df_bad.loc[i,'Year']})" for i in range(len(df_bad))]
    good_movies = [f"{df_good.loc[i,'Title']} ({df_good.loc[i,'Year']})" for i in range(len(df_good))]
    return bad_movies, good_movies

def do_I_backup_this_movie(drive,movie,bad_movies,good_movies,imdb_min,no_movie_drives):
    if movie not in bad_movies and drive not in no_movie_drives:
        keywords = []; keyword_exceptions = []
        drive_name = get_drive_name(drive)
        no_anime_drives = ["B's Movies","B's Movies 2","Dani's Movies","Mike's Movies",'NielsonMovies','McGugh Movies','Fives','Vaughn','Lindsay_Movie_HHD']
        if drive_name in no_movie_drives:
            return False
        elif drive_name in no_anime_drives:
            if movie in anime_movies:
                return False
            keywords = ['Scooby-Doo','Pokémon','Chipmunks','Tom and Jerry','Atlas Shrugged','Futurama']
        if drive_name in ["B's Movies","B's Movies 2",'McGugh Movies']:
            if get_file_size(f'{movie_dir}/{movie}/{movie}') > 4.5: return False
            keywords += ['Fifty Shades','Twilight','Divergent','Underworld','Resident Evil','Magic Mike',
                         'Barbie','Blue Lagoon','Final Destination','Ice Age','(193','Saw ','Batman -', 'Batman Beyond',
                         'Batman vs. ', '(192']
            keyword_exceptions += ['Scooby-Doo (2002)','Scooby-Doo 2 - Monsters Unleashed (2004)','Pokémon - Detective Pikachu (2019)',
                                   'The Wizard Of Oz (1939)','Saw (2004)']
        if drive_name in ["Dani's Movies"]:
            keywords += ['Barbie','Final Destination','Ice Age','Saw ','Batman -','Batman Beyond','Bill & T','Death Race','Halloween ',
                         'Hellboy','Hotel Trans','Insidious','James Bond','Batman vs. ','Superman','Conjuring','[REC]', 
                         'VeggieTales','Karate Kid','Lethal Weapons','Paranormal Act','Scream ','Star Trek','Stargate',
                         '(192','(193','(194','(195','(196']
            keyword_exceptions += ['Scooby-Doo (2002)','Scooby-Doo 2 - Monsters Unleashed (2004)','Pokémon - Detective Pikachu (2019)',
                                   'The Wizard Of Oz (1939)','Casino Royale (2006)','No Time to Die','Quantum of S','Skyfall','Spectre',
                                   'Goosebumps 2']     
        for k in keywords:
            if k in movie and movie not in keyword_exceptions:
                return False
        return True
    return False

def remove_empty_folders(drive,folders=['Movies','Anime Movies','Shows','Anime']):
    for folder in folders:
        subdirs = [x[0] for x in os.walk(f'{drive}:/{folder}/')]
        for sd in subdirs:
            if not os.listdir(sd):
                print(f'Removing Empty Folder: {sd}')
                os.rmdir(sd)

def backup(bd,no_movie_drives,uhd_movie_drives,music_drives,book_drives):
    def backup_function(backup_tuples):
        for bt in backup_tuples: 
            sfile = fr'{bt[0]}'; dfile = fr'{"/".join(bt[1].split("/")[:-1])}'
            file_title = sfile.split('/')[-1][:-4].strip()
            if os.path.isfile(sfile): 
                print(f'{Fore.YELLOW}{Style.BRIGHT}Backing up{Style.RESET_ALL} {file_title} from {drive_colors[sfile[0]]}{Style.BRIGHT}{get_drive_name(sfile[0])}{Style.RESET_ALL} to {drive_colors[dfile[0]]}{Style.BRIGHT}{get_drive_name(dfile[0])}{Style.RESET_ALL}')
                cmd = fr'copy "{sfile}" "{dfile}/"'.replace('/','\\')
                subprocess.call(cmd, shell=True, stdout=subprocess.PIPE)
    def integrity_assurance(bd,print_space_bool=False):
        if print_space_bool: print('\n')
        primary_items = [(primary_paths[i] + '/' +primary_titles[i])[1:] for i in range(len(primary_titles))]
        backup_items = [(backup_paths[i] + '/' +backup_titles[i])[1:] for i in range(len(backup_titles))]
        combined_items = sorted(list(set(backup_items)&set(primary_items)))
        with alive_bar(len(combined_items),ctrl_c=False,dual_line=True,title=f'{Fore.YELLOW}{Style.BRIGHT}Integrity Check{Style.RESET_ALL}',bar='classic',spinner='classic') as bar:
            for i in range(len(combined_items)):
                if 'Anime' in combined_items[i] and 'Movie'in combined_items[i] and combined_items[i][-4:] in ['.mp4','.mkv']:
                    primary_size = os.stat(f'{anime_movie_dir[0]}{combined_items[i]}').st_size
                    sfile = fr'{anime_movie_dir[0]+combined_items[i]}'
                elif 'Anime' in combined_items[i] and combined_items[i][-4:] in ['.mp4','.mkv']:
                    primary_size = os.stat(f'{anime_dir[0]}{combined_items[i]}').st_size
                    sfile = fr'{anime_dir[0]+combined_items[i]}'
                elif 'Shows' in combined_items[i] and 'Movie'not in combined_items[i] and combined_items[i][-4:] in ['.mp4','.mkv']:
                    primary_size = os.stat(f'{show_dir[0]}{combined_items[i]}').st_size
                    sfile = fr'{show_dir[0]+combined_items[i]}'
                elif '4K' in combined_items[i] and combined_items[i][-4:] in ['.mp4','.mkv']:
                    primary_size = os.stat(f'{uhd_movie_dir[0]}{combined_items[i]}').st_size
                    sfile = fr'{uhd_movie_dir[0]+combined_items[i]}'
                elif 'Movies' in combined_items[i] and combined_items[i][-4:] in ['.mp4','.mkv']:
                    primary_size = os.stat(f'{movie_dir[0]}{combined_items[i]}').st_size
                    sfile = fr'{movie_dir[0]+combined_items[i]}'               
                elif 'Books' in combined_items[i] and '.pdf' in combined_items[i]:
                    primary_size = os.stat(f'{book_dir[0]}{combined_items[i]}').st_size
                    sfile = fr'{book_dir[0]+combined_items[i]}'
                elif 'Music' in combined_items[i] and '.mp3' in combined_items[i]:
                    primary_size = os.stat(f'{music_dir[0]}{combined_items[i]}').st_size
                    sfile = fr'{music_dir[0]+combined_items[i]}'
                else:
                    primary_size = os.stat(f'{movie_dir[0]}{combined_items[i]}').st_size
                    sfile = fr'{movie_dir[0]+combined_items[i]}'
                backup_size = os.stat(f'{bd}{combined_items[i]}').st_size
                if primary_size != backup_size and primary_size > 100:
                    print(f'[{i+1}/{len(combined_items)}] Rewriting \"{combined_items[i].split("/")[-1][:-4]}"')                
                    # shutil.copyfile(sfile, f'{bd+combined_items[i]}')
                    dfile = fr'{bd+combined_items[i]}'
                    cmd = fr'copy "{sfile}" "{dfile}"'.replace('/','\\')
                    subprocess.call(cmd, shell=True, stdout=subprocess.PIPE)
                bar()
    backup_titles, backup_paths = read_alexandria([f'{bd}:/Movies/',f'{bd}:/Shows/',f'{bd}:/Anime/',f'{bd}:/Anime Movies/',f'{bd}:/4K Movies/',f'{bd}:/Music/',f'{bd}:/Books/'])
    primary_items = [(primary_paths[i] + '/' +primary_titles[i])[1:] for i in range(len(primary_titles))]
    backup_items = [(backup_paths[i] + '/' +backup_titles[i])[1:] for i in range(len(backup_titles))]
    not_in_backup = []
    for pi in primary_items:
        if pi not in backup_items: not_in_backup.append(pi)
    not_in_primary = []
    for bi in backup_items:
        if bi not in primary_items: not_in_primary.append(bi)
    ui = ''
    if len(not_in_primary) > 0:
        print(f'\n{Back.RED}The following files are not in the primary drives:')
        for nip in not_in_primary:
            print(nip)
        ui = ''
        while ui != 'n' and ui != 'y':
            if len(not_in_primary) > 1:
                ui = input(f'\nDo you want to delete these {len(not_in_primary)} items? [Y/N] {Style.RESET_ALL}').lower()
            else:
                ui = input(f'\nDo you want to delete this item? [Y/N] {Style.RESET_ALL}').lower()
    if ui.lower() == 'y':
        for nip in not_in_primary:
            print(f'Deleting: {bd}{nip}')
            os.remove(f'{bd}{nip}')
    ### backup primary ###
    drive_name = get_drive_name(bd)
    whitelist = read_whitelist(drive_name)
    backup_tuples = []
    bad_movies, good_movies = movie_score_filter(imdb_min)
    space_bool = False
    for i in range(len(not_in_backup)):
        file = ''.join(not_in_backup[i].split('/')[-1]).strip()
        media_folder_type = not_in_backup[i].split('/')[1]
        if 'Shows' in media_folder_type or ('Anime' in media_folder_type and 'Movies' not in media_folder_type):
            series_name = ' '.join(file.split()[:-1])
            series_name_with_season = ' '.join(file.split()[:-1] + [file.split()[-1][:3]])
            if series_name not in whitelist and series_name_with_season not in whitelist and 'Movies' not in media_folder_type: continue
        elif '4K' in media_folder_type:
            if drive_name not in uhd_movie_drives: continue
        elif 'Music' in media_folder_type:
            if drive_name not in music_drives: continue
        elif 'Books' in media_folder_type:
            if drive_name not in book_drives: continue
        elif drive_name in no_movie_drives and 'Movies' in media_folder_type: continue
        elif 'Movies' not in media_folder_type: 
            # file is likely a TV Show
            pass
        else: # file is likely an HD movie
            if not do_I_backup_this_movie(bd,file[:-4],bad_movies,good_movies,imdb_min,no_movie_drives): continue
        path = '/'.join(not_in_backup[i].split('/')[:-1]).strip()+'/'
        if 'Anime' in path.split('/')[1] and 'Movie' in path.split('/')[1]:
            ppath = anime_movie_dir[0]+path
            print(ppath)
        elif 'Anime' in path.split('/')[1]:
            ppath = anime_dir[0]+path
        elif 'Shows' in path.split('/')[1] and 'Movie'not in path.split('/')[1]:
            ppath = show_dir[0]+path  
        elif '4K' in path.split('/')[1]:
            ppath = uhd_movie_dir[0]+path  
        elif 'Books' in path.split('/')[1]:
            ppath = book_dir[0]+path  
        elif 'Music' in path.split('/')[1]:
            ppath = book_dir[0]+path    
        else: 
            ppath = movie_dir[0]+path
        bpath = bd+path
        original = r'{}{}'.format(ppath,file)
        target = r'{}{}'.format(bpath,file)
        while True:
            if os.path.isdir(bpath):
                backup_tuples.append((original,target))
                break
            else:
                if not space_bool: print('\n'); space_bool  = True
                try:
                    os.mkdir(bpath)
                    print(f'Creating path: {bpath}')
                    backup_tuples.append((original,target))
                    break
                except FileNotFoundError:
                    index = -2
                    while True:
                        try:
                            bpath2 = '/'.join(bpath.split('/')[:index])
                            os.mkdir(bpath2)
                            print(f'Creating path: {bpath2}')
                            break
                        except:
                            index += 1
                            if index > len(bpath.split('/')):
                                break 
    if len(backup_tuples) == 1: print(f'Backing up {len(backup_tuples)} file to {drive_colors[bd]}{Style.BRIGHT}{get_drive_name(bd)}{Style.RESET_ALL}...\n')
    elif len(backup_tuples) > 0: print(f'Backing up {len(backup_tuples):,} files to {drive_colors[bd]}{Style.BRIGHT}{get_drive_name(bd)}{Style.RESET_ALL}...\n')
    else: integrity_assurance(bd); return 0
    backup_function(backup_tuples)
    integrity_assurance(bd)
        
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

def determine_backup_feasibility(bd,no_movie_drives,uhd_movie_drives,music_drives,book_drives):
    try:
        drive_name = get_drive_name(bd)
        drive_size = get_drive_size(bd)
        whitelist = read_whitelist(drive_name)
        whitelist = [w.split(' S0')[0] for w in whitelist]
        tv_names_with_path = [primary_paths[i]+'/'+primary_titles[i] for i in range(len(primary_paths)) if 'Movies' not in primary_paths[i]]
        uhd_movies_with_path = [primary_paths[i]+'/'+primary_titles[i] for i in range(len(primary_paths)) if '4K Movies' in primary_paths[i]]
        music_with_path = [primary_paths[i]+'/'+primary_titles[i] for i in range(len(primary_paths)) if 'Music' in primary_paths[i]]
        books_with_path = [primary_paths[i]+'/'+primary_titles[i] for i in range(len(primary_paths)) if 'Books' in primary_paths[i]]
        movie_names_with_path = [primary_paths[i]+'/'+primary_titles[i] for i in range(len(primary_paths)) if 'Movies' in primary_paths[i] and '4K' not in primary_paths[i]]
        size_needed = 0
        bad_movies, good_movies = movie_score_filter(imdb_min)
        for mnwp in movie_names_with_path:
            if drive_name not in no_movie_drives:
                if do_I_backup_this_movie(bd,'.'.join(mnwp.split('/')[-1].split('.')[:-1]),bad_movies,good_movies,imdb_min,no_movie_drives):
                      size_needed += get_file_size(mnwp)
        if drive_name in uhd_movie_drives:
            for uhdmnwp in uhd_movies_with_path:
                size_needed += get_file_size(uhdmnwp)
        if drive_name in music_drives:
            for mwp in music_with_path:
                size_needed += get_file_size(mwp)
        if drive_name in book_drives:
            for bwp in books_with_path:
                size_needed += get_file_size(bwp)
        for tnwp in tv_names_with_path:
            name = ' '.join(tnwp.split('/')[-1].split()[:-1])
            if name in whitelist:
                size_needed += get_file_size(tnwp)
        # print(f'Drive Size: {drive_size}, Backup Size {size_needed}')
        all_show_titles = read_alexandria([f'{bd}:\\Shows\\',f'{bd}:\\Anime\\'])[0]
        shows_on_drive = sorted(list(set([' '.join(at.split()[:-1]) for at in all_show_titles])))
        not_on_whitelist = []
        not_backed_up = []
        for show in shows_on_drive:
            if show not in whitelist and show != 'Spongebob Squarepants':
                not_on_whitelist.append(show)
        for wShow in whitelist:
            if wShow not in shows_on_drive and ' '.join(wShow.split()[:-1]) not in shows_on_drive:
                not_backed_up.append(wShow)
        if len(not_on_whitelist) > 0:
            if len(not_on_whitelist) == 1: print(f'\n{len(not_on_whitelist)} Show Unexpectedly on {drive_colors[bd]}{Style.BRIGHT}{drive_name} ({bd} drive){Style.RESET_ALL}')
            else: print(f'\n{len(not_on_whitelist)} Shows Unexpectedly on {drive_colors[bd]}{Style.BRIGHT}{drive_name} ({bd} drive){Style.RESET_ALL}\n')
            for now in not_on_whitelist:
                ui = ''
                while ui not in ['y','n']:
                    ui = input(f'Do you want to delete {Back.CYAN}{now}{Style.RESET_ALL} from {drive_colors[bd]}{Style.BRIGHT}{drive_name}{Style.RESET_ALL}? [Y/N] ').lower()
                if ui == 'y':
                    print(f'Deleting {Back.CYAN}{now}{Style.RESET_ALL} from {drive_colors[bd]}{Style.BRIGHT}{drive_name}{Style.RESET_ALL}...')
                    files_with_path = [bd+x[1:] for x in get_show_files(now)]
                    shows_with_path = list(set(['/'.join(fwp.split('/')[:-2]) for fwp in files_with_path]))
                    # for fwp in files_with_path:
                    #     os.remove(fwp)
                    for swp in shows_with_path:
                        # print(swp)
                        if len(swp.split('/'))  > 2:
                            shutil.rmtree(swp)
        remove_empty_folders(bd)
        if len(not_backed_up) > 0:
            if len(not_backed_up) == 1: print(f'{len(not_backed_up)} show not backed up {drive_colors[bd]}{Style.BRIGHT}{drive_name} ({bd} drive){Style.RESET_ALL}')
            else: print(f'{len(not_backed_up)} shows not backed up to {drive_colors[bd]}{Style.BRIGHT}{drive_name} ({bd} drive){Style.RESET_ALL}')
            for i,nbu in enumerate(not_backed_up):
                print(f'[-] {nbu}')
                # if i == len(not_backed_up) - 1 : print('\n')
        if drive_size > size_needed:
            return True
        else:
            print(f'\nThe requested backup to {drive_colors[bd]}{Style.BRIGHT}{drive_name} ({bd} drive){Style.RESET_ALL} is {int(size_needed - drive_size)} GB too big!')     
            return False
    except FileNotFoundError as e:
        print(f'Backup feasibility check bypassed due to FileNotFoundError: {e}')
        return True

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


   
