#!/usr/bin/env python

def import_libraries(libraries):
    """
    Helps load/install required libraries when running from cmd prompt

    Parameters
    ----------
    libraries : list
        List of libraries.

    Returns
    -------
    None.

    """
    import subprocess
    import warnings
    warnings.filterwarnings("ignore")
    exec('warnings.filterwarnings("ignore")')
    aliases = {'numpy':'np','pandas':'pd','matplotlib.pyplot':'plt'}
    for s in libraries:
        try:
            exec(f"import {s[0]} as {aliases[s[0]]}") if s[0] in list(aliases.keys()) else exec(f"import {s[0]}")
        except ImportError:
            print(f'Installing... {s[0].split(".")[0]}')
            cmd = f'python -m pip install {s[0].split(".")[0]}'
            subprocess.call(cmd, shell=True, stdout=subprocess.PIPE)
        if len(s) == 1: continue
        for sl in s[1]:
            exec(f'from {s[0]} import {sl}')

def read_alexandria(parent_dirs,extensions = ['.mp4','.mkv','.pdf','.mp3']) -> tuple[list[str], list[str]]:
    """
    Returns all files of a given extension from a list of parent directories

    Parameters
    ----------
    parent_dirs : list
        Parent directories to be searched through.
    extensions : list, optional
        Extensions to search for. The defaults are '.mp4' & '.mkv'.

    Returns
    -------
    all_titles : list
        A list of all filenames, excluding the extension.
    all_paths : list
        A list of all paths to corresponding files.
        
    """
    import os
    if not isinstance(parent_dirs,list) and parent_dirs.count(':') == 1: parent_dirs = [parent_dirs]
    if not isinstance(extensions,list) and extensions.count('.') == 1: extensions = [extensions]
    assert isinstance(parent_dirs,list) and isinstance(extensions,list), "Input directory is not in list format."
    all_titles, all_paths = [], []
    for p in parent_dirs:
        walk = sorted(list([x for x in os.walk(p) if x[2] != []]))
        for w in walk:
            parent_path = w[0]
            if parent_path[-1] == '/' or parent_path[-1] == '\\': parent_path = parent_path[:-1]
            file_list = [f for f in w[-1] if '.'+f.split('.')[-1] in extensions]
            for i,f in enumerate(file_list):
                all_titles.append(f.replace('\\','/'))
                all_paths.append(parent_path.replace('\\','/'))
    return all_titles, all_paths

def read_json(filepath):
    import json
    with open(filepath, 'r') as json_file:
        json_data = json.load(json_file)
    return json_data