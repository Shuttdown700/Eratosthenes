import os

def print_directory_tree(startpath):
    for root, dirs, files in os.walk(startpath):
        level = root.replace(startpath, '').count(os.sep)
        indent = ' ' * 4 * (level)
        print(f'{indent}{os.path.basename(root)}/')
        subindent = ' ' * 4 * (level + 1)
        for f in files:
            print(f'{subindent}{f}')

# directory = os.path.join(os.path.dirname(__file__), '..', '..')
directory = r"K:\Temp\Lego Star Wars Droid Tales Complete 2015 Burntodisc\Disc\VIDEO_TS"
print_directory_tree(directory)