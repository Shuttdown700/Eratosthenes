from pathlib import Path
import zipfile
import shutil
import tempfile

import py7zr

from utilities_games import (
    format_size,
    get_size,
    clean_name
)

# Import colorama for terminal colors
try:
    from colorama import Fore, Style, init
    init() # Initializes colorama so colors render properly on Windows
except ImportError:
    print("Error: 'colorama' is not installed. To install, run: pip install colorama")
    exit(1)

# Colors
RED = Fore.RED
YELLOW = Fore.YELLOW
GREEN = Fore.GREEN
BLUE = Fore.BLUE
MAGENTA = Fore.MAGENTA
CYAN = Fore.CYAN
RESET = Style.RESET_ALL
BRIGHT = Style.BRIGHT


SOURCE_DIRECTORIES = [
    r"T:\ShuttFlix-Temp\Games\Xbox"
]
OUTPUT_DIRECTORIES = [
    r"T:\ShuttFlix-Temp\Games\Xbox\Extracted"
]

IS_DRY_RUN = False


def process_archives(source_dir: str, dest_dir: str, unwanted_files: list, dry_run: bool = False, strip_tags: bool = False):
    """
    Extracts archives into subdirectories named after the archive file,
    removes unwanted files, optionally strips region tags, and deletes the original archives.
    """
    source_path = Path(source_dir)
    dest_path = Path(dest_dir)
    
    if not source_path.exists() or not source_path.is_dir():
        raise FileNotFoundError(f"Source directory not found: {source_path!s}")

    if not dry_run:
        dest_path.mkdir(parents=True, exist_ok=True)
        
    supported_extensions = ['.zip', '.7z']

    for archive in source_path.iterdir():
        if not archive.is_file() or archive.suffix.lower() not in supported_extensions:
            continue

        if archive.suffix.lower() == '.7z' and py7zr is None:
            continue

        archive_size_str = format_size(get_size(archive))
        
        # Determine the name for the new folder based on the archive's name
        folder_name = clean_name(archive.stem, has_extension=False, strip_tags=strip_tags)
        specific_dest_path = dest_path / folder_name

        if dry_run:
            print(f"{YELLOW}[DRY RUN]{RESET} Would extract '{archive.name}' [{archive_size_str}] into folder '{folder_name}'")
            print(f"{YELLOW}[DRY RUN]{RESET} Would delete listed unwanted files (e.g., {', '.join(unwanted_files[:2])})")
            print(f"{YELLOW}[DRY RUN]{RESET} Would delete original archive '{archive.name}'\n")
            continue

        print(f"{BLUE}Processing archive: {archive.name} [{archive_size_str}]{RESET}")
        extraction_successful = False

        # Extract to a temp directory to safely process files before moving them to the final destination
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            try:
                if archive.suffix.lower() == '.zip':
                    with zipfile.ZipFile(archive, 'r') as z:
                        z.extractall(path=temp_path)
                elif archive.suffix.lower() == '.7z':
                    with py7zr.SevenZipFile(archive, mode='r') as z:
                        z.extractall(path=temp_path)
                extraction_successful = True
            except Exception as e:
                print(f"{RED}{BRIGHT}  -> Failed to extract {archive.name}: {e}{RESET}")
                continue

            # Process extracted files
            if extraction_successful:
                moved_any_files = False
                
                # Use rglob to catch files even if the archive contained an internal folder
                # This safely flattens the archive into the new specific_dest_path
                for extracted_file in temp_path.rglob('*'):
                    if not extracted_file.is_file():
                        continue

                    original_name = extracted_file.name

                    # 1. Check for and delete unwanted text files
                    if original_name in unwanted_files:
                        try:
                            extracted_file.unlink()
                            print(f"{BLUE}  -> Removed unwanted file: {original_name}{RESET}")
                        except Exception as e:
                            print(f"{RED}  -> Failed to remove unwanted file {original_name}: {e}{RESET}")
                        continue 

                    # Create the target directory only if we have a valid file to move
                    if not moved_any_files:
                        specific_dest_path.mkdir(parents=True, exist_ok=True)
                        moved_any_files = True

                    # 2. Clean region tags (if enabled) and move to destination
                    new_name = clean_name(original_name, has_extension=True, strip_tags=strip_tags)
                    final_path = specific_dest_path / new_name

                    # Handle naming collisions in the directory
                    if final_path.exists():
                        stem = final_path.stem
                        suffix = final_path.suffix
                        i = 1
                        candidate = final_path.with_name(f"{stem}_{i}{suffix}")
                        while candidate.exists():
                            i += 1
                            candidate = final_path.with_name(f"{stem}_{i}{suffix}")
                        final_path = candidate

                    try:
                        # Move from temp to final destination
                        shutil.move(str(extracted_file), str(final_path))
                    except Exception as e:
                        print(f"{RED}  -> Failed to move {new_name} to destination: {e}{RESET}")
                        extraction_successful = False # Prevent archive deletion if a file fails to move

        # 3. Delete original archive
        if extraction_successful:
            try:
                archive.unlink()
                print(f"{GREEN}  -> Success. Deleted original archive: {archive.name}{RESET}")
            except Exception as e:
                print(f"{RED}  -> Extracted successfully, but failed to delete original {archive.name}: {e}{RESET}")

# ---------------------------------------------------------
# Execution Block
# ---------------------------------------------------------
if __name__ == "__main__":
    # List of exact filenames to delete during standard extraction
    UNWANTED_FILES = [
        "Vimm's Lair.txt",
        "readme.txt"
    ]

    print(f"\n{CYAN}{BRIGHT}--- Starting ROM Extraction Process ---{RESET}\n")

    for sDir, oDir in zip(SOURCE_DIRECTORIES, OUTPUT_DIRECTORIES):
        print(f"{MAGENTA}{BRIGHT}Target Directory:{RESET} {sDir}")
        try:
            process_archives(
                source_dir=sDir, 
                dest_dir=oDir, 
                unwanted_files=UNWANTED_FILES, 
                dry_run=IS_DRY_RUN, 
                strip_tags=False
            )
        except Exception as e:
            print(f"{RED}{BRIGHT}Critical Error processing {sDir}:{RESET} {e}")
            
    print(f"\n{GREEN}{BRIGHT}--- Process Complete ---{RESET}\n")