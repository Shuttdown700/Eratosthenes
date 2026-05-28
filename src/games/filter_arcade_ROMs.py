import os
import shutil
import xml.etree.ElementTree as ET
import re

# ================= CONFIGURATION =================
DRY_RUN = False

REQUIRE_MEDIA = True  # Set to False until your re-import is 100% finished
KEEP_PRELIMINARY = False # Allow "New" but imperfect systems like 3DO or 32X
KEEP_UNKNOWN = False     # Keep BIOS and Hardware files just in case

MAME_XML_PATH = r"T:\LaunchBox\Emulators\MAME 0.260\mame_data.xml"
LB_XML_PATH = r"T:\LaunchBox\Data\Platforms\Arcade.xml"
LB_IMAGES_DIR = r"T:\LaunchBox\Images\Arcade\Box - 3D"

ROM_SOURCE_DIR = r"V:\Games\Emulation\Game Files\Arcade (MAME 0.260)"
BAD_ROM_DESTINATION = r"V:\Games\Emulation\Game Files\Arcade (MAME 0.260) - Revoked"
# =================================================

def simplify(s):
    if not s: return ""
    return re.sub(r'[^a-zA-Z0-9]', '', str(s).lower())

def get_mame_status(xml_path):
    print("--- Step 1: Parsing MAME XML ---")
    status_map = {}
    tree = ET.parse(xml_path)
    root = tree.getroot()
    for machine in root.findall('machine'):
        name = machine.get('name').lower()
        driver = machine.find('driver')
        is_device = machine.get('isdevice') == "yes"
        status = driver.get('status') if driver is not None else "unknown"
        if not is_device:
            status_map[name] = status
    return status_map

def get_lb_data(xml_path, images_dir):
    print("--- Step 2: Parsing LaunchBox XML & Media ---")
    lb_games = {} # rom_name -> title
    image_names_simplified = set()

    for root_dir, _, files in os.walk(images_dir):
        for f in files:
            image_names_simplified.add(simplify(f))
    
    tree = ET.parse(xml_path)
    root = tree.getroot()
    for game in root.findall('Game'):
        title = (game.find('Title').text or "")
        app_path = (game.find('ApplicationPath').text or "")
        if app_path:
            rom_name = os.path.splitext(os.path.basename(app_path))[0].lower()
            lb_games[rom_name] = title

    return lb_games, image_names_simplified

def main():
    mame_status = get_mame_status(MAME_XML_PATH)
    lb_games, images = get_lb_data(LB_XML_PATH, LB_IMAGES_DIR)
    
    source_files = [f for f in os.listdir(ROM_SOURCE_DIR) if f.lower().endswith(('.7z', '.zip'))]
    
    keep_count = 0
    move_count = 0

    print(f"\n--- Analyzing {len(source_files)} ROMs ---")

    for filename in source_files:
        rom_name = os.path.splitext(filename)[0].lower()
        reason = ""
        
        # REVISED GATES:
        status = mame_status.get(rom_name, "missing")
        
        if status == "missing":
            if KEEP_UNKNOWN:
                # It's probably a BIOS or Support file
                reason = "" 
            else:
                reason = "Not a recognized MAME driver"
        
        elif status == "preliminary" and not KEEP_PRELIMINARY:
            reason = "MAME status is preliminary"

        # Check LaunchBox only if it passed MAME checks
        if not reason:
            title = lb_games.get(rom_name)
            if REQUIRE_MEDIA and title:
                clean_title = simplify(title)
                clean_rom = simplify(rom_name)
                has_image = any((clean_title in f or clean_rom in f) for f in images)
                if not has_image:
                    reason = f"No image found for '{title}'"
            elif REQUIRE_MEDIA and not title:
                reason = "Not tracked in LaunchBox"

        if not reason:
            keep_count += 1
        else:
            move_count += 1
            if DRY_RUN:
                # Only print specific games we are troubleshooting or the first few
                if move_count <= 20:
                    print(f"[MOVE] {filename.ljust(12)} | Reason: {reason}")
            else:
                if not os.path.exists(BAD_ROM_DESTINATION): os.makedirs(BAD_ROM_DESTINATION)
                shutil.move(os.path.join(ROM_SOURCE_DIR, filename), os.path.join(BAD_ROM_DESTINATION, filename))

    print(f"\n--- Final Results ---")
    print(f"Kept: {keep_count} | Moved: {move_count}")

if __name__ == "__main__":
    main()