import os
import sys
import io
import re
import zipfile
import unicodedata
from pathlib import Path
from pdf2image import convert_from_path
from PIL import Image
from colorama import Fore, init

try:
    import rarfile
except ImportError:
    rarfile = None

# Point rarfile at the bundled unrar binary (guarded so a missing rarfile
# install can't crash the script at import time).
if rarfile is not None:
    rarfile.UNRAR_TOOL = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'bin', 'UnRAR.exe')
    )

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utilities import get_drive_letter, read_alexandria_config, read_json, get_primary_root_directories

init(autoreset=True)

# ==========================================

IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.webp')

# Filename hints (substring match on the lowercased basename, no extension).
COVER_NAME_HINTS = ('cover', 'front')
BACK_NAME_HINTS = ('back', 'rear', 'bcover', 'rcover')
# Scanning-group credit / banner pages: not real content, and they often sort
# to the very front (e.g. a leading hyphen) or back. '-x-x-' is Retromags' marker.
CREDIT_NAME_HINTS = ('retromags', '-x-x-', 'credits')


def sanitize_path(path: Path) -> str:
    """
    Normalize Unicode and apply long path prefix on Windows if needed.
    """
    safe_path = unicodedata.normalize("NFKD", str(path))

    if os.name == 'nt':
        abs_path = os.path.abspath(safe_path)
        if not abs_path.startswith(r"\\?\\"):
            safe_path = r"\\?\{}".format(abs_path)

    return safe_path


def open_comic_archive(file_path: Path):
    """
    Open a .cbz/.cbr as the correct archive type based on its *content*,
    not its extension. Comic archives are frequently misnamed (a .cbr that
    is really a zip, and vice versa), so we sniff the file instead of trusting
    the suffix. Returns an open archive supporting .namelist() and .open().
    """
    path_str = str(file_path)

    if zipfile.is_zipfile(path_str):
        return zipfile.ZipFile(path_str, 'r')

    if rarfile is not None and rarfile.is_rarfile(path_str):
        return rarfile.RarFile(path_str, 'r')

    if rarfile is None:
        raise RuntimeError(
            "File looks like a RAR archive but the 'rarfile' package is not "
            "installed (pip install rarfile, plus an unrar backend)."
        )
    raise ValueError("Not a valid ZIP or RAR comic archive.")


def _natural_sort_key(name: str):
    """
    Order embedded numbers naturally (2 before 10), case-insensitively:
    '01' < '2' < '10' < 'a'. Fixes plain-text sorting grabbing the wrong page.
    """
    return [int(chunk) if chunk.isdigit() else chunk
            for chunk in re.split(r'(\d+)', name.lower())]


def _stem(name: str) -> str:
    return os.path.splitext(os.path.basename(name))[0].lower()


def _basename_has_digit(name: str) -> bool:
    return any(ch.isdigit() for ch in os.path.basename(name))


def _is_back_cover(name: str) -> bool:
    return any(hint in _stem(name) for hint in BACK_NAME_HINTS)


def _is_credit_page(name: str) -> bool:
    return any(hint in _stem(name) for hint in CREDIT_NAME_HINTS)


def _is_front_cover(name: str) -> bool:
    stem = _stem(name)
    return any(hint in stem for hint in COVER_NAME_HINTS) and not _is_back_cover(name)


def _pick_cover(image_files):
    """
    Choose the cover from a naturally-sorted list of image members.
    Priority:
      1. A file explicitly named like a front cover (wherever it sorts).
      2. Lowest-numbered real page, after dropping back covers and scan-group
         credit/banner pages. Real scan pages carry a page number; logos and
         credit banners usually don't, and those are what sort to the wrong end.
      3. Fallbacks if nothing looks like a numbered page.
    """
    fronts = [f for f in image_files if _is_front_cover(f)]
    if fronts:
        return fronts[0]

    pool = [f for f in image_files
            if not _is_back_cover(f) and not _is_credit_page(f)]

    numbered = [f for f in pool if _basename_has_digit(f)]
    if numbered:
        return numbered[0]   # already natural-sorted -> lowest page number

    if pool:
        return pool[0]
    return image_files[0]


def save_cover_from_archive(archive, image_path: Path):
    """
    Find the cover in an open zip/rar archive and save it as a PNG.
    Returns the archive member used, or None if no usable image was found.
    """
    image_files = sorted(
        (name for name in archive.namelist()
         if name.lower().endswith(IMAGE_EXTENSIONS)
         and not name.endswith('/')                       # skip directory entries
         and '__MACOSX' not in name                       # skip macOS metadata
         and not os.path.basename(name).startswith('._')),  # skip resource forks
        key=_natural_sort_key,
    )
    if not image_files:
        return None

    cover = _pick_cover(image_files)

    # Read fully into memory so PIL always has a seekable stream. rarfile's
    # piped streams are not always seekable, which can break Image.open for
    # certain formats; BytesIO sidesteps that for both zip and rar.
    with archive.open(cover) as member:
        data = member.read()

    img = Image.open(io.BytesIO(data)).convert("RGB")
    img.save(image_path, "PNG")
    return cover


def generate_pdf_and_cbz_thumbnails(root_dir: str,
                                    output_name: str = "cover.png",
                                    overwrite: bool = False):
    root_path = Path(root_dir)
    script_dir = os.path.dirname(__file__)
    poppler_bin = os.path.abspath(os.path.join(script_dir, '..', 'bin', 'poppler'))

    for file_path in root_path.rglob("*"):
        if not file_path.is_file():
            continue

        ext = file_path.suffix.lower()
        output_dir = file_path.parent
        image_path = output_dir / output_name

        if image_path.exists() and not overwrite:
            continue

        if any(ord(c) > 127 for c in file_path.name):
            print(Fore.YELLOW + f"[NOTE] Special characters in filename: {file_path.name}")

        try:
            if ext == ".pdf":
                # PDF thumbnail
                safe_pdf_path = sanitize_path(file_path)
                pages = convert_from_path(
                    safe_pdf_path,
                    first_page=1,
                    last_page=1,
                    poppler_path=poppler_bin
                )
                pages[0].save(image_path, "PNG")
                print(Fore.GREEN + f"[PDF] {image_path} from {file_path.name}")

            elif ext in (".cbz", ".cbr"):
                # Comic archive thumbnail (CBZ = zip, CBR = rar)
                with open_comic_archive(file_path) as archive:
                    cover_member = save_cover_from_archive(archive, image_path)

                if cover_member:
                    label = ext[1:].upper()
                    print(Fore.GREEN + f"[{label}] {image_path} from {file_path.name} (cover: {cover_member})")
                else:
                    print(Fore.YELLOW + f"[SKIP] No images found in: {file_path.name}")

        except Exception as e:
            print(Fore.RED + f"[ERROR] {file_path.name}: {e}")


if __name__ == "__main__":
    # === CONFIGURATION ===
    root_dirs = get_primary_root_directories(["Books"])
    bool_overwrite = False
    # ======================
    for directory in root_dirs:
        generate_pdf_and_cbz_thumbnails(directory, overwrite=bool_overwrite)