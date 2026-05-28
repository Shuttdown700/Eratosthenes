import os
import subprocess
import shutil

# ================= CONFIGURATION =================
# Path to your 7-Zip executable
SEVEN_ZIP_PATH = r"C:\Program Files\7-Zip\7z.exe"

# The folder containing your original .7z ROMs
SOURCE_DIR = r"V:\Games\Emulation\Game Files\Arcade"

# Where the new .zip files will be saved
DEST_DIR = r"V:\Games\Emulation\Game Files\Arcade_Zips"

# Temporary extraction folder (will be cleaned up automatically)
TEMP_EXTRACT_DIR = r"V:\Games\Emulation\Game Files\temp_conversion"
# =================================================

def convert_to_zip():
    # Ensure destination and temp folders exist
    if not os.path.exists(DEST_DIR):
        os.makedirs(DEST_DIR)
    if not os.path.exists(TEMP_EXTRACT_DIR):
        os.makedirs(TEMP_EXTRACT_DIR)

    files = [f for f in os.listdir(SOURCE_DIR) if f.lower().endswith('.7z')]
    total = len(files)
    print(f"Found {total} files to convert.")

    for index, filename in enumerate(files):
        base_name = os.path.splitext(filename)[0]
        src_7z = os.path.join(SOURCE_DIR, filename)
        dst_zip = os.path.join(DEST_DIR, f"{base_name}.zip")

        # Skip if zip already exists (useful if you have to resume the script)
        if os.path.exists(dst_zip):
            print(f"[{index + 1}/{total}] Skipping {filename} - already exists.")
            continue

        print(f"[{index + 1}/{total}] Converting {filename}...")

        # 1. Extract .7z to the temp folder
        # -o{path} must NOT have a space after the -o
        extract_cmd = [SEVEN_ZIP_PATH, "x", src_7z, f"-o{TEMP_EXTRACT_DIR}", "-y"]
        
        # 2. Compress the contents of temp folder into .zip in the DEST_DIR
        # -mx1 = "Fastest" compression (perfect for MAME ROMs)
        compress_cmd = [SEVEN_ZIP_PATH, "a", "-tzip", "-mx1", dst_zip, os.path.join(TEMP_EXTRACT_DIR, "*")]

        try:
            # Execute Extraction
            subprocess.run(extract_cmd, check=True, capture_output=True)
            
            # Execute Compression
            subprocess.run(compress_cmd, check=True, capture_output=True)

            # 3. Clean up temp folder contents for the next file
            # We use a wildcard delete to keep the folder but clear the files
            for item in os.listdir(TEMP_EXTRACT_DIR):
                item_path = os.path.join(TEMP_EXTRACT_DIR, item)
                if os.path.isfile(item_path):
                    os.remove(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)

        except subprocess.CalledProcessError as e:
            print(f"Error converting {filename}: {e}")
            continue

    # Final cleanup of the temp directory itself
    if os.path.exists(TEMP_EXTRACT_DIR):
        shutil.rmtree(TEMP_EXTRACT_DIR)

    print(f"\nSuccess! All files converted to: {DEST_DIR}")

if __name__ == "__main__":
    convert_to_zip()