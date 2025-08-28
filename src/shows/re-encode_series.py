import os
import subprocess
import glob

# Configuration: Hardcoded paths and settings
FFMPEG_BIN = "C:/ffmpeg/bin/ffmpeg.exe"  # Path to FFmpeg executable
ROOT_DIR = "D:/VideoSeries"              # Root directory to start recursive search
OUTPUT_DIR = "D:/VideoSeries/Output"     # Directory for output re-encoded files
ALLOWED_EXTENSIONS = (".mkv", ".mp4")    # Supported video file extensions
DELETE_ORIGINAL = False                  # Set to True to delete original files after successful re-encoding

def ensure_output_dir(input_path):
    """Create output directory structure mirroring input path."""
    relative_path = os.path.relpath(os.path.dirname(input_path), ROOT_DIR)
    output_subdir = os.path.join(OUTPUT_DIR, relative_path)
    if not os.path.exists(output_subdir):
        os.makedirs(output_subdir)
    return output_subdir

def get_video_files():
    """Recursively find video files in root directory and subdirectories."""
    video_files = []
    for root, _, files in os.walk(ROOT_DIR):
        for file in files:
            if file.lower().endswith(ALLOWED_EXTENSIONS):
                video_files.append(os.path.join(root, file))
    return sorted(video_files)

def reencode_video(input_file, output_file):
    """Re-encode a single video file from x264 to x265."""
    command = [
        FFMPEG_BIN,
        "-i", input_file,               # Input file
        "-c:v", "libx265",             # Video codec: x265
        "-preset", "medium",           # Encoding speed vs. compression
        "-crf", "23",                  # Constant Rate Factor (quality, lower = better)
        "-c:a", "copy",                # Copy audio streams unchanged
        "-c:s", "copy",                # Copy subtitle streams unchanged
        "-map", "0",                   # Include all streams from input
        "-y",                          # Overwrite output file if exists
        output_file
    ]
    
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        print(f"Successfully re-encoded: {input_file} -> {output_file}")
        
        # Delete original file if DELETE_ORIGINAL is True and re-encoding was successful
        if DELETE_ORIGINAL:
            try:
                os.remove(input_file)
                print(f"Deleted original file: {input_file}")
            except OSError as e:
                print(f"Error deleting original file {input_file}: {e}")
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error re-encoding {input_file}: {e.stderr}")
        return False

def main():
    """Main function to process all video files recursively."""
    video_files = get_video_files()
    
    if not video_files:
        print("No video files found in root directory or subdirectories.")
        return
    
    total_files = len(video_files)
    successful = 0
    
    for idx, input_file in enumerate(video_files, 1):
        output_subdir = ensure_output_dir(input_file)
        filename = os.path.basename(input_file)
        output_file = os.path.join(output_subdir, filename)
        
        print(f"Processing ({idx}/{total_files}): {input_file}")
        if reencode_video(input_file, output_file):
            successful += 1
    
    print(f"\nCompleted: {successful}/{total_files} files successfully re-encoded.")

if __name__ == "__main__":
    main()