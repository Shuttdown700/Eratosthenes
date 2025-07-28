import os
import re
from pathlib import Path
from PyPDF2 import PdfReader, PdfWriter
from colorama import init, Fore

# === CONFIGURATION ===
ROOT_DIR = r"W:\Books"
EXTENSIONS = ['.pdf', '.cbz']
DRY_RUN = False
# ======================

init(autoreset=True)

def rename_and_organize_files(root_dir: str,
                              extensions: list[str],
                              dry_run: bool = False):
    original_pattern = re.compile(
        r"^\((\d{1,4})\)\s+(.+?)\s+\[(.+?)\]\.(pdf|cbz|epub|mobi|azw3)$",
        re.IGNORECASE
    )
    correct_format_pattern = re.compile(
        r"^(.+?)\s+\((\d{1,4})(?:\s+(BC|BCE|CE))?\)\.(pdf|cbz|epub|mobi|azw3)$",
        re.IGNORECASE
    )

    root_path = Path(root_dir)
    seen_dirs = set()

    for dirpath, _, filenames in os.walk(root_path):
        for filename in filenames:
            extension = Path(filename).suffix.lower()
            if extension not in extensions:
                continue

            file_path = Path(dirpath) / filename
            seen_dirs.add(Path(dirpath))

            # === Case 1: Already in correct format ===
            match_correct = correct_format_pattern.match(filename)
            if match_correct:
                title_part, year, era, ext = match_correct.groups()
                expected_folder = f"{title_part.strip()} ({year}{f' {era}' if era else ''})"
                current_folder = Path(dirpath).name

                if current_folder == expected_folder:
                    continue  # Already correctly placed

                new_subdir_path = Path(dirpath) / expected_folder
                new_file_path = new_subdir_path / filename

                if dry_run:
                    print(Fore.CYAN + f"[DRY RUN] Would move into folder: {new_file_path}")
                    continue

                try:
                    new_subdir_path.mkdir(exist_ok=True)
                    file_path.rename(new_file_path)
                    print(Fore.MAGENTA + f"[MOVED] Into folder: {new_file_path.relative_to(root_path)}")
                except Exception as e:
                    print(Fore.RED + f"[ERROR] Moving correct file: {file_path} -> {e}")
                continue

            # === Case 2: Needs renaming ===
            match_original = original_pattern.match(filename)
            if not match_original:
                print(Fore.YELLOW + f"[SKIP] Unmatched format: {filename}")
                continue

            year, title, author, ext = match_original.groups()
            new_filename = f"{title.strip()} ({year}).{ext.lower()}"
            subdir_name = os.path.splitext(new_filename)[0]
            new_subdir_path = Path(dirpath) / subdir_name
            new_file_path = new_subdir_path / new_filename

            if dry_run:
                print(Fore.CYAN + f"[DRY RUN] Would create: {new_subdir_path}")
                print(Fore.CYAN + f"[DRY RUN] Would move: {file_path} -> {new_file_path}")
                continue

            try:
                new_subdir_path.mkdir(exist_ok=True)

                if extension == '.pdf':
                    reader = PdfReader(file_path)
                    writer = PdfWriter()

                    for page in reader.pages:
                        writer.add_page(page)

                    writer.add_metadata({
                        "/Title": title.strip(),
                        "/Author": author.strip(),
                        "/CreationDate": f"D:{year}0101000000"
                    })

                    with open(new_file_path, "wb") as f_out:
                        writer.write(f_out)

                    file_path.unlink()
                else:
                    file_path.rename(new_file_path)

                print(Fore.GREEN + f"[RENAMED] {file_path.name} -> {new_file_path.relative_to(root_path)}")

            except Exception as e:
                print(Fore.RED + f"[ERROR] Processing file: {file_path} -> {e}")

    # === Cleanup: Remove empty directories ===
    if not dry_run:
        empty_dirs = sorted(seen_dirs, key=lambda d: len(str(d)), reverse=True)
        for d in empty_dirs:
            try:
                if d.exists() and not any(d.iterdir()):
                    d.rmdir()
                    print(Fore.BLUE + f"[CLEANED] Removed empty folder: {d}")
            except Exception as e:
                print(Fore.RED + f"[ERROR] Removing folder {d}: {e}")

if __name__ == "__main__":
    rename_and_organize_files(ROOT_DIR, EXTENSIONS, DRY_RUN)
