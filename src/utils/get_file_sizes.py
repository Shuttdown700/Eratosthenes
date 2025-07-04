import os

def get_sorted_files_by_size(directory, allowed_extensions):
    try:
        # Walk through all subdirectories and get files with the allowed extensions
        files = [
            (f, os.path.getsize(os.path.join(root, f)))
            for root, _, filenames in os.walk(directory)
            for f in filenames
            if os.path.splitext(f)[1].lower() in allowed_extensions
        ]

        # Sort files by size in descending order
        sorted_files = sorted(files, key=lambda x: x[1], reverse=True)
        num_files_to_show = min(10, len(sorted_files))
        sorted_files = sorted_files[:num_files_to_show]  # Limit to top 100 files
        # Print the sorted list of files with sizes in GB
        # print(f"{'File Path':<100} {'Size (GB)':>10}")
        # print("-" * 120)
        for file, size in sorted_files:
            print(f"{size / (1024 ** 3):>10.2f} GB | {file:<100} ")
    
    except FileNotFoundError:
        print(f"Error: The directory '{directory}' does not exist.")
    except PermissionError:
        print(f"Error: Permission denied to access '{directory}'.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

# Set the directory to scan and allowed file extensions
directory_path = "A:\\4K Movies\\"
allowed_extensions = {".mkv", ".mp4"}

# Call the function
get_sorted_files_by_size(directory_path, allowed_extensions)
