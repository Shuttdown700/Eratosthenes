#!/usr/bin/env python3
import zipfile
from pathlib import Path
import re

def extract_ext_from_zips(zip_dir: Path, output_dir: Path, tgt_file_ext: str = ".z64"):
    """Extract files with a specific extension from all zip files in a directory."""
    output_dir.mkdir(exist_ok=True)

    # Iterate over all zip files in zip_dir
    for zip_path in zip_dir.glob("*.zip"):
        with zipfile.ZipFile(zip_path, "r") as z:
            # Loop through all files inside the zip
            for member in z.namelist():
                if member.lower().endswith(tgt_file_ext):
                    # Extract into the output directory
                    target_path = output_dir / Path(member).name
                    with z.open(member) as source, open(target_path, "wb") as dest:
                        dest.write(source.read())

def clean_region_tags(game_dir: str):
    """
    Remove trailing parenthetical tags from filenames in `game_dir`.
    Examples:
      "Bomberman 64 (USA).z64" -> "Bomberman 64.z64"
      "Beetle Adventure Racing! (USA) (En,Fr,De).z64" -> "Beetle Adventure Racing!.z64"

    - Operates on all files directly inside the given directory (non-recursive).
    - If the resulting filename would collide with an existing file, a numeric
      suffix is appended before the extension (e.g. "_1", "_2", ...).
    """
    directory = Path(game_dir)
    if not directory.exists() or not directory.is_dir():
        raise FileNotFoundError(f"Directory not found: {directory!s}")

    # Matches one or more " ( ... )" groups that occur just before the extension.
    trailing_parens_re = re.compile(r'(?:\s*\([^)]*\))+(?=\.[^.]+$)')

    for p in directory.iterdir():
        if not p.is_file():
            continue

        original_name = p.name
        # Remove trailing parenthetical groups
        new_name = trailing_parens_re.sub('', original_name)

        # If nothing changed, continue
        if new_name == original_name:
            continue

        new_path = p.with_name(new_name)

        # If target exists, append a numeric suffix to avoid overwriting
        if new_path.exists():
            stem = new_path.stem
            suffix = new_path.suffix
            i = 1
            candidate = new_path.with_name(f"{stem}_{i}{suffix}")
            while candidate.exists():
                i += 1
                candidate = new_path.with_name(f"{stem}_{i}{suffix}")
            new_path = candidate

        p.rename(new_path)

if __name__ == "__main__":
    zip_dir = Path(r"W:\Temp\Games\N64 Games")          # Directory containing .zip files
    output_dir = Path(r"W:\Temp\Games\N64 Games\Exracted N64 Files")  # Directory to store extracted .n64 files
    # extract_ext_from_zips(zip_dir, output_dir)
    clean_region_tags(output_dir)
