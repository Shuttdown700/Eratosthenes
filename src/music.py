# -*- coding: utf-8 -*-
"""
Created on Sun Aug  4 17:41:39 2024

@author: brend
"""

import json, os
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TPE2, TALB, TRCK, TCON
from alive_progress import alive_bar
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from utilities import read_alexandria

def identify_popular_artists_without_albums(music_dir):
    files, paths = read_alexandria([music_dir],extensions=['.mp3'])
    artists_with_albums = []
    for path in paths:
        path_split = path.split('/')
        if len(path_split) == 4:
            continue
        if len(path_split) > 4:
            album_artist = path_split[3]
            artists_with_albums.append(album_artist.lower())
    
    artists_with_albums = list(set(artists_with_albums))
    
    artists_without_albums = {}
    with alive_bar(len(files),ctrl_c=False,dual_line=True,title='Progress',bar='classic',spinner='classic') as bar:
        for index,file in enumerate(files):
            filename = file.strip()
            path = paths[index]
            filepath = f'{path}/{filename}'
            audiofile = MP3(filepath)
            title = str(audiofile.get('TIT2','Unknown'))
            artist = str(audiofile.get('TPE1','Unknown'))
            album = str(audiofile.get('TALB','Unknown'))
            duration = audiofile.info.length
            bps = audiofile.info.bitrate_mode
            sample_rate_hz = audiofile.info.sample_rate
            channels = audiofile.info.channels
            if artist.lower() not in artists_with_albums:
                try:
                    artists_without_albums[artist] += 1
                except KeyError:
                    artists_without_albums.update({artist:1})
            bar()
    
    artists_without_albums = dict(sorted(artists_without_albums.items(),key=lambda x: x[1],reverse=True))
    with open('music_artists_without_albums.json','w') as json_file:
        json.dump(artists_without_albums,json_file,indent=4)

def rename_essentials_albums(music_dir):
    buzzword_list = ['essentials','greatest songs','greatest hits']
    filepaths = read_alexandria([music_dir],extensions=['.mp3'])
    with alive_bar(len(filepaths),ctrl_c=False,dual_line=True,title='Progress',bar='classic',spinner='classic') as bar:
        for index,filepath in enumerate(filepaths):
            artist_from_path = filepath.split('/')[3]
            # album_from_path = ')'.join(path.split('/')[4].split(')')[1:]).strip()
            audiofile = MP3(filepath)
            # title = str(audiofile.get('TIT2','Unknown'))
            artist = str(audiofile.get('TPE1','Unknown'))
            album_artist = str(audiofile.get('TPE2','Unknown'))
            album = str(audiofile.get('TALB','Unknown'))
            # Load the existing ID3 tags or create a new one if not present
            tags = ID3(filepath)
            # Set or update properties
            updates_bool = False
            if album.lower() in buzzword_list and artist.lower() not in album.lower():
                new_album = artist_from_path+' '+album.strip()
                tags['TALB'] = TALB(encoding=3, text=new_album)
                updates_bool = True
            if artist.lower() != artist_from_path.lower() or album_artist.lower() != artist_from_path.lower():
                tags['TPE1'] = TPE1(encoding=3, text=artist_from_path)
                tags['TPE2'] = TPE2(encoding=3, text=artist_from_path)
                updates_bool = True
    
            # Save changes to the file
            if updates_bool: tags.save()
            bar()

def rename_playlist_albums(music_playlist_dir):
    files, paths = read_alexandria([music_playlist_dir],extensions=['.mp3'])
    with alive_bar(len(files),ctrl_c=False,dual_line=True,title='Progress',bar='classic',spinner='classic') as bar:
        for index,path in enumerate(paths):
            album_from_path = path.split('/')[3].strip()
            filepath = path+'/'+files[index]
            audiofile = MP3(filepath)
            # title = str(audiofile.get('TIT2','Unknown'))
            # artist = str(audiofile.get('TPE1','Unknown'))
            album_artist = str(audiofile.get('TPE2','Unknown'))
            album = str(audiofile.get('TALB','Unknown'))
            # Load the existing ID3 tags or create a new one if not present
            tags = ID3(filepath)
            # Set or update properties
            updates_bool = False
            if album_from_path != album:
                tags['TALB'] = TALB(encoding=3, text=album_from_path)
                updates_bool = True
            fixed_album_artist = 'Various Artists'
            if fixed_album_artist != album_artist:
                tags['TPE2'] = TPE2(encoding=3, text=fixed_album_artist)
                updates_bool = True
    
            # Save changes to the file
            if updates_bool: tags.save()
            bar()

def rename_OTSs(ost_soundtrack):
    from mutagen.mp3 import MP3  
    from mutagen.easyid3 import EasyID3  
    from mutagen.id3 import ID3, TIT2, TIT3, TALB, TPE1, TRCK, TYER  
    filepaths = sorted(read_alexandria([ost_soundtrack],extensions=['.mp3']))
    num_track = 1
    with alive_bar(len(filepaths),ctrl_c=False,dual_line=True,title='Progress',bar='classic',spinner='classic') as bar:
        for index,filepath in enumerate(filepaths):
            album_from_path = filepath.split('/')[3].strip()
            name = filepath.split('/')[-1].split('.')[-2].strip()
            mp3file = MP3(filepath, ID3=EasyID3)
            mp3file['title'] = [name]
            mp3file['album'] = [album_from_path]
            mp3file['artist'] = ['John Williams']
            mp3file['albumartist'] = ['John Williams']  
            mp3file['tracknumber'] = str(num_track)
            mp3file.save() 
            num_track += 1
            bar()

def encode_multiple_bitrates():
    import os
    os.chdir(rf'{os.path.realpath(os.path.dirname(__file__))}')
    from main import read_alexandria, import_libraries
    from utilities import remove_empty_folders
    libraries = [['os'],['subprocess']]
    import_libraries(libraries)
    import subprocess
    os.chdir(rf'{os.path.realpath(os.path.dirname(__file__))}')

    def check_directory(file_out):
        path = '/'.join(file_out.split('/')[:-1])
        if not os.path.exists(path):
            os.makedirs(path)

    def re_encode_tracks(parent_dir,bitrate_desired=128,desired_extension='.mp3'):
        all_titles, all_paths = read_alexandria([parent_dir],['.mp3','.flac','.m4a'])
        for i,at in enumerate(all_titles):
            file_in = all_paths[i]+'/'+at
            file_out = ('/').join([f'{parent_dir[0]}:',parent_dir.split('\\')[1],f'MP3s_{bitrate_desired}'] + file_in.split("/")[3:-1] + ['.'.join(file_in.split("/")[-1].split('.')[:-1])+'.mp3'])
            if os.path.isfile(file_out): continue
            os.path.isfile(file_out)
            check_directory(file_out)
            print(f'Re-encoding to: {file_out}')
            cmd = f'ffmpeg -i "{file_in}" -ab {bitrate_desired}k -map_metadata 0 -id3v2_version 3 "{file_out}"'
            subprocess.run(cmd, shell=True, stdout=subprocess.PIPE)

    def copy_images(parent_dir,bitrate_desired):
        all_titles, all_paths = read_alexandria([parent_dir],['.jpeg','.png','.jpg'])
        for i,at in enumerate(all_titles):
            file_in = all_paths[i]+'/'+at
            file_out = ('/').join([f'{parent_dir[0]}:','Music',f'MP3s_{bitrate_desired}'] + file_in.split("/")[3:])
            if os.path.isfile(file_out): continue
            cmd = fr'copy "{file_in}" "{file_out}/"'.replace('/','\\')
            subprocess.run(cmd, shell=True, stdout=subprocess.PIPE)
    drive = 'W'
    parent_dir = f'{drive}:\\Music\\MP3s_320'
    bitrates_desired = [128,196]
    extension_desired = '.mp3'
    for bd in bitrates_desired:
        re_encode_tracks(parent_dir,bitrate_desired=bd,desired_extension=extension_desired)
        copy_images(parent_dir,bd)
    remove_empty_folders('W',['Music'])    

music_temp_dir = 'W:/Temp/MP3s_320_Essentials/'
rename_essentials_albums(music_temp_dir)
# music_320_dir = 'W:/Music/MP3s_320/'
# identify_popular_artists_without_albums(music_320_dir)
# music_playlist_dir = 'W:/Temp/MP3_320_Playlist_Albums'
# rename_playlist_albums(music_playlist_dir)
# ost_soundtrack = 'W:/Temp/OSTs/Star Wars OST/'
# rename_OTSs(ost_soundtrack)


"""
dev notes 

"""










