#!/usr/bin/env python3

import os
import io
import subprocess
import shutil

from PIL import Image
from io import BytesIO
from colorama import Fore, Style
from mutagen import File
from mutagen.flac import FLAC, Picture
from mutagen.id3 import (
    ID3, TIT2, TPE1, TPE2, TALB, TRCK, TCON, COMM, APIC, error
)
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4, MP4Cover

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utilities import (
    read_alexandria, remove_empty_folders, generate_music_file_print_message,
    read_json, read_alexandria_config, get_drive_letter
)

# Define terminal color shortcuts
RED = Fore.RED
YELLOW = Fore.YELLOW
GREEN = Fore.GREEN
BLUE = Fore.BLUE
MAGENTA = Fore.MAGENTA
RESET = Style.RESET_ALL
BRIGHT = Style.BRIGHT

# Supported file extensions
IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png')
AUDIO_EXTENSIONS = ('.mp3', '.flac', '.m4a')

def embed_album_covers(base_directory, override_cover=False):
    def find_image_in_dir(directory):
        candidate = None
        for filename in os.listdir(directory):
            if filename.lower().endswith(IMAGE_EXTENSIONS):
                if "back" in filename and candidate is not None:
                    continue
                candidate = os.path.join(directory, filename)
                if "cover" in filename:
                    return os.path.join(directory, filename)
        return candidate

    def convert_image_to_jpeg(image_path):
        img = Image.open(image_path).convert('RGB')
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='JPEG')
        return img_buffer.getvalue(), 'image/jpeg'

    def has_embedded_image(audio):
        if isinstance(audio, MP3):
            return any(key.startswith("APIC") for key in audio.tags.keys())
        elif isinstance(audio, FLAC):
            return len(audio.pictures) > 0
        elif isinstance(audio, MP4):
            return 'covr' in audio
        return False

    def make_square_image(image_bytes: bytes) -> bytes:
        """Convert an image to a square 1:1 aspect ratio by center-cropping."""
        try:
            with Image.open(BytesIO(image_bytes)) as img:
                width, height = img.size
                if width == height:
                    return image_bytes  # Already square

                min_dim = min(width, height)
                left = (width - min_dim) // 2
                top = (height - min_dim) // 2
                right = left + min_dim
                bottom = top + min_dim

                square_img = img.crop((left, top, right, bottom))
                output = BytesIO()
                square_img.save(output, format='JPEG')
                return output.getvalue()
        except Exception as e:
            print(f"❌ Failed to convert image to square: {e}")
            return image_bytes  # Return original if conversion fails

    def extract_image_from_audio(audio):
        try:
            if isinstance(audio, MP3):
                for tag in audio.tags.values():
                    if isinstance(tag, APIC):
                        return tag.data
            elif isinstance(audio, FLAC) and audio.pictures:
                return audio.pictures[0].data
            elif isinstance(audio, MP4) and 'covr' in audio:
                return audio['covr'][0]
        except Exception:
            print(f"❌ Failed to extract image from audio: {getattr(audio, 'filename', '?')}")
            return None
        return None

    def embed_image(audio_path, image_path):
        try:
            audio = File(audio_path, easy=False)
            if audio is None:
                print(f"❌ Unsupported file: {audio_path}")
                return

            if has_embedded_image(audio) and not override_cover:
                return

            image_data, mime_type = convert_image_to_jpeg(image_path)

            if isinstance(audio, MP3):
                audio = MP3(audio_path, ID3=ID3)
                try:
                    audio.add_tags()
                except error:
                    pass
                audio.tags.delall("APIC")
                audio.tags.add(APIC(
                    encoding=3,
                    mime=mime_type,
                    type=3,
                    desc='Cover',
                    data=image_data
                ))
                audio.save(v2_version=3)

            elif isinstance(audio, FLAC):
                picture = Picture()
                picture.data = image_data
                picture.type = 3
                picture.mime = mime_type
                picture.desc = "Cover"
                audio.clear_pictures()
                audio.add_picture(picture)
                audio.save()

            elif isinstance(audio, MP4):
                audio['covr'] = [MP4Cover(image_data, imageformat=MP4Cover.FORMAT_JPEG)]
                audio.save()

        except Exception as e:
            print(f"❌ Failed to embed cover into: {audio_path} ({e})")

    # === MAIN LOGIC ===
    if not os.path.isdir(base_directory):
        print("Invalid base directory.")
        return

    for dirpath, _, filenames in os.walk(base_directory):
        audio_files = [f for f in filenames if f.lower().endswith(AUDIO_EXTENSIONS)]
        if not audio_files:
            continue

        cover_path = os.path.join(dirpath, "cover.jpg")
        image_path = find_image_in_dir(dirpath)

        # Step 1: Try to find or create a cover.jpg
        if not image_path:
            embedded_image = None
            for audio_file in audio_files:
                file_path = os.path.join(dirpath, audio_file)
                try:
                    audio = File(file_path, easy=False)
                except Exception:
                    continue
                if audio and has_embedded_image(audio):
                    embedded_image = extract_image_from_audio(audio)
                    if embedded_image:
                        try:
                            square_img = make_square_image(embedded_image)
                            with open(cover_path, 'wb') as f:
                                f.write(square_img)
                            image_path = cover_path
                        except Exception as e:
                            print(f"❌ Failed to write cover.jpg: {e}")
                        break

        if not image_path and os.path.exists(cover_path):
            image_path = cover_path

        if not image_path:
            continue

        for audio_file in audio_files:
            file_path = os.path.join(dirpath, audio_file)
            try:
                audio = File(file_path, easy=False)
                if not audio:
                    continue
            except Exception:
                continue
            if not has_embedded_image(audio) or override_cover:
                embed_image(file_path, image_path)


def encode_multiple_bitrates(parent_dir='W:\\Music\\FLAC', bitrates_desired=[320]):
    """Encodes audio files in the specified parent directory to multiple bitrates."""
    os.chdir(os.path.join(os.path.realpath(os.path.dirname(__file__)), "..", "bin"))

    def check_directory(file_out):
        path = os.path.dirname(file_out)
        if not os.path.exists(path):
            os.makedirs(path)

    def safe_output_path(parent_dir, bitrate_desired):
        drive = os.path.splitdrive(parent_dir)[0]
        path_parts = parent_dir.split(os.sep)
        safe_tail = path_parts[3:] if len(path_parts) > 3 else []
        output_base = os.path.join(drive + os.sep, "Music", f'MP3s_{bitrate_desired}', *safe_tail)
        return output_base

    def re_encode_tracks(parent_dir, bitrate_desired=128, desired_extension='.mp3'):
        filepaths = read_alexandria([parent_dir], ['.mp3', '.flac', '.m4a'])
        output_base = safe_output_path(parent_dir, bitrate_desired)

        for file_in in filepaths:
            rel_path = os.path.relpath(file_in, start=parent_dir)
            rel_path_no_ext = os.path.splitext(rel_path)[0]
            file_out = os.path.join(output_base, rel_path_no_ext + desired_extension)

            if os.path.isfile(file_out):
                continue

            check_directory(file_out)

            print(f'{GREEN}{BRIGHT}Re-encoding{RESET} {generate_music_file_print_message(file_in)} '
                  f'in {YELLOW}{BRIGHT}{bitrate_desired}kbps{RESET} to: {os.path.dirname(file_out)}')
            cmd = [
                'ffmpeg',
                '-i', file_in,
                '-ab', f'{bitrate_desired}k',
                '-map_metadata', '0',
                '-id3v2_version', '3',
                file_out
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def copy_images(parent_dir, bitrate_desired):
        filepaths = read_alexandria([parent_dir], ['.jpeg', '.png', '.jpg'])
        output_base = safe_output_path(parent_dir, bitrate_desired)

        for file_in in filepaths:
            rel_path = os.path.relpath(file_in, start=parent_dir)
            file_out = os.path.join(output_base, rel_path)

            if os.path.isfile(file_out):
                continue

            check_directory(file_out)
            shutil.copy2(file_in, file_out)

    for bd in bitrates_desired:
        re_encode_tracks(parent_dir, bitrate_desired=bd, desired_extension='.mp3')
        copy_images(parent_dir, bd)
    remove_empty_folders([parent_dir])


if __name__ == "__main__":

    src_directory = os.path.dirname(os.path.abspath(__file__))
    filepath_drive_hierarchy = os.path.join(src_directory, "..", "..", "config", "alexandria_drives.config")
    drive_config = read_json(filepath_drive_hierarchy)
    primary_drives_name_dict = read_alexandria_config(drive_config)[0]
    drive_letter = get_drive_letter(primary_drives_name_dict['Music'][0])

    dirs_to_reencode = [drive_letter+r":\Music\FLAC"]
    for directory in dirs_to_reencode:
        embed_album_covers(directory, override_cover=False)
        encode_multiple_bitrates(directory, bitrates_desired=[320])

    dirs_embed_covers = [drive_letter+r":\Music\MP3s_320"]
    for directory in dirs_embed_covers:
        embed_album_covers(directory, override_cover=False)
