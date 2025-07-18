import os

from utilities import get_file_size

def list_mp4_files(mp4_root_dir, output_file):
    with open(output_file, 'w', encoding='utf-8') as f:
        for dirpath, _, filenames in os.walk(mp4_root_dir):
            for filename in filenames:
                if filename.lower().endswith('.mp4'):
                    filze_size_GB = get_file_size(os.path.join(dirpath, filename),"GB")
                    f.write(filename + " | " + str(round(filze_size_GB,2)) + " GB" + '\n')

if __name__ == "__main__":
    # Set the directory where .mp4 files are located
    mp4_root_dir = r"B:\Shows"

    # Build the output file path relative to project root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, '..'))
    output_path = os.path.join(project_root, 'output', 'mp4_shows_BACARA.txt')

    # Make sure the output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    list_mp4_files(mp4_root_dir, output_path)
    print(f"MP4 file list saved to: {output_path}")
