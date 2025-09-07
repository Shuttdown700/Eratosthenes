from pathlib import Path
from colorama import init, Fore, Style
import re

def find_mismatched_shows(root_dir, dry_run=True):
    # Initialize colorama for colored output
    init(autoreset=True)
    
    # Video file extensions to filter
    VIDEO_EXTENSIONS = [".mp4", ".mkv"]
    
    # Convert root_dir to Path object
    root_path = Path(root_dir)
    
    # Ensure root directory exists
    if not root_path.exists() or not root_path.is_dir():
        print(f"{Fore.RED}Error: {root_dir} is not a valid directory.")
        return
    
    # Regular expression for season directory (e.g., "Season 1", "Season 1950")
    season_pattern = re.compile(r'^Season\s*\d{1,4}$', re.IGNORECASE)
    
    # Regular expression to extract show name and season/episode from filename
    # Matches "Show Name S01E01.ext", "Show.Name.S1950E29.ext", where ext is mp4 or mkv
    filename_pattern = re.compile(r'^(.*?)([\s._-]*S\d{1,4}E\d{1,3})([\s._-].*?)?\.(?:' + '|'.join(ext[1:] for ext in VIDEO_EXTENSIONS) + r')$', re.IGNORECASE)
    
    mismatches = []
    
    # Iterate through all video files in the directory tree
    for ext in VIDEO_EXTENSIONS:
        for file_path in root_path.rglob(f"*{ext}"):
            # Check if parent directory matches "Season XX" or "Season XXXX"
            parent_dir = file_path.parent.name
            if not season_pattern.match(parent_dir):
                print(f"{Fore.YELLOW}Warning: Skipping {file_path} - parent directory '{parent_dir}' does not match 'Season XX' format")
                continue
            
            # Get the show name from the grandparent directory
            parent_show = file_path.parent.parent.name
            
            # Get the show name and season/episode from the filename
            filename = file_path.name
            match = filename_pattern.match(filename)
            if not match:
                print(f"{Fore.YELLOW}Warning: Could not parse show name from {filename}")
                print(f"{Fore.YELLOW}  Path: {file_path}")
                print(f"{Fore.YELLOW}  Regex attempted: {filename_pattern.pattern}")
                continue
            
            file_show = match.group(1).strip(' .-')
            season_episode = match.group(2)
            trailing_text = match.group(3) if match.group(3) else ''
            
            # Normalize show names for comparison (remove special chars, lowercase)
            parent_show_normalized = re.sub(r'[^\w\s]', '', parent_show).lower().strip()
            file_show_normalized = re.sub(r'[^\w\s]', '', file_show).lower().strip()
            
            # Check for mismatch using partial matching
            if file_show_normalized not in parent_show_normalized:
                mismatches.append((file_path, parent_show, file_show, season_episode, trailing_text))
    
    # Process mismatches
    if not mismatches:
        print(f"{Fore.GREEN}No mismatches found!")
    else:
        print(f"{Fore.RED}Found {len(mismatches)} mismatched files:")
        for file_path, parent_show, file_show, season_episode, trailing_text in mismatches:
            print(f"{Fore.CYAN}File: {file_path}")
            print(f"  {Fore.MAGENTA}Directory show: {parent_show}")
            print(f"  {Fore.MAGENTA}Filename show: {file_show}")
            
            # Propose new filename using parent show name
            new_filename = f"{parent_show}{season_episode}{trailing_text}{file_path.suffix}"
            new_file_path = file_path.parent / new_filename
            print(f"  {Fore.BLUE}Proposed rename: {new_filename}")
            
            if not dry_run:
                try:
                    file_path.rename(new_file_path)
                    print(f"  {Fore.GREEN}Renamed to: {new_filename}")
                except Exception as e:
                    print(f"  {Fore.RED}Error renaming {filename}: {e}")
            print()

if __name__ == "__main__":
    dry_run = True
    show_dirs = [
        r"B:\Shows",
        r"K:\Shows",
        r"A:\Anime"
    ]
    for show_dir in show_dirs:
        print(f"{Fore.YELLOW}Checking directory: {show_dir}")
        find_mismatched_shows(show_dir,dry_run=dry_run)