import os
import sys
import zipfile
import unicodedata
from pathlib import Path
from pdf2image import convert_from_path
from PIL import Image
from colorama import Fore, init

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utilities import get_drive_letter, read_alexandria_config, read_json, get_primary_root_directories

init(autoreset=True)

# ==========================================

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

            elif ext == ".cbz":
                # CBZ thumbnail
                with zipfile.ZipFile(file_path, 'r') as cbz:
                    # List image files and sort them (assumes first = cover)
                    image_files = sorted(
                        [f for f in cbz.namelist() if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]
                    )
                    if not image_files:
                        print(Fore.YELLOW + f"[SKIP] No images found in: {file_path.name}")
                        continue

                    # Extract and save the first image
                    with cbz.open(image_files[0]) as img_file:
                        img = Image.open(img_file).convert("RGB")
                        img.save(image_path, "PNG")
                        print(Fore.GREEN + f"[CBZ] {image_path} from {file_path.name}")

        except Exception as e:
            print(Fore.RED + f"[ERROR] {file_path.name}: {e}")

if __name__ == "__main__":
    # === CONFIGURATION ===
    root_dirs = get_primary_root_directories(["Books"])
    bool_overwrite = False
    # ======================
    for directory in root_dirs:
        generate_pdf_and_cbz_thumbnails(directory, overwrite=bool_overwrite)