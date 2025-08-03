import os
import json
from collections import defaultdict, OrderedDict

from colorama import Fore, init, Style

init(autoreset=True)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "../.."))

WHITELIST_FOLDER = os.path.join(PROJECT_ROOT, "config", "show_whitelists" ,"active")
SHOWS_LIST_PATH = os.path.join(PROJECT_ROOT, "output", "shows", "shows_list.txt")
ANIME_LIST_PATH = os.path.join(PROJECT_ROOT, "output", "anime", "anime_list.txt")
OUTPUT_JSON = os.path.join(PROJECT_ROOT, "output", "active_backup_summary.json")

def load_list(path):
    with open(path, encoding='utf-8') as f:
        return set(line.strip() for line in f if line.strip())

def main():
    from update_media_list import update_all_media_lists
    update_all_media_lists()
    # Load master list
    all_titles = load_list(SHOWS_LIST_PATH) | load_list(ANIME_LIST_PATH)

    # Track how many drives back up each title
    backup_locations = defaultdict(list)

    for filename in os.listdir(WHITELIST_FOLDER):
        if "_whitelist" in filename:
            path = os.path.join(WHITELIST_FOLDER, filename)
            drive_name = os.path.splitext(filename)[0].replace("_whitelist", "")
            with open(path, encoding='utf-8') as f:
                for line in f:
                    title = line.strip()
                    if title:
                        backup_locations[title].append(drive_name)

    # Organize into buckets
    buckets = defaultdict(dict)
    for title in all_titles:
        drives = backup_locations.get(title, [])
        count = len(drives)
        bucket_key = f"{count} backup" if count == 1 else f"{count} backups"
        if count == 0:
            bucket_key = "0 backups"
        buckets[bucket_key][title] = drives

    # Sort keys numerically
    def sort_key(label):
        return int(label.split()[0])
    
    sorted_buckets = OrderedDict()
    for key in sorted(buckets.keys(), key=sort_key):
        sorted_buckets[key] = dict(sorted(buckets[key].items()))  # Sort titles alphabetically

    # Save output
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(sorted_buckets, f, indent=4, ensure_ascii=False)

    print(f"{Fore.GREEN}Detailed backup summary saved{Style.RESET_ALL}: {OUTPUT_JSON}")

if __name__ == "__main__":
    main()