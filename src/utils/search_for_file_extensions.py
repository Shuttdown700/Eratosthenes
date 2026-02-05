import pathlib
import os

# --- Global Configurations ---
TARGET_EXTENSION = ".mp4"
# Add as many root paths as you need to this list
media_type = "Movies"
ROOT_DIRECTORIES = [
    rf"R:\{media_type}",
    rf"A:\{media_type}",
]
OUTPUT_FOLDER = os.path.join(os.path.dirname(__file__),"..","..","output",media_type)
OUTPUT_FILENAME = f"{media_type.lower()}_mp4_list.txt"

def find_files_multi_root():
    output_dir = pathlib.Path(OUTPUT_FOLDER)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file_path = output_dir / OUTPUT_FILENAME
    
    all_found_files = []

    for root_path in ROOT_DIRECTORIES:
        root = pathlib.Path(root_path)
        
        # Check if the path actually exists to avoid errors
        if not root.exists():
            print(f"Skipping: {root_path} (Directory not found)")
            continue
            
        print(f"Searching in: {root.absolute()}...")
        
        # Collect paths and add them to our master list
        files_found = list(root.rglob(f"*{TARGET_EXTENSION}"))
        all_found_files.extend(files_found)

    if not all_found_files:
        print("No matching files found across any directories.")
        return

    # Write all combined results to the single output file
    with open(output_file_path, "w", encoding="utf-8") as f:
        for file in all_found_files:
            size = round(os.path.getsize(file)/10**9, 2)  # Convert to GB and round to 2 decimal places
            f.write(f"{file.absolute()} ({size} GB)\n")

    print("-" * 30)
    print(f"Success! Found {len(all_found_files)} total files.")
    print(f"Combined list saved to: {output_file_path.absolute()}")

if __name__ == "__main__":
    find_files_multi_root()