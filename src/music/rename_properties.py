import os
import re
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
    ID3, TIT2, TPE1, TPE2, TALB, TRCK, TYER, TDRC, TCON, COMM, APIC, error
)
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4, MP4Cover
from mutagen.easymp4 import EasyMP4

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utilities import read_alexandria, remove_empty_folders, generate_music_file_print_message

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
                print(f"{GREEN}{BRIGHT}Updated album{RESET} for: {filename}")
            except Exception as e:
                print(f"{RED}{BRIGHT}Failed to update{RESET} {filename}: {e}")

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
                print(f"{GREEN}{BRIGHT}Updated artist and album artist{RESET} for: {filename}")
            except Exception as e:
                print(f"{RED}{BRIGHT}Failed to update{RESET} {filename}: {e}")

def rename_comment(directory, comment_text):
    """
    Update (or remove) the comment metadata for MP3, FLAC, and M4A files.
    - For MP3: uses ID3 COMM frames.
    - For FLAC: writes Vorbis 'comment' as a list of strings.
    - For M4A: writes the MP4 atom '\xa9cmt' (comment) as a list.

    To remove the comment, pass None or an empty string.
    """
    for filename in os.listdir(directory):
        if not filename.lower().endswith(AUDIO_EXTENSIONS):
            continue

        filepath = os.path.join(directory, filename)
        try:
            # MP3 (ID3)
            if filename.lower().endswith('.mp3'):
                audio = MP3(filepath, ID3=ID3)
                # Remove all existing COMM tags
                audio.tags.delall('COMM')
                if comment_text:
                    audio['COMM'] = COMM(encoding=3, lang='eng', desc='', text=comment_text)
                audio.save()

            # FLAC (Vorbis comments)
            elif filename.lower().endswith('.flac'):
                audio = FLAC(filepath)
                # Remove existing comment tags (various possible keys)
                for key in ('comment', 'COMMENT'):
                    if key in audio:
                        del audio[key]
                if comment_text:
                    # Vorbis comments expect a list of strings
                    audio['comment'] = [comment_text]
                audio.save()

            # M4A / MP4 (EasyMP4)
            elif filename.lower().endswith('.m4a'):
                audio = EasyMP4(filepath)
                # MP4 comment atom is '\xa9cmt' (and mutagen expects a list)
                if '\xa9cmt' in audio:
                    del audio['\xa9cmt']
                if comment_text:
                    audio['\xa9cmt'] = [comment_text]
                audio.save()

            action = "Removed" if not comment_text else "Updated"
            print(f"{action} comment for: {filename}")

        except Exception as e:
            print(f"{RED}{BRIGHT}Failed to update comment{RESET} for {filename}: {e}")

def rename_year_and_date(directory, year_text):
    """
    Updates or removes the 'year' and 'date released' tags for all supported audio files in a directory.

    Args:
        directory (str): Directory containing the audio files.
        year_text (str | None): The new year/date string (e.g. '2025' or '2025-10-26'),
                                or None/empty string to remove both tags.
    """
    for filename in os.listdir(directory):
        if filename.lower().endswith(AUDIO_EXTENSIONS):
            filepath = os.path.join(directory, filename)
            try:
                # --- MP3 FILES ---
                if filename.lower().endswith('.mp3'):
                    audio = MP3(filepath, ID3=ID3)

                    # Remove all existing year/date tags
                    audio.tags.delall('TYER')
                    audio.tags.delall('TDRC')
                    audio.tags.delall('TDAT')

                    # Add new year/date if provided
                    if year_text:
                        # TDRC is the preferred modern ID3v2.4 frame for date released
                        audio['TDRC'] = TDRC(encoding=3, text=year_text)
                        # Optionally include TYER for older tag readers
                        audio['TYER'] = TYER(encoding=3, text=year_text)

                    audio.save()

                # --- FLAC FILES ---
                elif filename.lower().endswith('.flac'):
                    audio = FLAC(filepath)
                    # Remove both 'date' and 'year' tags if they exist
                    for tag in ('date', 'year', 'originaldate', 'originalyear'):
                        if tag in audio:
                            del audio[tag]
                    if year_text:
                        audio['date'] = [year_text]
                        audio['year'] = [year_text]
                    audio.save()

                # --- M4A FILES ---
                elif filename.lower().endswith('.m4a'):
                    audio = EasyMP4(filepath)
                    for tag in ('date', 'year'):
                        if tag in audio:
                            del audio[tag]
                    if year_text:
                        audio['date'] = [year_text]
                        audio['year'] = [year_text]
                    audio.save()

                action = "Removed" if not year_text else "Updated"
                print(f"{action} year/date for: {filename}")

            except Exception as e:
                print(f"{RED}{BRIGHT}Failed to update year/date{RESET} for {filename}: {e}")

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
        print(f"{RED}{BRIGHT}Directory does not exist{RESET}: {album_directory}")
        return

    audio_files = sorted([
        f for f in os.listdir(album_directory)
        if f.lower().endswith(AUDIO_EXTENSIONS)
    ])

    if not audio_files:
        print(f"{YELLOW}No audio files found{RESET} in: {album_directory}")
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

                print(f"{GREEN}{BRIGHT}Tagged:{RESET} {filename} -> Track {index}")
            except Exception as e:
                print(f"{RED}{BRIGHT}Error tagging{RESET} {filename}: {e}")
            bar()

def set_year_from_folder(directory, bypass_dirs=[r"W:\Music\MP3s_320\_Playlists"]):
    """
    Walk through a music directory and set 'year' and 'release date' tags
    for MP3/FLAC files based on the parent folder name (e.g. '(2015) The Living Room').

    - Skips files whose year already matches the folder year.
    - Skips any directory listed in `bypass_dirs` (by full or partial path match).
    """

    if bypass_dirs is None:
        bypass_dirs = []

    # Normalize bypass directories to lowercase absolute paths for comparison
    bypass_dirs = [os.path.abspath(d).lower() for d in bypass_dirs]

    year_pattern = re.compile(r'\((\d{4})\)')
    updated = 0
    skipped = 0
    failed = 0
    bypassed = 0

    for root, _, files in os.walk(directory):
        abs_root = os.path.abspath(root).lower()

        # Skip any folder in the bypass list (or subfolder of one)
        if any(abs_root.startswith(b) for b in bypass_dirs):
            print(f"{YELLOW}Bypassed directory:{RESET} {root}")
            bypassed += 1
            continue

        # Try to extract (YYYY) pattern from the folder name
        match = year_pattern.search(os.path.basename(root))
        if not match:
            continue

        year = match.group(1)

        for filename in files:
            if not filename.lower().endswith(AUDIO_EXTENSIONS):
                continue

            filepath = os.path.join(root, filename)
            try:
                already_correct = False

                # --- MP3 FILES ---
                if filename.lower().endswith('.mp3'):
                    audio = MP3(filepath, ID3=ID3)
                    existing_years = []
                    if 'TDRC' in audio.tags:
                        existing_years.append(str(audio['TDRC']))
                    if 'TYER' in audio.tags:
                        existing_years.append(str(audio['TYER']))

                    if any(year in y for y in existing_years):
                        already_correct = True
                    else:
                        audio.tags.delall('TYER')
                        audio.tags.delall('TDRC')
                        audio['TYER'] = TYER(encoding=3, text=year)
                        audio['TDRC'] = TDRC(encoding=3, text=year)
                        audio.save()

                # --- FLAC FILES ---
                elif filename.lower().endswith('.flac'):
                    audio = FLAC(filepath)
                    existing_years = []
                    for tag in ('date', 'year'):
                        if tag in audio:
                            existing_years += audio[tag]

                    if any(year in y for y in existing_years):
                        already_correct = True
                    else:
                        for tag in ('date', 'year', 'originaldate', 'originalyear'):
                            if tag in audio:
                                del audio[tag]
                        audio['date'] = [year]
                        audio['year'] = [year]
                        audio.save()

                if already_correct:
                    print(f"{YELLOW}Skipped{RESET} (already {year}): {generate_music_file_print_message(filepath)}")
                    skipped += 1
                else:
                    print(f"{GREEN}Updated{RESET} year/date to {YELLOW}{year}{RESET} for: {generate_music_file_print_message(filepath)}")
                    updated += 1

            except Exception as e:
                print(f"{RED}{BRIGHT}Failed{RESET} to update year/date for {filepath}: {e}")
                failed += 1

    print("\n" + "-"*60)
    print(f"{GREEN}Updated:{RESET} {updated}")
    print(f"{YELLOW}Skipped (already correct):{RESET} {skipped}")
    print(f"{YELLOW}Bypassed directories:{RESET} {bypassed}")
    print(f"{RED}Failed:{RESET} {failed}")
    print("-"*60)

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
                        print(f'{GREEN}{BRIGHT}Renaming {RESET}"{title}" -> "{new_title}" in: {filename}')
                        audio["title"] = new_title
                        audio.save()
                    else:
                        print(f'{YELLOW}No change needed{RESET} for: {filename}')
                else:
                    print(f"{YELLOW}No title tag found{RESET} in: {filename}")
            except Exception as e:
                print(f"{RED}{BRIGHT}Error processing{RESET} {filename}: {e}")

def update_flac_titles_from_filename(directory):
    """
    Update the TITLE tag in FLAC files by extracting text after the first XX-XX pattern.
    Works for filenames like:
    'Avenged Sevenfold - Waking The Fallen_ Resurrected - 01-15 Chapter Four.flac'
    """
    # Regex to find the first occurrence of XX-XX followed by optional spaces
    track_pattern = re.compile(r"\d{1,2}-\d{1,2}\s+(.*)\.flac$", re.IGNORECASE)

    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(".flac"):
                match = track_pattern.search(file)
                if not match:
                    print(f"{YELLOW}{BRIGHT}Skipping{RESET} {file}, does not match expected pattern")
                    continue

                track_title = match.group(1).strip()

                filepath = os.path.join(root, file)
                audio = FLAC(filepath)
                audio["TITLE"] = track_title
                audio.save()

                print(f"{GREEN}{BRIGHT}Updated{RESET}: {file} -> Title: {track_title}")

def search_for_missing_properties(root_dir):
    pass

if __name__ == "__main__":
    # Example usage:
    dir_root_FLAC = r'W:\Music\FLAC'
    dir_root_mp3320 = r'W:\Music\MP3s_320'
    dir_temp_essential_albums = r'W:\Temp\Download Zone\Essentials'
    dir_temp_playlist_albums = r'W:\Temp\Download Zone\Playlists'
    dir_temp_OSTs = r'W:\Temp\Download Zone\OSTs'
    dir_temp = r'W:\Music\Temp\Download Zone'
    dir_custom = r"W:\Music\MP3s_320\Eminem\(2004) Encore"
    dir_custom2 = r"W:\Music\FLAC\Eminem\(2004) Encore"

    # rename_essentials_albums(dir_temp_essential_albums)
    # rename_playlist_albums(dir_temp_playlist_albums)
    # rename_OTSs(dir_temp_OSTs)  
    
    # rename_album(dir_custom, "LIFE")
    rename_artist(dir_custom, 'Eminem')
    rename_artist(dir_custom2, 'Eminem')
    # rename_comment(dir_custom, '')
    # set_year_from_folder(dir_custom)
    # set_track_numbers(dir_custom)

    # rename_year_and_date(dir_custom, '2015')
    # clean_flac_titles(dir_custom)
    # update_flac_titles_from_filename(dir_custom)
    
