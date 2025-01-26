#!/usr/bin/env python

# define libraries
libraries = [['os'],
             ['typing',['List','Tuple']],
             ['colorama',['Fore','Back','Style']]
             ]
from utilities import import_libraries
import_libraries(libraries)

from typing import List, Tuple
from colorama import Fore, Back, Style
from utilities import files_are_identical, read_alexandria, read_alexandria_config, read_csv, read_json
from utilities import get_drive_letter, get_drive_name, get_file_size, get_space_remaining, remove_empty_folders

import os
import shutil
import datetime

class Backup:
    def __init__(self):
        """
        Initialize the Backup class and set up essential attributes.
        """
        from analytics import read_media_statistics, read_media_file_data
        from utilities import get_drive_name, read_alexandria_config, read_json
        self.timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.src_directory = os.path.dirname(os.path.abspath(__file__))
        self.filepath_drive_hierarchy = os.path.join(self.src_directory, "config", "alexandria_drives.config").replace("\\", "/")
        self.output_directory = os.path.join(os.path.dirname(self.src_directory), "output").replace("\\", "/")
        self.filepath_statistics = os.path.join(self.output_directory, "alexandria_media_statistics.json")
        self.filepath_alexandria_media_details = os.path.join(self.output_directory, "alexandria_media_details.json").replace("\\", "/")

        # Read configuration and initialize dictionaries
        self.drive_config = read_json(self.filepath_drive_hierarchy)
        self.primary_drives_letter_dict, self.backup_drives_letter_dict, self.extensions_dict = read_alexandria_config(self.drive_config)

        # Drive letters and names
        self.primary_drive_letters = self._get_drive_letters(self.primary_drives_letter_dict)
        self.backup_drive_letters = self._get_drive_letters(self.backup_drives_letter_dict)
        self.all_drives = sorted(set(self.primary_drive_letters + self.backup_drive_letters))
        self.backup_drive_letters = sorted(set(self.backup_drive_letters))
        self.backup_drive_names = [get_drive_name(drive) for drive in self.backup_drive_letters]

        # Media types and file paths
        self.media_types = list(self.primary_drives_letter_dict.keys())
        self.primary_filepaths_dict = {}
        self.drive_stats_dict = {}


    def backup_output_files(self):
        """
        Backs up all files from the specified output directory to a dated backup folder.

        Args:
            output_dir (str): The directory containing files to back up.

        Returns:
            None
        """
        try:
            # Define the backup directory path with current date
            current_date = datetime.now().strftime('%Y%m%d')
            backup_dir = os.path.join(self.output_directory, 'backups', current_date)

            # Create the backup directory if it doesn't exist
            os.makedirs(backup_dir, exist_ok=True)

            # Loop through all files in the output directory
            for filename in os.listdir(self.output_directory):
                file_path = os.path.join(self.output_directory, filename)

                # Skip directories, process only files
                if os.path.isfile(file_path):
                    # Generate the backup file name
                    backup_filename = f"{os.path.splitext(filename)[0]} - backup {current_date}{os.path.splitext(filename)[1]}"
                    backup_file_path = os.path.join(backup_dir, backup_filename)

                    # Copy the file to the backup directory with the new name
                    shutil.copy2(file_path, backup_file_path)

                    print(f"Backed up: {filename} -> {backup_file_path}")

            print(f"\nBackup completed successfully. Files saved to: {backup_dir}")

        except Exception as e:
            print(f"Error during backup: {e}")


    def apply_show_backup_filters(self, media_type: str, backup_filepaths: list):
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
        from utilities import get_drive_name, read_file_as_list
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
                src_directory, "config", "show_whitelists",
                f"{get_drive_name(drive_letter).replace(' ', '_')}_whitelist.txt"
            ).replace("\\", "/")
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
            num_deleted = self.remove_excess_files(blocked_filepaths, updated_block_list=True)
            if num_deleted > 0:
                return False
            return adjusted_filepaths

        return adjusted_filepaths
    

    def remove_excess_files(self, filepaths_backup_excess, updated_block_list=False, non_configured_backup=False):
        """
        Removes excess files from backup drives.

        Parameters
        ----------
        filepaths_backup_excess : list
            List of excess file paths to be removed.
        updated_block_list : bool, optional
            Indicates if the files are blocked by backup config settings. Default is False.
        non_configured_backup : bool, optional
            Indicates if the files are not expected to be backed up on this drive. Default is False.

        Returns
        -------
        int
            Number of files successfully deleted.
        """
        from utilities import get_file_size
        num_files_deleted = 0
        total_size_gb = 0

        # Check if there are any excess files
        if not filepaths_backup_excess:
            return 0

        # Determine the message based on the context
        if updated_block_list:
            context_message = "blocked by backup config settings"
        elif non_configured_backup:
            context_message = "not expected to be backed up on this drive"
        else:
            context_message = "not in the primary drives"

        print(f'\n{len(filepaths_backup_excess):,} excess {"file is" if len(filepaths_backup_excess) == 1 else "files are"} {context_message}:')
        for filepath in filepaths_backup_excess:
            print(filepath)
            total_size_gb += get_file_size(filepath)

        # User confirmation
        confirmation_message = (
            f'\nDo you want to delete these {len(filepaths_backup_excess):,} items '
            f'({int(total_size_gb):,} GB)? [Y/N] '
            if len(filepaths_backup_excess) > 1
            else '\nDo you want to delete this item? [Y/N] '
        )

        user_input = input(confirmation_message).strip().lower()
        while user_input not in ('y', 'n'):
            user_input = input("Invalid input. Please enter 'Y' or 'N': ").strip().lower()

        # Proceed with deletion if confirmed
        if user_input == 'y':
            for excess_file in filepaths_backup_excess:
                if '$Recycle' in excess_file:
                    continue
                try:
                    print(f'Deleting: {excess_file}')
                    os.remove(excess_file)
                    num_files_deleted += 1
                except Exception as e:
                    print(f'Error deleting {excess_file}: {e}')

        return num_files_deleted


    def backup_mapper(self,media_type: str, drive_backup_letter: str, primary_filepaths_dict: dict, bool_recursive=False):
        """
        Maps and filters backup files for a given media type and drive.

        Parameters
        ----------
        media_type : str
            The type of media (e.g., 'movies', 'shows').
        drive_backup_letter : str
            The drive letter of the backup drive (e.g., 'D').
        primary_filepaths_dict : dict
            A dictionary containing primary file paths grouped by media type.
        bool_recursive : bool, optional
            Whether the function is running recursively (default is False).

        Returns
        -------
        tuple_filepaths_missing : list
            List of missing backup file paths as tuples (primary, backup).
        tuple_filepaths_modified : list
            List of modified backup file paths as tuples (primary, backup).
        filepaths_backup_current : list
            List of currently valid backup file paths.
        filepaths_backup_excess : list
            List of excess backup file paths.
        """
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
                backup_full_path = os.path.join(backup_path, primary_no_letter)
                tuple_filepaths_missing.append((primary_full_path, backup_full_path))
            else:
                # Backup file exists
                backup_idx = filepaths_backup_no_letter.index(primary_no_letter)
                backup_full_path = filepaths_backup[backup_idx][0] + primary_no_letter
                tuple_filepaths_existing_backup.append((primary_full_path, backup_full_path))

        # Apply media-specific filters
        if media_type.lower() in ["movies", "anime movies"]:
            tuple_filepaths_missing = self.apply_movie_backup_filters(media_type, tuple_filepaths_missing)
            if not bool_recursive:
                self.apply_movie_backup_filters(media_type, filepaths_backup)

        elif media_type.lower() in ["shows", "anime"]:
            if not bool_recursive:
                filepaths_backup_current = self.apply_show_backup_filters(media_type, filepaths_backup)
                if not isinstance(filepaths_backup_current, list):
                    return self.backup_mapper(media_type, drive_backup_letter, primary_filepaths_dict, bool_recursive=True)
        tuple_filepaths_missing = self.apply_show_backup_filters(media_type, tuple_filepaths_missing)

        # Identify excess and current backup files
        filepaths_backup_excess = []
        filepaths_backup_current = []
        primary_no_letter_set = set(filepaths_primary_no_letter)

        for idx, backup_no_letter in enumerate(self.filepaths_backup_no_letter):
            backup_full_path = filepaths_backup[idx][0] + backup_no_letter
            if backup_no_letter not in primary_no_letter_set:
                filepaths_backup_excess.append(backup_full_path)
            else:
                filepaths_backup_current.append(backup_full_path)

        # Remove excess backup files
        num_files_deleted = self.remove_excess_files(filepaths_backup_excess)
        if num_files_deleted > 0 and not bool_recursive:
            return self.backup_mapper(media_type, drive_backup_letter, primary_filepaths_dict, bool_recursive=True)

        # Check for modified files
        tuple_filepaths_modified = backup_integrity(tuple_filepaths_existing_backup)

        return tuple_filepaths_missing, tuple_filepaths_modified, filepaths_backup_current, filepaths_backup_excess


    def assess_backup_feasibility(missing_filepaths, modified_filepaths):
        """
        Determine the feasibility of a backup by calculating required and remaining space.

        Parameters
        ----------
        missing_filepaths : list
            List of missing file tuples. Format: [(primary, backup), (primary, backup), ...]
        modified_filepaths : list
            List of modified file tuples. Format: [(primary, backup), (primary, backup), ...]

        Returns
        -------
        required_space : float
            Total space (in GB) required for the backup.
        remaining_space : float
            Total remaining space (in GB) across the backup drives.
        """
        # Import any necessary utilities
        import os
        from utilities import get_space_remaining, get_file_size

        # Determine all backup drives involved
        backup_drives = set([filepair[1][0] for filepair in missing_filepaths] +
                            [filepair[1][0] for filepair in modified_filepaths])

        # Calculate total remaining space across all drives
        remaining_space = sum(get_space_remaining(drive) for drive in backup_drives)

        # Calculate required backup space
        required_space = sum(get_file_size(filepair[0]) for filepair in missing_filepaths)

        # Adjust for modified files (add new versions and subtract old ones)
        for primary, backup in modified_filepaths:
            required_space += get_file_size(primary)
            remaining_space += get_file_size(backup)  # Reclaim space from the old backup version

        return required_space, remaining_space


    def backup_function(self,backup_tuples: List[Tuple[str, str]], modified_tuples: List[Tuple[str, str]]) -> None:
        """
        Batch backup function to handle missing and modified file backups.

        Parameters
        ----------
        backup_tuples : list
            List of backup file tuples. Format: [(src, dest), (src, dest), ...]
        modified_tuples : list
            List of modified file tuples. Format: [(src, dest), (src, dest), ...]

        Returns
        -------
        None
        """
        import subprocess
        from utilities import get_file_size, get_space_remaining, get_drive_name
        def process_file_pairs(file_pairs: List[Tuple[str, str]], action: str) -> None:
            """
            Process a list of file pairs (source, destination) for backup or update.

            Parameters
            ----------
            file_pairs : list
                List of file tuples. Format: [(src, dest), (src, dest), ...]
            action : str
                Action type ('Backing up' or 'Updating').

            Returns
            -------
            None
            """
            for src_file, dest_file in file_pairs:
                file_title = os.path.basename(src_file).strip()
                if os.path.isfile(src_file):
                    dest_dir = os.path.dirname(dest_file)
                    os.makedirs(dest_dir, exist_ok=True)
                    print(
                        f"{Fore.YELLOW}{Style.BRIGHT}\t{action} File:{Style.RESET_ALL} {file_title} "
                        f"{Fore.RED}|{Style.RESET_ALL} {Fore.BLUE}{get_drive_name(src_file[0])}{Style.RESET_ALL} "
                        f"-> {Fore.GREEN}{get_drive_name(dest_file[0])}{Style.RESET_ALL}"
                    )
                    try:
                        cmd = fr'copy "{src_file}" "{dest_file}"'.replace('/', '\\')
                        result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        if result.returncode != 0:
                            print(f"{Fore.RED}Error:{Style.RESET_ALL} Failed to copy {file_title}: {result.stderr.decode()}")
                    except Exception as e:
                        print(f"{Fore.RED}Exception:{Style.RESET_ALL} {e}")

        # Process backup tuples
        if backup_tuples:
            total_backup_size = sum(get_file_size(src) for src, _ in backup_tuples)
            remaining_space = get_space_remaining(backup_tuples[0][1][0]) - total_backup_size
            print(
                f"\nBacking up {Fore.RED}{len(backup_tuples):,} file(s){Style.RESET_ALL} "
                f"({Fore.YELLOW}{int(total_backup_size):,} GB{Style.RESET_ALL}, "
                f"{Fore.GREEN}{int(remaining_space):,} GB remaining{Style.RESET_ALL}):"
            )
            process_file_pairs(backup_tuples, action="Backing up")

        # Process modified tuples
        if modified_tuples:
            print(f"\nUpdating {Fore.RED}{len(modified_tuples):,} file(s){Style.RESET_ALL}:")
            process_file_pairs(modified_tuples, action="Updating")


    def backup_integrity(existing_backup_tuples: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
        """
        Checks the integrity of existing backups by comparing primary and backup files.

        Parameters
        ----------
        existing_backup_tuples : list
            List of tuples containing primary and backup file paths. 
            Format: [(primary, backup), (primary, backup), ...]

        Returns
        -------
        modified_files : list
            List of tuples where the backup files are outdated compared to the primary files. 
            Format: [(primary, backup), (primary, backup), ...]
        """
        modified_files = []

        for primary_path, backup_path in existing_backup_tuples:
            try:
                # Skip if either the primary or backup file is missing
                if not os.path.isfile(primary_path) or not os.path.isfile(backup_path):
                    continue

                # Check if files are not identical
                if not files_are_identical(primary_path, backup_path):
                    modified_files.append((primary_path, backup_path))
            except Exception as e:
                print(f"Error processing {primary_path} and {backup_path}: {e}")

        return modified_files


    def main(self):
        import os
        from analytics import read_media_statistics, read_media_file_data

        print(f'\n{"#" * 10}\n\n{Fore.MAGENTA}{Style.BRIGHT}Initiating Alexandria Backup...{Style.RESET_ALL}\n\n{"#" * 10}')

        # Back up output files
        self.backup_output_files()

        # Iterate through all backup drives
        for drive_backup_letter in self.all_drives:
            drive_backup_name = get_drive_name(drive_backup_letter)
            print(f'\n### {Fore.GREEN}{Style.BRIGHT}{drive_backup_name} ({drive_backup_letter.upper()} drive){Style.RESET_ALL} ###')

            # Process each media type for the current drive
            for media_type in self.media_types:
                self._process_media_type_for_drive(
                    media_type, drive_backup_letter, drive_backup_name
                )

            # Display remaining space on the drive
            self._log_remaining_space(drive_backup_letter, drive_backup_name)

        # Update drive statistics and display summary
        self._update_drive_statistics()
        read_media_statistics(self.filepath_statistics, bool_update=True)
        read_media_file_data(self.filepath_alexandria_media_details, bool_update=True)

        # Final message
        print(f'\n{"#" * 10}\n\n{Fore.GREEN}{Style.BRIGHT}Alexandria Backup Complete{Style.RESET_ALL}\n\n{"#" * 10}\n')


    def _process_media_type_for_drive(self, media_type, drive_backup_letter, drive_backup_name):
        """
        Process backup for a specific media type on a backup drive.
        """
        # Skip if the drive is not associated with the media type
        if not self._is_drive_associated_with_media_type(media_type, drive_backup_letter):
            self._handle_undirected_backups(media_type, drive_backup_letter)
            return

        # Skip primary drives as they don't need backups
        if drive_backup_letter in self.primary_drive_letter_dict[media_type]:
            return

        print(f'\n\tAssessing {Fore.YELLOW}{Style.BRIGHT}{media_type}{Style.RESET_ALL} in backup drive: '
            f'{Fore.GREEN}{Style.BRIGHT}{drive_backup_name} ({drive_backup_letter.upper()} drive){Style.RESET_ALL}')

        # Determine primary parent paths and collect file paths for this media type
        primary_parent_paths = [f'{x}:/{media_type}' for x in self.primary_drive_letter_dict[media_type]]
        self._update_drive_statistics(media_type)
        primary_filepaths = read_alexandria(primary_parent_paths, self.extensions_dict[media_type])
        self.primary_filepaths_dict[media_type] = primary_filepaths

        # Map backup files and determine feasibility
        missing, modified, current, excess = self.backup_mapper(
            media_type, drive_backup_letter, self.primary_filepaths_dict
        )
        required_space, remaining_space = self.assess_backup_feasibility(missing, modified)

        if required_space > remaining_space:
            print(f'\n{Back.RED}{Style.BRIGHT}{Fore.RESET}The {Fore.YELLOW}{media_type}{Fore.RESET} backup to the '
                f'{Fore.YELLOW}{drive_backup_name} ({drive_backup_letter}) drive{Fore.RESET} is '
                f'{abs(int(remaining_space - required_space))} GB too large{Style.RESET_ALL}')
        else:
            self.backup_function(missing, modified)

        # Remove empty sub-directories
        remove_empty_folders(primary_parent_paths + [f'{drive_backup_letter}:/{media_type}'])


    def _is_drive_associated_with_media_type(self, media_type, drive_backup_letter):
        """
        Check if a backup drive is associated with the given media type.
        """
        return (
            drive_backup_letter in self.backup_drives_letter_dict[media_type]
            or drive_backup_letter in self.primary_drives_letter_dict[media_type]
        )


    def _handle_undirected_backups(self, media_type, drive_backup_letter):
        """
        Handle undirected backups for drives that are not explicitly associated with a media type.
        """
        root_path = f'{drive_backup_letter}:/{media_type}'
        undirected_files = read_alexandria([root_path], self.extensions_dict[media_type])

        if undirected_files:
            self.remove_excess_files(undirected_files, updated_block_list=False, non_configured_backup=True)
            remove_empty_folders([root_path])


    def _log_remaining_space(self, drive_backup_letter, drive_backup_name):
        """
        Log the remaining space on the backup drive.
        """
        space_remaining_tb = get_space_remaining(drive_backup_letter) / 1000
        self.drive_stats_dict[drive_backup_name] = {"Space Remaining (TB)": space_remaining_tb}

        print(f'\n{Fore.MAGENTA}{Style.BRIGHT}Space remaining{Style.RESET_ALL} in '
            f'{Fore.GREEN}{Style.BRIGHT}{drive_backup_name} ({drive_backup_letter.upper()} drive){Style.RESET_ALL}: '
            f'{Fore.BLUE}{Style.BRIGHT}{space_remaining_tb:,.2f} TB{Style.RESET_ALL}')


    def _update_drive_statistics(self):
        """
        Sort and display drive statistics.
        """
        self.drive_stats_dict = dict(sorted(self.drive_stats_dict.items(), key=lambda item: item[0].title()))

        print(f'\n{Fore.MAGENTA}{Style.BRIGHT}Space Remaining on Drives{Style.RESET_ALL}\n')
        for drive_name, stats in self.drive_stats_dict.items():
            print(f'{Fore.GREEN}{Style.BRIGHT}{drive_name}:{Style.RESET_ALL} {stats["Space Remaining (TB)"]:,.2f} TB')


    def _get_drive_letters(self, drives_dict):
        """
        Extract unique drive letters from a dictionary of drive paths.
        
        :param drives_dict: Dictionary with drive categories and paths
        :return: List of unique drive letters
        """
        from utilities import get_drive_letter
        drive_letters = []
        for key, paths in drives_dict.items():
            drive_letters.extend([get_drive_letter(path) for path in paths if get_drive_letter(path)])
        return sorted(set(drive_letters))


    def __str__(self):
        """
        Return a string representation of the Backup object.
        """
        return f"timestamp='{self.timestamp}')"

if __name__ == '__main__':
    backup = Backup()
    backup.main()