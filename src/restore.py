#!/usr/bin/env python

import argparse
import datetime
import os
import shutil
import sys
from pathlib import Path
from typing import List, Tuple

from colorama import Fore, Back, Style

# Add custom module paths
sys.path.append(os.path.join(os.path.dirname(__file__), "analysis"))
sys.path.append(os.path.join(os.path.dirname(__file__), "utils"))

# Import from updated cross-platform utilities
from utilities import (
    files_are_identical,
    get_volume_root,
    get_file_size,
    get_space_remaining,
    read_alexandria,
    read_alexandria_config,
    read_json,
    human_readable_size,
    validate_json_file
)

from generate_audio_file_print_string import generate_audio_file_print_string

# Colors
RED = Fore.RED
YELLOW = Fore.YELLOW
GREEN = Fore.GREEN
BLUE = Fore.BLUE
MAGENTA = Fore.MAGENTA
RESET = Style.RESET_ALL
BRIGHT = Style.BRIGHT


class Restore:
    def __init__(self) -> None:
        """Initialize the Restore class and set up essential attributes."""
        self.timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.src_directory = os.path.dirname(os.path.abspath(__file__))
        self.output_directory = os.path.join(os.path.dirname(self.src_directory), "output")
        self.filepath_drive_hierarchy = os.path.join(self.src_directory, "..", "config", "alexandria_drives.config")
        self.filepath_restore_log = os.path.join(self.output_directory, "restore.log")
        
        # Ensure output directory exists for the log
        os.makedirs(self.output_directory, exist_ok=True)
        
        # Read configuration and initialize dictionaries
        self.drive_config = read_json(self.filepath_drive_hierarchy)
        if not validate_json_file(self.filepath_drive_hierarchy):
            raise ValueError("Invalid drive hierarchy JSON file.")
            
        self.primary_drives_name_dict, self.backup_drives_name_dict, self.extensions_dict = read_alexandria_config(self.drive_config)
        
        self.primary_drives_root_dict = {}
        self.backup_drives_root_dict = {}
        self.root_to_name = {}  # Internal mapping to translate volume roots back to names

        # Map Primary Drives
        for key, val in self.primary_drives_name_dict.items():
            roots = []
            for name in val:
                root = get_volume_root(name)
                if root:
                    roots.append(root)
                    self.root_to_name[root] = name
            self.primary_drives_root_dict[key] = roots

        # Map Backup Drives
        for key, val in self.backup_drives_name_dict.items():
            roots = []
            for name in val:
                root = get_volume_root(name)
                if root:
                    roots.append(root)
                    self.root_to_name[root] = name
            self.backup_drives_root_dict[key] = roots
        
        # Media types to process
        self.media_types = list(self.primary_drives_root_dict.keys())
        self.drive_stats_dict = {}

    def _log_event(self, message: str) -> None:
        """Appends a timestamped message to the restore log."""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with open(self.filepath_restore_log, 'a', encoding='utf-8') as log_file:
                log_file.write(f"[{timestamp}] {message}\n")
        except Exception as e:
            print(f"{RED}Error writing to log file: {e}{RESET}")

    def _get_name_from_path(self, filepath: str) -> str:
        """Helper to resolve a human readable drive name from a file path."""
        for root, name in self.root_to_name.items():
            if filepath.startswith(root):
                return name
        return "Unknown"

    def restore_mapper(self, media_type: str) -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]]]:
        """Maps backup files to primary locations, grouping media and balancing space."""
        backup_roots = self.backup_drives_root_dict.get(media_type, [])
        primary_roots = self.primary_drives_root_dict.get(media_type, [])

        if not backup_roots or not primary_roots:
            return [], []

        missing_on_primary = []
        modified_on_primary = []
        
        # Track available space for balancing completely new groups
        available_space = {p_root: get_space_remaining(p_root, "GB") for p_root in primary_roots}

        # 1. Map existing files and establish group locations on primary drives
        primary_rel_map = {}
        group_locations = {} # Maps 'Group Name' -> 'Primary Root'
        
        for p_root in primary_roots:
            p_base = os.path.join(p_root, media_type)
            if not os.path.exists(p_base):
                continue
                
            # Map top-level directories to this drive to keep groups together
            for item in os.listdir(p_base):
                if os.path.isdir(os.path.join(p_base, item)):
                    group_locations[item] = p_root
            
            p_files = read_alexandria([p_base], self.extensions_dict[media_type])
            for fp in p_files:
                rel_path = os.path.relpath(fp, p_base)
                primary_rel_map[rel_path] = fp

        # 2. Iterate through backup drives to group missing files
        missing_groups = {} # Maps 'Group Name' -> List of (backup_filepath, relative_path)
        
        for b_root in backup_roots:
            b_base = os.path.join(b_root, media_type)
            if not os.path.exists(b_base):
                continue
                
            b_files = read_alexandria([b_base], self.extensions_dict[media_type])

            for b_fp in b_files:
                rel_path = os.path.relpath(b_fp, b_base)

                if rel_path in primary_rel_map:
                    # File exists on a primary drive, check if it's identical
                    p_fp = primary_rel_map[rel_path]
                    try:
                        if not files_are_identical(b_fp, p_fp):
                            modified_on_primary.append((b_fp, p_fp))
                    except Exception as e:
                        print(f"{RED}Error comparing {b_fp} and {p_fp}: {e}{RESET}")
                else:
                    # Extract the top-level folder name (or file name if in root) as the group key
                    group_name = Path(rel_path).parts[0]
                    if group_name not in missing_groups:
                        missing_groups[group_name] = []
                    missing_groups[group_name].append((b_fp, rel_path))

        # 3. Assign missing groups to primary drives intelligently
        for group_name, files in missing_groups.items():
            target_p_root = None
            
            # If the group already has a home on a primary drive, stick to it
            if group_name in group_locations:
                target_p_root = group_locations[group_name]
            else:
                # Group is entirely missing. Calculate total size and assign to drive with most space.
                group_size_gb = sum(get_file_size(b_fp, "GB") for b_fp, _ in files)
                
                # Sort primary roots by available space (descending) and select the highest
                best_p_root = max(available_space, key=available_space.get)
                target_p_root = best_p_root
                
                # Lock this group to the chosen drive for any subsequent references
                group_locations[group_name] = target_p_root
                # Deduct projected space to balance the next group properly
                available_space[target_p_root] -= group_size_gb
                
            # Queue the files for restore
            for b_fp, rel_path in files:
                target_p_fp = os.path.join(target_p_root, media_type, rel_path)
                missing_on_primary.append((b_fp, target_p_fp))

        return missing_on_primary, modified_on_primary

    def assess_restore_feasibility(self, restore_tuples: List[Tuple[str, str]]) -> bool:
        """Determine if there is enough space on the primary drives to restore data."""
        if not restore_tuples:
            return True

        # Group required space by target primary volume root
        space_required_per_drive = {}
        for _, target_path in restore_tuples:
            target_root = next((r for r in self.root_to_name.keys() if target_path.startswith(r)), None)
            if target_root:
                file_size = get_file_size(restore_tuples[0][0], "GB")
                space_required_per_drive[target_root] = space_required_per_drive.get(target_root, 0) + file_size

        # Check against available space
        feasible = True
        for target_root, required_gb in space_required_per_drive.items():
            remaining_gb = get_space_remaining(target_root, "GB")
            drive_name = self.root_to_name.get(target_root, "Unknown")
            
            if required_gb > remaining_gb:
                print(f'\n\t{Back.RED}[ALERT]{RESET} Cannot restore to '
                      f'{YELLOW}{drive_name} ({target_root}){Fore.RESET}. '
                      f'Requires {required_gb:,.2f} GB but only {remaining_gb:,.2f} GB available.')
                feasible = False

        return feasible

    def restore_function(self, restore_tuples: List[Tuple[str, str]], action: str, media_type: str) -> None:
        """Handles the actual restoration of files using shutil and logs the outcome."""
        if not restore_tuples:
            return

        total_gb = sum(get_file_size(src, "GB") for src, _ in restore_tuples)
        total_size_val, total_unit = human_readable_size(total_gb)

        print(f"\n\t{action} {RED}{len(restore_tuples):,} file{'s' if len(restore_tuples) != 1 else ''}{RESET} "
              f"({YELLOW}{total_size_val:.2f} {total_unit}{RESET}):")

        for src_file, dest_file in restore_tuples:
            ext = os.path.splitext(src_file)[1].lower() 
            if media_type.lower() == "music" and ext in ['.mp3', '.flac']:
                file_title = generate_audio_file_print_string(src_file)
            else:
                file_title = '.'.join(os.path.basename(src_file).strip().split('.')[:-1])
                
            if os.path.isfile(src_file):
                os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                
                src_name = self._get_name_from_path(src_file)
                dest_name = self._get_name_from_path(dest_file)
                
                print(
                    f"{YELLOW}{BRIGHT}\t{action}:{RESET} {file_title} "
                    f"{RED}|{RESET} {Fore.BLUE}{src_name}{RESET} "
                    f"-> {GREEN}{dest_name}{RESET}"
                )
                try:
                    shutil.copy2(src_file, dest_file)
                    self._log_event(f"SUCCESS | {action} | SRC: '{src_file}' | DEST: '{dest_file}'")
                except Exception as e:
                    print(f"{RED}Error:{RESET} Failed to restore {file_title}: {e}")
                    self._log_event(f"FAILED  | {action} | SRC: '{src_file}' | DEST: '{dest_file}' | ERROR: {e}")

    def main(self) -> None:
        """Main function to initiate the Alexandria Restore process."""
        print(f'\n{"#" * 10}\n\n{MAGENTA}{BRIGHT}Initiating Alexandria Restore...{RESET}\n\n{"#" * 10}\n')
        
        # Write a header block to the log file for this specific run
        with open(self.filepath_restore_log, 'a', encoding='utf-8') as log_file:
            log_file.write(f"\n{'='*60}\n")
            log_file.write(f"RESTORE INITIATED: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            log_file.write(f"{'='*60}\n")

        for media_type in self.media_types:
            print(f'\n### {GREEN}{BRIGHT}Checking {media_type}{RESET} ###')
            
            missing, modified = self.restore_mapper(media_type)
            
            if not missing and not modified:
                print(f'\t{BLUE}Primary drives are fully up to date for {media_type}.{RESET}')
                continue
                
            if self.assess_restore_feasibility(missing + modified):
                if missing:
                    self.restore_function(missing, action="Restoring (Missing)", media_type=media_type)
                if modified:
                    self.restore_function(modified, action="Restoring (Corrupted/Modified)", media_type=media_type)

        print(f'\n{"#" * 10}\n\n{GREEN}{BRIGHT}Alexandria Restore Complete{RESET}\n\n{"#" * 10}\n')
        
        # Log completion
        with open(self.filepath_restore_log, 'a', encoding='utf-8') as log_file:
            log_file.write(f"RESTORE COMPLETE: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            log_file.write(f"\n{'='*60}\n")


if __name__ == '__main__':
    # Initialize Restore to load the config mapping
    restorer = Restore()
    
    # Initialize Argparse using identical logic to backup.py
    parser = argparse.ArgumentParser(description="Alexandria Restore Utility")
    
    # Dynamically generate arguments based on the media types
    for m_type in restorer.media_types:
        flag_name = f"--{m_type.lower().replace(' ', '-')}"
        dest_name = m_type.lower().replace(' ', '_')
        parser.add_argument(flag_name, action='store_true', dest=dest_name, help=f"Run restore only for {m_type}")

    args = parser.parse_args()
    args_dict = vars(args)

    # Check which flags the user actually passed
    selected_media_types = []
    for m_type in restorer.media_types:
        dict_key = m_type.lower().replace(' ', '_')
        if args_dict.get(dict_key):
            selected_media_types.append(m_type)
            
    # If any specific flags were used, overwrite the default 'run all' list
    if selected_media_types:
        restorer.media_types = selected_media_types
        print(f"{Fore.CYAN}{Style.BRIGHT}Filtering restore to specific media types: {', '.join(restorer.media_types)}{Style.RESET_ALL}")
        
    restorer.main()