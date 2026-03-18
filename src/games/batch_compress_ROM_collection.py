from pathlib import Path
import zipfile
import shutil

import py7zr

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


SOURCE_DIRECTORIES = [
    r"V:\Games\Emulation\Game Files\Sega Model 2"
]
OUTPUT_DIRECTORIES = [
    r"V:\Games\Emulation\Game Files\Sega Model 2"
]

IS_DRY_RUN = False

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
    for sDir, oDir in zip(SOURCE_DIRECTORIES, OUTPUT_DIRECTORIES):
    
        print(f"\n{BLUE}{BRIGHT}Starting Compression for: {sDir}{RESET}")
        compress_directories(oDir, sDir, archive_format='.zip', dry_run=IS_DRY_RUN)