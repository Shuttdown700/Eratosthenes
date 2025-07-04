#!/usr/bin/env python


def edit_multi_episode_filenames():
    import os, re
    def search_filenames_with_pattern(start_directory):
        file_list = []
        # Define the regular expression pattern to match a number followed by "-" followed by another number
        pattern = re.compile(r'\d+-\d+')
    
        # Walk through the directory tree starting from the specified directory
        for root, dirs, files in os.walk(start_directory):
            for filename in files:
                # Check if the filename matches the pattern and has a ".mp4" or ".mkv" extension
                if pattern.search(filename) and (filename.lower().endswith('.mp4') or filename.lower().endswith('.mkv')):
                    # Print the full path of the matching file
                    file_list.append(os.path.join(root, filename))
        return file_list
    
    # Example usage
    file_list = search_filenames_with_pattern('K:\Shows')
    
    new_files = []
    for file in file_list:
        front = '-'.join(file.split('-')[:-1])
        back = file.split('-')[-1]
        if back[1] == '.': continue
        if back[0].upper() == 'E': continue
        new_file = front+'-E'+back
        new_files.append(new_file)
    
    for index, old_file in enumerate(file_list):
        os.rename(old_file,new_files[index])
        print('Old filename: ',old_file.strip()+'\n','New filename: ',new_files[index]+'\n')


import os

def find_mp4_files(root_dir):
    mp4_files = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for file in filenames:
            if file.lower().endswith('.mp4'):
                full_path = os.path.join(dirpath, file)
                mp4_files.append(full_path)
    return mp4_files

# Example usage:
if __name__ == "__main__":
    search_directory = "A:/Anime"  # Replace with the actual directory path
    mp4_files = find_mp4_files(search_directory)
    for file in mp4_files:
        print(file)

