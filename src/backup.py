#!/usr/bin/env python

import datetime
import os
import shutil
import sys
import zipfile
from typing import List, Tuple

from utilities import (
    files_are_identical,
    generate_music_file_print_message,
    get_drive_letter,
    get_drive_name,
    get_file_size,
    get_space_remaining,
    read_alexandria,
    read_alexandria_config,
    read_csv,
    remove_empty_folders
)

sys.path.append(os.path.join(os.path.dirname(__file__), "analysis"))
from analysis.read_server_statistics import read_media_statistics
from analysis.assess_backup import main as assess_backup

from api import API

from colorama import Fore, Back, Style

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
        from utilities import get_drive_name, read_alexandria_config, read_json
        self.timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.src_directory = os.path.dirname(os.path.abspath(__file__))
        self.filepath_drive_hierarchy = os.path.join(self.src_directory, "..", "config", "alexandria_drives.config")
        self.output_directory = os.path.join(os.path.dirname(self.src_directory), "output")
        self.filepath_statistics = os.path.join(self.output_directory, "alexandria_media_statistics.json")
        self.filepath_alexandria_media_details = os.path.join(self.output_directory, "alexandria_media_details.json")

        # Read configuration and initialize dictionaries
        self.drive_config = read_json(self.filepath_drive_hierarchy)
        self.primary_drives_name_dict, self.backup_drives_name_dict, self.extensions_dict = read_alexandria_config(self.drive_config)
        self.primary_drives_letter_dict = {}
        self.backup_drives_letter_dict = {}
        for key,val in self.primary_drives_name_dict.items():
            self.primary_drives_letter_dict[key] = [get_drive_letter(name) for name in val]
        for key, val in self.backup_drives_name_dict.items():
            self.backup_drives_letter_dict[key] = [get_drive_letter(name) for name in val if get_drive_letter(name)]
        
        # Drive letters and names
        self.primary_drive_letters = []
        for val in self.primary_drives_letter_dict.values():
            if None not in val: 
                self.primary_drive_letters += val
            else:
                print(f"{RED}{BRIGHT}[ALERT] {RESET}Primary drive letter is None for {val}. Please check the drive configuration.")
                raise 
        self.primary_drive_letters = sorted(set(self.primary_drive_letters))
        self.backup_drive_letters = []
        for val in self.backup_drives_letter_dict.values():
            if val: self.backup_drive_letters += val
        self.backup_drive_letters = sorted(set(self.backup_drive_letters))
        self.all_drive_letters = sorted(set(self.primary_drive_letters + self.backup_drive_letters))
        self.backup_drive_names = [get_drive_name(drive) for drive in self.backup_drive_letters]

        # Media types and file paths
        self.media_types = list(self.primary_drives_letter_dict.keys())
        self.primary_filepaths_dict = {}
        self.drive_stats_dict = {}

    def backup_output_files(self, compress: bool = True) -> None:
        """Backs up all files in the output directory (recursively) to a dated backup folder or zip archive."""
        try:
            # Define the backup base path with current date
            current_date = datetime.datetime.now().strftime('%Y%m%d')
            backup_base = os.path.join(self.output_directory, 'backups')
            os.makedirs(backup_base, exist_ok=True)

            if compress:
                zip_path = os.path.join(backup_base, f'alexandria_output_backup_{current_date}.zip')
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for root, _, files in os.walk(self.output_directory):
                        if 'backups' in root:
                            continue
                        for filename in files:
                            file_path = os.path.join(root, filename)
                            relative_path = os.path.relpath(file_path, self.output_directory)
                            zipf.write(file_path, arcname=relative_path)
                print(f"{GREEN}Backup ZIP created: {RESET}{zip_path}")

            else:
                backup_dir = os.path.join(backup_base, current_date)
                os.makedirs(backup_dir, exist_ok=True)

                for root, _, files in os.walk(self.output_directory):
                    if 'backups' in root:
                        continue
                    for filename in files:
                        file_path = os.path.join(root, filename)
                        relative_path = os.path.relpath(file_path, self.output_directory)

                        # Create subdirectories in backup path
                        backup_subdir = os.path.join(backup_dir, os.path.dirname(relative_path))
                        os.makedirs(backup_subdir, exist_ok=True)

                        name, ext = os.path.splitext(filename)
                        backup_filename = f"{name} - backup {current_date}{ext}"
                        backup_file_path = os.path.join(backup_subdir, backup_filename)

                        shutil.copy2(file_path, backup_file_path)
                        print(f"{GREEN}Output file backed up: {RESET}{os.path.join('output', 'backups', current_date, relative_path)}")

        except Exception as e:
            print(f"Error during backup: {e}")

    def apply_movie_backup_filters(self, media_type: str, backup_candidate_tuples: list[tuple[str,str]]) -> list[tuple[str,str]]: 
        """Filter movie backups using ratings, blocked keywords, file sizes, tmdb data."""
        import ast

        if not backup_candidate_tuples or len(backup_candidate_tuples) == 0:
            return []
        
        # Validate input
        assert media_type.lower() in ["movies", "anime movies"], "Invalid media type for movie backup filters."
        assert isinstance(backup_candidate_tuples, list), "backup_filepaths must be a list."
        assert all(isinstance(item, tuple) and len(item) == 2 for item in backup_candidate_tuples), "backup_filepaths must be a list of tuples of length 2."
        assert all(isinstance(item[0], str) and isinstance(item[1], str) for item in backup_candidate_tuples), "Each tuple in backup_filepaths must contain two strings."

        drive_letters_backup = sorted(set({x[1][0] for x in backup_candidate_tuples}))

        # Initialize IMDb minimums and other configurations from drive config
        imdb_mins = {}
        imdb_maxes = {}
        release_year_min = {}
        release_year_max = {}
        backup_unknown_ratings = {}
        exclude_strings = {}
        exclude_strings_exceptions = {}
        file_size_max_GB = {}

        for drive_letter in drive_letters_backup:
            drive_name = get_drive_name(drive_letter)
            imdb_mins[drive_letter] = float(self.drive_config[media_type]['backup_drives'][drive_name]["rating_minimum"])
            imdb_maxes[drive_letter] = float(self.drive_config[media_type]['backup_drives'][drive_name]["rating_maximum"])
            release_year_min[drive_letter] = int(self.drive_config[media_type]['backup_drives'][drive_name]["release_year_minimum"])
            release_year_max[drive_letter] = int(self.drive_config[media_type]['backup_drives'][drive_name]["release_year_maximum"])
            file_size_max_GB[drive_letter] = float(self.drive_config[media_type]['backup_drives'][drive_name]["maximum_file_size_GB"])
            backup_unknown_ratings[drive_letter] = ast.literal_eval(self.drive_config[media_type]['backup_drives'][drive_name]["backup_unknown_ratings"])
            exclude_strings[drive_letter] = self.drive_config[media_type]['backup_drives'][drive_name]["backup_exclusion_strings"]
            exclude_strings_exceptions[drive_letter] = self.drive_config[media_type]['backup_drives'][drive_name]["backup_exclusion_override_strings"]

        # Read the most recent TMDb data
        tmdb_filepath = os.path.join(self.output_directory, 'movies', 'tmdb.csv')
        tmdb_data = read_csv(tmdb_filepath)

        # Initialize counters and lists
        backup_tuple_accepted = []
        backup_filepaths_blocked = []
        backup_filepaths_revoked = []
        num_not_in_tmdb = 0
        num_blocked_by_lack_of_tmbd_data = 0
        num_revoked_by_lack_of_tmbd_data = 0
        num_blocked_by_file_size = 0
        num_revoked_by_file_size = 0
        num_blocked_by_rating = 0
        num_revoked_by_rating = 0
        num_blocked_by_release_year = 0
        num_revoked_by_release_year = 0
        num_blocked_by_keyword = 0
        num_revoked_by_keyword = 0
        num_exceptions_by_keyword = 0
        exceptions_flagged_tmdb = [
            ""
        ]


        # Process each candidate backup tuple (primary source, backup destination)
        for backup_candidate_tuple in backup_candidate_tuples:
            filepath_primary = backup_candidate_tuple[0]
            # if 'featurettes' in os.path.dirname(filepath_primary).lower():
            #     continue
            filepath_backup_candidate = backup_candidate_tuple[1]
            movie_with_year = os.path.splitext(os.path.basename(filepath_primary))[0]
            backup_drive_letter = filepath_backup_candidate[0]

            # Check for exceptions
            if any(exc.lower() in movie_with_year.lower() for exc in exclude_strings_exceptions[filepath_backup_candidate[0]]):
                num_exceptions_by_keyword += 1
                backup_tuple_accepted.append((filepath_primary, filepath_backup_candidate))
                continue

            # Find movie in TMDb data
            tmdb_entry = next((item for item in tmdb_data if item.get('Title_Alexandria') == movie_with_year), None)

            if not tmdb_entry or not 0 < float(tmdb_entry['Rating']) <= 10:
                num_not_in_tmdb += 1
                if not backup_unknown_ratings[backup_drive_letter]:
                    if os.path.isfile(filepath_backup_candidate):
                        backup_filepaths_revoked.append(filepath_backup_candidate)
                        num_revoked_by_lack_of_tmbd_data += 1
                    else:
                        backup_filepaths_blocked.append(filepath_backup_candidate)
                        num_blocked_by_lack_of_tmbd_data += 1
                    if 'featurettes' not in os.path.dirname(filepath_primary).lower():
                        print(f'\t{RED}{BRIGHT}[ALERT] {RESET}No (or invalid) TMDb data for: {movie_with_year}')
                else:
                    backup_tuple_accepted.append(backup_candidate_tuple)
                continue

            # Check file size
            if get_file_size(filepath_primary,"GB") > float(file_size_max_GB[backup_drive_letter]):
                if os.path.isfile(filepath_backup_candidate):
                    backup_filepaths_revoked.append(filepath_backup_candidate)
                    num_revoked_by_file_size += 1
                else:
                    backup_filepaths_blocked.append(filepath_backup_candidate)
                    num_blocked_by_file_size += 1
                continue

            # Check rating
            movie_rating = float(tmdb_entry['Rating'])
            if not float(imdb_mins[backup_drive_letter]) <= movie_rating <= float(imdb_maxes[backup_drive_letter]):
                if os.path.isfile(filepath_backup_candidate):
                    backup_filepaths_revoked.append(filepath_backup_candidate)
                    num_revoked_by_rating += 1
                else:
                    # if abs(movie_rating-imdb_mins[backup_drive_letter]) <= .1: print(f"Rating: {movie_rating} | Min: {imdb_mins[backup_drive_letter]} | Max: {imdb_maxes[backup_drive_letter]}")
                    backup_filepaths_blocked.append(filepath_backup_candidate)
                    num_blocked_by_rating += 1
                continue

            # Check release year
            try:
                year = int(movie_with_year.split("(")[-1].split(')')[0])
                if not release_year_min[backup_drive_letter] <= year <= release_year_max[backup_drive_letter]:
                    if os.path.isfile(filepath_backup_candidate):
                        backup_filepaths_revoked.append(filepath_backup_candidate)
                        num_revoked_by_release_year += 1
                    else:
                        backup_filepaths_blocked.append(filepath_backup_candidate)
                        num_blocked_by_release_year += 1
                    continue
            except:
                pass

            # Check for excluded strings
            if any(exc.lower() in movie_with_year.lower() for exc in exclude_strings[backup_drive_letter]):
                if os.path.isfile(filepath_backup_candidate):
                    backup_filepaths_revoked.append(filepath_backup_candidate)
                    num_revoked_by_keyword += 1
                else:
                    backup_filepaths_blocked.append(filepath_backup_candidate)
                    num_blocked_by_keyword += 1
                continue

            # If not filtered, add to accepted list
            backup_tuple_accepted.append((filepath_primary, filepath_backup_candidate))

        # Remove revoked backup files
        if len(backup_filepaths_revoked) > 0:
            self.remove_revoked_files(backup_filepaths_revoked)

        return backup_tuple_accepted

    def apply_show_backup_filters(self, media_type: str, backup_filepaths: list[tuple[str,str]]) -> list[tuple[str,str]] | bool:
        """
        Filters show backup file paths based on whitelist and blocked keywords.

        Parameters
        ----------
        media_type : str
            The type of media being processed (e.g., 'shows', 'anime').
        backup_filepaths : list
            List of file paths to be filtered. Can contain either tuples (proposed backups)
            or strings (existing backups).

        Returns
        -------
        list
            Adjusted list of backup file paths. Returns False if excess files are removed
            during current backup assessment.

        Notes
        -----
        The function reads whitelists for each backup drive to filter file paths.
        """
        from utilities import get_drive_name, read_file_as_list, order_file_contents
        # Return immediately if no file paths are provided
        if not backup_filepaths:
            return backup_filepaths

        # Initialize variables
        adjusted_filepaths = []
        blocked_filepaths = []
        drive_whitelists = {}

        # Determine the type of input (proposed or existing backups)
        is_existing_backup = isinstance(backup_filepaths[0], str)
        backup_drives = (
            list({x[1][0] for x in backup_filepaths}) if not is_existing_backup
            else list({x[0] for x in backup_filepaths})
        )

        # Load whitelists for each backup drive
        src_directory = os.path.dirname(os.path.abspath(__file__))
        for drive_letter in backup_drives:
            whitelist_path = os.path.join(
                src_directory, "..", "config", "show_whitelists", "active",
                f"{get_drive_name(drive_letter).replace(' ', '_')}_whitelist.txt"
            ).replace("\\", "/")
            order_file_contents(whitelist_path)
            drive_whitelists[drive_letter] = read_file_as_list(whitelist_path)

        # Process each file path
        for file_entry in backup_filepaths:
            # Determine source and destination paths
            file_src = file_entry[0] if not is_existing_backup else file_entry
            file_dst = file_entry[1] if not is_existing_backup else file_entry

            # Extract show-related details
            show_with_year = file_src.split('/')[2]  # Assuming this structure is consistent
            show_filename = os.path.basename(file_src)

            # Check if the show is in the whitelist
            drive_letter = file_dst[0]
            is_whitelisted = any(
                keyword.lower() in show_with_year.lower() or keyword.lower() in show_filename.lower()
                for keyword in drive_whitelists.get(drive_letter, [])
            )

            if is_whitelisted:
                adjusted_filepaths.append(file_entry)
            else:
                blocked_filepaths.append(file_dst)

        # Handle excess files for existing backups
        if is_existing_backup and blocked_filepaths:
            num_deleted = self.remove_revoked_files(blocked_filepaths)
            if num_deleted > 0:
                return False
            return adjusted_filepaths

        return adjusted_filepaths

    def apply_audio_file_backup_filters(self, media_type, backup_candidate_tuples: list[tuple[str,str]]) -> list[tuple[str,str]]:

        """Filter audio file backups using Quality, <>..."""
        import ast

        if not backup_candidate_tuples:
            return []
        
        # Validate input
        assert isinstance(backup_candidate_tuples, list), "backup_candidate_tuples must be a list."
        assert all(isinstance(item, tuple) and len(item) == 2 for item in backup_candidate_tuples), "backup_candidate_tuples must be a list of tuples of length 2."
        assert all(isinstance(item[0], str) and isinstance(item[1], str) for item in backup_candidate_tuples), "Each tuple in backup_candidate_tuples must contain two strings."

        drive_letters_backup = sorted(set({x[1][0] for x in backup_candidate_tuples}))

        # Initialize IMDb minimums and other configurations from drive config
        backup_qualities = {}
        for drive_letter in drive_letters_backup:
            drive_name = get_drive_name(drive_letter)
            backup_qualities[drive_letter] = str(self.drive_config[media_type]['backup_drives'][drive_name]["quality"]).lower().strip()

        # Initialize counters and lists
        backup_tuple_accepted = []
        backup_filepaths_blocked = []
        backup_filepaths_revoked = []
        num_revoked_by_quality = 0

        # Process each candidate backup tuple (primary source, backup destination)
        for backup_candidate_tuple in backup_candidate_tuples:
            filepath_primary = backup_candidate_tuple[0]
            filepath_backup_candidate = backup_candidate_tuple[1]
            backup_drive_letter = filepath_backup_candidate[0]
            path_parts = os.path.normpath(filepath_primary).split(os.sep)
            dir_quality = path_parts[2].split("_")[-1].lower() if len(path_parts) > 2 else ""
            file_quality = 'flac' if '.flac' in filepath_primary.lower() else dir_quality

            # Check quality
            if file_quality not in backup_qualities[backup_drive_letter]:
                if os.path.isfile(filepath_backup_candidate):
                    backup_filepaths_revoked.append(filepath_backup_candidate)
                    num_revoked_by_quality += 1
                else:
                    backup_filepaths_blocked.append(filepath_backup_candidate)
                    num_revoked_by_quality += 1
                continue

            # If not filtered, add to accepted list
            backup_tuple_accepted.append((filepath_primary, filepath_backup_candidate))

        # Remove revoked backup files
        if len(backup_filepaths_revoked) > 0:
            self.remove_revoked_files(backup_filepaths_revoked)

        return backup_tuple_accepted

    def remove_revoked_files(self, filepaths_backup_revoked: list) -> int:
        """Removes excess files from backup drives."""
        from utilities import get_file_size
        num_files_deleted = 0
        total_size_gb = 0

        # Check if the excess files exist
        filepaths_backup_revoked = [fp for fp in filepaths_backup_revoked if os.path.isfile(fp)]

        # Check if there are any excess files
        if len(filepaths_backup_revoked) == 0:
            return 0

        for idx, filepath in enumerate(filepaths_backup_revoked):
            if idx == 0: print('\n')
            print(F'\t{RED}{BRIGHT}[ALERT] Revoked Backup File: {RESET} {filepath}')
            total_size_gb += get_file_size(filepath,"GB")

        # User confirmation
        confirmation_message = (
            f'\n\tDo you want to {RED}{BRIGHT}delete{RESET} these {len(filepaths_backup_revoked):,} revoked backup files '
            f'({int(total_size_gb):,} GB)? [Y/N] '
            if len(filepaths_backup_revoked) > 1
            else f'\n\tDo you want to {RED}{BRIGHT}delete{RESET} this revoked backup file? [Y/N] '
        )

        user_input = input(confirmation_message).strip().lower()
        while user_input not in ('y', 'n'):
            user_input = input("Invalid input. Please enter 'Y' or 'N': ").strip().lower()

        # Proceed with deletion if confirmed
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
                # Skip if either the primary or backup file is missing
                if not os.path.isfile(primary_filepath) or not os.path.isfile(backup_filepath):
                    continue

                # Check if files are not identical
                if not files_are_identical(primary_filepath, backup_filepath):
                    modified_backup_filepath_tuples.append((primary_filepath, backup_filepath))
            except Exception as e:
                print(f"Error processing {primary_filepath} and {backup_filepath}: {e}")
        return modified_backup_filepath_tuples

    def backup_mapper(self,media_type: str, drive_backup_letter: str, primary_filepaths_dict: dict, bool_recursive: bool=False) -> Tuple[list, list, list, list]:
        """Maps and filters backup files for a given media type and drive."""
        # Ensure backup directory exists
        backup_path = os.path.join(f"{drive_backup_letter}:/", media_type)
        os.makedirs(backup_path, exist_ok=True)

        # Load file extensions and initialize variables
        extensions_dict = read_alexandria_config(self.drive_config)[2]
        filepaths_primary = primary_filepaths_dict[media_type]
        filepaths_primary_no_letter = [fp[1:] for fp in filepaths_primary]
        filepaths_backup = read_alexandria([backup_path], extensions_dict[media_type])
        filepaths_backup_no_letter = [fp[1:] for fp in filepaths_backup]

        tuple_filepaths_missing = []
        tuple_filepaths_existing_backup = []

        # Identify missing and existing backup files
        for idx, primary_no_letter in enumerate(filepaths_primary_no_letter):
            primary_full_path = filepaths_primary[idx][0] + primary_no_letter
            if primary_no_letter not in filepaths_backup_no_letter:
                # Backup file is missing
                backup_full_path = drive_backup_letter + primary_no_letter
                tuple_filepaths_missing.append((primary_full_path, backup_full_path))
            else:
                # Backup file exists               
                backup_full_path = drive_backup_letter + primary_no_letter
                tuple_filepaths_existing_backup.append((primary_full_path, backup_full_path))

        # Apply media-specific filters
        if media_type.lower() in ["movies", "anime movies"]:
            tuple_filepaths_missing = self.apply_movie_backup_filters(media_type, tuple_filepaths_missing)
            tuple_filepaths_existing_backup = self.apply_movie_backup_filters(media_type, tuple_filepaths_existing_backup)

        elif media_type.lower() in ["shows", "anime"]:
            if not bool_recursive:
                filepaths_backup_current = self.apply_show_backup_filters(media_type, filepaths_backup)
                if not isinstance(filepaths_backup_current, list):
                    return self.backup_mapper(media_type, drive_backup_letter, primary_filepaths_dict, bool_recursive=True)
            tuple_filepaths_missing = self.apply_show_backup_filters(media_type, tuple_filepaths_missing)

        elif media_type.lower() in ["music","audiobooks"]:
            tuple_filepaths_missing = self.apply_audio_file_backup_filters(media_type, tuple_filepaths_missing)
            tuple_filepaths_existing_backup = self.apply_audio_file_backup_filters(media_type, tuple_filepaths_existing_backup)

        # Identify excess and current backup files
        filepaths_backup_excess = []
        filepaths_backup_current = []
        primary_no_letter_set = set(filepaths_primary_no_letter)

        for idx, backup_no_letter in enumerate(filepaths_backup_no_letter):
            backup_full_path = filepaths_backup[idx][0] + backup_no_letter
            if backup_no_letter not in primary_no_letter_set:
                filepaths_backup_excess.append(backup_full_path)
            else:
                filepaths_backup_current.append(backup_full_path)

        # Remove excess backup files
        num_files_deleted = self.remove_revoked_files(filepaths_backup_excess)
        if num_files_deleted > 0 and not bool_recursive:
            return self.backup_mapper(media_type, drive_backup_letter, primary_filepaths_dict, bool_recursive=True)

        # Check for modified files
        tuple_filepaths_modified = self.backup_integrity(tuple_filepaths_existing_backup)

        return tuple_filepaths_missing, tuple_filepaths_modified, filepaths_backup_current, filepaths_backup_excess

    def assess_backup_feasibility(self, 
                                  missing_filepaths: list, 
                                  modified_filepaths: list
                                  ) -> Tuple[float, float]:
        """Determine the feasibility of a backup by calculating required and remaining space."""
        # Import any necessary utilities
        from utilities import get_space_remaining, get_file_size

        # Determine all backup drives involved
        backup_drives = set([filepair[1][0] for filepair in missing_filepaths] +
                            [filepair[1][0] for filepair in modified_filepaths])

        # Calculate total remaining space across all drives
        remaining_space = sum(get_space_remaining(drive,"GB") for drive in backup_drives)

        # Calculate required backup space
        required_space = sum(get_file_size(filepair[0],"GB") for filepair in missing_filepaths)

        # Adjust for modified files (add new versions and subtract old ones)
        for primary, backup in modified_filepaths:
            required_space += get_file_size(primary,"GB")
            remaining_space += get_file_size(backup,"GB")  # Reclaim space from the old backup version

        return required_space, remaining_space

    def backup_function(self, 
                        backup_tuples: List[Tuple[str, str]], 
                        modified_tuples: List[Tuple[str, str]]
                        ) -> None:
        """
        Handles backup of missing and modified files in batch.

        Parameters
        ----------
        backup_tuples : List[Tuple[str, str]]
            List of new file backup pairs as (src, dest).

        modified_tuples : List[Tuple[str, str]]
            List of modified file pairs as (src, dest).

        Returns
        -------
        None
        """
        from utilities import human_readable_size, get_file_size, get_space_remaining

        # Handle new backups
        if backup_tuples:
            # Calculate total backup size in GB
            total_gb = sum(get_file_size(src, "GB") for src, _ in backup_tuples)
            
            # Determine available space on destination drive
            destination_path = backup_tuples[0][1]
            if not destination_path:
                print(f"{RED}Destination path is missing. Skipping backup.{RESET}")
                return

            available_gb = get_space_remaining(destination_path[0], "GB") - total_gb

            # Format sizes for output
            total_size_val, total_unit = human_readable_size(total_gb)
            remaining_val, remaining_unit = human_readable_size(available_gb)

            print(
                f"\n\tBacking up {RED}{len(backup_tuples):,} file{'s' if len(backup_tuples) != 1 else ''}{RESET} "
                f"({YELLOW}{total_size_val:.2f} {total_unit}{RESET}, "
                f"{GREEN}{remaining_val:.2f} {remaining_unit} will remain{RESET}):"
            )

            self._process_file_pairs(backup_tuples, action="Backing up")

        # Handle modified files
        if modified_tuples:
            print(f"\n\tUpdating {RED}{len(modified_tuples):,} file{'s' if len(modified_tuples) != 1 else ''}{RESET}:")
            self._process_file_pairs(modified_tuples, action="Updating")

    def main(self) -> None:
        """Main function to initiate the Alexandria backup process."""
        print(f'\n{"#" * 10}\n\n{MAGENTA}{BRIGHT}Initiating Alexandria Backup...{RESET}\n\n{"#" * 10}\n')
        # Back up output files
        self.backup_output_files()

        # Update TMDb data
        api = API()
        print(f'\n{"#" * 10}\n')
        print(f"{YELLOW}{BRIGHT}Refreshing{RESET} TMDb Movie Data\n")
        api.tmdb_movies_fetch()
        print(f'\n{"#" * 10}\n')

        # Iterate through all backup drives
        for drive_backup_letter in self.all_drive_letters:
            drive_backup_name = get_drive_name(drive_backup_letter)
            print(f'\n### {GREEN}{BRIGHT}{drive_backup_name} ({drive_backup_letter.upper()} drive){RESET} ###')

            # Process each media type for the current drive
            for media_type in self.media_types:
                self._process_media_type_for_drive(
                    media_type, drive_backup_letter, drive_backup_name
                )

            # Display remaining space on the drive
            self._log_remaining_space(drive_backup_letter, drive_backup_name)

        # Display drive statistics and display summary
        self._display_drive_statistics()
        assess_backup()
        read_media_statistics(bool_update=False, bool_print=True)
        # read_media_file_data(self.filepath_alexandria_media_details, bool_update=False)

        # Final message
        print(f'\n{"#" * 10}\n\n{GREEN}{BRIGHT}Alexandria Backup Complete{RESET}\n\n{"#" * 10}\n')

    def _process_file_pairs(self, file_pairs: List[Tuple[str, str]], action: str) -> None:
        import subprocess
        """Process a list of file pairs (source, destination) for backup or update."""
        for src_file, dest_file in file_pairs:
            media_type = os.path.split(src_file)[0].split('/')[1]
            ext = os.path.splitext(src_file)[1].lower() 
            if media_type == "Music" and ext in ['.mp3', '.flac']:
                file_title = generate_music_file_print_message(src_file)
            else:
                file_title = '.'.join(os.path.basename(src_file).strip().split('.')[:-1])
            if os.path.isfile(src_file):
                dest_dir = os.path.dirname(dest_file)
                os.makedirs(dest_dir, exist_ok=True)
                print(
                    f"{YELLOW}{BRIGHT}\t{action} File:{RESET} {file_title} "
                    f"{RED}|{RESET} {Fore.BLUE}{get_drive_name(src_file[0])}{RESET} "
                    f"-> {GREEN}{get_drive_name(dest_file[0])}{RESET}"
                )
                try:
                    cmd = fr'copy "{src_file}" "{dest_file}"'.replace('/', '\\')
                    result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    if result.returncode != 0:
                        print(f"{RED}Error:{RESET} Failed to copy {file_title}: {result.stderr.decode()}")
                except Exception as e:
                    print(f"{RED}Exception:{RESET} {e}")

    def _process_media_type_for_drive(self, media_type: str, drive_backup_letter: str, drive_backup_name: str) -> None:
        """Process backup for a specific media type on a backup drive."""
        # Skip if the drive is not associated with the media type
        if not self._is_drive_associated_with_media_type(media_type, drive_backup_letter):
            self._handle_undirected_backups(media_type, drive_backup_letter)
            return

        # Skip primary drives
        if drive_backup_letter in self.primary_drives_letter_dict[media_type]:
            return

        print(f'\n\tAssessing {YELLOW}{BRIGHT}{media_type}{RESET} in backup drive: '
            f'{GREEN}{BRIGHT}{drive_backup_name} ({drive_backup_letter.upper()} drive){RESET}')

        # Determine primary parent paths and collect file paths for this media type
        primary_parent_paths = [f'{x}:/{media_type}' for x in self.primary_drives_letter_dict[media_type]]
        primary_filepaths = read_alexandria(primary_parent_paths, self.extensions_dict[media_type])
        self.primary_filepaths_dict[media_type] = primary_filepaths

        # Map backup files and determine feasibility
        missing, modified, current, excess = self.backup_mapper(
            media_type, drive_backup_letter, self.primary_filepaths_dict
        )

        # Remove excess files if necessary
        if len(excess) > 0:
            self.remove_revoked_files(excess)

        # Assess feasibility and proceed with backup if possible
        required_space, remaining_space = self.assess_backup_feasibility(missing, modified)
        if required_space > remaining_space:
            print(f'\n\t{Back.RED}[ALERT]{RESET} The {YELLOW}{media_type}{Fore.RESET} backup to the '
                f'{YELLOW}{drive_backup_name} ({drive_backup_letter}) drive{Fore.RESET} is '
                f'{RED}{BRIGHT}{abs(int(remaining_space - required_space)):,.0f} GB too large{RESET}')
        else:
            self.backup_function(missing, modified)

        # Remove empty sub-directories
        directories = primary_parent_paths
        directories += [os.path.join(f'{p}:/', m) for p in drive_backup_letter for m in self.media_types]
        # directories.append(f'{drive_backup_letter}:/')
        directories = list(dict.fromkeys(directories))
        remove_empty_folders(directories, print_line_prefix="\t", print_header="\n")

    def _is_drive_associated_with_media_type(self, media_type: str, drive_backup_letter: str) -> bool:
        """Check if a backup drive is associated with the given media type."""
        return (
            drive_backup_letter in self.backup_drives_letter_dict[media_type]
            or drive_backup_letter in self.primary_drives_letter_dict[media_type]
        )

    def _handle_undirected_backups(self, media_type: str, drive_backup_letter: str) -> None:
        """Handle undirected backups for drives that are not explicitly associated with a media type."""
        root_path = f'{drive_backup_letter}:/{media_type}'
        undirected_files = read_alexandria([root_path], self.extensions_dict[media_type])

        if undirected_files:
            self.remove_revoked_files(undirected_files)
            remove_empty_folders([root_path])

    def _log_remaining_space(self, drive_backup_letter: str, drive_backup_name: str) -> None:
        """Log the remaining space on the backup drive."""
        space_remaining_tb = get_space_remaining(drive_backup_letter,"TB")
        self.drive_stats_dict[drive_backup_name] = {"Space Remaining (TB)": space_remaining_tb}

        print(f'\n{MAGENTA}{BRIGHT}Space remaining{RESET} in '
            f'{GREEN}{BRIGHT}{drive_backup_name} ({drive_backup_letter.upper()} drive){RESET}: '
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

"""
NOTES:
- add context to revoke backup files
- keep track of user choices in the event the same action is asked multiple times
"""