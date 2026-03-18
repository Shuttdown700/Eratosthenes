from pathlib import Path
import re


def clean_name(name: str, has_extension: bool = True, strip_tags: bool = False) -> str:
    """
    Strips trailing parenthetical region tags from strings if strip_tags is True.
    Handles both filenames (with extensions) and directory/base names.
    """
    if not strip_tags:
        return name

    if has_extension:
        pattern = re.compile(r'(?:\s*\([^)]*\))+(?=\.[^.]+$)')
    else:
        pattern = re.compile(r'(?:\s*\([^)]*\))+$')

    return pattern.sub('', name)


def format_size(size_in_bytes: int) -> str:
    """Converts bytes to a human-readable format (e.g., MB, GB)."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_in_bytes < 1024.0:
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024.0
    return f"{size_in_bytes:.2f} PB"


def get_size(path: Path) -> int:
    """Returns the size of a file, or the total size of all files in a directory."""
    if path.is_file():
        return path.stat().st_size
    elif path.is_dir():
        return sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
    return 0