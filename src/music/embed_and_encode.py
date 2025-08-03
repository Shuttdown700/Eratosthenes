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

from utilities import read_alexandria, remove_empty_folders

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

def embed_album_covers(base_directory, override_cover = False):
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

    def squish_to_square_image(image_bytes: bytes, size: int = 500) -> bytes:
        """
        Force an image to a square 1:1 aspect ratio by resizing (squishing/stretching).
        'size' determines the output square dimension (default 500x500).
        """
        try:
            with Image.open(BytesIO(image_bytes)) as img:
                squished_img = img.resize((size, size))  # Force resize to square
                output = BytesIO()
                squished_img.save(output, format='JPEG')
                return output.getvalue()
        except Exception as e:
            print(f"❌ Failed to squish image to square: {e}")
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
            print(f"❌ Failed to extract image from audio due to error: {audio.filename}")
            return None
        print(f"❌ No embedded image found in: {audio.filename}")
        return None

    def embed_image(mp3_path, image_path):
        try:
            audio = File(mp3_path, easy=False)
            if audio is None:
                print(f"❌ Unsupported file: {mp3_path}")
                return

            if has_embedded_image(audio) and not override_cover:
                # print(f"⏭️  Skipping (already has cover): {mp3_path}")
                return

            image_data, mime_type = convert_image_to_jpeg(image_path)

            if isinstance(audio, MP3):
                audio = MP3(mp3_path, ID3=ID3)
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
                picture.width = picture.height = 0
                audio.add_picture(picture)
                audio.save()

            elif isinstance(audio, MP4):
                audio['covr'] = [MP4Cover(image_data, imageformat=MP4Cover.FORMAT_JPEG)]
                audio.save()

            print(f"✅ Embedded cover into: {mp3_path}")
        except Exception as e:
            print(f"❌ Failed to embed cover into: {mp3_path} ({e})")

    if not os.path.isdir(base_directory):
        print("Invalid base directory.")
        return

    for dirpath, _, filenames in os.walk(base_directory):
        audio_files = [f for f in filenames if f.lower().endswith(AUDIO_EXTENSIONS)]
        if not audio_files:
            continue

        cover_path = os.path.join(dirpath, "cover.jpg")
        image_path = find_image_in_dir(dirpath)

        # Attempt to extract embedded image if all files have embedded covers but no cover.jpg
        if not image_path and not os.path.exists(cover_path):
            embedded_images = []
            for audio_file in audio_files:
                file_path = os.path.join(dirpath, audio_file)
                audio = File(file_path, easy=False)
                if not audio or not has_embedded_image(audio):
                    break
                embedded_images.append(extract_image_from_audio(audio))

            if len(embedded_images) == len(audio_files) and embedded_images[0]:
                try:
                    square_image_bytes = make_square_image(embedded_images[0])
                    with open(cover_path, 'wb') as f:
                        f.write(square_image_bytes)
                    print(f"📸 Extracted and squared cover.jpg: {cover_path}")
                    image_path = cover_path
                except Exception as e:
                    print(f"❌ Failed to save cover.jpg: {e}")
            else:
                print(f"❌ No image found or not all files have embedded images in {dirpath}")
                continue

        if not image_path:
            print(f"❌ No image to embed in {dirpath}")
            continue

        for audio_file in audio_files:
            file_path = os.path.join(dirpath, audio_file)
            embed_image(file_path, image_path)

def encode_multiple_bitrates(parent_dir = 'W:\\Music\\FLAC', 
                             bitrates_desired = [320]):
    """Encodes audio files in the specified parent directory to multiple bitrates."""
    os.chdir(os.path.join(os.path.realpath(os.path.dirname(__file__)),"..","bin"))

    def check_directory(file_out):
        path = os.path.dirname(file_out)
        if not os.path.exists(path):
            os.makedirs(path)

    def safe_output_path(parent_dir, bitrate_desired):
        drive = os.path.splitdrive(parent_dir)[0]
        path_parts = parent_dir.split(os.sep)

        # Only use elements from index 3 onward if they exist
        safe_tail = path_parts[3:] if len(path_parts) > 3 else []

        output_base = os.path.join(drive + os.sep, "Music", f'MP3s_{bitrate_desired}', *safe_tail)
        return output_base

    def re_encode_tracks(parent_dir, bitrate_desired=128, desired_extension='.mp3'):
        filepaths = read_alexandria([parent_dir], ['.mp3', '.flac', '.m4a'])
        output_base = safe_output_path(parent_dir, bitrate_desired)

        for file_in in filepaths:
            # Recreate relative path inside output directory
            rel_path = os.path.relpath(file_in, start=parent_dir)
            rel_path_no_ext = os.path.splitext(rel_path)[0]
            file_out = os.path.join(output_base, rel_path_no_ext + desired_extension)

            if os.path.isfile(file_out):
                continue

            check_directory(file_out)  # Ensure destination dir exists

            print(f'{GREEN}{BRIGHT}Re-encoding{RESET} {os.path.basename(file_out)} in {YELLOW}{BRIGHT}{bitrate_desired}kbps{RESET} to: {os.path.dirname(file_out)}')
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
            print(f'{GREEN}{BRIGHT}Copying image{RESET} to: {file_out}')
            shutil.copy2(file_in, file_out)
    
    for bd in bitrates_desired:
        re_encode_tracks(parent_dir,bitrate_desired=bd,desired_extension='.mp3')
        copy_images(parent_dir,bd)
    remove_empty_folders([parent_dir])

if __name__ == "__main__":

    dirs_to_reencode = [
        r"W:\Music\FLAC"]
    
    for directory in dirs_to_reencode:
        embed_album_covers(directory, override_cover = False)
        encode_multiple_bitrates(directory, bitrates_desired = [320])

    dirs_embed_covers = [
        r"W:\Music\MP3s_320"]
       
    # dirs_embed_covers = [
    #     r"W:\Music\FLAC\Weezer\(1994) Weezer (Blue Album)\Disc 1",
    #     r"W:\Music\FLAC\Weezer\(1994) Weezer (Blue Album)\Disc 2",
    #     r"W:\Music\MP3s_320\Weezer\(1994) Weezer (Blue Album)\Disc 1",
    #     r"W:\Music\MP3s_320\Weezer\(1994) Weezer (Blue Album)\Disc 2"
    # ]
    
    for directory in dirs_embed_covers:
        embed_album_covers(directory,override_cover = False)