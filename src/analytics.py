#!/usr/bin/env python

def update_movie_metadata():
    def get_json_files(directory):
        import os
        json_files = []
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.json'):
                    json_files.append(os.path.join(root, file))
        return json_files
    # import libraries
    import glob, math, os
    from utilities import read_json, write_to_csv
    # define movie metadata directories
    tmdb_base_dir = 'C:\\EmbyServerCache\\tmdb-movies2'
    omdb_base_dir = 'C:\\EmbyServerCache\\omdb'
    # set source path
    src_directory = os.path.dirname(os.path.abspath(__file__))
    # capture all metadata files 
    tmdb_dirs = sorted([x[0].replace('\\','/') for x in os.walk(tmdb_base_dir) if x[0] != tmdb_base_dir],key = lambda x: int(x.split('/')[-1]))
    omdb_files = get_json_files(omdb_base_dir)
    omdb_files = [x for x in omdb_files if 'season' not in x]
    tmdb_files = get_json_files(tmdb_base_dir)
    tmdb_files = [x for x in tmdb_files if 'all-en' in x]
    # data array attributes
    title_years = []
    data_array = []; header = ['Title','Year','Release Date','Rating','Runtime (hrs)']
    # read omdb files
    for file in omdb_files:
        data = read_json(file)
        if "Season" in data.keys() or "totalSeasons" in data.keys() or "Episode" in data.keys(): continue
        title = data['Title']
        release_date = data['Released'] # DD MMM YYYY
        year = data['Year']
        title_with_year = f'{title} ({year})'
        if title_with_year in title_years: continue
        title_years.append(title_with_year)
        runtime_minutes = int(data['Runtime'].split()[0])
        runtime_hours = f'{runtime_minutes/60:.2f}'
        rating = data['imdbRating']
        data_array.append([title,year,release_date,rating,runtime_hours])  
    # read tmdb files
    for file in tmdb_files:
        data = read_json(file)
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
        # budget = data['budget']
        # revenue = data['revenue']
        # if budget > 0 and revenue > 0: profit = revenue - budget
        # else: profit = math.nan
        # genres = [g['name'] for g in data['genres']]
        # actors = [c['name'] for c in data['casts']['cast']]
        # keywords = [k['name'].title() for k in data['keywords']['keywords']]
        # production_companies = [pc['name'] for pc in data['production_companies']]
        # countries = [pc['name'] for pc in data['production_countries']]
        data_array.append([title,year,release_date,rating,runtime_hours])
    output_filepath = ("\\".join(src_directory.split('\\')[:-1])+"/output/").replace('\\','/')+'movies.csv'
    write_to_csv(output_filepath,data_array,header)

def update_show_metadata():
    pass

if __name__ == '__main__':
    update_movie_metadata()