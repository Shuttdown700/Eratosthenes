# -*- coding: utf-8 -*-
"""
Created on Sun Aug  4 17:41:39 2024

@author: brend
"""

import json, os
from mutagen import File
from mutagen.flac import FLAC, Picture
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TPE2, TALB, TRCK, TCON, APIC, error
from mutagen.mp4 import MP4, MP4Cover
from mutagen.easymp4 import EasyMP4
from PIL import Image
import io
import time
from alive_progress import alive_bar
from mimetypes import guess_type
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from utilities import read_alexandria

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
                    audio['TPE1'] = TPE1(encoding=3, text=artist_name)
                    audio.save()
                elif filename.lower().endswith('.flac'):
                    audio = FLAC(filepath)
                    audio['artist'] = artist_name
                    audio.save()
                elif filename.lower().endswith('.m4a'):
                    audio = EasyMP4(filepath)
                    audio['artist'] = artist_name
                    audio.save()
                print(f"Updated artist for: {filename}")
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

def encode_multiple_bitrates(parent_dir = 'W:\\Music\\MP3s_320', 
                             bitrates_desired = [128,196]):
    import os
    os.chdir(rf'{os.path.realpath(os.path.dirname(__file__))}')
    from utilities import read_alexandria, import_libraries
    from utilities import remove_empty_folders
    libraries = [['os'],['subprocess']]
    import_libraries(libraries)
    import subprocess, shutil
    os.chdir(os.path.join(os.path.realpath(os.path.dirname(__file__)),"bin"))

    def check_directory(file_out):
        path = os.path.dirname(file_out)
        if not os.path.exists(path):
            os.makedirs(path)

    def safe_output_path(parent_dir, bitrate_desired):
        drive = os.path.splitdrive(parent_dir)[0]
        path_parts = parent_dir.split(os.sep)

        # Only use elements from index 3 onward if they exist
        safe_tail = path_parts[3:] if len(path_parts) > 3 else []

        output_base = os.path.join(drive + os.sep, "Music", f'MP3s_{bitrate_desired}', *safe_tail)
        return output_base

    def re_encode_tracks(parent_dir, bitrate_desired=128, desired_extension='.mp3'):
        filepaths = read_alexandria([parent_dir], ['.mp3', '.flac', '.m4a'])
        output_base = safe_output_path(parent_dir, bitrate_desired)

        for file_in in filepaths:
            # Recreate relative path inside output directory
            rel_path = os.path.relpath(file_in, start=parent_dir)
            rel_path_no_ext = os.path.splitext(rel_path)[0]
            file_out = os.path.join(output_base, rel_path_no_ext + desired_extension)

            if os.path.isfile(file_out):
                continue

            check_directory(file_out)  # Ensure destination dir exists

            print(f'Re-encoding to: {file_out}')
            cmd = [
                'ffmpeg',
                '-i', file_in,
                '-ab', f'{bitrate_desired}k',
                '-map_metadata', '0',
                '-id3v2_version', '3',
                file_out
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def copy_images(parent_dir, bitrate_desired):
        filepaths = read_alexandria([parent_dir], ['.jpeg', '.png', '.jpg'])

        output_base = safe_output_path(parent_dir, bitrate_desired)

        for file_in in filepaths:
            rel_path = os.path.relpath(file_in, start=parent_dir)
            file_out = os.path.join(output_base, rel_path)

            if os.path.isfile(file_out):
                continue

            check_directory(file_out)
            print(f'Copying image to: {file_out}')
            shutil.copy2(file_in, file_out)
    
    extension_desired = '.mp3'
    for bd in bitrates_desired:
        re_encode_tracks(parent_dir,bitrate_desired=bd,desired_extension=extension_desired)
        copy_images(parent_dir,bd)
    remove_empty_folders([parent_dir])

def embed_album_covers(base_directory):
    def find_image_in_dir(directory):
        candidate = None
        for filename in os.listdir(directory):
            if filename.lower().endswith(IMAGE_EXTENSIONS):
                if "back" in filename and candidate != None: continue
                candidate = os.path.join(directory, filename)
                if "cover" in filename: 
                    return os.path.join(directory, filename)
        return candidate

    def convert_image_to_jpeg(image_path):
        img = Image.open(image_path).convert('RGB')
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='JPEG')
        return img_buffer.getvalue(), 'image/jpeg'

    def has_embedded_image(audio):
        if isinstance(audio, MP3):
            return any(key.startswith("APIC") for key in audio.tags.keys())
        elif isinstance(audio, FLAC):
            return len(audio.pictures) > 0
        elif isinstance(audio, MP4):
            return 'covr' in audio
        return False

    def embed_image(mp3_path, image_path):
        try:
            audio = File(mp3_path, easy=False)
            if audio is None:
                print(f"❌ Unsupported file: {mp3_path}")
                return

            if has_embedded_image(audio):
                print(f"⏭️  Skipping (already has cover): {mp3_path}")
                return

            image_data, mime_type = convert_image_to_jpeg(image_path)

            if isinstance(audio, MP3):
                audio = MP3(mp3_path, ID3=ID3)
                try:
                    audio.add_tags()
                except error:
                    pass  # tags already exist
                # Remove any existing cover images
                audio.tags.delall("APIC")

                # Add new cover
                audio.tags.add(APIC(
                    encoding=3,
                    mime=mime_type,
                    type=3,
                    desc='Cover',
                    data=image_data
                ))
                audio.save(v2_version=3)

            elif isinstance(audio, FLAC):
                picture = Picture()
                picture.data = image_data
                picture.type = 3  # Cover (front)
                picture.mime = mime_type
                picture.desc = "Cover"
                picture.width = picture.height = 0  # optional
                audio.add_picture(picture)
                audio.save()

            elif isinstance(audio, MP4):
                audio['covr'] = [MP4Cover(image_data, imageformat=MP4Cover.FORMAT_JPEG)]
                audio.save()

            print(f"✅ Embedded cover into: {mp3_path}")
        except Exception as e:
            print(f"❌ Failed to embed cover into: {mp3_path} ({e})")

    if not os.path.isdir(base_directory):
        print("Invalid base directory.")
        return

    for dirpath, _, filenames in os.walk(base_directory):
        audio_files = [f for f in filenames if f.lower().endswith(AUDIO_EXTENSIONS)]
        if not audio_files:
            continue

        image_path = find_image_in_dir(dirpath)
        if not image_path:
            print(f"❌ No image found in {dirpath}")
            continue

        for audio_file in audio_files:
            file_path = os.path.join(dirpath, audio_file)
            embed_image(file_path, image_path)
            # time.sleep(0.2)

# # Embed album covers in the specified directory:
# dir_embed_album_covers = r"W:\Music\MP3s_320\BØRNS\(2015) Dopamine"
# embed_album_covers(dir_embed_album_covers)

# # Rename essentials albums:
# dir_temp_essential_albums = 'W:/Temp/MP3s_320_Essentials/'
# rename_essentials_albums(dir_temp_essential_albums)

# # Encode multiple bitrates for MP3s:
# dir_base_encode_source = r'W:\Music\MP3s_320\Childish Gambino'
# encode_multiple_bitrates(dir_base_encode_source, bitrates_desired = [196])

# # Identify popular artists without albums:
# dir_identify_popular_artists = 'W:/Music/MP3s_320/'
# identify_popular_artists_without_albums(dir_identify_popular_artists)

# # Rename playlist albums:
# dir_music_playlists = 'W:/Temp/MP3_320_Playlist_Albums'
# rename_playlist_albums(dir_music_playlists)

# # Rename OSTs:
# dir_ost = 'W:/Temp/OSTs/Star Wars OST/'
# rename_OTSs(dir_ost)

# Rename specific album:
directory = r'A:\Temp\Audiobooks\ENGESVO1DA\English_eng_ESV_OT_Non-Drama'
name = 'Holy Bible: Old Testament (ESV)'
rename_album(directory, name)

# Rename specific album:
directory = r'A:\Temp\Audiobooks\ENGESVO1DA\English_eng_ESV_OT_Non-Drama'
artist_name = 'Crossway'
rename_artist(directory, artist_name)