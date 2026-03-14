import os
import re

# Set this to your directory path if running from elsewhere, e.g., "C:\\ROMs"
DIRECTORY = r"V:\Temp\saturn" 

# Add exactly matching filenames or partial strings here that you NEVER want deleted
EXCLUSIONS = []

class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    RESET = '\033[0m'

def parse_rom_info(filename):
    # Extract base name (everything before the first '(' or '[')
    base_name_match = re.match(r'^([^\[\(]+)', filename)
    base_name = base_name_match.group(1).strip() if base_name_match else filename.replace('.zip', '')
    
    lower_name = filename.lower()
    
    # Extract all tags
    tags_list = re.findall(r'\(([^)]+)\)|\[([^\]]+)\]', filename)
    tags_raw = [t[0] or t[1] for t in tags_list]
    tags_lower = [t.lower().strip() for t in tags_raw]
    tags_string = " ".join(tags_lower)
    
    # 1. Determine if English (Foreign games without an English tag get flagged)
    is_english = True 
    if re.search(r'\b(japan|taiwan|china|korea|france|germany|es|it|nl|sv|pt)\b', tags_string):
        if not re.search(r'\b(en|usa|europe|world|uk|australia|ue)\b', tags_string):
            is_english = False

    # 2. Track & Mod Identification
    is_unl = bool(re.search(r'\b(unl|pirate|aftermarket)\b', tags_string))
    is_hack = 'hack' in tags_string
    is_subset = 'subset' in tags_string
    
    # Translations: Fan translations of USA/Europe games (standalone language tags)
    is_translated = False
    for t in tags_lower:
        # Common standalone fan-translation languages applied to English games
        if t in ['ru', 'pt', 'pt-br', 'tr', 'pl', 'zh', 'ar'] and not is_unl and not is_hack:
            is_translated = True
        # If a USA game has a standalone foreign language tag, it's almost certainly a fan translation patch
        if t in ['es', 'fr', 'de', 'it', 'nl', 'sv'] and 'usa' in tags_lower and not is_unl and not is_hack:
            is_translated = True

    # 3. Find unique variant tags to protect distinct mods (e.g. "Luigi", "Widescreen", "Zelda64rus")
    safe_words = {'usa', 'europe', 'japan', 'world', 'australia', 'uk', 'france', 'germany', 'spain', 'italy', 'sweden', 'korea', 'taiwan', 'china', 'brazil', 'u', 'e', 'j', 'w', 'en'}
    lang_pattern = r'^[a-z]{2}(-[a-z]{2})?(,[a-z]{2}(-[a-z]{2})?)*$'
    version_pattern = r'^(rev\s*\w+|v\d+(\.\d+)*|beta\s*\d*|proto\s*\d*|demo|sample|alt)$'
    
    non_standard_tags = []
    for tag in tags_raw:
        t_clean = tag.strip().lower()
        
        # Skip standard checks if it's explicitly one of our known track keywords
        if t_clean in ['hack', 'unl', 'pirate', 'aftermarket'] or 'subset' in t_clean:
            continue
            
        # Check if it's a known language, region, or version
        is_safe = False
        if re.match(lang_pattern, t_clean) or re.match(r'^m\d+$', t_clean): 
            is_safe = True
        elif re.match(version_pattern, t_clean): 
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
            
    v_match = re.search(r'\bv([0-9]+)\.([0-9]+)\b', tags_string)
    if v_match:
        v_score = int(v_match.group(1)) * 10 + int(v_match.group(2))
        version_score = max(version_score, v_score)
        
    if 'proto' in tags_string or 'beta' in tags_string:
        version_score = -1
        
    return {
        'filename': filename,
        'base_name': base_name,
        'track': track,
        'is_english': is_english,
        'region_score': region_score,
        'version_score': version_score
    }

def main():
    extensions= ['.zip','.7z','.rar','.gz','.chd','.iso','.bin','.cue','.img','.nrg','.mdf','.n64']
    all_files = [f for f in os.listdir(DIRECTORY) if f.lower().endswith(tuple(extensions))]
    if not all_files:
        print(f"{Colors.RED}No files found in the specified directory.{Colors.RESET}")
        return

    roms = []
    for f in all_files:
        if any(excl.lower() in f.lower() for excl in EXCLUSIONS):
            print(f"{Colors.GREEN}[PROTECTED]{Colors.RESET} {f}")
            continue
        roms.append(f)

    delete_candidates = []
    games_by_group = {}

    for rom in roms:
        info = parse_rom_info(rom)
        if not info['is_english']:
            delete_candidates.append((rom, "Non-English/Foreign Release"))
        else:
            group_key = f"{info['base_name']} ({info['track']})"
            
            if group_key not in games_by_group:
                games_by_group[group_key] = []
            games_by_group[group_key].append(info)

    for group_key, versions in games_by_group.items():
        if len(versions) > 1:
            # SORTS BY REGION FIRST, THEN VERSION. 
            # This ensures (USA) always defeats (Europe) or (Japan)(En) regardless of the version number.
            versions.sort(key=lambda x: (x['region_score'], x['version_score'], -len(x['filename'])), reverse=True)
            keeper = versions[0]
            for duplicate in versions[1:]:
                reason = f"Superseded by '{keeper['filename']}' ({keeper['track']} track)"
                delete_candidates.append((duplicate['filename'], reason))

    if not delete_candidates:
        print(f"\n{Colors.GREEN}Directory is completely clean! No files need to be deleted.{Colors.RESET}")
        return

    print(f"\n{Colors.CYAN}--- DELETE CANDIDATES ROLLUP ---{Colors.RESET}")
    for filename, reason in delete_candidates:
        print(f"{Colors.YELLOW}[DELETE]{Colors.RESET} {filename}")
        print(f"         {Colors.RED}Reason:{Colors.RESET} {reason}")
        
    print(f"{Colors.CYAN}--------------------------------{Colors.RESET}")
    print(f"Total files to delete: {Colors.RED}{len(delete_candidates)}{Colors.RESET} out of {len(all_files)}")

    confirm = input(f"\nDo you want to permanently delete these files? (y/n): ").strip().lower()
    
    if confirm == 'y':
        for filename, _ in delete_candidates:
            file_path = os.path.join(DIRECTORY, filename)
            try:
                os.remove(file_path)
                print(f"{Colors.GREEN}Deleted:{Colors.RESET} {filename}")
            except Exception as e:
                print(f"{Colors.RED}Error deleting {filename}:{Colors.RESET} {e}")
        print(f"\n{Colors.GREEN}Cleanup complete! Enjoy your curated list.{Colors.RESET}")
    else:
        print(f"\n{Colors.YELLOW}Operation cancelled. No files were deleted.{Colors.RESET}")

if __name__ == "__main__":
    main()