import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import ast
import os
import numpy as np
from adjustText import adjust_text

def run_movie_analytics(directory):
    csv_path = os.path.join(directory, "tmdb.csv")
    output_subdir = os.path.join(directory, "graphics")
    if not os.path.exists(output_subdir):
        os.makedirs(output_subdir)
    
    if not os.path.exists(csv_path):
        print(f"Error: Could not find 'tmdb.csv' in {directory}")
        return

    # 1. Load Data & Global Style
    df = pd.read_csv(csv_path)
    plt.style.use('ggplot')

    # 2. Cleaning & Required Columns
    df['Release_Date'] = pd.to_datetime(df['Release_Date'], errors='coerce')
    df = df.dropna(subset=['Release_Year', 'Title_TMDb'])
    
    df['Decade'] = (df['Release_Year'] // 10) * 10
    df['Five_Year'] = (df['Release_Year'] // 5) * 5
    df['Display_Title'] = df.apply(lambda x: f"{x['Title_TMDb']} ({int(x['Release_Year'])})", axis=1)

    # 3. Inflation Adjustment Logic (Relative to 2026)
    def get_inflation_factor(year):
        if year >= 2024: return 1.05
        if year >= 2015: return 1.35
        if year >= 2005: return 1.75
        if year >= 1990: return 2.80
        if year >= 1975: return 5.50
        return 10.0 # Historical multiplier for mid-century and older

    # Apply inflation to both Budget and Revenue
    df['Adj_Budget'] = df.apply(lambda x: x['Budget'] * get_inflation_factor(x['Release_Year']), axis=1)
    df['Adj_Revenue'] = df.apply(lambda x: x['Revenue'] * get_inflation_factor(x['Release_Year']), axis=1)
    
    # Financial filter: Must have both Budget and Revenue > 0
    df_finance = df[(df['Budget'] > 0) & (df['Revenue'] > 0)].copy()
    # ROI based on adjusted values (mathematically the same as unadjusted, but consistent)
    df_finance['ROI'] = (df_finance['Adj_Revenue'] - df_finance['Adj_Budget']) / df_finance['Adj_Budget']

    # Parsing lists
    def parse_list(val):
        try: return ast.literal_eval(val) if isinstance(val, str) else []
        except: return []
    df['Genres_List'] = df['Genres'].apply(parse_list)
    df['Prod_List'] = df['Production_Companies'].apply(parse_list)

    # Helpers
    def currency_fmt(x, pos):
        if x >= 1e9: return f'${x*1e-9:.1f}B'
        if x >= 1e6: return f'${x*1e-6:.0f}M'
        return f'${x:,.0f}'

    def save_plot(filename):
        plt.savefig(os.path.join(output_subdir, filename), dpi=300, bbox_inches='tight')
        plt.close()

    # --- VOLUME: 5-Year Intervals ---
    plt.figure(figsize=(12, 6))
    counts = df['Five_Year'].value_counts().sort_index()
    total = counts.sum()
    ax = counts.plot(kind='bar', color='#2c3e50', width=0.85)
    for p in ax.patches:
        ax.annotate(f'{(p.get_height()/total)*100:.1f}%', (p.get_x() + p.get_width()/2., p.get_height()), 
                    ha='center', va='center', xytext=(0, 9), textcoords='offset points', fontsize=8)
    plt.title('Library Growth: 5-Year Release Intervals [Shuttflix]', fontsize=14, fontweight='bold')
    plt.ylabel('Movie Count')
    plt.xlabel('Release Year Interval')
    save_plot('movie_release_years.png')

    # --- RUNTIMES ---
    plt.figure(figsize=(12, 7))
    df_runtime = df[df['Runtime_Min'] > 0].dropna(subset=['Runtime_Min'])
    plt.hist(df_runtime['Runtime_Min'] / 60, bins=45, color='#8e44ad', alpha=0.6, edgecolor='white')
    plt.title('Runtime Distribution & Extremes [Shuttflix]', fontsize=14, fontweight='bold')
    plt.xlabel('Hours')
    plt.ylabel('Movie Count')
    save_plot('movie_runtimes.png')

    # --- BUDGET: Adjusted Trend ---
    plt.figure(figsize=(10, 6))
    df_finance.groupby('Five_Year')['Adj_Budget'].median().plot(kind='line', marker='o', color='#c0392b', linewidth=2)
    plt.gca().yaxis.set_major_formatter(ticker.FuncFormatter(currency_fmt))
    plt.title('Median Inflation-Adjusted Budget (2026$) [Shuttflix]', fontsize=14, fontweight='bold')
    plt.xlabel('Release Year Interval')
    plt.ylabel('Median Adjusted Budget')
    save_plot('movie_adjusted_budget_trend.png')

    # --- POPULAR STUDIOS: Production ---
    plt.figure(figsize=(12, 7))
    
    # Explode and filter production companies
    exp_prod = df.explode('Prod_List')
    exp_prod = exp_prod[exp_prod['Prod_List'].notna() & (exp_prod['Prod_List'] != '')]
    
    # Get Top 10 studios by count
    top_studios = exp_prod['Prod_List'].value_counts().head(10).index
    studio_stats = exp_prod[exp_prod['Prod_List'].isin(top_studios)]
    
    # Calculate Median Adjusted Budget for these studios
    studio_investment = studio_stats.groupby('Prod_List')['Adj_Budget'].median().sort_values()
    
    # Create the horizontal bar chart
    ax = studio_investment.plot(kind='barh', color='#3498db', edgecolor='white')
    
    # Add labels for movie counts (Library Share) next to the bars
    studio_counts = exp_prod['Prod_List'].value_counts()
    for i, v in enumerate(studio_investment):
        count = studio_counts[studio_investment.index[i]]
        ax.text(v + 5000000, i, f'({count} Titles)', va='center', fontsize=9, fontweight='bold', color='#2c3e50')

    plt.title('Top 10 Studios: Median Investment Scale [Shuttflix]', fontsize=14, fontweight='bold')
    plt.xlabel('Median Inflation-Adjusted Budget (2026$)')
    plt.ylabel('Production Studio')
    plt.gca().xaxis.set_major_formatter(ticker.FuncFormatter(currency_fmt))
    
    save_plot('movie_popular_studios.png')

    # --- GENRE EVOLUTION: Top Genres ---
    plt.figure(figsize=(12, 7))
    
    # Explode genres and group by decade
    exp_gen_dec = df.explode('Genres_List')
    exp_gen_dec = exp_gen_dec[exp_gen_dec['Genres_List'].notna() & (exp_gen_dec['Genres_List'] != '')]
    
    # Pivot table to count occurrences
    genre_pivot = exp_gen_dec.groupby(['Decade', 'Genres_List']).size().unstack(fill_value=0)
    
    # Filter for decades that have a significant sample size
    recent_decades = genre_pivot.index[genre_pivot.sum(axis=1) > 10]
    genre_trend = genre_pivot.loc[recent_decades]
    
    # Normalize to percentages
    genre_trend_pct = genre_trend.div(genre_trend.sum(axis=1), axis=0) * 100
    
    # NEW: Filter to start the visualization at the 1940s
    genre_trend_pct = genre_trend_pct[genre_trend_pct.index >= 1940]
    
    # Pick the top 5 overall genres to keep the line chart clean
    top_overall = exp_gen_dec['Genres_List'].value_counts().head(7).index
    
    # Plotting
    genre_trend_pct[top_overall].plot(kind='line', marker='o', linewidth=3, ax=plt.gca())

    plt.title('Genre Dominance Shift Over Decades (Post-1940) [Shuttflix]', fontsize=14, fontweight='bold')
    plt.ylabel('% Share of Library per Decade')
    plt.xlabel('Decade')
    plt.legend(title="Top Genres", bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.grid(True, linestyle='--', alpha=0.7)
    
    save_plot('movie_genre_evolution.png')

    # --- GENRES: Commonality with % ---
    plt.figure(figsize=(10, 7))
    exp_gen = df.explode('Genres_List')
    exp_gen = exp_gen[exp_gen['Genres_List'].notna() & (exp_gen['Genres_List'] != '')]
    g_counts = exp_gen['Genres_List'].value_counts().head(15).sort_values()
    g_total = g_counts.sum()
    ax = g_counts.plot(kind='barh', color='#e67e22')
    for i, v in enumerate(g_counts):
        ax.text(v + 1, i, f'{(v/g_total)*100:.1f}%', va='center', fontsize=9)
    plt.title('Most Frequent Genres (% of Top 15) [Shuttflix]', fontsize=14, fontweight='bold')
    plt.xlabel('Movie Count')
    plt.ylabel('Genre')
    save_plot('movie_genre_distribution.png')

    # --- RELEASE SEASONALITY ---
    plt.figure(figsize=(11, 6))
    month_counts = df['Release_Date'].dt.month.value_counts().sort_index()
    m_total = month_counts.sum()
    ax = month_counts.plot(kind='bar', color='#16a085', edgecolor='white', width=0.8)
    for p in ax.patches:
        ax.annotate(f'{(p.get_height()/m_total)*100:.1f}%', (p.get_x() + p.get_width()/2., p.get_height()), 
                    ha='center', va='center', xytext=(0, 9), textcoords='offset points', fontsize=8)
    plt.xticks(range(0, 12), ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'], rotation=0)
    plt.title('Release Seasonality [Shuttflix]', fontsize=14, fontweight='bold')
    plt.xlabel('Release Month')
    plt.ylabel('Movie Count')
    save_plot('movie_release_seasonality.png')

    # --- RATINGS: Annual Distribution (Candle/Box Chart) ---
    plt.figure(figsize=(16, 7))
    
    # Filter for years from 1920 onwards
    min_year = 1920
    df_annual = df[df['Release_Year'] >= min_year].dropna(subset=['Rating', 'Release_Year'])
    
    # Prepare data: Grouping ratings by every unique year
    years = sorted(df_annual['Release_Year'].unique())
    data_to_plot = [df_annual[df_annual['Release_Year'] == y]['Rating'] for y in years]
    
    # Create the annual 'candle' chart
    # showfliers=False removes extreme outliers (dots) to keep the "candles" clean
    bp = plt.boxplot(data_to_plot, patch_artist=True, labels=[int(y) for y in years], showfliers=False)
    
    # Styling
    for box in bp['boxes']:
        box.set(facecolor='#3498db', alpha=0.6, linewidth=1)
    for median in bp['medians']:
        median.set(color='#e74c3c', linewidth=1.5)
        
    # Clean up X-Axis: Only show every 5th year label to prevent overlap
    ax = plt.gca()
    for i, label in enumerate(ax.get_xticklabels()):
        if i % 5 != 0:
            label.set_visible(False)

    plt.title(f'Annual Rating Distribution Extremes (Post-{min_year}) [Shuttflix]', fontsize=14, fontweight='bold')
    plt.ylabel('TMDb User Rating')
    plt.xlabel('Release Year')
    plt.grid(axis='y', linestyle='--', alpha=0.4)
    
    save_plot('movie_rating_candle_distributions.png')

    # Summary Statistics Output
    print("-" * 30)
    print(f"SHUTTFLIX ANALYTICS COMPLETE")
    print(f"Total Movies Analyzed: {len(df):,}")
    print(f"Total Runtime: {df['Runtime_Min'].sum() / 60 / 24:,.0f} days")
    print(f"Graphics Saved to: {output_subdir}")
    print("-" * 30)

if __name__ == "__main__":
    TARGET_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "output", "movies")
    run_movie_analytics(TARGET_DIR)