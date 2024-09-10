#!/usr/bin/env python

def update_movie_metadata():
    # import libraries
    import glob, math, os
    from utilities import read_json, write_to_csv
    # define movie metadata directories
    directory1 = 'C:/EmbyServerCache/tmdb-movies2'
    directory2 = 'C:/EmbyServerCache/tvdb-movies'
    # set source path
    src_directory = os.path.dirname(os.path.abspath(__file__))
    # capture all metadata files 
    dirs = sorted([x[0].replace('\\','/') for x in os.walk(directory1) if x[0] != directory1],key = lambda x: int(x.split('/')[-1]))
    dirs += sorted([x[0].replace('\\','/') for x in os.walk(directory2) if x[0] != directory2],key = lambda x: int(x.split('/')[-1]))
    all_files = []
    for d in dirs:
        all_files += sorted([gg.replace('\\','/') for gg in glob.glob(f'{d}/*.json')])
    en_files = []
    for af in all_files:
        if 'all-en' in af:
            en_files.append(af)
    # data array attributes
    title_years = []
    data_array = []; header = ['Title','Year','Release Date','Rating','Num Raters','Popularity','Runtime (hrs)','Budget ($)','Revenue ($)','Profit ($)','Genres','Actors','Keywords','Production Companies','Countries']
    # read metadata files
    for en in en_files:
        data = read_json(en)
        title = data['title']
        release_date = data['release_date'] # YYYY-MM-DD
        year = data['release_date'][:4]
        title_with_year = f'{title} ({year})'
        # bypass duplicates
        if title_with_year in title_years: continue
        title_years.append(title_with_year)
        runtime_minutes = data['runtime']
        runtime_hours = f'{runtime_minutes/60:.2f}'
        rating = data['vote_average']
        num_raters = data['vote_count']
        popularity = data['popularity']
        budget = data['budget']
        revenue = data['revenue']
        if budget > 0 and revenue > 0: profit = revenue - budget
        else: profit = math.nan
        genres = [g['name'] for g in data['genres']]
        actors = [c['name'] for c in data['casts']['cast']]
        keywords = [k['name'].title() for k in data['keywords']['keywords']]
        production_companies = [pc['name'] for pc in data['production_companies']]
        countries = [pc['name'] for pc in data['production_countries']]
        data_array.append([title,year,release_date,rating,num_raters,popularity,runtime_hours,budget,revenue,profit,genres,actors,keywords,production_companies,countries])
    output_filepath = ("\\".join(src_directory.split('\\')[:-1])+"/output/").replace('\\','/')+'movies.csv'
    write_to_csv(output_filepath,data_array,header)

def update_show_metadata():
    pass

if __name__ == '__main__':
    update_movie_metadata()