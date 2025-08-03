import os
import shutil
from mutagen.easyid3 import EasyID3

# Map 3-letter codes to full book names
book_code_map = {
    'MAT': 'Matthew', 'MRK': 'Mark', 'LUK': 'Luke', 'JHN': 'John',
    'ACT': 'Acts', 'ROM': 'Romans', '1CO': '1 Corinthians', '2CO': '2 Corinthians',
    'GAL': 'Galatians', 'EPH': 'Ephesians', 'PHP': 'Philippians', 'COL': 'Colossians',
    '1TH': '1 Thessalonians', '2TH': '2 Thessalonians', '1TI': '1 Timothy', '2TI': '2 Timothy',
    'TIT': 'Titus', 'PHM': 'Philemon', 'HEB': 'Hebrews', 'JAS': 'James',
    '1PE': '1 Peter', '2PE': '2 Peter', '1JN': '1 John', '2JN': '2 John',
    '3JN': '3 John', 'JUD': 'Jude', 'REV': 'Revelation',
}

def update_titles(mp3_folder: str, dry_run: bool = False):
    output_folder = os.path.join(mp3_folder, "tagged")
    os.makedirs(output_folder, exist_ok=True)

    # Sort for deterministic absolute track numbers
    mp3_files = sorted(f for f in os.listdir(mp3_folder) if f.lower().endswith('.mp3'))
    
    for track_index, filename in enumerate(mp3_files, start=1):
        parts = filename.split('_')
        if len(parts) != 4:
            print(f"[SKIP] Unexpected format: {filename}")
            continue

        book_code = parts[2]
        chapter_num = parts[3].replace('.mp3', '')

        book_name = book_code_map.get(book_code)
        if not book_name:
            print(f"[SKIP] Unknown book code: {book_code} in file {filename}")
            continue

        title = f"{book_name} {chapter_num.zfill(2)}"
        album = "The Holy Bible: New Testament (KJV)"
        tracknumber = str(track_index)

        src_path = os.path.join(mp3_folder, filename)
        dest_path = os.path.join(output_folder, filename)

        if os.path.exists(dest_path):
            print(f"[SKIP] Already exists: {dest_path}")
            continue

        if dry_run:
            print(f"[DRY RUN] Would copy to: {dest_path}")
            print(f"           Set Title: '{title}', Album: '{album}', Track #: {tracknumber}")
        else:
            shutil.copy2(src_path, dest_path)
            try:
                audio = EasyID3(dest_path)
            except Exception:
                from mutagen.mp3 import MP3
                audio = MP3(dest_path)
                audio.add_tags()
                audio = EasyID3(dest_path)

            audio['title'] = title
            audio['album'] = album
            audio['tracknumber'] = tracknumber
            audio.save()
            print(f"[OK] Wrote: {dest_path}")
            print(f"     Title: '{title}', Album: '{album}', Track #: {tracknumber}")

if __name__ == "__main__":
    update_titles(r"A:\Temp\Audiobooks\The Holy Bible - New Testament (KJV)", dry_run=False)

