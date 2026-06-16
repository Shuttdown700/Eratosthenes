#!/usr/bin/env python3
import os
import sys
import argparse
import shutil
import subprocess
from pathlib import Path

from utilities_games import (
    clean_name,
    format_size,
    get_size
)

# Import colorama for terminal colors
try:
    from colorama import Fore, Style, init
    init()  # Initializes colorama so colors render properly on Windows
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


def extract_chd(
    source_dir: str,
    dest_dir: str,
    chdman_path: str = 'chdman',
    output_format: str = 'auto',
    dry_run: bool = False,
    strip_tags: bool = False,
    delete_source: bool = False,
):
    """
    Finds .chd files in source_dir and extracts them using chdman.

    Output format selection (--format):
      auto    — tries extractcd first; falls back to extractdvd on failure (default)
      cd      — forces 'chdman extractcd'  → produces .cue + .bin
      dvd     — forces 'chdman extractdvd' → produces .iso
      iso     — alias for dvd

    On success, the extracted file(s) land in dest_dir.
    If --delete-source is passed, the original .chd is removed after a
    successful extraction.
    """
    source_path = Path(source_dir)
    dest_path = Path(dest_dir)

    if not source_path.exists() or not source_path.is_dir():
        raise FileNotFoundError(f"Source directory not found: {source_path!s}")

    if not dry_run:
        dest_path.mkdir(parents=True, exist_ok=True)
        if shutil.which(chdman_path) is None:
            print(f"{RED}{BRIGHT}Error: '{chdman_path}' not found in PATH.{RESET}")
            print(f"{RED}Please install MAME tools and ensure 'chdman' is accessible.{RESET}")
            return

    chd_files = sorted(source_path.rglob("*.chd"))

    if not chd_files:
        print(f"{YELLOW}No .chd files found in: {source_path}{RESET}")
        return

    # ------------------------------------------------------------------
    # Core extraction helper
    # ------------------------------------------------------------------
    def run_extract(chd_file: Path, out_file: Path, mode: str) -> bool:
        """
        Calls 'chdman extractcd' or 'chdman extractdvd'.

        mode must be 'cd' or 'dvd'.
        For 'cd', out_file should have a .cue extension — chdman writes
        the matching .bin automatically alongside it.
        For 'dvd', out_file should have an .iso extension.
        """
        cmd = [chdman_path, f"extract{mode}", '-i', str(chd_file), '-o', str(out_file)]

        if dry_run:
            print(f"{YELLOW}[DRY RUN]{RESET} Would run: {' '.join(cmd)}")
            return True

        input_size_str = format_size(get_size(chd_file))
        print(f"{BLUE}  Extracting ({mode}): {chd_file.name} [{input_size_str}]...{RESET}")

        try:
            result = subprocess.run(
                cmd,
                check=True,
                timeout=600,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            output_size_str = format_size(get_size(out_file))
            print(f"{GREEN}  -> Successfully extracted {out_file.name} [{output_size_str}]{RESET}")
            return True

        except subprocess.TimeoutExpired:
            print(f"{RED}  -> Extraction timed out for {chd_file.name}{RESET}")
            if out_file.exists():
                out_file.unlink()
            return False

        except subprocess.CalledProcessError as e:
            err_msg = e.stderr.decode('utf-8', errors='replace').strip() if e.stderr else str(e)
            print(f"{RED}  -> Extraction failed ({mode}) for {chd_file.name}: {err_msg}{RESET}")
            if out_file.exists():
                out_file.unlink()
            return False

    # ------------------------------------------------------------------
    # Per-file processing
    # ------------------------------------------------------------------
    for chd_file in chd_files:
        chd_size_str = format_size(get_size(chd_file))
        clean_game_name = clean_name(chd_file.stem, has_extension=False, strip_tags=strip_tags)

        print(f"{MAGENTA}Processing CHD: {chd_file.name} [{chd_size_str}]{RESET}")

        if dry_run:
            print(f"{YELLOW}[DRY RUN]{RESET} Would extract '{chd_file.name}' to '{dest_path}'.")
            continue

        success = False

        # --- Forced modes ---
        if output_format in ('dvd', 'iso'):
            out_iso = dest_path / f"{clean_game_name}.iso"
            success = run_extract(chd_file, out_iso, 'dvd')

        elif output_format == 'cd':
            out_cue = dest_path / f"{clean_game_name}.cue"
            success = run_extract(chd_file, out_cue, 'cd')

        # --- Auto mode: try CD first, fall back to DVD ---
        else:
            out_cue = dest_path / f"{clean_game_name}.cue"
            success = run_extract(chd_file, out_cue, 'cd')

            if not success:
                print(f"{YELLOW}  -> CD extraction failed. Retrying as DVD/ISO...{RESET}")
                out_iso = dest_path / f"{clean_game_name}.iso"
                success = run_extract(chd_file, out_iso, 'dvd')

        # --- Cleanup ---
        if success and delete_source:
            try:
                chd_file.unlink()
                print(f"{GREEN}  -> Deleted original CHD: {chd_file.name}{RESET}")
            except Exception as e:
                print(f"{RED}  -> Extracted, but failed to delete {chd_file.name}: {e}{RESET}")
        elif not success:
            print(f"{RED}  -> Skipping cleanup — extraction was not successful for {chd_file.name}{RESET}")


# ==========================================================================
# Entry point
# ==========================================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="ROM CHD Extraction Tool — converts .chd back to .cue/.bin or .iso"
    )
    parser.add_argument(
        "--format",
        choices=["auto", "cd", "dvd", "iso"],
        default="auto",
        help=(
            "Output format. "
            "'auto' tries extractcd (CUE/BIN) first and falls back to extractdvd (ISO). "
            "'cd' forces CUE/BIN output. "
            "'dvd' / 'iso' forces ISO output. "
            "(default: auto)"
        ),
    )
    parser.add_argument(
        "--delete-source",
        action="store_true",
        help="Delete the original .chd file after a successful extraction.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate the process without making any actual changes to the files.",
    )
    parser.add_argument(
        "--strip-tags",
        action="store_true",
        help="Strip trailing parenthetical region tags from output filenames.",
    )

    args = parser.parse_args()

    # --- Configuration ---
    SOURCE_DIRECTORIES = [
        r"T:\ShuttFlix-Temp\Games\ps2",
    ]
    OUTPUT_DIRECTORIES = [
        r"T:\ShuttFlix-Temp\Games\ps2\Converted",
    ]

    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    CHDMAN_EXECUTABLE = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "bin", "chdman.exe"))

    if not os.path.exists(CHDMAN_EXECUTABLE) and not args.dry_run:
        print(f"{RED}{BRIGHT}Error: Could not find chdman.exe at {CHDMAN_EXECUTABLE}{RESET}")
        exit(1)

    # ------------------------------------------------------------------
    # Execute CHD Extraction
    # ------------------------------------------------------------------
    for sDir, oDir in zip(SOURCE_DIRECTORIES, OUTPUT_DIRECTORIES):
        print(f"\n{BLUE}{BRIGHT}Starting CHD Extraction for: {sDir}{RESET}")
        extract_chd(
            source_dir=sDir,
            dest_dir=oDir,
            chdman_path=CHDMAN_EXECUTABLE,
            output_format=args.format,
            dry_run=args.dry_run,
            strip_tags=args.strip_tags,
            delete_source=args.delete_source,
        )