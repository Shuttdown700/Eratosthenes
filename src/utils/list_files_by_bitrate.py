import os
import subprocess
import json
from pathlib import Path
from tqdm import tqdm

import statistics
import math
import matplotlib.pyplot as plt

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utilities import get_primary_root_directories

# --- Configuration ---
FFPROBE = Path(__file__).resolve().parents[1] / "bin" / "ffprobe.exe"
EXTENSIONS = {'.mkv', '.mp4'}

def get_duration(file_path):
    """
    Uses ffprobe to get the duration of a video file in seconds.
    Returns float duration or None if it fails.
    """
    cmd = [
        FFPROBE, 
        '-v', 'error', 
        '-show_entries', 'format=duration', 
        '-of', 'json', 
        str(file_path)
    ]
    
    try:
        # Run ffprobe and capture output
        result = subprocess.run(cmd, capture_output=True, text=True)
        data = json.loads(result.stdout)
        return float(data['format']['duration'])
    except (ValueError, KeyError, json.JSONDecodeError, subprocess.SubprocessError):
        return None

def calculate_bitrate(file_path, duration):
    """
    Calculates bitrate and formats data for a single file.
    Returns a dictionary of file stats.
    """
    try:
        size_bytes = file_path.stat().st_size
        
        if duration > 0:
            # Raw bitrate: Bytes / Seconds
            raw_bitrate = size_bytes / duration
            
            # Convert to Mbps for display (Bytes * 8 / 1,000,000)
            mbps = (raw_bitrate * 8) / 1_000_000
            
            return {
                'path': file_path,
                'filename': file_path.name,
                'bitrate_raw': raw_bitrate,
                'mbps': mbps,
                'size_gb': size_bytes / (1024**3),
                'duration_min': duration / 60
            }
    except Exception as e:
        print(f"Error calculating bitrate for {file_path.name}: {e}")
        return None


def scan_directory(directory):
    """
    Recursively scans a directory for video files and collects stats.
    Returns a list of video data dictionaries.
    """
    video_data = []
    directory_path = Path(directory)
    
    if not directory_path.exists():
        print(f"Warning: Directory not found - {directory}")
        return []

    print(f"Scanning files in: {directory}...")
    
    # Step 1: Collect all valid file paths first (Instant)
    files_to_process = []
    for root, _, files in os.walk(directory_path):
        for file in files:
            if Path(file).suffix.lower() in EXTENSIONS:
                files_to_process.append(Path(root) / file)

    # Step 2: Process with Progress Bar
    # unit='vid' changes the label from "it/s" to "vid/s"
    # desc adds a label to the bar
    for full_path in tqdm(files_to_process, desc="Analyzing Bitrates", unit="vid"):
        
        # Get duration
        duration = get_duration(full_path)
        
        if duration:
            # Calculate stats (Assuming calculate_bitrate is defined elsewhere)
            # We must pass 'full_path.stat().st_size' if your calc function doesn't get it
            # But based on previous logic, calculate_bitrate takes (path, duration)
            stats = calculate_bitrate(full_path, duration)
            
            if stats:
                video_data.append(stats)
        else:
            # We use tqdm.write to avoid breaking the progress bar visual
            tqdm.write(f"Skipping (No Duration): {full_path.name}")
                    
    return video_data

def generate_statistics(media_type, video_data, output_dir):
    """
    Calculates stats (Mean, Median, 95% CI) and generates distribution plots.
    """
    if not video_data:
        return

    # Extract just the Mbps values for analysis
    bitrates = [v['mbps'] for v in video_data]
    n = len(bitrates)
    
    # --- 1. Calculate Statistics ---
    mean_val = statistics.mean(bitrates)
    median_val = statistics.median(bitrates)
    stdev_val = statistics.stdev(bitrates) if n > 1 else 0.0
    
    # Calculate 95% Confidence Interval
    # Formula: Mean ± (1.96 * StdDev)
    margin_of_error = 1.96 * (stdev_val)
    ci_lower = mean_val - margin_of_error
    ci_upper = mean_val + margin_of_error

    # Write Text Report
    stats_file = output_dir / f"{media_type.lower()[:-1].replace(' ', '_') if media_type.endswith('s') and media_type != 'series' else media_type.lower().replace(' ', '_')}_bitrate_stats.txt"
    with open(stats_file, 'w', encoding='utf-8') as f:
        f.write("Bitrate Statistics (Mbps)\n")
        f.write("=========================\n")
        f.write(f"Total Files:      {n}\n")
        f.write(f"Mean Bitrate:     {mean_val:.2f} Mbps\n")
        f.write(f"Median Bitrate:   {median_val:.2f} Mbps\n")
        f.write(f"Std Deviation:    {stdev_val:.2f} Mbps\n")
        f.write(f"95% Conf Interval: [{ci_lower:.2f} - {ci_upper:.2f}] Mbps\n")
        f.write("\nDistribution Context:\n")
        f.write(" - Files below lower CI might be low quality (Candidates for upgrade).\n")
        f.write(" - Files above upper CI might be inefficient (Candidates for re-encoding).\n")

    print(f"Stats written to: {stats_file}")

    # --- 2. Generate Graphics ---
    # We will create a figure with 2 subplots: A Histogram and a Box Plot
    plt.style.use('bmh') # Use a clean style
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 12))

    # Histogram (Frequency of bitrates)
    ax1.hist(bitrates, bins=20, color='#3498db', edgecolor='black', alpha=0.7)
    ax1.axvline(mean_val, color='red', linestyle='dashed', linewidth=1, label=f'Mean: {mean_val:.2f}')
    ax1.axvline(median_val, color='green', linestyle='dashed', linewidth=1, label=f'Median: {median_val:.2f}')
    ax1.set_title('Bitrate Distribution (Histogram)')
    ax1.set_xlabel('Bitrate (Mbps)')
    ax1.set_ylabel('Count of Files')
    ax1.legend()

    # Box Plot (Good for seeing outliers)
    ax2.boxplot(bitrates, vert=False, patch_artist=True, 
                boxprops=dict(facecolor='#2ecc71', color='black'))
    ax2.set_title('Bitrate Ranges & Outliers (Box Plot)')
    ax2.set_xlabel('Bitrate (Mbps)')
    
    # Save the plot
    plot_file = output_dir / f"{media_type.lower()[:-1].replace(' ', '_') if media_type.endswith('s') and media_type != 'series' else media_type.lower().replace(' ', '_')}_bitrate_distribution.png"
    plt.tight_layout()
    plt.savefig(plot_file)
    plt.close() # Close memory to prevent leaks
    
    print(f"Distribution plot saved to: {plot_file}")


def write_results(media_type, video_data, output_path):
    """
    Writes the ranked list to a text file AND triggers stats generation.
    """
    # Sort by bitrate (Highest to Lowest)
    video_data.sort(key=lambda x: x['bitrate_raw'], reverse=True)
    
    output_file = Path(output_path)
    # Get the parent directory so we can save stats/images next to the list
    output_dir = output_file.parent 
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nWriting {len(video_data):,} files to: {output_file}")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        # Header
        f.write(f"{'Bitrate (Mbps)':<15} {'Size (GB)':<10} {'Duration (m)':<12} {'File'}\n")
        f.write("-" * 80 + "\n")
        
        # Rows
        for vid in video_data:
            line = (
                f"{vid['mbps']:<15.2f} "
                f"{vid['size_gb']:<10.2f} "
                f"{vid['duration_min']:<12.1f} "
                f"{vid['path']}\n"
            )
            f.write(line)

    # --- NEW: Generate Stats & Plots ---
    if len(video_data) > 1:
        generate_statistics(media_type, video_data, output_dir)

def main(media_type, output_parent_folder):
    """
    Main orchestrator function.
    """

    source_dirs = get_primary_root_directories([media_type])

    script_dir = Path(__file__).parent.resolve()
    output_file_path = (script_dir / ".." / ".." /"output" / output_parent_folder / f"{media_type.lower()[:-1].replace(' ', '_') if media_type.endswith('s') and media_type != 'series' else media_type.lower().replace(' ', '_')}_bitrates.txt").resolve()

    all_video_data = []
    
    # 1. Scan all source directories
    for source in source_dirs:
        results = scan_directory(source)
        all_video_data.extend(results)

    # 2. Write ranked results
    if all_video_data:
        write_results(media_type, all_video_data, output_file_path)
        print("Done.")
    else:
        print("No video files found.")

if __name__ == "__main__":
    media_type = "Movies"  # Change to "Series" if needed
    output_parent_folder = "movies"  # Change to "series" if needed
    input_tuples = [
        ("Movies", "movies"),
        ("4K Movies", "movies"),
        ("Anime Movies", "movies"),
        ("Shows", "series"),
        ("Anime", "series"),
    ]
    input_tuples = [("Anime", "series")]  # For only doing one media type, comment out the above line and use this one
    for media_type, output_parent_folder in input_tuples:
        print(f"\n{'='*60}\nProcessing Media Type: {media_type}\n{'='*60}")
        main(media_type, output_parent_folder)