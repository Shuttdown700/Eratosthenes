import os
import subprocess
import json

# Path to your binaries
BIN_DIR = os.path.join(os.path.dirname(__file__), "bin")
FFMPEG = os.path.join(BIN_DIR, "ffmpeg.exe")
FFPROBE = os.path.join(BIN_DIR, "ffprobe.exe")


def extract_subtitles_to_srt(input_mkv, subtitles_dir, dry_run=False):
    """
    Extract subtitles from an MKV file and save them in a specific format.

    Args:
        input_mkv (str): Path to the input MKV file.
        subtitles_dir (str): Path to the directory where subtitles will be saved.
        dry_run (bool): If True, simulates operations without extracting subtitles.
    """
    # Ensure the subtitles directory exists
    os.makedirs(subtitles_dir, exist_ok=True)

    # Use ffprobe to list streams and find subtitle tracks
    try:
        result = subprocess.run(
            [FFPROBE, "-v", "error", "-show_entries",
             "stream=index:stream_tags=language:stream_tags=title", 
             "-select_streams", "s", "-of", "json", input_mkv],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        subtitle_info = result.stdout
    except FileNotFoundError:
        print("FFmpeg or FFprobe not found in the specified bin directory.")
        return

    # Parse the subtitle streams
    subtitle_data = json.loads(subtitle_info)
    streams = subtitle_data.get("streams", [])

    if not streams:
        print(f"No subtitles found in {input_mkv}.")
        return

    # Extract each subtitle stream
    for stream in streams:
        index = stream["index"]
        lang = stream.get("tags", {}).get("language", f"track{index}")  # Use language tag or default name
        title = stream.get("tags", {}).get("title", "").replace(" ", "_").lower()  # Title as a distinguishing feature
        mkv_filename = os.path.splitext(os.path.basename(input_mkv))[0]

        # Build the subtitle filename
        if title:
            output_srt = os.path.join(subtitles_dir, f"{mkv_filename}.{lang}.{title}.srt")
        else:
            output_srt = os.path.join(subtitles_dir, f"{mkv_filename}.{lang}.srt")

        # Skip if the subtitle file already exists
        if os.path.exists(output_srt):
            print(f"Subtitle file already exists: {output_srt}")
            continue

        # Dry run mode: Show intended operations
        if dry_run:
            print(f"[Dry Run] Would extract subtitle from track {index} to: {output_srt}")
            continue

        # Run FFmpeg to extract the subtitle
        subprocess.run(
            [FFMPEG, "-i", input_mkv, "-map", f"0:s:{index}", output_srt, "-y"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        print(f"Extracted subtitle to: {output_srt}")


def process_mkv_files(root_dir, dry_run=False):
    """
    Find all MKV files in the given root directory and extract their subtitles.

    Args:
        root_dir (str): Path to the root directory to search for MKV files.
        dry_run (bool): If True, simulates operations without extracting subtitles.
    """
    for subdir, _, files in os.walk(root_dir):
        for file in files:
            if file.lower().endswith(".mkv"):
                input_mkv = os.path.join(subdir, file)
                subtitles_dir = os.path.join(subdir, "subtitles")
                print(f"Processing: {input_mkv}")
                extract_subtitles_to_srt(input_mkv, subtitles_dir, dry_run=dry_run)


if __name__ == "__main__":
    # Define the root directory to search for MKV files
    movie_directory = r"G:\Movies"  # Replace with your directory
    # Enable dry run by setting dry_run=True
    process_mkv_files(movie_directory, dry_run=True)
