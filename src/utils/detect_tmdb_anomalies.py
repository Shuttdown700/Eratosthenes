import csv
import re
import difflib
from pathlib import Path
from colorama import init, Fore, Style

# Initialize colorama to auto-reset colors after each print statement
init(autoreset=True)

def normalize_title(title):
    """Cleans the title for a more accurate comparison."""
    title = re.sub(r'\s*\(\d{4}\)', '', title)
    title = re.sub(r'[^\w\s]', '', title)
    return title.strip().lower()

def calculate_difference(title_a, title_b):
    """Returns a difference score from 0.0 (identical) to 1.0 (completely different)."""
    norm_a = normalize_title(title_a)
    norm_b = normalize_title(title_b)
    
    similarity = difflib.SequenceMatcher(None, norm_a, norm_b).ratio()
    return round(1.0 - similarity, 4)

def load_whitelist(filepath):
    """Loads attested titles into a set for fast lookup."""
    whitelist = set()
    if filepath.exists():
        with filepath.open(mode='r', encoding='utf-8') as f:
            whitelist = {line.strip() for line in f if line.strip()}
        print(f"{Fore.GREEN}Loaded {len(whitelist)} known correct titles from whitelist.")
    else:
        print(f"{Fore.YELLOW}No whitelist found. Proceeding without manual attestations.")
    return whitelist

def main():
    script_dir = Path(__file__).parent.resolve()
    
    input_file = (script_dir / "../../output/movies/tmdb.csv").resolve()
    output_file = input_file.parent / "tmdb_differences.csv"
    whitelist_file = input_file.parent / "tmdb_known_name_whitelist.txt"

    results = []

    print(f"{Style.BRIGHT}Reading from: {Fore.CYAN}{input_file}")
    
    if not input_file.exists():
        print(f"{Fore.RED}{Style.BRIGHT}Error: Could not find the file at {input_file}")
        return

    attested_titles = load_whitelist(whitelist_file)

    with input_file.open(mode='r', encoding='utf-8-sig') as infile:
        reader = csv.DictReader(infile)
        
        required_cols = {'Title_Alexandria', 'Title_TMDb', 'Release_Year'}
        if not required_cols.issubset(reader.fieldnames):
            missing = required_cols - set(reader.fieldnames)
            print(f"{Fore.RED}{Style.BRIGHT}Error: The input file is missing required columns: {missing}")
            return

        for row in reader:
            t_alex = row.get('Title_Alexandria', '').strip()
            t_tmdb = row.get('Title_TMDb', '').strip()
            r_year = row.get('Release_Year', '').strip()

            if t_alex in attested_titles:
                diff_score = 0.0
            else:
                diff_score = calculate_difference(t_alex, t_tmdb)

            results.append({
                'Difference_Score': diff_score,
                'Title_Alexandria': t_alex,
                'Title_TMDb': t_tmdb,
                'Release_Year': r_year
            })

    # Sort descending by Difference_Score
    results.sort(key=lambda x: x['Difference_Score'], reverse=True)

    print(f"{Style.BRIGHT}Writing sorted results to: {Fore.CYAN}{output_file}")
    
    with output_file.open(mode='w', encoding='utf-8', newline='') as outfile:
        output_fields = ['Difference_Score', 'Title_Alexandria', 'Title_TMDb', 'Release_Year']
        writer = csv.DictWriter(outfile, fieldnames=output_fields)
        
        writer.writeheader()
        writer.writerows(results)

    # --- Print Statistics & Top 15 ---
    total_movies = len(results)
    if total_movies > 0:
        avg_diff = sum(r['Difference_Score'] for r in results) / total_movies
        perfect_matches = sum(1 for r in results if r['Difference_Score'] == 0.0)
        significant_diffs = sum(1 for r in results if r['Difference_Score'] >= 0.5)

        print(f"\n{Fore.CYAN}{Style.BRIGHT}=========================================")
        print(f"{Fore.CYAN}{Style.BRIGHT}          PROCESSING STATISTICS          ")
        print(f"{Fore.CYAN}{Style.BRIGHT}=========================================")
        print(f"{Style.BRIGHT}Total Movies Analyzed: {Fore.YELLOW}{total_movies:,}")
        print(f"{Style.BRIGHT}Average Difference:    {Fore.YELLOW}{avg_diff:.4f}")
        print(f"{Style.BRIGHT}Perfect Matches:       {Fore.GREEN}{perfect_matches}")
        print(f"{Style.BRIGHT}Major Differences:     {Fore.RED}{significant_diffs}")
        
        print(f"\n{Fore.MAGENTA}{Style.BRIGHT}=========================================")
        print(f"{Fore.MAGENTA}{Style.BRIGHT}       TOP 15 MOST DIFFERENT TITLES      ")
        print(f"{Fore.MAGENTA}{Style.BRIGHT}=========================================")
        
        for i, r in enumerate(results[:15], 1):
            score = r['Difference_Score']
            
            # Color-code the score based on severity
            if score >= 0.5:
                score_color = Fore.RED
            elif score > 0.0:
                score_color = Fore.YELLOW
            else:
                score_color = Fore.GREEN
                
            print(f"{Fore.WHITE}{i:2}. {score_color}[{score:.4f}] {Fore.CYAN}{r['Title_Alexandria']} {Fore.WHITE}vs {Fore.CYAN}{r['Title_TMDb']}")
            
        print(f"\n{Fore.GREEN}{Style.BRIGHT}Done! Results saved successfully.\n")

if __name__ == "__main__":
    main()