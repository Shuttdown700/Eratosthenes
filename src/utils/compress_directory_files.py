#!/usr/bin/env python

import os
import py7zr
from colorama import Fore, Back, Style

RED = Fore.RED
YELLOW = Fore.YELLOW
GREEN = Fore.GREEN
BLUE = Fore.BLUE
MAGENTA = Fore.MAGENTA
RESET = Style.RESET_ALL
BRIGHT = Style.BRIGHT

def compress_item(item_path, output_dir, delete_original=False):
    # Get the base name without extension for files, or full name for directories
    item_name = os.path.basename(item_path)
    if os.path.isfile(item_path):
        item_name = os.path.splitext(item_name)[0]
    
    # Create output 7z file name
    output_file = os.path.join(output_dir, f"{item_name}.7z")

    try:
        # Create a 7z archive for the item
        with py7zr.SevenZipFile(output_file, 'w') as archive:
            if os.path.isfile(item_path):
                # For files, write directly with the original filename
                print(f"{GREEN}Compressing file{RESET}: {item_path} -> {output_file}")
                archive.write(item_path, os.path.basename(item_path))
                print(f"{GREEN}{BRIGHT}File compressed successfully{RESET}: {output_file}")
            elif os.path.isdir(item_path):
                # For directories, include all contents with relative paths
                print(f"{GREEN}Compressing directory{RESET}: {item_path} -> {output_file}")
                for root, _, files in os.walk(item_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, os.path.dirname(item_path))
                        archive.write(file_path, rel_path)
                print(f"{GREEN}{BRIGHT}Directory compressed successfully{RESET}: {output_file}")
                

        # Delete original item if specified
        if delete_original:
            try:
                if os.path.isfile(item_path):
                    os.remove(item_path)
                    print(f"{RED}Deleted{RESET}: {item_path}")
                elif os.path.isdir(item_path):
                    # Remove directory and its contents
                    for root, dirs, files in os.walk(item_path, topdown=False):
                        for file in files:
                            os.remove(os.path.join(root, file))
                            print(f"{RED}Deleted{RESET}: {os.path.join(root, file)}")
                        for dir in dirs:
                            os.rmdir(os.path.join(root, dir))
                            print(f"{RED}Deleted directory{RESET}: {os.path.join(root, dir)}")
                    os.rmdir(item_path)
                    print(f"{RED}Deleted directory{RESET}: {item_path}")
            except Exception as e:
                print(f"{RED}{BRIGHT}Error deleting{RESET} {item_path}: {e}")

    except Exception as e:
        print(f"{RED}{BRIGHT}Error creating archive{RESET} {output_file}: {e}")

def compress_directory(input_dir, delete_original=False):
    # Ensure the input directory exists
    if not os.path.isdir(input_dir):
        print(f"{RED}{BRIGHT}Error{RESET}: {input_dir} is not a valid directory")
        return

    try:
        # Get immediate files and directories in the input directory
        for item in os.listdir(input_dir):
            item_path = os.path.join(input_dir, item)
            # Skip any .7z files to avoid re-compressing
            if item_path.endswith('.7z'):
                print(f"{YELLOW}Skipping existing archive{RESET}: {item_path}")
                continue
            # Compress files and directories
            if os.path.isfile(item_path) or os.path.isdir(item_path):
                compress_item(item_path, input_dir, delete_original)

        print(f"\n{GREEN}{BRIGHT}All items processed successfully{RESET}")

    except Exception as e:
        print(f"{RED}{BRIGHT}Error processing directory{RESET} {input_dir}: {e}")

def main():
    # Hardcoded inputs
    input_directory = r"W:\Games\FitGirl Repacks"  # Replace with your directory path
    delete_original = True  # Set to True to delete original files after compression
    
    compress_directory(input_directory, delete_original)

if __name__ == "__main__":
    main()