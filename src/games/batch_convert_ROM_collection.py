#!/usr/bin/env python3
import os
import sys
import zipfile
import tempfile
import subprocess
from pathlib import Path
import re
import shutil
import argparse

from utilities_games import (
    clean_name,
    format_size,
    get_size
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
RESET = Style.RESET_ALL
BRIGHT = Style.BRIGHT

# Attempt to import py7zr for .7z support
try:
    import py7zr
except ImportError:
    print(f"{YELLOW}Warning: 'py7zr' is not installed. .7z files will be skipped.{RESET}")
    print(f"{YELLOW}To install, run: pip install py7zr{RESET}")
    py7zr = None


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


def extract_pbp(pbp_file: Path, output_dir: Path, extractor_path: str) -> bool:
    """
    Extracts a .PBP file to .bin/.cue format using PSXPackager.
    """
    if shutil.which(extractor_path) is None:
        print(f"{RED}{BRIGHT}Error: PBP extractor '{extractor_path}' not found.{RESET}")
        print(f"{RED}Please install a tool like PSXPackager to unpack PBP files before CHD conversion.{RESET}")
        return False
        
    print(f"{BLUE}Unpacking PBP to CUE/BIN: {pbp_file.name}...{RESET}")
    cmd = [extractor_path, '-i', str(pbp_file), '-o', str(output_dir)]
    
    try:
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"{RED}  -> PBP extraction failed for {pbp_file.name}.{RESET}")
        return False


def convert_to_chd(source_dir: str, dest_dir: str, chdman_path: str = 'chdman', pbp_extractor_path: str = 'psxpackager', dry_run: bool = False, strip_tags: bool = False):
    """
    Extracts archives if necessary, finds target files, and converts them to CHD format.
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
        is_iso = input_file.suffix.lower() == '.iso'
        
        if is_iso:
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
            # 300-second (5 minute) timeout to prevent infinite nan% hangs
            subprocess.run(cmd, check=True, timeout=300, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            output_size_str = format_size(get_size(output_file))
            print(f"{GREEN}  -> Successfully created {output_file.name} [{output_size_str}]{RESET}")
            return True
        except subprocess.TimeoutExpired:
            print(f"{RED}  -> CHD creation timed out (likely a missing .img/.bin file or nan% bug) for {input_file.name}{RESET}")
            if output_file.exists():
                output_file.unlink() # Clean up broken partial CHD
            return False
        except subprocess.CalledProcessError as e:
            err_msg = e.stderr.decode('utf-8').strip() if e.stderr else str(e)
            
            # --- ISO FALLBACK FIX ---
            # If an ISO fails with the 2048 sector error, it's actually a raw PSX CD. Generate a dummy CUE and retry.
            if is_iso and "not divisible by sector size 2048" in err_msg:
                print(f"{YELLOW}  -> ISO is a disguised Raw CD image. Auto-generating CUE and retrying...{RESET}")
                
                dummy_cue_path = input_file.with_suffix('.cue')
                try:
                    with open(dummy_cue_path, 'w', encoding='utf-8') as f:
                        f.write(f'FILE "{input_file.name}" BINARY\n')
                        f.write('  TRACK 01 MODE2/2352\n')
                        f.write('    INDEX 01 00:00:00\n')
                    
                    retry_cmd = [chdman_path, 'createcd', '-i', str(dummy_cue_path), '-o', str(output_file)]
                    subprocess.run(retry_cmd, check=True, timeout=300, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                    
                    output_size_str = format_size(get_size(output_file))
                    print(f"{GREEN}  -> Successfully created {output_file.name} (via generated CUE) [{output_size_str}]{RESET}")
                    
                    if dummy_cue_path.exists():
                        dummy_cue_path.unlink() # Cleanup dummy CUE
                    return True
                    
                except Exception as e2:
                    print(f"{RED}  -> Retry failed for {input_file.name}{RESET}")
                    if output_file.exists(): output_file.unlink()
                    if dummy_cue_path.exists(): dummy_cue_path.unlink()
                    return False
            # ------------------------
            
            print(f"{RED}  -> CHD creation failed for {input_file.name}: {err_msg}{RESET}")
            if output_file.exists():
                output_file.unlink() # Clean up broken partial CHD
            return False

    def process_target(target_file: Path, output_file: Path) -> bool:
        """Handles routing between native chdman conversions and temporary PBP extractions."""
        if target_file.suffix.lower() == '.pbp':
            if dry_run:
                print(f"{YELLOW}[DRY RUN]{RESET} Would unpack PBP '{target_file.name}', check for multi-disc, convert if single, and clean up.")
                return True
                
            with tempfile.TemporaryDirectory() as pbp_temp:
                pbp_temp_path = Path(pbp_temp)
                if not extract_pbp(target_file, pbp_temp_path, pbp_extractor_path):
                    return False
                    
                extracted_cues = list(pbp_temp_path.rglob("*.cue"))
                
                # --- PBP FALLBACK FIX ---
                # If extraction succeeded but no CUE was created, find the BIN and auto-generate one.
                if not extracted_cues:
                    extracted_bins = list(pbp_temp_path.rglob("*.bin")) + list(pbp_temp_path.rglob("*.img")) + list(pbp_temp_path.rglob("*.iso"))
                    if not extracted_bins:
                        print(f"{RED}  -> Extraction succeeded, but no .cue or raw data file found for {target_file.name}{RESET}")
                        return False
                        
                    print(f"{YELLOW}  -> Extractor failed to generate CUE. Auto-generating CUE for {extracted_bins[0].name}...{RESET}")
                    dummy_cue = extracted_bins[0].with_suffix('.cue')
                    with open(dummy_cue, 'w', encoding='utf-8') as f:
                        f.write(f'FILE "{extracted_bins[0].name}" BINARY\n')
                        f.write('  TRACK 01 MODE2/2352\n')
                        f.write('    INDEX 01 00:00:00\n')
                    
                    extracted_cues = [dummy_cue]
                # ------------------------
                
                # Check for multi-disc PBP and abort CHD conversion if found
                if len(extracted_cues) > 1:
                    print(f"{YELLOW}  -> Multi-disc game detected. Keeping original PBP format: {target_file.name}{RESET}")
                    return False # Returning False prevents the original PBP from being deleted
                    
                return run_chdman(extracted_cues[0], output_file)
        else:
            return run_chdman(target_file, output_file)

    def find_target_files(directory: Path) -> list:
        # Prioritize .cue files
        cues = list(directory.rglob("*.cue"))
        if cues: return cues
        # Fall back to PBP files
        pbps = list(directory.rglob("*.pbp"))
        if pbps: return pbps
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
                        print(f"{RED}  -> No target files (.iso, .cue, .pbp) found inside {item.name}{RESET}")
                        continue
                        
                    all_success = True
                    for target in targets:
                        clean_game_name = clean_name(target.stem, has_extension=False, strip_tags=strip_tags)
                        out_chd = dest_path / f"{clean_game_name}.chd"
                        
                        if not process_target(target, out_chd):
                            all_success = False
                            
                    if all_success:
                        try:
                            item.unlink()
                            print(f"{GREEN}  -> Success. Deleted original archive: {item.name}{RESET}")
                        except Exception as e:
                            print(f"{RED}  -> Converted, but failed to delete archive {item.name}: {e}{RESET}")

            # 2. HANDLE LOOSE FILES (.iso, .cue, .pbp)
            elif item.suffix.lower() in ['.iso', '.cue', '.pbp']:
                clean_game_name = clean_name(item.stem, has_extension=False, strip_tags=strip_tags)
                out_chd = dest_path / f"{clean_game_name}.chd"
                
                # For loose files, get the size of the control file + associated data files
                total_loose_size = get_size(item)
                if item.suffix.lower() == '.cue':
                    bin_files = get_bin_files_from_cue(item)
                    for b_file in bin_files:
                        b_path = item.parent / b_file
                        if b_path.exists():
                            total_loose_size += get_size(b_path)
                            
                item_size_str = format_size(total_loose_size)
                
                if dry_run:
                    print(f"{YELLOW}[DRY RUN]{RESET} Would process loose file '{item.name}' [{item_size_str}].")
                    continue
                    
                print(f"{MAGENTA}Processing loose file for CHD: {item.name} [{item_size_str}]{RESET}")
                success = process_target(item, out_chd)
                
                if success:
                    try:
                        # Clean up the loose files
                        if item.suffix.lower() == '.cue':
                            bin_files = get_bin_files_from_cue(item)
                            item.unlink()
                            for b_file in bin_files:
                                b_path = item.parent / b_file
                                if b_path.exists():
                                    b_path.unlink()
                        else:
                            item.unlink() 
                        print(f"{GREEN}  -> Success. Deleted original loose file(s) for: {item.name}{RESET}")
                    except Exception as e:
                        print(f"{RED}  -> Converted, but failed to delete loose files: {e}{RESET}")

        # 3. HANDLE DIRECTORIES
        elif item.is_dir():
            item_size_str = format_size(get_size(item))
            
            if dry_run:
                print(f"{YELLOW}[DRY RUN]{RESET} Would process contents of directory '{item.name}' [{item_size_str}].")
                continue
                
            print(f"{MAGENTA}Processing directory for CHD: {item.name} [{item_size_str}]{RESET}")
            targets = find_target_files(item)
            
            if not targets:
                print(f"{RED}  -> No target files (.iso, .cue, .pbp) found inside {item.name}{RESET}")
                continue
                
            all_success = True
            for target in targets:
                clean_game_name = clean_name(target.stem, has_extension=False, strip_tags=strip_tags)
                out_chd = dest_path / f"{clean_game_name}.chd"
                
                if not process_target(target, out_chd):
                    all_success = False
                    
            if all_success:
                try:
                    shutil.rmtree(item)
                    print(f"{GREEN}  -> Success. Deleted original directory: {item.name}{RESET}")
                except Exception as e:
                    print(f"{RED}  -> Converted, but failed to delete directory {item.name}: {e}{RESET}")


if __name__ == "__main__":
    # Setup Argument Parser
    parser = argparse.ArgumentParser(description="ROM CHD Conversion Tool")
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
        r"V:\Temp\Sega Dreamcast\CUE"
    ]
    OUTPUT_DIRECTORIES = [
        r"V:\Temp\Sega Dreamcast\CUE"
    ]

    IS_DRY_RUN = args.dry_run
    
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    CHDMAN_EXECUTABLE = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "bin", "chdman.exe"))
    PBP_EXTRACTOR_EXECUTABLE = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "bin", "psxpackager.exe"))

    # Quick check to warn you if it can't find it before running the whole process
    if not os.path.exists(CHDMAN_EXECUTABLE) and not IS_DRY_RUN:
        print(f"{RED}{BRIGHT}Error: Could not find chdman.exe at {CHDMAN_EXECUTABLE}{RESET}")
        exit(1)

    # ---------------------------------------------------------
    # Execute CHD Conversion
    # ---------------------------------------------------------
    for sDir, oDir in zip(SOURCE_DIRECTORIES, OUTPUT_DIRECTORIES):
        print(f"\n{BLUE}{BRIGHT}Starting CHD Conversion for: {sDir}{RESET}")
        convert_to_chd(sDir, oDir, chdman_path=CHDMAN_EXECUTABLE, pbp_extractor_path=PBP_EXTRACTOR_EXECUTABLE, dry_run=IS_DRY_RUN, strip_tags=args.strip_tags)