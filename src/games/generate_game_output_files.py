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

def generate_lists(root_dir: str):
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
            
            out_file.write("FILE TYPES\n")
            out_file.write("-" * 60 + "\n")
            for ext, count in ext_counts.most_common():
                ext_label = ext if ext else "[No Extension]"
                # Pad the label to 15 characters and right-align the count
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
    for game_dir in game_directories:
        generate_lists(game_dir)