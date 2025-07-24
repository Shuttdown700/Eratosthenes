#!/usr/bin/env python

import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utilities import get_file_size

def list_mp4_files(mp4_root_dir, output_file):
    # Collect all mp4 files first
    mp4_files = []
    for dirpath, _, filenames in os.walk(mp4_root_dir):
        for filename in filenames:
            if filename.lower().endswith('.mp4'):
                file_path = os.path.join(dirpath, filename)
                file_size_GB = get_file_size(file_path, "GB")
                mp4_files.append((filename, file_size_GB))
    
    # Sort files alphabetically by filename
    mp4_files.sort(key=lambda x: x[0].lower())
    
    # Write sorted files to output
    with open(output_file, 'w', encoding='utf-8') as f:
        for filename, file_size_GB in mp4_files:
            f.write(f"{filename} | {round(file_size_GB, 2)} GB\n")

if __name__ == "__main__":
    # Set the directory where .mp4 files are located
    mp4_root_dir = r"K:\Shows"

    # Build the output file path relative to project root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, '..'))
    output_path = os.path.join(project_root, '..', 'output', 'mp4_shows_KEELI.txt')

    # Make sure the output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    list_mp4_files(mp4_root_dir, output_path)
    print(f"MP4 file list saved to: {output_path}")