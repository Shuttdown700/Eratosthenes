#!/usr/bin/env python3
import os
os.chdir(rf'{os.getcwd()[0]}:\Users\brend\Documents\Coding Projects\alexandria-media-manager\src')
from main import do_I_backup_this_movie, get_drive_name, get_show_files, get_file_size, import_libraries, movie_score_filter, read_alexandria, get_imdb_minimum, does_drive_exist,write_all_shows_to_whitelist

import glob
import json
import math
# import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import random
import shutil
import string
import subprocess
import time
import urllib
import urllib.request
import warnings
import win32file
import win32api
import collections
# from matplotlib import style
# style.use('ggplot')
# from matplotlib.ticker import PercentFormatter

import alive_progress
from alive_progress import alive_bar
from mutagen.mp4 import MP4, MP4Cover
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from pymediainfo import MediaInfo

warnings.filterwarnings("ignore")

# import_libraries()

def remove_duplicate_tv_shows(all_titles):
    all_titles2 = []
    for at in all_titles:
        if at[-1] == ')':
            all_titles2.append(at)
        else:
            all_titles2.append(' '.join(at.split()[:-1]))
    return sorted(list(set(all_titles2)))
   
# write_all_shows_to_whitelist('O','O')

def delete_metadata(drive,file_extensions = ['.jpg','.nfo','.png','.jpeg','.info','.srt']):
    for e in file_extensions:
        file_names, file_paths = read_alexandria([f'{drive}:/Movies/',f'{drive}:/Shows/',f'{drive}:/Anime/',f'{drive}:/4K Movies/'],extensions = [e])
        file_names_with_path = [file_paths[i]+'/'+file_names[i] for i in range(len(file_paths))]
        if len(file_names_with_path) > 0:
            with alive_bar(len(file_names_with_path),ctrl_c=False,dual_line=False,title=f'Deleting {e} files',bar='classic',spinner='classic') as bar:
                for fnwp in file_names_with_path:
                    os.remove(fnwp)
                    bar()
        else:
            print(f'No {e} files in {drive} drive!')

# delete_metadata('B')

def remove_movies(drive,keywords=[],movieFiles=[]):
    if keywords == movieFiles == []:
        keywords = ['Scooby-Doo','Pokémon','Chipmunks','Tom and Jerry','Atlas Shrugged','Futurama']
        movieFiles = ['anime_movies.txt']
    movie_list = []
    os.chdir(r'C:\Users\brend\Documents\Coding Projects\Alexandria\Show Lists')
    for mf in movieFiles:
        with open(mf,mode='r',encoding='utf-8') as movie_file:
            movie_list += [m.strip() for m in movie_file.readlines()]
    file_names, file_paths = read_alexandria(movie_path = f'{drive}:/Movies/',tv_path = f'{drive}:/Shows/',extension = '.mp4')
    movies_with_path = [file_paths[i]+'/'+file_names[i]+'.mp4' for i in range(len(file_paths)) if file_paths[i] == f'{drive}:/Movies']
    delete_pile = []
    for mwp in movies_with_path:
        for k in keywords:
            if k in mwp:
               delete_pile.append(mwp)
               break
        if mwp.split('/')[-1].split('.mp4')[0] in movie_list:
               delete_pile.append(mwp)
    for d in delete_pile:
        print(f'Deleting: {d.split("/")[-1].split(".mp4")[0]} from {drive} drive')
        os.remove(d)
        
# remove_movies('D')

def change_show_year(drive):
    file_names, file_paths = read_alexandria(movie_path = f'{drive}:/Movies/',tv_path = f'{drive}:/Shows/',extension = '.mp4')
    old_file_paths = sorted(list(set(['/'.join(fp.split('/')[:-1]) for fp in file_paths if fp != f'{drive}:/Movies'])))[1:]
    new_file_paths = []
    for ofp in old_file_paths:
        ofp1 = '/'.join(ofp.split('/')[:-1])
        ofp2 = ofp.split('/')[-1]
        title1 = ' '.join(ofp2.split()[:-1])
        title2 = ofp2.split()[-1]
        if len(title2) == 6:
            new_file_paths.append(ofp)
            continue
        elif len(title2) == 7 and title2[-2] == '-':
            title2 = title2[:-2]+')'
            new_file = ofp1+'/'+title1+' '+title2
            new_file_paths.append(new_file)
        elif len(title2) > 7:
            title2 = title2.split('-')[0]+')'
            new_file = ofp1+'/'+title1+' '+title2
            new_file_paths.append(new_file)
        else:
            print(ofp)
    if len(old_file_paths) == len(new_file_paths):
        for i in range(len(old_file_paths)):
            os.rename(old_file_paths[i],new_file_paths[i])

# change_show_year('D')
    
def hide_metadata(drive):
    import stat, win32con
    extensions_list = ['.jpg','.nfo','.png']
    file_names, file_paths = read_alexandria([f'{drive}:/Movies/',f'{drive}:/Shows/',f'{drive}:/Anime/',f'{drive}:/Anime Movies/',f'{drive}:/4K Movies/'],extensions = extensions_list)
    file_names_with_path = [file_paths[i]+'/'+file_names[i] for i in range(len(file_paths))]
    if len(file_names_with_path) > 0:
        with alive_bar(len(file_names_with_path),ctrl_c=False,dual_line=False,title=f'Hiding {", ".join(extensions_list)} files',bar='classic',spinner='classic') as bar:
            for fnwp in file_names_with_path:
                # if 'Clone Wars S' in fnwp: break
                fa = os.stat(fnwp).st_file_attributes
                if bool(fa & stat.FILE_ATTRIBUTE_HIDDEN):
                    bar()
                    continue
                win32api.SetFileAttributes(fnwp,win32con.FILE_ATTRIBUTE_HIDDEN)
                bar()
    else:
        print(f'No {", ".join(extensions_list)} files in {drive} drive!')

# drives = ['E','G','R','W']
# for d in drives:    
#     hide_metadata(d)

def full_inventory(drive):
    drive = 'D'
    extensions_list = ['.mp4','.mkv']
    drive_name = get_drive_name(drive)
    file_names, file_paths = read_alexandria([f'{drive}:/Movies/',f'{drive}:/Shows/',f'{drive}:/Anime/',f'{drive}:/Anime Movies/'],extensions = extensions_list)
    movies = []; shows = []
    for i,fp in enumerate(file_paths):
        if fp == f'{drive}:/Movies':
            movies.append(file_names[i][:-4])
        if fp.split('/')[1] in ['Shows','Anime']:
            shows.append(fp.split('/')[2])
    shows = sorted(list(set(shows)))
    movies.sort()
    os.chdir(r'C:\Users\brend\Documents\Coding Projects\Alexandria')
    with open(f'{drive_name} inventory.txt',mode='w',encoding='utf-8') as file:
        file.seek(0)
        file.write('\n###\nSHOWS\n###\n')
        for s in shows:
            file.write(s+'\n')
        file.write('\n###\nMOVIES\n###\n')
        for m in movies:
            file.write(m+'\n')

def remove_empty_folders(drive,folders=['Movies','Anime Movies','Shows','Anime','Music']):
    for folder in folders:
        subdirs = [x[0] for x in os.walk(f'{drive}:/{folder}/')]
        for sd in subdirs:
            if not os.listdir(sd):
                print(f'Removing: {sd}')
                os.rmdir(sd)
                
# remove_empty_folders('V')
# drives = ['E','G','R','W','M']
# for d in drives:
#     remove_empty_folders(d)
    
def video_metadata(path_list=[],extensions_list=[],metadata_file_name=''):
    import ffmpeg
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



# os.path.realpath(os.path.dirname(os.path.abspath('__file__')))

# video_metadata()

def read_metadata_csv(filepath):
    return pd.read_csv(filepath)

# df = read_metadata_csv('S:/tv_metadata.csv')
 
def delete_bad_movies(drive):
    imdb_min = get_imdb_minimum(drive)
    print(f'\nLooking for movies under a {imdb_min} IMDB rating on {get_drive_name(drive)}...')
    bad_movies,good_movies = movie_score_filter(imdb_min)
    titles, paths = read_alexandria([f'{drive}:/Movies/',f'{drive}:/Anime Movies/'],['.mp4','.mkv'])
    extensions = [t[-4:] for t in titles]
    titles = [t[:-4] for t in titles]
    movies_to_delete = []
    for i,t in enumerate(titles):
        if t in bad_movies:
            movies_to_delete.append(f'{paths[i]}/{t}{extensions[i]}')
        elif not do_I_backup_this_movie(drive,t,bad_movies,good_movies,imdb_min,[]):
            movies_to_delete.append(f'{paths[i]}/{t}{extensions[i]}')
    if len(movies_to_delete) > 0:
        print('\nMovies to detete:',end='\n\n')
        for mtd in movies_to_delete:
            print(mtd)
        print(f'\nThis will delete {float(len(movies_to_delete)/len(titles))*100:.2f}% of movies on {get_drive_name(drive)}')
        ui = ''
        while ui not in ['Y','N']: ui = input('Proceed? [Y/N] ').upper()
        if ui == 'Y':
            for mtd in movies_to_delete:
                print(f'Deleting: {mtd}')
                os.remove(mtd)
    delete_metadata(drive)
    remove_empty_folders(drive,folders=['Movies','Anime Movies','Shows','Anime','Music','Books'])

# delete_bad_movies("D")
# for d in ['F','V','W']:
#     delete_bad_movies(d)

def analyze_metadata():
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

# analyze_metadata()

def edit_mkv_metadata():
    mkvtoolnix_dir = 'C:\\Program Files\\MKVToolNix\\mkvtoolnix\\'
    exiftool_dir = r'C:\\Users\\brend\\Documents\\Coding Projects\\Alexandria\\exiftool-12.62\\'
    # mediaInfo_dir = r'C:\Program Files\MediaInfo'
    # Possible properties: title, date, codec-name, display-width, display-height, channels
    binary_mkv = f'{mkvtoolnix_dir}+mkvpropedit.exe'
    binary_mp4 = f'{exiftool_dir}+exiftool.exe'
    drive_blacklist = ['C','T']
    drives = [sau for sau in string.ascii_uppercase if does_drive_exist(sau) and sau != os.getcwd()[0] and sau not in drive_blacklist]
    dir_types = [':/Movies/',':/Shows/',':/Anime/',':/Anime Movies/',':/4K Movies/']
    dir_list = []
    for d in drives:
        for dt in dir_types:
            dir_list.append(f'{d}{dt}')
    print('Fetching all files...')
    file_names, file_paths = read_alexandria(dir_list)
    with alive_bar(len(file_names),ctrl_c=False,dual_line=False,title=f'Writing Metadata to files',bar='classic',spinner='classic') as bar:
        for i,file_name in enumerate(file_names):
                file_extension = file_name[-4:]
                if file_extension != '.mkv': bar(); continue
                file_path = file_paths[i]+'/'+file_name
                mediaInfo = MediaInfo.parse(file_path)
                for track in mediaInfo.tracks:
                    if track.track_type == 'General':
                        curr_file_title = track.title
                file_title = file_name[:-4]
                if curr_file_title == file_title: bar(); continue
                # file_year = file_paths[i].split('(')[-1].split(')')[0].strip()
                actions_mkv = ''
                if True == True: actions_mkv += f'--set "title={file_title}"'
                # The property value is not a valid date & time string in '--set date=2021'. The recognized format is 'YYYY-mm-ddTHH:MM:SS+zz:zz': the year, month, day, letter 'T', hours, minutes, seconds and the time zone's offset from UTC; example: 2017-03-28T17:28-02:00.
                cmd_mkv = f'{binary_mkv} "{file_path}" {actions_mkv}'.replace('/','\\')
                cmd_mp4 = f'{binary_mp4} -Title="{file_title}" "{file_path}"'
                subprocess.run(cmd_mkv, shell=True, stdout=subprocess.PIPE)
                print(f'Editing {get_drive_name(file_path[0])}: {file_name[:-4]}')
                # print(os.curdir)
                # print(file_path)
                # print(cmd_mkv)
                bar()

# edit_mkv_metadata()

def update_tmdb():
    directory = 'C:/EmbyServerCache/tmdb-movies2'
    movie_dir = 'G:/Movies/'
    dirs = sorted([x[0].replace('\\','/') for x in os.walk(directory) if x[0] != directory],key = lambda x: int(x.split('/')[-1]))
    all_files = []
    for d in dirs:
        all_files += sorted([gg.replace('\\','/') for gg in glob.glob(f'{d}/*.json')])
    en_files = []
    for af in all_files:
        if 'all-en' in af:
            en_files.append(af)
    df_data = []; columns = ['Title','Year','Release Date','Rating','Num Raters','Popularity','Runtime (hrs)','Budget ($)','Revenue ($)','Profit ($)','Genres','Actors','Keywords','Production Companies','Countries']
    with alive_bar(len(en_files),ctrl_c=False,dual_line=False,title='Scraping Film Data',bar='classic',spinner='classic') as bar:
        for en in en_files:
            with open(en,'r',encoding='utf-8') as file:
                data = json.load(file)
            title = data['title']
            release_date = data['release_date'] # YYYY-MM-DD
            year = data['release_date'][:4]
            # title_with_year = f'{title} ({year})'
            runtime_minutes = data['runtime']
            runtime_hours = f'{runtime_minutes/60:.2f}'
            rating = data['vote_average']
            num_raters = data['vote_count']
            popularity = data['popularity']
            budget = data['budget']
            revenue = data['revenue']
            if budget > 0 and revenue > 0: profit = revenue - budget
            else: profit = np.nan
            genres = [g['name'] for g in data['genres']]
            actors = [c['name'] for c in data['casts']['cast']]
            keywords = [k['name'].title() for k in data['keywords']['keywords']]
            production_companies = [pc['name'] for pc in data['production_companies']]
            countries = [pc['name'] for pc in data['production_countries']]
            df_data.append([title,year,release_date,rating,num_raters,popularity,runtime_hours,budget,revenue,profit,genres,actors,keywords,production_companies,countries])
            bar()
    df_tmdb = pd.DataFrame(df_data,columns=columns)
    df_tmdb.to_csv(rf'{movie_dir[0]}:\tmdb.csv')
    df_tmdb.to_csv(rf'{os.path.realpath(os.path.dirname(__file__))}\tmdb.csv')

# update_tmdb()
        
def edit_books():
    book_inventory = []
    file_names, file_paths = read_alexandria(['W:/Books/'],['.pdf','.epub'])
    for i,fn in enumerate(file_names):
        fn_comma_split = fn.split(',')
        if fn[0] != '(':  print(fn)
        if len(fn_comma_split) < 3 or 'COPY' in fn or fn[0] == '(': continue
        extension = fn[-4:]
        year = fn_comma_split[-1].split('.')[0].strip()[1:-1]
        author = fn_comma_split[-2].strip()
        title = ','.join(fn_comma_split[:-2]).strip()
        book_data = [title,author,year]
        book_inventory.append(book_data)
        old_filename_with_path = file_paths[i]+'/'+fn
        new_filename_with_path = file_paths[i]+'/'+f'({year}) {title} [{author}]{extension}'
        os.replace(old_filename_with_path,new_filename_with_path)
    book_df = pd.DataFrame(book_inventory,columns=['Title','Author','Year'])
    from pdfrw import PdfReader, PdfWriter, PdfDict
    file_path = r"W:\Books\Business, Economics, & Mentorship\The Myth of the Rational Market - A History of Risk, Reward, and Delusion on Wall Street, Justin Fox, (2009).pdf"
    pdf_reader = PdfReader(file_path)
    metadata = PdfDict(Author='Someone', Title='PDF in Python')
    pdf_reader.Info.update(metadata)
    new_path = r"W:\Books\Business, Economics, & Mentorship\()The Myth of the Rational Market - A History of Risk, Reward, and Delusion on Wall Street, Justin Fox, (2009).pdf"
    PdfWriter().write(new_path, pdf_reader)

def get_shows_not_on_drive(drives):
    drives.sort()
    show_drive = 'R'; anime_drive = 'O'; movie_drive = 'G'
    show_names, show_paths = read_alexandria([f'{show_drive}:/Shows/',f'{anime_drive}:/Anime/'])
    shows = list(set([' '.join(f.strip().split()[:-1]) for i,f in enumerate(show_names) if show_paths[i] != f'{movie_drive}:/Movies']))
    drive_file_names = []; drive_file_paths = []
    for d in drives:
        file_names, file_paths = read_alexandria([f'{d}:/Shows/',f'{d}:/Anime/'])
        drive_file_names += file_names
        drive_file_paths += file_paths
    duplicate_items = list(set([' '.join(show.split()[:-1]) for show in [fn for fn in drive_file_names if drive_file_names.count(fn) > 1]]))
    if len(duplicate_items) > 0: print(f'Duplicate saved shows: {", ".join(duplicate_items)}')
    drive_shows = list(set([' '.join(f.strip().split()[:-1]) for i,f in enumerate(drive_file_names) if drive_file_paths[i] != f'{movie_drive}:/Movies']))
    diff_list = sorted(list(set(shows) - set(drive_shows)),key= lambda x: x.lower())
    drive_names = [get_drive_name(drive) for drive in drives]
    with open(f'{os.path.dirname(__file__)}'+f'\\Show Lists\\{"_".join("_".join(drive_names).split())}_missing_shows.txt',mode='w',encoding='utf-8') as whitelist:
        whitelist.seek(0)
        for dl in diff_list:
            whitelist.write(dl+'\n')

# get_shows_not_on_drive(['B','S'])