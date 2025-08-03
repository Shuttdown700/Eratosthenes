import os
import re
from pathlib import Path
from datetime import datetime
from PIL import Image
from PIL.ExifTags import TAGS
from collections import defaultdict
from colorama import init, Fore, Style

# Initialize colorama
init(autoreset=True)

MEDIA_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.heic', '.mp4', '.mov', '.avi', '.mkv', '.webm')

def get_exif_date_taken(filepath: Path):
    try:
        img = Image.open(filepath)
        exif_data = img._getexif()
        if exif_data:
            for tag, value in exif_data.items():
                if TAGS.get(tag) == 'DateTimeOriginal':
                    return datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
    except Exception:
        pass
    return None

def get_file_date(filepath: Path):
    exif_date = get_exif_date_taken(filepath)
    if exif_date:
        return exif_date
    stat = filepath.stat()
    return datetime.fromtimestamp(stat.st_mtime)

def is_formatted_correctly(filename: str, dirname: str):
    """Check if filename matches 'NN dirname YYYYMMDD.ext'"""
    pattern = rf"^\d{{2,4}}\s+{re.escape(dirname)}\s+\d{{8}}\.[a-z0-9]+$"
    return re.match(pattern, filename, re.IGNORECASE)

def rename_files_in_directory(
    root_dir: str,
    omit_dirs=None,
    dry_run=False,
    skip_if_formatted=True,
    redo_if_formatted=False
):
    root_path = Path(root_dir).resolve()
    omit_dirs = set(omit_dirs or [])
    renamed_names = defaultdict(list)

    for dirpath, _, filenames in os.walk(root_path):
        rel_dir = Path(dirpath).relative_to(root_path)
        if any(part in omit_dirs for part in rel_dir.parts):
            print(Fore.YELLOW + f"[SKIP]{Style.RESET_ALL} Omitted directory: {rel_dir}")
            continue

        dir_label = rel_dir.name if rel_dir.name else "Root"
        filepaths = [Path(dirpath) / f for f in filenames if f.lower().endswith(MEDIA_EXTENSIONS)]

        if not filepaths:
            continue

        # Collect all file dates and paths
        dated_files = []
        for fp in filepaths:
            try:
                file_date = get_file_date(fp)
                dated_files.append((fp, file_date))
            except Exception as e:
                print(Fore.RED + f"[ERROR]{Style.RESET_ALL} Could not get date for {fp}: {e}")

        if not dated_files:
            continue

        # Sort all by date — this guarantees unique numbering
        dated_files.sort(key=lambda x: x[1])

        # If all files are already named correctly in order, we can skip if allowed
        already_correct = True
        for i, (fp, dt) in enumerate(dated_files, 1):
            date_str = dt.strftime("%Y%m%d")
            expected_name = f"{i:02} {dir_label} {date_str}{fp.suffix.lower()}"
            if fp.name != expected_name:
                already_correct = False
                break

        if already_correct:
            if skip_if_formatted:
                print(Fore.YELLOW + f"[SKIP]{Style.RESET_ALL} All files in '{rel_dir}' already correctly formatted")
                continue
            if not redo_if_formatted:
                print(Fore.CYAN + f"[NOTICE]{Style.RESET_ALL} '{rel_dir}' appears formatted. Skipping unless redo enabled.")
                continue

        # Process all files and assign unique numbers
        for i, (fp, dt) in enumerate(dated_files, 1):
            date_str = dt.strftime("%Y%m%d")
            index = f"{i:02}"
            ext = fp.suffix.lower()
            new_name = f"{index} {dir_label} {date_str}{ext}"
            new_path = fp.parent / new_name

            renamed_names[new_name].append(str(fp))

            if new_path == fp:
                continue  # Already correct

            if new_path.exists():
                print(Fore.RED + f"[ERROR]{Style.RESET_ALL} Target file already exists: {new_path.name}. Skipping.")
                continue

            if dry_run:
                print(Fore.CYAN + f"[DRY-RUN]{Style.RESET_ALL} Would rename: {fp.name} -> {new_name}")
            else:
                try:
                    fp.rename(new_path)
                    print(Fore.GREEN + f"[RENAMED]{Style.RESET_ALL} {fp.name} -> {new_name}")
                except Exception as e:
                    print(Fore.RED + f"[ERROR]{Style.RESET_ALL} Failed to rename {fp.name}: {e}")

    # 🔍 Report duplicates
    print("\n" + Style.BRIGHT + Fore.MAGENTA + f"[SUMMARY]{Style.RESET_ALL} Checking for duplicates in target names...")
    duplicates = {name: files for name, files in renamed_names.items() if len(files) > 1}
    if duplicates:
        print(Fore.RED + f"[WARNING]{Style.RESET_ALL} Found {len(duplicates)} name collision(s):")
        for name, files in duplicates.items():
            print(Fore.RED + f" - {name}:")
            for f in files:
                print(Fore.RED + f"    - {f}")
    else:
        print(Fore.GREEN + f"[OK]{Style.RESET_ALL} No duplicate names detected after renaming.")


# ✅ Call it like this:
if __name__ == "__main__":
    rename_files_in_directory(
        root_dir=r"T:\Photos",
        omit_dirs=["Drone Footage"],
        dry_run=False,
        skip_if_formatted=True,
        redo_if_formatted=False
    )
