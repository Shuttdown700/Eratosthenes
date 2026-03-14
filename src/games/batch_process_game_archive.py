#!/usr/bin/env python3
import os
import zipfile
import tempfile
import subprocess
from pathlib import Path
import re
import shutil
import argparse

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
RESET = Style.RESET_ALL
BRIGHT = Style.BRIGHT

# Attempt to import py7zr for .7z support
try:
    import py7zr
except ImportError:
    print(f"{YELLOW}Warning: 'py7zr' is not installed. .7z files will be skipped.{RESET}")
    print(f"{YELLOW}To install, run: pip install py7zr{RESET}")
    py7zr = None

# --- Helper Functions for File Sizes ---
def get_size(path: Path) -> int:
    """Returns the size of a file, or the total size of all files in a directory."""
    if path.is_file():
        return path.stat().st_size
    elif path.is_dir():
        return sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
    return 0


def format_size(size_in_bytes: int) -> str:
    """Converts bytes to a human-readable format (e.g., MB, GB)."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_in_bytes < 1024.0:
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024.0
    return f"{size_in_bytes:.2f} PB"


def clean_name(name: str, has_extension: bool = True, strip_tags: bool = False) -> str:
    """
    Strips trailing parenthetical region tags from strings if strip_tags is True.
    Handles both filenames (with extensions) and directory/base names.
    """
    if not strip_tags:
        return name

    if has_extension:
        pattern = re.compile(r'(?:\s*\([^)]*\))+(?=\.[^.]+$)')
    else:
        pattern = re.compile(r'(?:\s*\([^)]*\))+$')

    return pattern.sub('', name)


def get_bin_files_from_cue(cue_path: Path) -> list:
    """Parses a .cue file to find the referenced .bin files for cleanup."""
    bin_files = []
    try:
        with open(cue_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                match = re.search(r'FILE\s+"([^"]+)"', line, re.IGNORECASE)
                if match:
                    bin_files.append(match.group(1))
    except Exception:
        pass
    return bin_files


def convert_to_chd(source_dir: str, dest_dir: str, chdman_path: str = 'chdman', dry_run: bool = False, strip_tags: bool = False):
    """
    Extracts archives if necessary, finds .cue or .iso files, and converts them to CHD format.
    Handles multi-disc games if present in a single directory.
    Deletes original source files/archives upon successful conversion.
    """
    source_path = Path(source_dir)
    dest_path = Path(dest_dir)

    if not source_path.exists() or not source_path.is_dir():
        raise FileNotFoundError(f"Source directory not found: {source_path!s}")

    if not dry_run:
        dest_path.mkdir(parents=True, exist_ok=True)
        # Verify chdman is accessible
        if shutil.which(chdman_path) is None:
            print(f"{RED}{BRIGHT}Error: '{chdman_path}' not found in PATH.{RESET}")
            print(f"{RED}Please install MAME tools and ensure 'chdman' is accessible.{RESET}")
            return

    def run_chdman(input_file: Path, output_file: Path) -> bool:
        if input_file.suffix.lower() == '.iso':
            cmd = [chdman_path, 'createdvd', '-i', str(input_file), '-o', str(output_file)]
        elif input_file.suffix.lower() == '.cue':
            cmd = [chdman_path, 'createcd', '-i', str(input_file), '-o', str(output_file)]
        else:
            return False
            
        if dry_run:
            print(f"{YELLOW}[DRY RUN]{RESET} Would run: {' '.join(cmd)}")
            return True

        input_size_str = format_size(get_size(input_file))
        print(f"{BLUE}Creating CHD for: {input_file.name} [{input_size_str}]...{RESET}")
        
        try:
            # Suppressing stdout to keep terminal clean, but keeping stderr for error logging
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            output_size_str = format_size(get_size(output_file))
            print(f"{GREEN}  -> Successfully created {output_file.name} [{output_size_str}]{RESET}")
            return True
        except subprocess.CalledProcessError as e:
            err_msg = e.stderr.decode('utf-8').strip() if e.stderr else str(e)
            print(f"{RED}  -> CHD creation failed for {input_file.name}: {err_msg}{RESET}")
            if output_file.exists():
                output_file.unlink() # Clean up broken partial CHD
            return False

    def find_target_files(directory: Path) -> list:
        # Prioritize .cue files (for bin/cue setups)
        cues = list(directory.rglob("*.cue"))
        if cues:
            return cues
        # Fall back to .iso
        return list(directory.rglob("*.iso"))

    for item in source_path.iterdir():
        if item.is_file():
            # 1. HANDLE ARCHIVES (.zip, .7z)
            if item.suffix.lower() in ['.zip', '.7z']:
                if item.suffix.lower() == '.7z' and py7zr is None:
                    continue
                
                item_size_str = format_size(get_size(item))
                    
                if dry_run:
                    print(f"{YELLOW}[DRY RUN]{RESET} Would extract '{item.name}' [{item_size_str}], convert to CHD, and delete archive.")
                    continue
                    
                print(f"{MAGENTA}Processing archive for CHD: {item.name} [{item_size_str}]{RESET}")
                
                # Extract to a temporary directory that auto-deletes when done
                with tempfile.TemporaryDirectory() as temp_dir:
                    temp_path = Path(temp_dir)
                    try:
                        if item.suffix.lower() == '.zip':
                            with zipfile.ZipFile(item, 'r') as z:
                                z.extractall(path=temp_path)
                        elif item.suffix.lower() == '.7z':
                            with py7zr.SevenZipFile(item, mode='r') as z:
                                z.extractall(path=temp_path)
                    except Exception as e:
                        print(f"{RED}  -> Failed to extract {item.name}: {e}{RESET}")
                        continue
                        
                    targets = find_target_files(temp_path)
                    if not targets:
                        print(f"{RED}  -> No .iso or .cue found inside {item.name}{RESET}")
                        continue
                        
                    all_success = True
                    for target in targets:
                        clean_game_name = clean_name(target.stem, has_extension=False, strip_tags=strip_tags)
                        out_chd = dest_path / f"{clean_game_name}.chd"
                        if not run_chdman(target, out_chd):
                            all_success = False
                            
                    if all_success:
                        try:
                            item.unlink()
                            print(f"{GREEN}  -> Success. Deleted original archive: {item.name}{RESET}")
                        except Exception as e:
                            print(f"{RED}  -> Converted, but failed to delete archive {item.name}: {e}{RESET}")

            # 2. HANDLE LOOSE FILES (.iso, .cue)
            elif item.suffix.lower() in ['.iso', '.cue']:
                clean_game_name = clean_name(item.stem, has_extension=False, strip_tags=strip_tags)
                out_chd = dest_path / f"{clean_game_name}.chd"
                
                # For loose files, if it's a .cue, get the size of the cue + associated bins
                total_loose_size = get_size(item)
                if item.suffix.lower() == '.cue':
                    bin_files = get_bin_files_from_cue(item)
                    for b_file in bin_files:
                        b_path = item.parent / b_file
                        if b_path.exists():
                            total_loose_size += get_size(b_path)
                            
                item_size_str = format_size(total_loose_size)
                
                if dry_run:
                    print(f"{YELLOW}[DRY RUN]{RESET} Would convert loose file '{item.name}' [{item_size_str}] to CHD and delete original(s).")
                    continue
                    
                print(f"{MAGENTA}Processing loose file for CHD: {item.name} [{item_size_str}]{RESET}")
                success = run_chdman(item, out_chd)
                
                if success:
                    try:
                        # Clean up the loose .cue and its associated .bin files
                        if item.suffix.lower() == '.cue':
                            bin_files = get_bin_files_from_cue(item)
                            item.unlink()
                            for b_file in bin_files:
                                b_path = item.parent / b_file
                                if b_path.exists():
                                    b_path.unlink()
                        else:
                            item.unlink() # Delete the loose .iso
                        print(f"{GREEN}  -> Success. Deleted original loose file(s) for: {item.name}{RESET}")
                    except Exception as e:
                        print(f"{RED}  -> Converted, but failed to delete loose files: {e}{RESET}")

        # 3. HANDLE DIRECTORIES
        elif item.is_dir():
            item_size_str = format_size(get_size(item))
            
            if dry_run:
                print(f"{YELLOW}[DRY RUN]{RESET} Would convert contents of directory '{item.name}' [{item_size_str}] to CHD and delete directory.")
                continue
                
            print(f"{MAGENTA}Processing directory for CHD: {item.name} [{item_size_str}]{RESET}")
            targets = find_target_files(item)
            
            if not targets:
                print(f"{RED}  -> No .iso or .cue found inside {item.name}{RESET}")
                continue
                
            all_success = True
            for target in targets:
                clean_game_name = clean_name(target.stem, has_extension=False, strip_tags=strip_tags)
                out_chd = dest_path / f"{clean_game_name}.chd"
                if not run_chdman(target, out_chd):
                    all_success = False
                    
            if all_success:
                try:
                    shutil.rmtree(item)
                    print(f"{GREEN}  -> Success. Deleted original directory: {item.name}{RESET}")
                except Exception as e:
                    print(f"{RED}  -> Converted, but failed to delete directory {item.name}: {e}{RESET}")


def process_archives(source_dir: str, dest_dir: str, unwanted_files: list, dry_run: bool = False, strip_tags: bool = False):
    """
    Extracts archives directly into the destination directory (no subdirectories),
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

        if dry_run:
            print(f"{YELLOW}[DRY RUN]{RESET} Would extract '{archive.name}' [{archive_size_str}] directly to '{dest_path}'")
            print(f"{YELLOW}[DRY RUN]{RESET} Would delete listed unwanted files (e.g., {', '.join(unwanted_files[:2])})")
            if strip_tags:
                print(f"{YELLOW}[DRY RUN]{RESET} Would strip region tags and move extracted files to root directory")
            else:
                print(f"{YELLOW}[DRY RUN]{RESET} Would move extracted files to root directory (keeping original names)")
            print(f"{YELLOW}[DRY RUN]{RESET} Would delete original archive '{archive.name}'\n")
            continue

        print(f"{BLUE}Processing archive: {archive.name} [{archive_size_str}]{RESET}")
        extraction_successful = False

        # Extract to a temp directory to safely process files before moving them to the final flat directory
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
                # Use rglob to catch files even if the archive contained an internal folder
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

                    # 2. Clean region tags (if enabled) and move to destination
                    new_name = clean_name(original_name, has_extension=True, strip_tags=strip_tags)
                    final_path = dest_path / new_name

                    # Handle naming collisions in the flat directory
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
                        # Move from temp to final flat destination
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


def compress_directories(source_dir: str, dest_dir: str, archive_format: str = '.zip', dry_run: bool = False):
    """
    Takes uncompressed game directories OR loose files, archives them into 
    .zip or .7z files, and deletes the original uncompressed source.
    """
    source_path = Path(source_dir)
    dest_path = Path(dest_dir)

    if not source_path.exists() or not source_path.is_dir():
        raise FileNotFoundError(f"Source directory not found: {source_path!s}")

    if not dry_run:
        dest_path.mkdir(parents=True, exist_ok=True)

    if archive_format not in ['.zip', '.7z']:
        raise ValueError("archive_format must be '.zip' or '.7z'")

    if archive_format == '.7z' and py7zr is None:
        raise ImportError("py7zr is required to create .7z archives.")

    for item in source_path.iterdir():
        # Determine names and skip conditions based on type
        if item.is_file():
            # Skip files that are already archives
            if item.suffix.lower() in ['.zip', '.7z']:
                continue
            archive_name = f"{item.stem}{archive_format}"
        elif item.is_dir():
            archive_name = f"{item.name}{archive_format}"
        else:
            continue

        archive_path = dest_path / archive_name
        item_type = "file" if item.is_file() else "directory"

        if dry_run:
            print(f"{YELLOW}[DRY RUN]{RESET} Would compress {item_type} '{item.name}' into '{archive_name}'")
            print(f"{YELLOW}[DRY RUN]{RESET} Would delete original {item_type} '{item.name}'\n")
            continue

        print(f"{BLUE}Compressing {item_type}: {item.name}{RESET}")
        compression_successful = False

        try:
            if archive_format == '.zip':
                with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as z:
                    if item.is_dir():
                        for file_path in item.iterdir():
                            if file_path.is_file():
                                z.write(file_path, arcname=file_path.name)
                    else:
                        z.write(item, arcname=item.name)
                compression_successful = True
            
            elif archive_format == '.7z':
                with py7zr.SevenZipFile(archive_path, 'w') as z:
                    if item.is_dir():
                        for file_path in item.iterdir():
                            if file_path.is_file():
                                z.write(file_path, arcname=file_path.name)
                    else:
                        z.write(item, arcname=item.name)
                compression_successful = True
                
        except Exception as e:
            print(f"{RED}{BRIGHT}  -> Failed to compress {item.name}: {e}{RESET}")
            if archive_path.exists():
                archive_path.unlink() # Clean up incomplete archive
            continue

        # Delete the original file or folder
        if compression_successful:
            try:
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
                print(f"{GREEN}  -> Success. Deleted original {item_type}: {item.name}{RESET}")
            except Exception as e:
                print(f"{RED}  -> Compressed successfully, but failed to delete {item.name}: {e}{RESET}")


if __name__ == "__main__":
    # Setup Argument Parser
    parser = argparse.ArgumentParser(description="ROM Archiving and Conversion Tool")
    parser.add_argument(
        "--mode", 
        type=str, 
        required=True, 
        choices=["extract", "compress", "convert"], 
        help="Select the operation to perform on the hardcoded directories."
    )
    parser.add_argument(
        "--dry-run", 
        action="store_true", 
        help="Simulate the process without making any actual changes to the files."
    )
    parser.add_argument(
        "--strip-tags", 
        action="store_true", 
        help="Strip trailing parenthetical region tags from filenames."
    )
    
    args = parser.parse_args()

    # --- Configuration ---
    SOURCE_DIRECTORIES = [
        r"V:\Games\Emulation\Game Files\PlayStation 2",
    ]
    OUTPUT_DIRECTORIES = [
        r"V:\Games\Emulation\Game Files\PlayStation 2",
    ]
    PS2_SOURCE_DIRECTORIES = [
        r"V:\Games\Emulation\Game Files\PlayStation 2",
    ]
    PS2_OUTPUT_DIRECTORIES = [
        r"V:\Games\Emulation\Game Files\PlayStation 2",
    ]
    
    # List of exact filenames to delete during standard extraction
    UNWANTED_FILES = [
        "Vimm's Lair.txt",
        "readme.txt"
    ]

    IS_DRY_RUN = args.dry_run
    
    # Use the os library to build an absolute path to ../bin/chdman.exe 
    # relative to where this script is located.
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    CHDMAN_EXECUTABLE = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "bin", "chdman.exe"))
    
    if args.mode == "convert":
        # Quick check to warn you if it can't find it before running the whole process
        if not os.path.exists(CHDMAN_EXECUTABLE) and not IS_DRY_RUN:
            print(f"{RED}{BRIGHT}Error: Could not find chdman.exe at {CHDMAN_EXECUTABLE}{RESET}")
            exit(1)

    # ---------------------------------------------------------
    # Execute based on selected Mode
    # ---------------------------------------------------------
    if args.mode in ["extract", "compress"]:
        for sDir, oDir in zip(SOURCE_DIRECTORIES, OUTPUT_DIRECTORIES):
            
            if args.mode == "extract":
                print(f"\n{BLUE}{BRIGHT}Starting Extraction for: {sDir}{RESET}")
                process_archives(sDir, oDir, UNWANTED_FILES, dry_run=IS_DRY_RUN, strip_tags=args.strip_tags)
                
            elif args.mode == "compress":
                print(f"\n{BLUE}{BRIGHT}Starting Compression for: {sDir}{RESET}")
                compress_directories(oDir, sDir, archive_format='.7z', dry_run=IS_DRY_RUN)

    elif args.mode in ["convert"]: 
        for sDir, oDir in zip(PS2_SOURCE_DIRECTORIES, PS2_OUTPUT_DIRECTORIES):
            
            print(f"\n{BLUE}{BRIGHT}Starting CHD Conversion for: {sDir}{RESET}")
            convert_to_chd(sDir, oDir, chdman_path=CHDMAN_EXECUTABLE, dry_run=IS_DRY_RUN, strip_tags=args.strip_tags)