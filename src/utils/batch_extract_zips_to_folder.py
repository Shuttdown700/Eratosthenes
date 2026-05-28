import os
import zipfile

def extract_zips_flat(source_dir, target_dir):
    """
    Extracts all zip files from source_dir into target_dir, 
    ignoring any internal directory structure within the zips.
    """
    # Create the target directory if it doesn't exist
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    # Loop through all items in the source directory
    for item in os.listdir(source_dir):
        if item.endswith('.zip'):
            zip_file_path = os.path.join(source_dir, item)
            print(f"Processing: {item}...")
            
            # Open the zip file
            with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                # Iterate through every item (file or folder) inside the zip
                for member in zip_ref.infolist():
                    # Skip internal directories
                    if member.is_dir():
                        continue
                        
                    # Extract just the filename, discarding its internal path
                    filename = os.path.basename(member.filename)
                    
                    # Failsafe: skip if the base filename is empty
                    if not filename:
                        continue
                        
                    # Construct the final destination path
                    target_path = os.path.join(target_dir, filename)
                    
                    # Read the file from the zip and write it directly to the target dir
                    with zip_ref.open(member) as source_file, open(target_path, "wb") as target_file:
                        target_file.write(source_file.read())
                        
    print("\nExtraction complete. All files are flattened in the target directory.")

# --- Example Usage ---
if __name__ == "__main__":
    # Replace these strings with your actual directory paths
    SOURCE_DIRECTORY = r'T:\ShuttFlix-Temp\Games\Arcade\snap_zips' 
    TARGET_DIRECTORY = r'T:\ShuttFlix-Temp\Games\Arcade\snaps'   
    
    extract_zips_flat(SOURCE_DIRECTORY, TARGET_DIRECTORY)