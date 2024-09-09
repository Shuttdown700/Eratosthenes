# -*- coding: utf-8 -*-
"""
Created on Sun Aug  4 17:41:39 2024

@author: brend
"""

import os, subprocess
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from main import read_alexandria

yt_temp_dir = 'A:/temp/YouTube/'
yt_primary_dir = 'A:/'

files, paths = read_alexandria([yt_temp_dir],extensions=['.mp4'])
temp_dirs = list(set(paths))
for index,file in enumerate(files):
    filename = file.strip()
    path = paths[index]
    sub_directory = '/'.join(path.split('/')[2:])
    if "preview" in filename.lower() or "#" not in filename:
        continue
    num = str(filename.split('#')[-1].split('.')[0])
    name = "#".join(filename.split('#')[:-1]).replace('：'," -").strip()
    if len(num) == 1: num = '0'+num
    filename_new = f'{num}. {name}.mp4'
    path_src = f'{path}/{filename}'
    path_dest = f'{yt_primary_dir}{sub_directory}/{filename_new}'
    if os.path.exists(path_dest): continue
    cmd = fr'copy "{path_src}" "{path_dest}"'.replace('/','\\')
    if not os.path.exists(f'{yt_primary_dir}{sub_directory}'): os.makedirs(f'{yt_primary_dir}{sub_directory}')
    subprocess.call(cmd, shell=True, stdout=subprocess.PIPE)
    
    
    
    
                         