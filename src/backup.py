#!/usr/bin/env python

import ast
import datetime
import os
import shutil
import sys
import zipfile
from pathlib import Path
from typing import List, Tuple, Union

from colorama import Fore, Back, Style

# Add custom module paths
sys.path.append(os.path.join(os.path.dirname(__file__), "analysis"))
sys.path.append(os.path.join(os.path.dirname(__file__), "utils"))

from read_server_statistics import read_media_statistics
from assess_backup import main as assess_backup
from generate_audio_file_print_string import generate_audio_file_print_string
from api import API

# Import from updated cross-platform utilities
from utilities import (
    files_are_identical,
    get_volume_root,
    get_file_size,
    get_space_remaining,
    read_alexandria,
    read_alexandria_config,
    read_csv,
    read_json,
    read_file_as_list,
    order_file_contents,
    remove_empty_folders,
    human_readable_size
)

# Colors
RED = Fore.RED
YELLOW = Fore.YELLOW
GREEN = Fore.GREEN
BLUE = Fore.BLUE
MAGENTA = Fore.MAGENTA
RESET = Style.RESET_ALL
BRIGHT = Style.BRIGHT


class Backup:
    def __init__(self) -> None:
        """Initialize the Backup class and set up essential attributes."""
        self.timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.src_directory = os.path.dirname(os.path.abspath(__file__))
        self.filepath_drive_hierarchy = os.path.join(self.src_directory, "..", "config", "alexandria_drives.config")
        self.output_directory = os.path.join(os.path.dirname(self.src_directory), "output")
        self.filepath_statistics = os.path.join(self.output_directory, "alexandria_media_statistics.json")
        self.filepath_alexandria_media_details = os.path.join(self.output_directory, "alexandria_media_details.json")

        # Read configuration and initialize dictionaries
        self.drive_config = read_json(self.filepath_drive_hierarchy)
        self.primary_drives_name_dict, self.backup_drives_name_dict, self.extensions_dict = read_alexandria_config(self.drive_config)
        
        self.primary_drives_root_dict = {}
        self.backup_drives_root_dict = {}
        self.root_to_name = {}  # Internal mapping to translate volume roots back to names

        for key, val in self.primary_drives_name_dict.items():
            roots = []
            for name in val:
                root = get_volume_root(name)
                if root:
                    roots.append(root)
                    self.root_to_name[root] = name
            self.primary_drives_root_dict[key] = roots

        for key, val in self.backup_drives_name_dict.items():
            roots = []
            for name in val:
                root = get_volume_root(name)
                if root:
                    roots.append(root)
                    self.root_to_name[root] = name
            self.backup_drives_root_dict[key] = roots
        
        # Consolidate Volume Roots
        self.primary_volume_roots = []
        for val in self.primary_drives_root_dict.values():
            if not val:
                print(f"{RED}{BRIGHT}[ALERT] {RESET}Primary volume root missing. Please check the drive configuration.")
                raise ValueError("Missing primary volume root.")
            self.primary_volume_roots += val
            
        self.primary_volume_roots = sorted(set(self.primary_volume_roots))
        
        self.backup_volume_roots = []
        for val in self.backup_drives_root_dict.values():
            if val: 
                self.backup_volume_roots += val
                
        self.backup_volume_roots = sorted(set(self.backup_volume_roots))
        self.all_volume_roots = sorted(set(self.primary_volume_roots + self.backup_volume_roots))

        # Media types and file paths
        self.media_types = list(self.primary_drives_root_dict.keys())
        self.primary_filepaths_dict = {}
        self.drive_stats_dict = {}

    def _get_name_from_path(self, filepath: str) -> str:
        """Helper to resolve a human readable drive name from a file path."""
        for root, name in self.root_to_name.items():
            if filepath.startswith(root):
                return name
        return "Unknown"

    def backup_mgmt_files(self, compress: bool = True) -> None:
        """Backs up both output and config directories to specific backup locations."""
        try:
            current_date = datetime.datetime.now().strftime('%Y%m%d')
            parent_dir = os.path.dirname(self.output_directory)
            config_dir = os.path.join(parent_dir, 'config')
            icons_dir = os.path.join(parent_dir, 'icons')
            
            tasks = [
                {"src": self.output_directory, "dest": os.path.join(parent_dir, 'backups', 'outputs'), "prefix": "alexandria_output_backup"},
                {"src": config_dir, "dest": os.path.join(parent_dir, 'backups', 'configs'), "prefix": "alexandria_config_backup"},
                {"src": icons_dir, "dest": os.path.join(parent_dir, 'backups', 'icons'), "prefix": "alexandria_icon_backup"}
            ]

            for task in tasks:
                src = task["src"]
                dest_base = task["dest"]
                os.makedirs(dest_base, exist_ok=True)

                if compress:
                    zip_path = os.path.join(dest_base, f"{task['prefix']}_{current_date}.zip")
                    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                        for root, _, files in os.walk(src):
                            if 'backups' in root or f'{os.path.sep}backup' in root:
                                continue
                            for filename in files:
                                file_path = os.path.join(root, filename)
                                relative_path = os.path.relpath(file_path, src)
                                zipf.write(file_path, arcname=relative_path)
                    print(f"{GREEN}Backup ZIP created: {RESET}{zip_path}")

                else:
                    dated_backup_dir = os.path.join(dest_base, current_date)
                    os.makedirs(dated_backup_dir, exist_ok=True)

                    for root, _, files in os.walk(src):
                        if 'backups' in root or f'{os.path.sep}backup' in root:
                            continue
                        for filename in files:
                            file_path = os.path.join(root, filename)
                            relative_path = os.path.relpath(file_path, src)
                            target_subdir = os.path.join(dated_backup_dir, os.path.dirname(relative_path))
                            os.makedirs(target_subdir, exist_ok=True)

                            name, ext = os.path.splitext(filename)
                            backup_filename = f"{name} - backup {current_date}{ext}"
                            shutil.copy2(file_path, os.path.join(target_subdir, backup_filename))
                    
                    print(f"{GREEN}Directory backup completed for: {RESET}{src} -> {dated_backup_dir}")

        except Exception as e:
            print(f"Error during backup: {e}")

    def apply_movie_backup_filters(self, media_type: str, backup_candidate_tuples: List[Tuple[str, str]], backup_volume_root: str) -> List[Tuple[str, str]]: 
        """Filter movie backups using ratings, blocked keywords, file sizes, tmdb data."""
        if not backup_candidate_tuples:
            return []
        
        assert media_type.lower() in ["movies", "anime movies"], "Invalid media type for movie backup filters."
        
        drive_name = self.root_to_name.get(backup_volume_root)
        if not drive_name:
            return backup_candidate_tuples
            
        config_node = self.drive_config[media_type]['backup_drives'][drive_name]
        
        imdb_min = float(config_node["rating_minimum"])
        imdb_max = float(config_node["rating_maximum"])
        release_year_min = int(config_node["release_year_minimum"])
        release_year_max = int(config_node["release_year_maximum"])
        file_size_max_gb = float(config_node["maximum_file_size_GB"])
        backup_unknown_ratings = ast.literal_eval(config_node["backup_unknown_ratings"])
        exclude_strings = config_node["backup_exclusion_strings"]
        exclude_strings_exceptions = config_node["backup_exclusion_override_strings"]

        tmdb_filepath = os.path.join(self.output_directory, 'movies', 'tmdb.csv')
        tmdb_data = read_csv(tmdb_filepath)

        backup_tuple_accepted = []
        backup_filepaths_blocked = []
        backup_filepaths_revoked = []

        for filepath_primary, filepath_backup_candidate in backup_candidate_tuples:
            movie_with_year = os.path.splitext(os.path.basename(filepath_primary))[0]

            # Check for exceptions
            if any(exc.lower() in movie_with_year.lower() for exc in exclude_strings_exceptions):
                backup_tuple_accepted.append((filepath_primary, filepath_backup_candidate))
                continue

            # Find movie in TMDb data
            tmdb_entry = next((item for item in tmdb_data if item.get('Title_Alexandria') == movie_with_year), None)

            if not tmdb_entry or not 0 < float(tmdb_entry['Rating']) <= 10:
                if not backup_unknown_ratings:
                    if os.path.isfile(filepath_backup_candidate):
                        backup_filepaths_revoked.append(filepath_backup_candidate)
                    else:
                        backup_filepaths_blocked.append(filepath_backup_candidate)
                    
                    if 'featurettes' not in os.path.dirname(filepath_primary).lower():
                        print(f'\t{RED}{BRIGHT}[ALERT] {RESET}No (or invalid) TMDb data for: {movie_with_year}')
                else:
                    backup_tuple_accepted.append((filepath_primary, filepath_backup_candidate))
                continue

            # Check file size
            if get_file_size(filepath_primary, "GB") > file_size_max_gb:
                if os.path.isfile(filepath_backup_candidate):
                    backup_filepaths_revoked.append(filepath_backup_candidate)
                else:
                    backup_filepaths_blocked.append(filepath_backup_candidate)
                continue

            # Check rating
            movie_rating = float(tmdb_entry['Rating'])
            if not (imdb_min <= movie_rating <= imdb_max):
                if os.path.isfile(filepath_backup_candidate):
                    backup_filepaths_revoked.append(filepath_backup_candidate)
                else:
                    backup_filepaths_blocked.append(filepath_backup_candidate)
                continue

            # Check release year
            try:
                year = int(movie_with_year.split("(")[-1].split(')')[0])
                if not (release_year_min <= year <= release_year_max):
                    if os.path.isfile(filepath_backup_candidate):
                        backup_filepaths_revoked.append(filepath_backup_candidate)
                    else:
                        backup_filepaths_blocked.append(filepath_backup_candidate)
                    continue
            except (IndexError, ValueError):
                pass

            # Check for excluded strings
            if any(exc.lower() in movie_with_year.lower() for exc in exclude_strings):
                if os.path.isfile(filepath_backup_candidate):
                    backup_filepaths_revoked.append(filepath_backup_candidate)
                else:
                    backup_filepaths_blocked.append(filepath_backup_candidate)
                continue

            # If not filtered, add to accepted list
            backup_tuple_accepted.append((filepath_primary, filepath_backup_candidate))

        if backup_filepaths_revoked:
            self.remove_revoked_files(backup_filepaths_revoked)

        return backup_tuple_accepted

    def apply_show_backup_filters(self, media_type: str, backup_filepaths: Union[List[Tuple[str, str]], List[str]], backup_volume_root: str) -> Union[List[Tuple[str, str]], List[str], bool]:
        """Filters show backup file paths based on whitelist and blocked keywords."""
        if not backup_filepaths:
            return backup_filepaths

        adjusted_filepaths = []
        blocked_filepaths = []
        is_existing_backup = isinstance(backup_filepaths[0], str)
        
        drive_name = self.root_to_name.get(backup_volume_root, "").replace(' ', '_')
        whitelist_path = os.path.join(self.src_directory, "..", "config", "series_whitelists", "active", f"{drive_name}_whitelist.txt")
        
        if os.path.exists(whitelist_path):
            order_file_contents(whitelist_path)
            whitelist = read_file_as_list(whitelist_path)
        else:
            whitelist = []

        for file_entry in backup_filepaths:
            file_src = file_entry[0] if not is_existing_backup else file_entry
            file_dst = file_entry[1] if not is_existing_backup else file_entry

            path_parts = Path(file_src).parts
            # Assuming structure: Root/Media_Type/Show_Name/Season/File
            # We dynamically search the parts for the media type directory to safely get the show name
            try:
                media_idx = [p.lower() for p in path_parts].index(media_type.lower())
                show_with_year = path_parts[media_idx + 1]
            except (ValueError, IndexError):
                show_with_year = path_parts[-2]
                
            show_filename = os.path.basename(file_src)

            is_whitelisted = any(
                keyword.lower() in show_with_year.lower() or keyword.lower() in show_filename.lower()
                for keyword in whitelist
            )

            if is_whitelisted:
                adjusted_filepaths.append(file_entry)
            else:
                blocked_filepaths.append(file_dst)

        if is_existing_backup and blocked_filepaths:
            num_deleted = self.remove_revoked_files(blocked_filepaths)
            if num_deleted > 0:
                return False
            return adjusted_filepaths

        return adjusted_filepaths

    def apply_audio_file_backup_filters(self, media_type: str, backup_candidate_tuples: List[Tuple[str, str]], backup_volume_root: str) -> List[Tuple[str, str]]:
        """Filter audio file backups using Quality."""
        if not backup_candidate_tuples:
            return []
            
        drive_name = self.root_to_name.get(backup_volume_root)
        if not drive_name:
            return backup_candidate_tuples
            
        backup_quality = str(self.drive_config[media_type]['backup_drives'][drive_name]["quality"]).lower().strip()

        backup_tuple_accepted = []
        backup_filepaths_blocked = []
        backup_filepaths_revoked = []

        for filepath_primary, filepath_backup_candidate in backup_candidate_tuples:
            path_obj = Path(filepath_primary)
            
            # 1. Start with the immediate parent directory of the file
            parent_dir = path_obj.parent
            
            # 2. If the immediate parent is a "Disc" folder, step up one level to the Album folder
            if "disc " in parent_dir.name.lower() or "cd " in parent_dir.name.lower():
                album_dir = parent_dir.parent
            else:
                album_dir = parent_dir
                
            # 3. Extract quality assuming "AlbumName_QUALITY" format
            dir_quality = album_dir.name.split("_")[-1].lower() if "_" in album_dir.name else ""
            
            # 4. Determine final quality 
            file_quality = 'flac' if path_obj.suffix.lower() == '.flac' else dir_quality

            # Check quality against your config
            if file_quality not in backup_quality:
                if os.path.isfile(filepath_backup_candidate):
                    backup_filepaths_revoked.append(filepath_backup_candidate)
                else:
                    backup_filepaths_blocked.append(filepath_backup_candidate)
                continue

            backup_tuple_accepted.append((filepath_primary, filepath_backup_candidate))

        if backup_filepaths_revoked:
            self.remove_revoked_files(backup_filepaths_revoked)

        return backup_tuple_accepted

    def remove_revoked_files(self, filepaths_backup_revoked: list) -> int:
        """Removes excess files from backup drives."""
        num_files_deleted = 0
        total_size_gb = 0

        filepaths_backup_revoked = [fp for fp in filepaths_backup_revoked if os.path.isfile(fp)]

        if not filepaths_backup_revoked:
            return 0

        for idx, filepath in enumerate(filepaths_backup_revoked):
            if idx == 0: 
                print('\n')
            print(f'\t{RED}{BRIGHT}[ALERT] Revoked Backup File: {RESET} {filepath}')
            total_size_gb += get_file_size(filepath, "GB")

        confirmation_message = (
            f'\n\tDo you want to {RED}{BRIGHT}delete{RESET} these {len(filepaths_backup_revoked):,} revoked backup files '
            f'({int(total_size_gb):,} GB)? [Y/N] '
            if len(filepaths_backup_revoked) > 1
            else f'\n\tDo you want to {RED}{BRIGHT}delete{RESET} this revoked backup file? [Y/N] '
        )

        user_input = input(confirmation_message).strip().lower()
        while user_input not in ('y', 'n'):
            user_input = input("Invalid input. Please enter 'Y' or 'N': ").strip().lower()

        if user_input == 'y':
            for revoked_file in filepaths_backup_revoked:
                if '$Recycle' in revoked_file:
                    continue
                try:
                    print(f'\t{RED}{BRIGHT}Deleting: {RESET}{revoked_file}')
                    os.remove(revoked_file)
                    num_files_deleted += 1
                except Exception as e:
                    print(f'\t[WARN] Error deleting {revoked_file}: {e}')
                    
        return num_files_deleted

    def backup_integrity(self, existing_backup_tuples: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
        """Identifies and returns backup files that do not match the primary file."""
        modified_backup_filepath_tuples = []
        for primary_filepath, backup_filepath in existing_backup_tuples:
            try:
                if not os.path.isfile(primary_filepath) or not os.path.isfile(backup_filepath):
                    continue
                if not files_are_identical(primary_filepath, backup_filepath):
                    modified_backup_filepath_tuples.append((primary_filepath, backup_filepath))
            except Exception as e:
                print(f"Error processing {primary_filepath} and {backup_filepath}: {e}")
        return modified_backup_filepath_tuples

    def backup_mapper(self, media_type: str, backup_volume_root: str, primary_filepaths_dict: dict, bool_recursive: bool = False) -> Tuple[list, list, list, list]:
        """Maps and filters backup files OS-Agnostically using relative paths."""
        backup_path_base = os.path.join(backup_volume_root, media_type)
        os.makedirs(backup_path_base, exist_ok=True)

        filepaths_primary = primary_filepaths_dict[media_type]
        filepaths_backup = read_alexandria([backup_path_base], self.extensions_dict[media_type])

        # Safely map primary files to their relative destination path based on the media_type folder
        primary_rel_map = {}
        for fp in filepaths_primary:
            for p_root in self.primary_drives_root_dict[media_type]:
                p_base = os.path.join(p_root, media_type)
                if fp.startswith(p_base):
                    rel_path = os.path.relpath(fp, p_base)
                    primary_rel_map[rel_path] = fp
                    break

        backup_rel_map = {}
        for fp in filepaths_backup:
            rel_path = os.path.relpath(fp, backup_path_base)
            backup_rel_map[rel_path] = fp

        tuple_filepaths_missing = []
        tuple_filepaths_existing_backup = []

        for rel_path, primary_full_path in primary_rel_map.items():
            backup_full_path = os.path.join(backup_path_base, rel_path)
            if rel_path not in backup_rel_map:
                tuple_filepaths_missing.append((primary_full_path, backup_full_path))
            else:
                tuple_filepaths_existing_backup.append((primary_full_path, backup_full_path))

        # Apply media-specific filters
        if media_type.lower() in ["movies", "anime movies"]:
            tuple_filepaths_missing = self.apply_movie_backup_filters(media_type, tuple_filepaths_missing, backup_volume_root)
            tuple_filepaths_existing_backup = self.apply_movie_backup_filters(media_type, tuple_filepaths_existing_backup, backup_volume_root)

        elif media_type.lower() in ["shows", "anime"]:
            if not bool_recursive:
                filepaths_backup_current = self.apply_show_backup_filters(media_type, filepaths_backup, backup_volume_root)
                if not isinstance(filepaths_backup_current, list):
                    return self.backup_mapper(media_type, backup_volume_root, primary_filepaths_dict, bool_recursive=True)
            tuple_filepaths_missing = self.apply_show_backup_filters(media_type, tuple_filepaths_missing, backup_volume_root)

        elif media_type.lower() in ["music"]:
            tuple_filepaths_missing = self.apply_audio_file_backup_filters(media_type, tuple_filepaths_missing, backup_volume_root)
            tuple_filepaths_existing_backup = self.apply_audio_file_backup_filters(media_type, tuple_filepaths_existing_backup, backup_volume_root)

        # Identify excess and current backup files
        filepaths_backup_excess = []
        filepaths_backup_current = []
        
        for rel_path, backup_full_path in backup_rel_map.items():
            if rel_path not in primary_rel_map:
                filepaths_backup_excess.append(backup_full_path)
            else:
                filepaths_backup_current.append(backup_full_path)

        num_files_deleted = self.remove_revoked_files(filepaths_backup_excess)
        if num_files_deleted > 0 and not bool_recursive:
            return self.backup_mapper(media_type, backup_volume_root, primary_filepaths_dict, bool_recursive=True)

        tuple_filepaths_modified = self.backup_integrity(tuple_filepaths_existing_backup)

        return tuple_filepaths_missing, tuple_filepaths_modified, filepaths_backup_current, filepaths_backup_excess

    def assess_backup_feasibility(self, missing_filepaths: list, modified_filepaths: list) -> Tuple[float, float]:
        """Determine the feasibility of a backup by calculating required and remaining space."""
        # Find roots dynamically based on the backup destination file paths
        backup_drives = set()
        for _, backup_path in missing_filepaths + modified_filepaths:
            for root in self.backup_volume_roots:
                if backup_path.startswith(root):
                    backup_drives.add(root)

        remaining_space = sum(get_space_remaining(drive, "GB") for drive in backup_drives)
        required_space = sum(get_file_size(filepair[0], "GB") for filepair in missing_filepaths)

        for primary, backup in modified_filepaths:
            required_space += get_file_size(primary, "GB")
            remaining_space += get_file_size(backup, "GB")  

        return required_space, remaining_space

    def backup_function(self, backup_tuples: List[Tuple[str, str]], modified_tuples: List[Tuple[str, str]], media_type: str) -> None:
        """Handles backup of missing and modified files using shutil."""
        if backup_tuples:
            total_gb = sum(get_file_size(src, "GB") for src, _ in backup_tuples)
            
            # Determine destination root
            destination_path = backup_tuples[0][1]
            dest_root = next((r for r in self.backup_volume_roots if destination_path.startswith(r)), None)
            
            if not dest_root:
                print(f"{RED}Destination path is missing or invalid. Skipping backup.{RESET}")
                return

            available_gb = get_space_remaining(dest_root, "GB") - total_gb

            total_size_val, total_unit = human_readable_size(total_gb)
            remaining_val, remaining_unit = human_readable_size(available_gb)

            print(
                f"\n\tBacking up {RED}{len(backup_tuples):,} file{'s' if len(backup_tuples) != 1 else ''}{RESET} "
                f"({YELLOW}{total_size_val:.2f} {total_unit}{RESET}, "
                f"{GREEN}{remaining_val:.2f} {remaining_unit} will remain{RESET}):"
            )

            self._process_file_pairs(backup_tuples, action="Backing up", media_type=media_type)

        if modified_tuples:
            print(f"\n\tUpdating {RED}{len(modified_tuples):,} file{'s' if len(modified_tuples) != 1 else ''}{RESET}:")
            self._process_file_pairs(modified_tuples, action="Updating", media_type=media_type)

    def main(self) -> None:
        """Main function to initiate the Alexandria backup process."""
        print(f'\n{"#" * 10}\n\n{MAGENTA}{BRIGHT}Initiating Alexandria Backup...{RESET}\n\n{"#" * 10}\n')
        self.backup_mgmt_files()

        api = API()
        print(f'\n{"#" * 10}\n')
        print(f"{YELLOW}{BRIGHT}Refreshing{RESET} TMDb Movie Data\n")
        api.tmdb_movies_fetch()
        print(f'\n{"#" * 10}\n')

        for backup_volume_root in self.all_volume_roots:
            drive_backup_name = self.root_to_name.get(backup_volume_root, "Unknown Drive")
            print(f'\n### {GREEN}{BRIGHT}{drive_backup_name} ({backup_volume_root}){RESET} ###')

            for media_type in self.media_types:
                self._process_media_type_for_drive(media_type, backup_volume_root, drive_backup_name)

            self._log_remaining_space(backup_volume_root, drive_backup_name)

        self._display_drive_statistics()
        assess_backup()
        read_media_statistics(bool_update=False, bool_print=True)

        print(f'\n{"#" * 10}\n\n{GREEN}{BRIGHT}Alexandria Backup Complete{RESET}\n\n{"#" * 10}\n')

    def _process_file_pairs(self, file_pairs: List[Tuple[str, str]], action: str, media_type: str) -> None:
        """Process a list of file pairs natively using shutil."""
        for src_file, dest_file in file_pairs:
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
                    f"{YELLOW}{BRIGHT}\t{action} File:{RESET} {file_title} "
                    f"{RED}|{RESET} {Fore.BLUE}{src_name}{RESET} "
                    f"-> {GREEN}{dest_name}{RESET}"
                )
                try:
                    # Native cross-platform file copy replacing subprocess shell commands
                    shutil.copy2(src_file, dest_file)
                except Exception as e:
                    print(f"{RED}Error:{RESET} Failed to copy {file_title}: {e}")

    def _process_media_type_for_drive(self, media_type: str, backup_volume_root: str, drive_backup_name: str) -> None:
        """Process backup for a specific media type on a backup drive."""
        if not self._is_drive_associated_with_media_type(media_type, backup_volume_root):
            self._handle_undirected_backups(media_type, backup_volume_root)
            return

        # Skip if this drive is the primary source for this media
        if backup_volume_root in self.primary_drives_root_dict.get(media_type, []):
            return

        print(f'\n\tAssessing {YELLOW}{BRIGHT}{media_type}{RESET} in backup drive: '
              f'{GREEN}{BRIGHT}{drive_backup_name} ({backup_volume_root}){RESET}')

        primary_parent_paths = [os.path.join(r, media_type) for r in self.primary_drives_root_dict[media_type]]
        self.primary_filepaths_dict[media_type] = read_alexandria(primary_parent_paths, self.extensions_dict[media_type])

        missing, modified, current, excess = self.backup_mapper(
            media_type, backup_volume_root, self.primary_filepaths_dict
        )

        if excess:
            self.remove_revoked_files(excess)

        required_space, remaining_space = self.assess_backup_feasibility(missing, modified)
        if required_space > remaining_space:
            print(f'\n\t{Back.RED}[ALERT]{RESET} The {YELLOW}{media_type}{Fore.RESET} backup to the '
                  f'{YELLOW}{drive_backup_name} ({backup_volume_root}){Fore.RESET} is '
                  f'{RED}{BRIGHT}{abs(int(remaining_space - required_space)):,.0f} GB too large{RESET}')
        else:
            self.backup_function(missing, modified, media_type)

        # Remove empty sub-directories
        directories = primary_parent_paths + [os.path.join(backup_volume_root, media_type)]
        directories = list(dict.fromkeys(directories))
        remove_empty_folders(directories, print_line_prefix="\t", print_header="\n")

    def _is_drive_associated_with_media_type(self, media_type: str, backup_volume_root: str) -> bool:
        """Check if a backup drive is associated with the given media type."""
        return (
            backup_volume_root in self.backup_drives_root_dict.get(media_type, [])
            or backup_volume_root in self.primary_drives_root_dict.get(media_type, [])
        )

    def _handle_undirected_backups(self, media_type: str, backup_volume_root: str) -> None:
        """Handle undirected backups for drives that are not explicitly associated with a media type."""
        root_path = os.path.join(backup_volume_root, media_type)
        if os.path.exists(root_path):
            undirected_files = read_alexandria([root_path], self.extensions_dict[media_type])
            if undirected_files:
                self.remove_revoked_files(undirected_files)
                remove_empty_folders([root_path])

    def _log_remaining_space(self, backup_volume_root: str, drive_backup_name: str) -> None:
        """Log the remaining space on the backup drive."""
        space_remaining_tb = get_space_remaining(backup_volume_root, "TB")
        self.drive_stats_dict[drive_backup_name] = {"Space Remaining (TB)": space_remaining_tb}

        print(f'\n{MAGENTA}{BRIGHT}Space remaining{RESET} in '
              f'{GREEN}{BRIGHT}{drive_backup_name} ({backup_volume_root}){RESET}: '
              f'{BLUE}{BRIGHT}{space_remaining_tb:,.2f} TB{RESET}')

    def _display_drive_statistics(self) -> None:
        """Sort and display drive statistics."""
        self.drive_stats_dict = dict(sorted(self.drive_stats_dict.items(), key=lambda item: item[0].title()))
        
        print(f'\n##########\n\n{BRIGHT}Space Remaining on Drives{RESET}\n')
        for drive_name, stats in self.drive_stats_dict.items():
            print(f'{Fore.GREEN}{BRIGHT}{drive_name}:{RESET} {stats["Space Remaining (TB)"]:,.2f} TB')
        print('\n##########\n')

if __name__ == '__main__':
    backup = Backup()
    backup.main()