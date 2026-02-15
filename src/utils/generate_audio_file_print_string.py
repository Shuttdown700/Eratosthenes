from colorama import init, Fore, Style
init(autoreset=True)
RED, YELLOW, GREEN, BLUE, MAGENTA, RESET, BRIGHT = (
    Fore.RED, Fore.YELLOW, Fore.GREEN, Fore.BLUE, Fore.MAGENTA, Style.RESET_ALL, Style.BRIGHT
)

def generate_audio_file_print_string(
    file_path,
    max_title_length=20,
    max_album_length=20,
    include_track=True,
    include_album=True,
    include_artist=True,
    separator=f"{MAGENTA}{BRIGHT} | {RESET}"
) -> str:
    """
    Extract and format music metadata into a string with length limits.
    Supports FLAC, MP3 (ID3), and M4A (MP4) files.
    """
    from mutagen.flac import FLAC
    from mutagen.mp3 import MP3
    from mutagen.mp4 import MP4 # Import MP4 for .m4a support
    from mutagen.id3 import ID3

    try:
        # Determine file type and load appropriate mutagen object
        file_path_lower = file_path.lower()

        if file_path_lower.endswith('.flac'):
            audio_file = FLAC(file_path)

            track_num = audio_file.get('tracknumber', [''])[0]
            track_title = audio_file.get('title', [''])[0]
            album_name = audio_file.get('album', [''])[0]
            album_artist = audio_file.get('albumartist', [''])[0]
            artist = audio_file.get('artist', [''])[0]

        elif file_path_lower.endswith('.mp3'):
            audio_file = MP3(file_path, ID3=ID3)
            if audio_file.tags is None:
                audio_file.add_tags()
                audio_file.save(v2_version=3)
                return "No tags found — initialized empty tag"

            id3 = audio_file.tags

            def get_text_frame(frame_id):
                frame = id3.get(frame_id)
                return frame.text[0] if frame and getattr(frame, "text", None) else ""

            track_num = get_text_frame('TRCK')
            track_title = get_text_frame('TIT2')
            album_name = get_text_frame('TALB')
            album_artist = get_text_frame('TPE2')  # album artist
            artist = get_text_frame('TPE1')        # track artist

        # 🚀 ADDED M4A/MP4 SUPPORT
        elif file_path_lower.endswith(('.m4a', '.mp4')):
            audio_file = MP4(file_path)

            def get_mp4_tag(tag_key):
                # MP4 tags are stored as lists, e.g., ['Title'] or [(1, 10)]
                return str(audio_file.get(tag_key, [''])[0]) if audio_file.get(tag_key) else ""

            # Standard MP4 atom names for tags:
            # Note: TPE2/TPE1 (MP3) is equivalent to aART/ART (MP4)
            track_num_raw = audio_file.get('trkn', [(0,0)])[0]
            track_num = str(track_num_raw[0]) if track_num_raw and track_num_raw[0] else ""
            
            track_title = get_mp4_tag('\xa9nam')
            album_name = get_mp4_tag('\xa9alb')
            album_artist = get_mp4_tag('aART') # Album Artist
            artist = get_mp4_tag('\xa9ART')    # Track Artist
        # 🚀 END M4A/MP4 SUPPORT

        else:
            return "Unsupported file format"

        # Use album artist if available, otherwise fall back to artist
        if not album_artist and artist:
            album_artist = artist

        # Clean up track number (handle e.g., "1/12")
        if track_num and '/' in track_num:
            track_num = track_num.split('/')[0].strip()
        # Clean up track number from M4A (it's often just a number string already, but good practice)
        try:
            if track_num:
                track_num = str(int(track_num))
        except ValueError:
            track_num = ""

        # Apply truncation
        if len(track_title) > max_title_length:
            track_title = track_title[:max_title_length - 3] + "..."
        if len(album_name) > max_album_length:
            album_name = album_name[:max_album_length - 3] + "..."

        # Build formatted message
        parts = []
        if include_track and track_num:
            try:
                track_num_int = int(track_num)
                parts.append(
                    f"{BLUE}{BRIGHT}Track #{track_num_int:02}{RESET}" if track_num_int == 1 else f"Track #{track_num_int:02}"
                )
            except ValueError:
                # Fallback if track_num is not a clean integer string
                parts.append(f"Track #??")

        if track_title:
            parts.append(track_title)
        if include_album and album_name:
            parts.append(album_name)
        if include_artist and album_artist:
            parts.append(album_artist)

        if not parts:
            return f"Unknown Track: {file_path}"

        return separator.join(parts)

    except Exception as e:
        return f"Error reading file: {str(e)[:50]}..."