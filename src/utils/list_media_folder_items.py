import os
import sys

from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utilities import write_list_to_txt_file

def export_directory_names(source_dir: str, output_filepath: str) -> None:
    """
    Lists all directory names in the source_dir and writes them
    as a space-separated string to the output_filepath.
    """
    source_path = Path(source_dir)
    
    # Ensure the source directory actually exists
    if not source_path.is_dir():
        print(f"Error: The directory '{source_dir}' does not exist.")
        return

    # Iterate through the path and extract names of directories only
    dir_names = [str(item.name) for item in source_path.iterdir() if item.is_dir()]
       
    # Write the space-separated string to the output text file
    write_list_to_txt_file(output_filepath, dir_names, bool_sort=True)

if __name__ == "__main__":
    # --- Configuration ---
    # Replace these strings with your actual paths
    TARGET_DIRECTORY = "E:/Shows" 
    OUTPUT_TEXT_FILE = "C:/Users/brend/Documents/Coding Projects/alexandria_media_manager/config/series_whitelists/active/Echo_whitelist.txt"
    
    export_directory_names(TARGET_DIRECTORY, OUTPUT_TEXT_FILE)