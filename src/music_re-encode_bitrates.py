#!/usr/bin/env python3
import os
os.chdir(rf'{os.path.realpath(os.path.dirname(__file__))}')
from main import read_alexandria, import_libraries
from alexandria_utilities import remove_empty_folders
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
###
if __name__ == '__main__':
    drive = 'W'
    parent_dir = f'{drive}:\\Music\\MP3s_320'
    bitrates_desired = [128,196]
    extension_desired = '.mp3'
    for bd in bitrates_desired:
        re_encode_tracks(parent_dir,bitrate_desired=bd,desired_extension=extension_desired)
        copy_images(parent_dir,bd)
    remove_empty_folders('W',['Music'])


'''
DEV notes:
    check to ensure no properties have changed for the music file and if tracks don't exist anymore'

'''