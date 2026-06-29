import os
import re

class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    RESET = '\033[0m'

def has_region_tag(filename):
    """Checks if a ROM filename contains a known region tag."""
    tags_list = re.findall(r'\(([^)]+)\)|\[([^\]]+)\]', filename)
    tags_raw = [t[0] or t[1] for t in tags_list]
    tags_lower = [t.lower().strip() for t in tags_raw]
    tags_string = " ".join(tags_lower)
    
    # Comprehensive list of standard region keywords
    region_keywords = r'\b(japan|taiwan|china|korea|asia|france|sweden|mexico|brazil|germany|es|it|nl|sv|pt|chinese|ch|netherlands|italy|switzerland|russian|russia|poland|portugal|spain|greece|norway|denmark|finland|en|usa|europe|world|uk|australia|ue|canada|india|czech|unknown)\b'
    
    if re.search(region_keywords, tags_string):
        return True
        
    # Check for standard shortcode region identifiers (like U, E, J, W from GoodTools)
    exact_short_codes = {'u', 'e', 'j', 'w', 'us', 'eu', 'uk', 'kr', 'tw', 'cn', 'br'}
    for tag in tags_lower:
        parts = re.split(r'[, ]+', tag)
        if any(p in exact_short_codes for p in parts):
            return True
            
    return False

def parse_rom_info(filename):
    # Extract base name (everything before the first '(' or '[')
    base_name_match = re.match(r'^([^\[\(]+)', filename)
    base_name = base_name_match.group(1).lower().strip() if base_name_match else filename.replace('.zip', '').lower()
    
    lower_name = filename.lower()
    
    # Extract all tags
    tags_list = re.findall(r'\(([^)]+)\)|\[([^\]]+)\]', filename)
    tags_raw = [t[0] or t[1] for t in tags_list]
    tags_lower = [t.lower().strip() for t in tags_raw]
    tags_string = " ".join(tags_lower)
    
    # 1. Determine if English (Foreign games without an English tag get flagged)
    is_english = True 
    if re.search(r'\b(japan|taiwan|china|korea|asia|france|sweden|brazil|germany|es|it|r|nl|sv|pt|chinese|chinese version|ch|Jjapan, asia|japan , korea|netherlands|italy|switzerland|russian|russia|poland|portugal|spain|germany|greece|norway|denmark|finland)\b', tags_string):
        if not re.search(r'\b(en|usa|europe|world|uk|australia|ue)\b', tags_string):
            is_english = False

    # 2. Track & Mod Identification
    is_unl = bool(re.search(r'\b(proto|prototype|hack|beta|demo|sample|unl|pirate|aftermarket|homebrew|program|pd|subset|sachen|p1|!)\b', tags_string))
    is_hack = 'hack' in tags_string
    is_subset = 'subset' in tags_string
    
    # 2.5 Flag Prototypes, Betas, and Demos for outright removal
    is_proto = bool(re.search(r'\b(proto|prototype|hack|beta|demo|sample|unl|pirate|aftermarket|homebrew|program|pd|subset|sachen|p1|!)\b', tags_string))
    
    # Translations: Fan translations of USA/Europe games (standalone language tags)
    is_translated = False
    for t in tags_lower:
        # Common standalone fan-translation languages applied to English games
        if t in ['ru', 'pt', 'pt-br', 'tr', 'pl', 'zh', 'ar'] and not is_unl and not is_hack:
            is_translated = True
        # If a USA game has a standalone foreign language tag, it's almost certainly a fan translation patch
        if t in ['es', 'fr', 'de', 'it', 'nl', 'sv', 't'] and 'usa' in tags_lower and not is_unl and not is_hack:
            is_translated = True

    # 3. Find unique variant tags to protect distinct mods (e.g. "Luigi", "Widescreen", "Zelda64rus")
    safe_words = {'usa', 'europe', 'japan', 'world', 'australia', 'uk', 'france', 'germany', 'spain', 'italy', 'sweden', 'korea', 'taiwan', 'china', 'brazil', 'u', 'e', 'j', 'w', 'en', 't-en'}
    lang_pattern = r'^[a-z]{2}(-[a-z]{2})?(,[a-z]{2}(-[a-z]{2})?)*$'
    version_pattern = r'^(rev\s*\w+|v\d+(\.\d+)*|beta\s*\d*|proto\s*\d*|demo|sample|alt)$'
    
    # Added a pattern to explicitly recognize serial numbers (e.g., slus-21358, sles-12345)
    serial_pattern = r'^[a-z]{3,4}-\d{3,5}$'
    
    non_standard_tags = []
    for tag in tags_raw:
        t_clean = tag.strip().lower()
        
        # Skip standard checks if it's explicitly one of our known track keywords
        if t_clean in ['hack', 'unl', 'pirate', 'aftermarket'] or 'subset' in t_clean:
            continue
            
        # Check if it's a known language, region, version, or serial number
        is_safe = False
        if re.match(lang_pattern, t_clean) or re.match(r'^m\d+$', t_clean): 
            is_safe = True
        elif re.match(version_pattern, t_clean): 
            is_safe = True
        elif re.match(serial_pattern, t_clean):
            is_safe = True
        else:
            parts = re.split(r'[, ]+', t_clean)
            if all(p in safe_words or re.match(lang_pattern, p) for p in parts):
                is_safe = True
                
        if not is_safe:
            non_standard_tags.append(tag.strip())

    # 4. Modify Base Name for Multipart or Unique Hacks
    vol_match = re.search(r'\b(part\s*\d+|vol\.?\s*\d+)\b', lower_name)
    if vol_match:
        base_name += f" ({vol_match.group(1).title()})"
        
    if non_standard_tags:
        # Append unique mod/translator names to the base name so they never compete with each other
        for nst in non_standard_tags:
            base_name += f" [{nst}]"

    # 5. Determine Final Track Category
    if is_subset: track = "Subset"
    elif is_hack: track = "Hack"
    elif is_unl: track = "Unlicensed"
    elif is_translated: track = "Translated"
    elif non_standard_tags: track = "Mod/Variant"
    else: track = "Licensed"

    # 6. Scoring
    region_score = 0
    if 'usa' in tags_string: region_score = 3
    elif 'world' in tags_string: region_score = 2
    elif 'europe' in tags_string: region_score = 1
        
    version_score = 0
    rev_match = re.search(r'\brev\s*([a-z0-9]+)\b', tags_string)
    if rev_match:
        val = rev_match.group(1)
        if val.isdigit():
            version_score = int(val)
        elif len(val) == 1 and val.isalpha():
            version_score = ord(val) - 96
        else:
            # Fallback for weird strings: extract digits or default to 1
            digits = ''.join(filter(str.isdigit, val))
            version_score = int(digits) if digits else 1
            
    # FIXED: Now matches up to three version numbers (Major.Minor.Patch)
    v_match = re.search(r'\bv([0-9]+)\.([0-9]+)(?:\.([0-9]+))?\b', tags_string)
    if v_match:
        major = int(v_match.group(1))
        minor = int(v_match.group(2))
        patch = int(v_match.group(3)) if v_match.group(3) else 0
        
        # Calculate a tiered score (e.g. v1.6.5 = 10605)
        v_score = (major * 10000) + (minor * 100) + patch
        version_score = max(version_score, v_score)
        
    return {
        'filename': filename,
        'base_name': base_name,
        'track': track,
        'is_english': is_english,
        'is_proto': is_proto,
        'region_score': region_score,
        'version_score': version_score
    }

def main(directory, exclusions):
    extensions = ['.zip','.7z','.rar','.gz','.chd','.iso','.bin','.cue','.img','.nrg','.mdf','.n64','.rvz','.nes','.pce','.pbp']
    all_files = [f for f in os.listdir(directory) if f.lower().endswith(tuple(extensions))]
    if not all_files:
        print(f"\n{Colors.RED}No files found in the {Colors.RESET}{os.path.basename(directory)}{Colors.RED} directory.{Colors.RESET}")
        return 0

    roms = []
    for f in all_files:
        if any(excl.lower() in f.lower() for excl in exclusions):
            print(f"{Colors.GREEN}[PROTECTED]{Colors.RESET} {f}")
            continue
            
        # --- NEW: Fix multiple (Unknown) tags ---
        # Finds 2 or more consecutive instances of "(Unknown)" (ignoring case/spacing) and replaces with a single one.
        clean_f = re.sub(r'(?:\s*\(\s*unknown\s*\)){2,}', ' (Unknown)', f, flags=re.IGNORECASE)
        if clean_f != f:
            old_path = os.path.join(directory, f)
            new_path = os.path.join(directory, clean_f)
            try:
                if not os.path.exists(new_path):
                    os.rename(old_path, new_path)
                    print(f"{Colors.GREEN}[FIXED DOUBLE TAG]{Colors.RESET} '{f}' -> '{clean_f}'")
                    f = clean_f # Update filename variable so the rest of the loop uses the corrected name
                else:
                    print(f"{Colors.RED}[CONFLICT]{Colors.RESET} Cannot fix '{f}', '{clean_f}' already exists.")
            except Exception as e:
                print(f"{Colors.RED}Error fixing {f}:{Colors.RESET} {e}")
        # ----------------------------------------

        # Region Check and File Renaming Logic
        if not has_region_tag(f):
            name, ext = os.path.splitext(f)
            new_f = f"{name} (Unknown){ext}"
            old_path = os.path.join(directory, f)
            new_path = os.path.join(directory, new_f)
            try:
                if not os.path.exists(new_path):
                    os.rename(old_path, new_path)
                    print(f"{Colors.YELLOW}[RENAMED - NO REGION]{Colors.RESET} '{f}' -> '{new_f}'")
                    f = new_f
                else:
                    print(f"{Colors.RED}[CONFLICT]{Colors.RESET} Cannot rename '{f}', '{new_f}' already exists.")
            except Exception as e:
                print(f"{Colors.RED}Error renaming {f}:{Colors.RESET} {e}")
                
        roms.append(f)

    delete_candidates = []
    games_by_group = {}

    for rom in roms:
        info = parse_rom_info(rom)
        if not info['is_english']:
            delete_candidates.append((rom, "Non-English/Foreign Release"))
        elif info['is_proto']:
            delete_candidates.append((rom, "Prototype/Beta/Demo Release"))
        else:
            group_key = f"{info['base_name']} ({info['track']})"
            
            if group_key not in games_by_group:
                games_by_group[group_key] = []
            games_by_group[group_key].append(info)

    for group_key, versions in games_by_group.items():
        if len(versions) > 1:
            # SORTS BY REGION FIRST, THEN VERSION, THEN FILENAME LENGTH, THEN ALPHABETICALLY
            versions.sort(key=lambda x: (x['region_score'], x['version_score'], len(x['filename']), x['filename']), reverse=True)
            keeper = versions[0]
            for duplicate in versions[1:]:
                reason = f"Superseded by '{keeper['filename']}' ({keeper['track']} track)"
                delete_candidates.append((duplicate['filename'], reason))

    if not delete_candidates:
        print(f"\n{Colors.GREEN}Directory for {Colors.RESET}{os.path.basename(directory)}{Colors.GREEN} is already clean with {Colors.RESET}{len(roms):,} ROMs{Colors.GREEN}. No files need to be deleted.{Colors.RESET}")
        return len(roms)

    print(f"\n{Colors.CYAN}--- DELETE CANDIDATES ROLLUP FOR {os.path.basename(directory).upper()} ---{Colors.RESET}")
    for filename, reason in delete_candidates:
        print(f"{Colors.YELLOW}[DELETE]{Colors.RESET} {filename}")
        print(f"         {Colors.RED}Reason:{Colors.RESET} {reason}")
        
    print(f"{Colors.CYAN}--------------------------------{Colors.RESET}")
    print(f"Total files to delete: {Colors.RED}{len(delete_candidates)}{Colors.RESET} out of {len(all_files)}")

    confirm = input(f"\nDo you want to permanently delete these files? (y/n): ").strip().lower()
    
    if confirm == 'y':
        for filename, _ in delete_candidates:
            file_path = os.path.join(directory, filename)
            try:
                os.remove(file_path)
                print(f"{Colors.GREEN}Deleted:{Colors.RESET} {filename}")
            except Exception as e:
                print(f"{Colors.RED}Error deleting {filename}:{Colors.RESET} {e}")
        print(f"\n{Colors.GREEN}Cleanup complete!.{Colors.RESET}")
        return len(roms) - len(delete_candidates)
    else:
        print(f"\n{Colors.YELLOW}Operation cancelled. No files were deleted.{Colors.RESET}")
        return len(roms)

def batch_cleanup_rom_collection():
    # Set this to your directory path if running from elsewhere, e.g., "C:\\ROMs"
    DIRECTORIES = [
    r"V:\Games\Emulation\Game Files\3DO Interactive Multiplayer",
    r"V:\Games\Emulation\Game Files\Atari 2600",
    r"V:\Games\Emulation\Game Files\Atari 5200",
    r"V:\Games\Emulation\Game Files\Atari 7800",
    r"V:\Games\Emulation\Game Files\Atari Jaguar",
    r"V:\Games\Emulation\Game Files\Atari Lynx",
    r"V:\Games\Emulation\Game Files\Commodore 64",
    r"V:\Games\Emulation\Game Files\Commodore Amiga CD32",
    r"V:\Games\Emulation\Game Files\Microsoft Xbox",
    r"V:\Games\Emulation\Game Files\NEC TurboGrafx-16",
    r"V:\Games\Emulation\Game Files\NEC TurboGrafx-CD",
    r"V:\Games\Emulation\Game Files\Nintendo 3DS",
    r"V:\Games\Emulation\Game Files\Nintendo 64",
    r"V:\Games\Emulation\Game Files\Nintendo DS",
    r"V:\Games\Emulation\Game Files\Nintendo Entertainment System",
    r"V:\Games\Emulation\Game Files\Nintendo Game Boy",
    r"V:\Games\Emulation\Game Files\Nintendo Game Boy Color",
    r"V:\Games\Emulation\Game Files\Nintendo Game Boy Advance",
    r"V:\Games\Emulation\Game Files\Nintendo GameCube",
    # r"V:\Games\Emulation\Game Files\Nintendo Switch",
    r"V:\Games\Emulation\Game Files\Nintendo Wii",
    r"V:\Games\Emulation\Game Files\Sega 32X",
    r"V:\Games\Emulation\Game Files\Sega CD",
    r"V:\Games\Emulation\Game Files\Sega Dreamcast",
    r"V:\Games\Emulation\Game Files\Sega Game Gear",
    r"V:\Games\Emulation\Game Files\Sega Genesis (aka Mega Drive)",
    r"V:\Games\Emulation\Game Files\Sega Master System",
    r"V:\Games\Emulation\Game Files\Sega Saturn",
    r"V:\Games\Emulation\Game Files\SNK Neo Geo CD",
    r"V:\Games\Emulation\Game Files\SNK Neo Geo Pocket",
    r"V:\Games\Emulation\Game Files\SNK Neo Geo Pocket Color",
    # r"V:\Games\Emulation\Game Files\SNK Neo-Geo AES",
    r"V:\Games\Emulation\Game Files\Sony PlayStation (PSX)",
    r"V:\Games\Emulation\Game Files\Sony PlayStation 2",
    # r"V:\Games\Emulation\Game Files\Sony PlayStation 3",
    r"V:\Games\Emulation\Game Files\Sony PSP",
    r"V:\Games\Emulation\Game Files\Super Nintendo Entertainment System"
    ]

    EXCLUSIONS = ["King's Field (Japan) (T-En)","Raiden DX (Japan)",
                  "Metal Wolf Chaos (Japan)",
                  "DoDonPachi (Japan)"]

    total_num_ROMs = 0
    for directory in DIRECTORIES:
        # Add exactly matching filenames or partial strings here that you NEVER want deleted
        num_ROMS = main(directory, EXCLUSIONS)
        total_num_ROMs += num_ROMS
    print(f"\n{Colors.GREEN}All directories processed.{Colors.RESET}")
    print(f"{Colors.GREEN}Total ROMs after cleanup: {Colors.RESET}{total_num_ROMs:,}")

if __name__ == "__main__":
    batch_cleanup_rom_collection()