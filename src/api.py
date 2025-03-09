#!/usr/bin/env python

class API(object):
    def __init__(self):
        from utilities import read_json
        self.src_directory = os.path.dirname(os.path.abspath(__file__))
        self.filepath_movie_list = ("\\".join(self.src_directory.split('\\')[:-1])+"/output/").replace('\\','/')+'movie_list.txt'
        self.filepath_tmdb_csv = ("\\".join(self.src_directory.split('\\')[:-1])+"/output/").replace('\\','/')+'tmdb.csv'
        self.filepath_tmdb_top_rated_csv = ("\\".join(self.src_directory.split('\\')[:-1])+"/output/").replace('\\','/')+'tmdb_top_rated.csv'
        self.filepath_movie_list_tmdb_not_found = ("\\".join(self.src_directory.split('\\')[:-1])+"/output/").replace('\\','/')+'movie_list_tdmb_not_found.txt'
        self.filepath_api_config = (self.src_directory+"/config/api.config").replace('\\','/')
        self.api_config = read_json(self.filepath_api_config)
        self.tmdb_api_url_base_search = self.api_config['tmdb']['api_url_base_search']
        self.tmdb_api_url_base_query = self.api_config['tmdb']['api_url_base_query']
        self.tmdb_api_url_base_discover = self.api_config['tmdb']['api_url_base_discover']
        self.tmdb_api_key = self.api_config['tmdb']['api_key']
        self.emby_api_key = self.api_config['emby']['api_key']
        self.emby_url = self.api_config['emby']['api_url']
        self.headers_tmdb = {
            "accept": "application/json",
            "Authorization": f"Bearer {self.tmdb_api_key}"
            }
        self.tvdb_api_key = self.api_config['tvdb']['api_key']
        
    def tmdb_movies_fetch(self):
        import requests
        from colorama import Fore, Back, Style
        from utilities import read_csv, read_file_as_list, write_list_to_txt_file, write_to_csv
        # read current movie list
        movie_list = read_file_as_list(self.filepath_movie_list)
        # read current movies in local tmdb database
        tmbd_current_movies = [x['Title_Alexandria'] for x in read_csv(self.filepath_tmdb_csv)]
        # generate list of movies to query
        movie_list_adjusted = [movie for movie in movie_list if movie not in tmbd_current_movies]
        # define csv header and existing data
        csv_headers = ['Title_Alexandria','Title_TMDb','Release_Date','Release_Year','Runtime_Min','Runtime_Hrs','Rating','Budget','Revenue','Genres','Production_Companies','Overview','TMDb_ID','IMDb_ID']
        csv_rows = [list(x.values()) for x in read_csv(self.filepath_tmdb_csv)]
        movie_list_bypass_list = ['Louis C.K. at the Dolby (2023)']
        movie_list_not_found = []
        for movie_with_year in movie_list_adjusted:
            if movie_with_year in movie_list_bypass_list: continue
            print(f'{Fore.GREEN}{Style.BRIGHT}Downloading data{Style.RESET_ALL} for {Fore.BLUE}{Style.BRIGHT}{movie_with_year}{Style.RESET_ALL}')
            movie = '('.join(movie_with_year.split('(')[:-1])
            year = movie_with_year.split('(')[-1].split(')')[0]
            params_tmdb_movie_query = {
                'query': movie,
                'include_adult': 'false',
                'language': 'en-US',
                'page': '1',
                'primary_release_year': year
            }
            response_search = requests.get(self.tmdb_api_url_base_search, params=params_tmdb_movie_query, headers=self.headers_tmdb)
            if response_search.status_code == 200:
                data_search = response_search.json()
                try:
                    id_tmdb = data_search['results'][0]['id']
                except IndexError:
                    print(f'{Fore.RED}{Style.BRIGHT}Error{Style.RESET_ALL} with {Fore.BLUE}{Style.BRIGHT}{movie_with_year}{Style.RESET_ALL}')
                    movie_list_not_found.append(movie_with_year)
                    continue
                url_query = f"{self.tmdb_api_url_base_query}{id_tmdb}?language=en-US"
                response_query = requests.get(url_query, headers=self.headers_tmdb)
                if response_query.status_code == 200:
                    data_query = response_query.json()
                    movie_data_title_alexandria = movie_with_year
                    movie_data_title_tmdb = data_query['title']
                    movie_data_release_date = data_query['release_date'] # YYYY-MM-DD
                    movie_data_release_year = movie_data_release_date.split('-')[0]
                    movie_data_runtime_min = data_query['runtime']
                    movie_data_runtime_hrs = f'{movie_data_runtime_min/60:.2f}'
                    movie_data_rating = data_query['vote_average']
                    movie_data_tmdb_id = id_tmdb
                    movie_data_imdb_id = data_query['imdb_id']
                    movie_data_budget = data_query['budget']
                    movie_data_revenue = data_query['revenue']
                    movie_data_genres = [x['name'] for x in data_query['genres']]
                    movie_data_production_companies = [x['name'] for x in data_query['production_companies']]
                    movie_data_overview = data_query['overview']
                    csv_row = [movie_data_title_alexandria,movie_data_title_tmdb,movie_data_release_date,movie_data_release_year,
                            movie_data_runtime_min,movie_data_runtime_hrs,movie_data_rating,
                            movie_data_budget,movie_data_revenue,movie_data_genres,movie_data_production_companies,
                            movie_data_overview,movie_data_tmdb_id,movie_data_imdb_id]
                    csv_rows.append(csv_row)
        csv_rows = sorted(csv_rows, key= lambda x: x[0], reverse=False)
        if csv_rows != [list(x.values()) for x in read_csv(self.filepath_tmdb_csv)]: write_to_csv(self.filepath_tmdb_csv,csv_rows,csv_headers)
        # write_list_to_txt_file(self.filepath_movie_list_tmdb_not_found, movie_list_not_found, bool_append=False)

    def tmdb_movies_pull_popular(self):
        csv_headers = ['Title_TMDb','Release_Date','Release_Year','Rating','Overview','TMDb_ID']
        csv_rows = []
        pages_min = 1; pages_max = 628
        for num_page in range(pages_min,pages_max+1):
            print(f'Searching for movies in {Fore.RED}{Style.BRIGHT}Page {num_page}{Style.RESET_ALL}')
            params_tmdb_movie_discover = {
                'include_adult': 'false',
                'include_video': 'false',
                'language': 'en-US',
                'page': num_page,
                'sort_by': 'vote_average.desc',
                'without_genres': '99,10755',
                'vote_count.gte': '200'
            }
            response_search = requests.get(self.tmdb_api_url_base_discover, params=params_tmdb_movie_discover, headers=self.headers_tmdb)
            if response_search.status_code == 200:
                results = response_search.json()['results']
                for result in results:
                    if result['original_language'] == 'en':
                        print(f'Storing {Fore.BLUE}{Style.BRIGHT}{result['title']}{Style.RESET_ALL}')
                        movie_data_title_tmdb = result['title']
                        movie_data_release_date = result['release_date'] # YYYY-MM-DD
                        movie_data_release_year = result['release_date'].split('-')[0]
                        movie_data_tmdb_id = result['id']
                        movie_data_rating = result['vote_average']
                        movie_data_overview = result['overview']
                        csv_row = [movie_data_title_tmdb,movie_data_release_date,movie_data_release_year,
                                movie_data_rating,movie_data_overview,movie_data_tmdb_id]
                        csv_rows.append(csv_row)
        write_to_csv(self.filepath_tmdb_top_rated_csv,csv_rows,csv_headers)
    
    def tvdb_show_fetch_ids(self,titles : list, filepath_series_ids = ''):
        import tvdb_v4_official
        from utilities import read_json
        try:
            series_ids = read_json(filepath_series_ids)
        except:
            series_ids = {}
        current_series_titles = list(series_ids.keys())
        tvdb = tvdb_v4_official.TVDB(self.tvdb_api_key)
        for title_with_year in titles:
            alexandria_title = " ".join(title_with_year.split()[:-1])
            if alexandria_title in current_series_titles: continue
            title = alexandria_title.replace(' - ', ': ')
            year = title_with_year.split()[-1][1:-1]
            search_result = tvdb.search(title)
            if search_result:
                index = 0
                try:
                    while True:
                        data = search_result[index]
                        id = data['id']
                        if "series" in id.lower():
                            try:
                                series_year = data['year']
                                print(index,series_year,year)
                                if series_year == year:
                                    id = id.split('-')[-1]
                                    break
                            except KeyError:
                                pass
                        index += 1
                    series_ids[alexandria_title] = id
                except IndexError:
                    print(f"Correct version of {title_with_year} is not found")
                    continue                
            else:
                print(f"{title_with_year} not found in search")
        series_ids = dict(sorted(series_ids.items()))
        if filepath_series_ids != '':
            import json
            with open(filepath_series_ids, 'w') as json_file:
                json.dump(series_ids, json_file, indent=4)
        return series_ids

    def tvdb_show_fetch_info(self,series_num):
        import tvdb_v4_official
        tvdb = tvdb_v4_official.TVDB(self.tvdb_api_key)
        # series = tvdb.get_series(series_num)
        # series_extended = tvdb.get_series_extended(series_num)
        series_episodes_info = tvdb.get_series_episodes(series_num, page=0)
        series_title = series_episodes_info['series']["name"]
        series_overview = series_episodes_info['series']["overview"]
        series_firstAired = series_episodes_info['series']['firstAired']
        series_year = series_episodes_info['series']['year']
        series_lastAired = series_episodes_info['series']['lastAired']
        episode_list = series_episodes_info['episodes']
        series_dict = {} ; series_episode_dict = {}
        for episode in episode_list:
            episode_dict = {}
            episode_name = episode['name']
            episode_aired_date = episode['aired']
            episode_year = episode['year']
            episode_runtime_min = episode['runtime']
            episode_overview = episode['overview']
            episode_image_url = episode['image']
            episode_number = episode['number']
            episode_absolute_number = episode['absoluteNumber']
            season_number = episode['seasonNumber']
            episode_id = episode['id']
            filename = f"{series_title} ({series_year}) S{season_number:02d}E{episode_number:02d}"
            episode_dict.update({
                "Episode Name" : episode_name,
                "Episode Air Date" : episode_aired_date,
                "Episode Runtime (min.)" : episode_runtime_min,
                "Episode Overview" : episode_overview,
                "Episode Number" : episode_number,
                "Episode Absolute Number" : episode_absolute_number,
                "Season Number" : season_number,
                "Episode Image URL" : episode_image_url,
                "Episode ID" : episode_id
            })
            series_episode_dict.update({
                filename : episode_dict
            })
        series_dict.update({
            "Series Title" : series_title,
            "Series First Airerd" : series_firstAired,
            "Series Last Aired" : series_lastAired,
            "Series Overview" : series_overview,
            "Series Episodes" : series_episode_dict,
            "Series ID" : series_num
        })
        return series_dict

    def tvdb_fetch_all_series_info(self, series_ids):
        list_series_ids = list(series_ids.values())
        for series_id in list_series_ids:
            self.tvdb_show_fetch_info(series_id)

    def emby_api(self):
        import requests
        # Set your Emby server information and API key
        emby_url = self.emby_url
        api_key = self.emby_api_key
        # Example: Get all items from your Emby server
        endpoint = f'{emby_url}/emby/Items'
        headers = {
            'X-Emby-Token': api_key
        }
        response = requests.get(endpoint, headers=headers)
        # Check if the request was successful
        if response.status_code == 200:
            data = response.json()
            for item in data['Items']:
                print(f"Title: {item['Name']}, Type: {item['Type']}")
        else:
            print(f"Error: {response.status_code} - {response.text}")

        ###

        import requests

        # Replace with the actual item ID of the actor and the path to the new image
        actor_item_id = 'ACTOR-ITEM-ID'
        image_path = 'path/to/actor-image.jpg'

        # Endpoint for updating the actor image
        endpoint = f'{emby_url}/emby/Items/{actor_item_id}/Images?Type=Primary'

        # Read the image file
        with open(image_path, 'rb') as image_file:
            image_data = image_file.read()

        # Headers with your API key
        headers = {
            'X-Emby-Token': api_key,
            'Content-Type': 'image/jpeg'
        }

        # Make the POST request to update the image
        response = requests.post(endpoint, headers=headers, data=image_data)

        if response.status_code == 204:
            print(f"Actor image updated successfully!")
        else:
            print(f"Failed to update actor image: {response.status_code} - {response.text}")

        ###

        actor_name = 'ACTOR-NAME'
        # Search for the actor by name
        search_endpoint = f'{emby_url}/emby/Persons?searchTerm={actor_name}'
        response = requests.get(search_endpoint, headers=headers)

        if response.status_code == 200:
            data = response.json()
            if data['Items']:
                actor_item_id = data['Items'][0]['Id']
                print(f"Found actor {actor_name} with ItemId: {actor_item_id}")
            else:
                print(f"Actor {actor_name} not found.")
        else:
            print(f"Error: {response.status_code} - {response.text}")

import os
if __name__ == '__main__':
    # import libraries
    import json, requests
    from analytics import update_movie_list
    from colorama import Fore, Back, Style
    from utilities import get_drive_letter, read_json
    # import utility methods
    from utilities import write_list_to_txt_file, write_to_csv, read_alexandria_config, read_csv, read_file_as_list, read_json
    src_directory = os.path.dirname(os.path.abspath(__file__))
    drive_hieracrchy_filepath = (src_directory+"/config/alexandria_drives.config").replace('\\','/')
    api_config_filepath = (src_directory+"/config/api.config").replace('\\','/')
    output_directory = ("\\".join(src_directory.split('\\')[:-1])+"/output").replace('\\','/')
    filepath_statistics = os.path.join(output_directory,"alexandria_media_statistics.json")
    drive_config = read_json(drive_hieracrchy_filepath)
    primary_drives_dict, backup_drives_dict, extensions_dict = read_alexandria_config(drive_config)
    primary_drive_letter_dict = {}; backup_drive_letter_dict = {}
    for key,value in primary_drives_dict.items(): primary_drive_letter_dict[key] = [get_drive_letter(x) for x in value]
    update_movie_list(primary_drive_letter_dict)
    media_statistics = read_json(filepath_statistics)
    list_tv_shows = media_statistics["TV Shows"]["Show Titles"]
    list_anime = media_statistics["Anime"]["Anime Titles"]
    list_series = list_tv_shows + list_anime
    # instantiate API handler
    api_handler = API()
    # filepath_series_ids = os.path.join(output_directory,"alexandria_series_ids.json").replace('\\','/')
    # series_ids = api_handler.tvdb_show_fetch_ids(list_series,filepath_series_ids)
    api_handler.tmdb_movies_fetch()
    # api_handler.tmdb_movies_pull_popular()
    # api_handler.tvdb_fetch_all_series_info(series_ids)
    # api_handler.tvdb_show_fetch_info(series_ids[0])