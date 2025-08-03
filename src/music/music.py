import os
import io
import json
import subprocess
import shutil

from PIL import Image
from alive_progress import alive_bar
from colorama import Fore, Style
from mutagen import File
from mutagen.flac import FLAC, Picture
from mutagen.id3 import (
    ID3, TIT2, TPE1, TPE2, TALB, TRCK, TCON, COMM, APIC, error
)
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4, MP4Cover
from mutagen.easymp4 import EasyMP4

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utilities import read_alexandria, remove_empty_folders

# Define terminal color shortcuts
RED = Fore.RED
YELLOW = Fore.YELLOW
GREEN = Fore.GREEN
BLUE = Fore.BLUE
MAGENTA = Fore.MAGENTA
RESET = Style.RESET_ALL
BRIGHT = Style.BRIGHT

# Supported file extensions
IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png')
AUDIO_EXTENSIONS = ('.mp3', '.flac', '.m4a')

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

def rename_album(directory, name):
    for filename in os.listdir(directory):
        if filename.lower().endswith(AUDIO_EXTENSIONS):
            filepath = os.path.join(directory, filename)
            try:
                if filename.lower().endswith('.mp3'):
                    audio = MP3(filepath, ID3=ID3)
                    audio['TALB'] = TALB(encoding=3, text=name)
                    audio.save()
                elif filename.lower().endswith('.flac'):
                    audio = FLAC(filepath)
                    audio['album'] = name
                    audio.save()
                elif filename.lower().endswith('.m4a'):
                    audio = EasyMP4(filepath)
                    audio['album'] = name
                    audio.save()
                print(f"Updated album for: {filename}")
            except Exception as e:
                print(f"Failed to update {filename}: {e}")

def rename_artist(directory, artist_name):
    for filename in os.listdir(directory):
        if filename.lower().endswith(AUDIO_EXTENSIONS):
            filepath = os.path.join(directory, filename)
            try:
                if filename.lower().endswith('.mp3'):
                    audio = MP3(filepath, ID3=ID3)
                    audio['TPE1'] = TPE1(encoding=3, text=artist_name)  # Track artist
                    audio['TPE2'] = TPE2(encoding=3, text=artist_name)  # Album artist
                    audio.save()
                elif filename.lower().endswith('.flac'):
                    audio = FLAC(filepath)
                    audio['artist'] = artist_name
                    audio['albumartist'] = artist_name
                    audio.save()
                elif filename.lower().endswith('.m4a'):
                    audio = EasyMP4(filepath)
                    audio['artist'] = artist_name
                    audio['albumartist'] = artist_name
                    audio.save()
                print(f"Updated artist and album artist for: {filename}")
            except Exception as e:
                print(f"Failed to update {filename}: {e}")

def rename_comment(directory, comment_text):
    for filename in os.listdir(directory):
        if filename.lower().endswith(AUDIO_EXTENSIONS):
            filepath = os.path.join(directory, filename)
            try:
                if filename.lower().endswith('.mp3'):
                    audio = MP3(filepath, ID3=ID3)
                    # Remove all existing COMM tags
                    audio.tags.delall('COMM')
                    if comment_text:
                        audio['COMM'] = COMM(encoding=3, lang='eng', desc='', text=comment_text)
                    audio.save()

                elif filename.lower().endswith('.flac'):
                    audio = FLAC(filepath)
                    if 'comment' in audio:
                        del audio['comment']
                    if comment_text:
                        audio['comment'] = comment_text
                    audio.save()

                elif filename.lower().endswith('.m4a'):
                    audio = EasyMP4(filepath)
                    if 'comment' in audio:
                        del audio['comment']
                    if comment_text:
                        audio['comment'] = comment_text
                    audio.save()

                action = "Removed" if not comment_text else "Updated"
                print(f"{action} comment for: {filename}")

            except Exception as e:
                print(f"Failed to update {filename}: {e}")

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

def set_track_numbers(album_directory: str) -> None:
    """
    Set track numbers in metadata for audio files in an album folder.
    Files are sorted by filename and tagged sequentially.

    Parameters
    ----------
    album_directory : str
        Path to the folder containing album audio files.
    """
    AUDIO_EXTENSIONS = ('.mp3', '.flac', '.m4a')

    if not os.path.isdir(album_directory):
        print(f"{Fore.RED}Directory does not exist: {album_directory}{Style.RESET_ALL}")
        return

    audio_files = sorted([
        f for f in os.listdir(album_directory)
        if f.lower().endswith(AUDIO_EXTENSIONS)
    ])

    if not audio_files:
        print(f"{Fore.YELLOW}No audio files found in: {album_directory}{Style.RESET_ALL}")
        return

    with alive_bar(len(audio_files), title="Tagging track numbers") as bar:
        for index, filename in enumerate(audio_files, start=1):
            filepath = os.path.join(album_directory, filename)
            ext = os.path.splitext(filename)[1].lower()

            try:
                if ext == '.mp3':
                    audio = MP3(filepath, ID3=ID3)
                    if audio.tags is None:
                        audio.add_tags()
                    audio.tags.add(TRCK(encoding=3, text=str(index)))
                    audio.save()
                elif ext == '.flac':
                    audio = FLAC(filepath)
                    audio['tracknumber'] = str(index)
                    audio.save()
                elif ext == '.m4a':
                    audio = MP4(filepath)
                    audio['trkn'] = [(index, 0)]  # (track number, total optional)
                    audio.save()

                print(f"{Fore.GREEN}Tagged:{Style.RESET_ALL} {filename} -> Track {index}")
            except Exception as e:
                print(f"{Fore.RED}Error tagging {filename}:{Style.RESET_ALL} {e}")
            bar()

def clean_flac_titles(directory):
    for filename in os.listdir(directory):
        if filename.lower().endswith('.flac'):
            filepath = os.path.join(directory, filename)
            try:
                audio = FLAC(filepath)
                title = audio.get("title", [None])[0]
                if title:
                    new_title = title.split('(')[0].strip()
                    if new_title != title:
                        print(f'Renaming "{title}" -> "{new_title}" in: {filename}')
                        audio["title"] = new_title
                        audio.save()
                    else:
                        print(f'No change needed for: {filename}')
                else:
                    print(f"No title tag found in: {filename}")
            except Exception as e:
                print(f"Error processing {filename}: {e}")

    # # Rename essentials albums:
    # dir_temp_essential_albums = 'W:/Temp/MP3s_320_Essentials/'
    # rename_essentials_albums(dir_temp_essential_albums)

# # Identify popular artists without albums:
# dir_identify_popular_artists = 'W:/Music/MP3s_320/'
# identify_popular_artists_without_albums(dir_identify_popular_artists)

# # Rename playlist albums:
# dir_music_playlists = 'W:/Temp/MP3_320_Playlist_Albums'
# rename_playlist_albums(dir_music_playlists)

# # Rename OSTs:
# dir_ost = 'W:/Temp/OSTs/Star Wars OST/'
# rename_OTSs(dir_ost)

# # Rename specific album:
# directory = r'A:\Audiobooks\The Holy Bible - New Testament (KJV)'
# name = 'The Holy Bible: New Testament (KJV)'
# rename_album(directory, name)

# # Rename artist:
# directory = r'C:\Users\brend\Downloads\ENGKJVO1DA\English_eng_KJV_OT_Non-Drama'
# artist_name = 'Faith Comes By Hearing'
# rename_artist(directory, artist_name)

# # Rename comment:
# directory = r'C:\Users\brend\Downloads\ENGKJVO1DA\English_eng_KJV_OT_Non-Drama'
# comment_text = ''
# rename_comment(directory, comment_text)

# Set Track Numbers Metadata:
directory = r"W:\Temp\Download Zone\John Williams\Star Wars - The Phantom Menance"
set_track_numbers(directory)

# Clean FLAC titles:
# directory = r"W:\Temp\Download Zone\(2020) TRON Legacy - The Complete Edition"
clean_flac_titles(directory)