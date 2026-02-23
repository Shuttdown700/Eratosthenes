import os
import re

# --- Configuration Values ---
RELATIVE_PATH = "../../output"
FILE_PREFIX = "bypassed_"
FILE_EXTENSION = ".txt"
REMOVE_DUPLICATES = True  # Set to False to keep duplicates
# ----------------------------

def get_year_from_line(line):
    """
    Extracts the year from a string formatted like 'Name (YYYY)'.
    Returns the year as an integer, or 0 if no year is found.
    """
    # Regex to find 4 digits inside parentheses
    match = re.search(r'\((\d{4})\)', line)
    if match:
        return int(match.group(1))
    return 0

def process_directory():
    # Determine the absolute path based on where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    target_directory = os.path.normpath(os.path.join(script_dir, RELATIVE_PATH))

    if not os.path.exists(target_directory):
        print(f"Error: Directory does not exist -> {target_directory}")
        return

    print(f"Scanning directory: {target_directory} ...\n")

    # Recursive search
    files_found = 0
    for root, dirs, files in os.walk(target_directory):
        for filename in files:
            if filename.startswith(FILE_PREFIX) and filename.endswith(FILE_EXTENSION):
                file_path = os.path.join(root, filename)
                sort_and_save_file(file_path)
                files_found += 1
    
    if files_found == 0:
        print("No matching files found.")
    else:
        print(f"\nProcessing complete. Updated {files_found} files.")

def sort_and_save_file(filepath):
    print(f"Processing: {filepath}")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"  [Error] Could not read file: {e}")
        return

    clean_lines = []
    seen_content = set()

    for line in lines:
        stripped_line = line.strip()
        if not stripped_line:
            continue # Skip empty lines

        # Duplicate detection logic
        if REMOVE_DUPLICATES:
            if stripped_line in seen_content:
                print(f"  [Duplicate Removed] {stripped_line}")
                continue
            seen_content.add(stripped_line)
        
        clean_lines.append(stripped_line)

    def get_sort_key(line):
        """
        Returns a tuple (year, name) for sorting.
        Example: 'Stargate Origins (2018)' -> (2018, 'Stargate Origins')
        """
        # Regex to find 4 digits inside parentheses
        match = re.search(r'(.+?)\s*\((\d{4})\)', line)
        if match:
            name = match.group(1).strip()
            year = int(match.group(2))
            return (year, name)
        
        # Fallback if the line doesn't match the expected format
        return (0, line)

    # Sort the list based on the extracted year (Oldest -> Newest)
    clean_lines.sort(key=get_sort_key)

    # Write the sorted content back to the same file
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            for line in clean_lines:
                f.write(line + "\n")
        print(f"  Saved {len(clean_lines)} entries.")
    except Exception as e:
        print(f"  [Error] Could not write to file: {e}")

if __name__ == "__main__":
    process_directory()