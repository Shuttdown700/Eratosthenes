import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import ast
import os
import numpy as np
from adjustText import adjust_text

def run_movie_analytics(directory):
    csv_path = os.path.join(directory, "tmdb.csv")
    output_subdir = os.path.join(directory, "shuttflix_insights")
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

    # --- 01. VOLUME: 5-Year Intervals ---
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
    save_plot('01_volume_5yr.png')

    # --- 02. RUNTIME: Dist with 4 High/4 Low Anomalies ---
    plt.figure(figsize=(12, 7))
    df_runtime = df[df['Runtime_Min'] > 0].dropna(subset=['Runtime_Min'])
    plt.hist(df_runtime['Runtime_Min'], bins=45, color='#8e44ad', alpha=0.6, edgecolor='white')
    sorted_run = df_runtime.sort_values('Runtime_Min')
    extremes = pd.concat([sorted_run.tail(4)])
    texts = [plt.text(r['Runtime_Min'], 5, r['Display_Title'], fontsize=8, fontweight='bold') for _, r in extremes.iterrows()]
    adjust_text(texts, arrowprops=dict(arrowstyle='->', color='black', lw=0.5))
    plt.title('Runtime Distribution & Extremes [Shuttflix]', fontsize=14, fontweight='bold')
    plt.xlabel('Minutes')
    save_plot('02_runtime.png')

    # --- 03. BUDGET: Inflation Trend ---
    plt.figure(figsize=(10, 6))
    df_finance.groupby('Five_Year')['Adj_Budget'].median().plot(kind='line', marker='o', color='#c0392b', linewidth=2)
    plt.gca().yaxis.set_major_formatter(ticker.FuncFormatter(currency_fmt))
    plt.title('Median Inflation-Adjusted Budget (2026$) [Shuttflix]', fontsize=14, fontweight='bold')
    save_plot('03_budget_trend.png')

    # --- 04. STUDIO PROFILE: Volume vs. Investment [Shuttflix] ---
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
    
    save_plot('04_studio_profile.png')

    # --- 05. GENRE EVOLUTION: Top 5 Genres per Decade [Shuttflix] ---
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
    
    save_plot('05_genre_evolution.png')

    # --- 06. GENRES: Commonality with % ---
    plt.figure(figsize=(10, 7))
    exp_gen = df.explode('Genres_List')
    exp_gen = exp_gen[exp_gen['Genres_List'].notna() & (exp_gen['Genres_List'] != '')]
    g_counts = exp_gen['Genres_List'].value_counts().head(15).sort_values()
    g_total = g_counts.sum()
    ax = g_counts.plot(kind='barh', color='#e67e22')
    for i, v in enumerate(g_counts):
        ax.text(v + 1, i, f'{(v/g_total)*100:.1f}%', va='center', fontsize=9)
    plt.title('Most Frequent Genres (% of Top 15) [Shuttflix]', fontsize=14, fontweight='bold')
    save_plot('06_genres.png')

    # --- 07. ANOMALIES: Inflation-Adjusted Cost vs Revenue ---
    plt.figure(figsize=(12, 8))
    plt.scatter(df_finance['Adj_Budget'], df_finance['Adj_Revenue'], alpha=0.2, color='#7f8c8d')
    # Identify 4 most expensive and 4 highest revenue (all adjusted)
    peaks = pd.concat([df_finance.sort_values('Adj_Budget').tail(4), 
                       df_finance.sort_values('Adj_Revenue').tail(4)]).drop_duplicates()
    texts_peaks = [plt.text(r['Adj_Budget'], r['Adj_Revenue'], r['Display_Title'], fontsize=8, fontweight='bold') for _, r in peaks.iterrows()]
    adjust_text(texts_peaks, arrowprops=dict(arrowstyle='->', color='red', lw=1))
    
    plt.gca().xaxis.set_major_formatter(ticker.FuncFormatter(currency_fmt))
    plt.gca().yaxis.set_major_formatter(ticker.FuncFormatter(currency_fmt))
    plt.xlabel('Production Budget (Adjusted 2026$)', fontsize=11)
    plt.ylabel('Box Office Revenue (Adjusted 2026$)', fontsize=11)
    plt.title('Adjusted Financial Scale & Outliers [Shuttflix]', fontsize=14, fontweight='bold')
    save_plot('07_adj_financial_peaks.png')

    # --- 08. PRODUCTION: Studio Share ---
    plt.figure(figsize=(10, 7))
    exp_prod = df.explode('Prod_List')
    exp_prod[exp_prod['Prod_List'].notna() & (exp_prod['Prod_List'] != '')].Prod_List.value_counts().head(8).plot(kind='pie', autopct='%1.1f%%', cmap='Set3')
    plt.title('Primary Production Studio Share [Shuttflix]', fontsize=14, fontweight='bold')
    plt.ylabel('')
    save_plot('08_studio_share.png')

    # --- 09. SEASONALITY: Monthly Bar with % ---
    plt.figure(figsize=(11, 6))
    month_counts = df['Release_Date'].dt.month.value_counts().sort_index()
    m_total = month_counts.sum()
    ax = month_counts.plot(kind='bar', color='#16a085', edgecolor='white', width=0.8)
    for p in ax.patches:
        ax.annotate(f'{(p.get_height()/m_total)*100:.1f}%', (p.get_x() + p.get_width()/2., p.get_height()), 
                    ha='center', va='center', xytext=(0, 9), textcoords='offset points', fontsize=8)
    plt.xticks(range(0, 12), ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'], rotation=0)
    plt.title('Release Seasonality [Shuttflix]', fontsize=14, fontweight='bold')
    save_plot('09_seasonality_bar.png')

    # --- 10. TREND: Runtime Evolution ---
    plt.figure(figsize=(11, 6))
    plt.scatter(df_runtime['Release_Year'], df_runtime['Runtime_Min'], alpha=0.15, color='#2c3e50', s=15)
    z = np.polyfit(df_runtime['Release_Year'], df_runtime['Runtime_Min'], 1)
    p = np.poly1d(z)
    plt.plot(df_runtime['Release_Year'], p(df_runtime['Release_Year']), color='#e74c3c', linestyle='--', linewidth=2)
    plt.title('Historical Evolution of Movie Runtimes [Shuttflix]', fontsize=14, fontweight='bold')
    plt.xlabel('Release Year'), plt.ylabel('Minutes')
    save_plot('10_runtime_trend.png')

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