import os
import re

class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    RESET = '\033[0m'


def parse_game_list(filepath: str) -> dict:
    """
    Parses your generated text files to extract game titles.
    Returns a dictionary mapping a 'cleaned' title to the original raw filename.
    """
    if not os.path.exists(filepath):
        print(f"{Colors.YELLOW}Error: File not found -> {filepath}{Colors.RESET}")
        return {}

    games = {}
    is_game_list_section = False
    
    with open(filepath, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            
            # Detect the start of the actual list section
            if "GAME LIST" in line:
                is_game_list_section = True
                continue
            
            # Parse the games under the header
            if is_game_list_section and line.startswith("-"):
                # Grab the raw title string, removing the " - " bullet point
                raw_title = line[1:].strip()
                
                # Normalize: remove anything in parentheses or brackets to ensure 
                # games match even if their region tags or revision numbers differ.
                # Example: "Spider-Man 2 (USA)" -> "spider-man 2"
                clean_title = re.sub(r'\(.*?\)|\[.*?\]', '', raw_title).strip().lower()
                
                if clean_title:
                    games[clean_title] = raw_title
                    
    return games


def find_duplicates(file1: str, file2: str):
    print(f"\n{Colors.CYAN}Analyzing files for duplicates...{Colors.RESET}")
    print(f"File 1: {file1}")
    print(f"File 2: {file2}\n")
    
    games1 = parse_game_list(file1)
    games2 = parse_game_list(file2)
    
    if not games1 or not games2:
        print("Cannot compare. One or both lists are empty or missing.")
        return

    # Find the intersection using the cleaned, normalized keys
    common_keys = set(games1.keys()).intersection(set(games2.keys()))
    
    # Extract console names from the filenames for a cleaner output display
    console1_name = os.path.basename(file1).replace("Game List - ", "").replace(".txt", "")
    console2_name = os.path.basename(file2).replace("Game List - ", "").replace(".txt", "")

    if not common_keys:
        print(f"{Colors.GREEN}No duplicate games found between {console1_name} and {console2_name}.{Colors.RESET}")
    else:
        print(f"{Colors.YELLOW}Found {len(common_keys)} duplicates across {console1_name} and {console2_name}:{Colors.RESET}")
        print("-" * 60)
        for key in sorted(common_keys):
            # Print the original formatting from File 1
            print(f" - {games1[key]}")
        print("-" * 60)
        print(f"\n{Colors.GREEN}Comparison Complete.{Colors.RESET}")

if __name__ == "__main__":
    # Initialize basic terminal colors for Windows
    os.system("")
    PS2_OUTPUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "output", "games", "Game List - Sony Playstation 2.txt")
    GAMECUBE_OUTPUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "output", "games", "Game List - Nintendo Gamecube.txt")

    find_duplicates(PS2_OUTPUT_PATH, GAMECUBE_OUTPUT_PATH)