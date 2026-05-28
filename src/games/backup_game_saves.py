import os
import shutil
import subprocess
from datetime import datetime

from colorama import Fore, Style, init
init() # Initializes colorama so colors render properly on Windows

game_save_locations = {
    "LaunchBox": r"T:\LaunchBox\Saves",
    "RetroArch": r"T:\LaunchBox\Emulators\RetroArch\saves",
    "MAME": r"T:\LaunchBox\Emulators\MAME 0.260\nvram",
    "DuckStation": r"C:\Users\brend\AppData\Local\DuckStation\memcards",
    "PCSX2": r"C:\Users\brend\Documents\PCSX2\memcards",
    "Dolphin - GameCube": r"C:\Users\brend\AppData\Roaming\Dolphin Emulator\GC",
    "Dolphin - Wii": r"C:\Users\brend\AppData\Roaming\Dolphin Emulator\Wii\title",
    "Sega Model 2 Emulator": r"C:\Users\brend\Sega Model 2 Emulator\NVDATA",
    "Sega Supermodel": r"C:\Users\brend\Sega Supermodel Emulator\NVRAM",
    "RPCS3": r"C:\Users\brend\RPCS3\dev_hdd0\home\00000001\savedata",
    "Ryubing Ryujinx": r"C:\Users\brend\Nintendo Swith Emulators\Ryujinx 1.3.3\portable\bis\user\save",
    "Azahar": r"C:\Users\brend\AppData\Roaming\Azahar\sdmc\Nintendo 3DS\00000000000000000000000000000000\00000000000000000000000000000000",
    "PPSSPP": r"C:\Users\brend\Documents\PPSSPP\PSP\SAVEDATA",
    "It Takes Two": r"C:\Users\brend\AppData\Local\ItTakesTwo",
    "Hollow Knight": r"C:\Users\brend\AppData\LocalLow\Team Cherry\Hollow Knight",
    "Overcooked - All You Can Eat": r"C:\Users\brend\AppData\LocalLow\Team17\Overcooked All You Can Eat",
    "Miyoo Mini Plus": r"\\10.0.0.193\Saves"
}

def is_device_online(ip_address):
    """Sends a single ping with a 1-second timeout to check if the device is active."""
    try:
        # -n 1 sends 1 packet, -w 1000 sets a 1000ms timeout
        result = subprocess.run(
            ["ping", "-n", "1", "-w", "1000", ip_address],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return result.returncode == 0
    except Exception:
        return False

def run_backup(game_save_locations,backup_location):
    print(f"Starting emulator save backup at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n" + "="*50)
    
    success_count = 0
    fail_count = 0

    for emulator, source_dir in game_save_locations.items():
        # Define the specific destination folder for this emulator
        destination = os.path.join(backup_location, emulator)
        
        # Intercept the Miyoo Mini Plus to verify network status first
        if emulator == "Miyoo Mini Plus":
            print("[INFO] Checking Miyoo Mini Plus network status...")
            if not is_device_online("10.0.0.193"):
                print(f"{Fore.YELLOW}[SKIP]{Style.RESET_ALL} Miyoo Mini Plus is offline. Skipping network backup.")
                continue

        # Check if the source path actually exists before trying to copy
        if os.path.exists(source_dir):
            try:
                if os.path.isdir(source_dir):
                    # dirs_exist_ok=True allows overwriting/updating existing backup folders
                    shutil.copytree(source_dir, os.path.join(backup_location, emulator), dirs_exist_ok=True)
                else:
                    # Fallback in case a specific path points to a file instead of a folder
                    os.makedirs(os.path.dirname(os.path.join(backup_location, emulator)), exist_ok=True)
                    shutil.copy2(source_dir, os.path.join(backup_location, emulator))
                    
                print(f"{Fore.GREEN}[SUCCESS]{Style.RESET_ALL} Backed up: {emulator}")
                success_count += 1
            except Exception as e:
                print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Failed to copy {emulator}. Reason: {e}")
                fail_count += 1
        else:
            print(f"{Fore.YELLOW}[WARNING]{Style.RESET_ALL} Path not found for {emulator}. Skipping.")
            fail_count += 1

    print("="*50)
    print(f"Backup complete. {success_count} succeeded, {fail_count} skipped/failed.")

if __name__ == "__main__":
    backup_location = r"I:\Backup\Emulator Game Saves"
    run_backup(game_save_locations, backup_location)

