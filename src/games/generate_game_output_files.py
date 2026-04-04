import os
from pathlib import Path
from collections import Counter
import sys

from utilities_games import format_size

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utilities import get_primary_root_directories

class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    RESET = '\033[0m'

def get_region(filename: str, regions: list[str] = ["USA", "Europe", "Japan"]) -> str:
    """
    Scans the filename for standard region tags enclosed in parentheses or brackets.
    If no parentheses or brackets exist, it is flagged as 'Untagged'.
    """
    # --- NEW: Check if the file lacks any standard tag containers ---
    if "(" not in filename and "[" not in filename:
        return "Untagged"

    name_upper = filename.upper()
    
    for region in regions:
        # Prevent these fallback categories from being searched as literal tags
        if region.lower() in ["other", "untagged"]:
            continue
            
        r_upper = region.upper()
        if f"({r_upper}" in name_upper or f"({r_upper})" in name_upper or f"[{r_upper}]" in name_upper:
            return region
            
    # It has parentheses/brackets, but didn't match the specific regions we care about
    return "Other"

def generate_lists(root_dir: str, regions: list[str] = ["USA", "Europe", "Japan"]) -> None:
    root_path = Path(root_dir)
    output_path = Path(OUTPUT_DIRECTORY)

    if not root_path.exists() or not root_path.is_dir():
        print(f"{Colors.YELLOW}Error: Root directory not found at {root_dir}{Colors.RESET}")
        return

    # Create the output directory if it doesn't exist
    output_path.mkdir(parents=True, exist_ok=True)
    
    print(f"\n{Colors.CYAN}Scanning {root_dir} for console directories...{Colors.RESET}\n")

    for console_dir in root_path.iterdir():
        if not console_dir.is_dir():
            continue

        console_name = console_dir.name
        files = [f for f in console_dir.iterdir() if f.is_file()]

        if not files:
            print(f"Skipping {console_name} (Directory is empty)")
            continue

        # Gather metadata
        total_files = len(files)
        total_size_bytes = sum(f.stat().st_size for f in files)
        formatted_size = format_size(total_size_bytes)
        ext_counts = Counter(f.suffix.lower() for f in files)
        
        # Count Regions
        region_counts = Counter(get_region(f.stem, regions) for f in files)

        # Output filename formatting
        output_file_path = output_path / f"Game List - {console_name}.txt"

        with open(output_file_path, "w", encoding="utf-8") as out_file:
            # --- Write Aesthetic Header ---
            out_file.write("=" * 60 + "\n")
            out_file.write(f"{console_name.upper():^60}\n")
            out_file.write("=" * 60 + "\n\n")
            
            # --- Write Summary Section ---
            out_file.write("SUMMARY\n")
            out_file.write("-" * 60 + "\n")
            out_file.write(f"Total Games : {total_files:,}\n")
            out_file.write(f"Total Size  : {formatted_size}\n\n")
            
            # --- Write Region Section ---
            out_file.write("REGIONS\n")
            out_file.write("-" * 60 + "\n")
            
            # Filter out the fallback tags so we can explicitly force them to print at the very bottom
            display_regions = [r for r in regions if r.lower() not in ["other", "untagged"]]
            display_regions.extend(["Other", "Untagged"])
            
            for region in display_regions:
                count = region_counts.get(region, 0)
                if count > 0:
                    out_file.write(f"  {region:<15} {count:>5,}\n")
            out_file.write("\n")
            
            # --- Write File Types Section ---
            out_file.write("FILE TYPES\n")
            out_file.write("-" * 60 + "\n")
            for ext, count in ext_counts.most_common():
                ext_label = ext if ext else "[No Extension]"
                out_file.write(f"  {ext_label:<15} {count:>5,}\n")
            out_file.write("\n")

            out_file.write("=" * 60 + "\n")
            out_file.write(f"{'GAME LIST':^60}\n")
            out_file.write("=" * 60 + "\n\n")

            # --- Write File List (Without Extensions) ---
            for f in sorted(files, key=lambda x: x.stem.lower()):
                out_file.write(f" - {f.stem}\n")

        print(f"{Colors.GREEN}Generated:{Colors.RESET} {output_file_path.name} ({total_files:,} games, {formatted_size})")

    print(f"\n{Colors.CYAN}All lists generated successfully in {OUTPUT_DIRECTORY}!{Colors.RESET}")

# --- Configuration ---
OUTPUT_DIRECTORY = os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","..","output","games")

if __name__ == "__main__":
    # Initialize basic terminal colors for Windows
    os.system("")
    game_directories = get_primary_root_directories(['Games'])
    game_directories = [os.path.join(d,"Emulation","Game Files") for d in game_directories]
    
    # Define the specific regions to look for. "Other" and "Untagged" are handled automatically.
    regions = ["USA", "Europe", "Japan", "France"]  
    
    for game_dir in game_directories:
        generate_lists(game_dir, regions)