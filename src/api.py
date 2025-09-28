#!/usr/bin/env python

import json
import os
import requests

from typing import Dict, List

import tvdb_v4_official

from colorama import Fore, Back, Style

from utilities import read_json, write_json

from utilities import (
    get_drive_letter,
    read_alexandria_config,
    read_csv,
    read_json,
    write_to_csv
)

RED = Fore.RED + Style.BRIGHT
YELLOW = Fore.YELLOW + Style.BRIGHT
GREEN = Fore.GREEN + Style.BRIGHT
RESET = Style.RESET_ALL

class API(object):
    def __init__(self):
        self.src_directory = os.path.dirname(os.path.abspath(__file__))
        self.root_directory = os.path.abspath(os.path.join(self.src_directory, ".."))
        self.output_directory = os.path.join(self.root_directory,"output")
        self.filepath_movie_list = os.path.join(self.output_directory,'movies','movie_list.txt')
        self.filepath_tmdb_csv = os.path.join(self.output_directory,'movies','tmdb.csv')
        self.filepath_tmdb_top_rated_current_csv = os.path.join(self.output_directory,'movies','tmdb_top_rated_existing.csv')
        self.filepath_tmdb_top_rated_missing_csv = os.path.join(self.output_directory,'movies','tmdb_top_rated_missing.csv')
        self.filepath_tmdb_recent_current_csv = os.path.join(self.output_directory,'movies','tmdb_recent_existing.csv')
        self.filepath_tmdb_recent_missing_csv = os.path.join(self.output_directory,'movies','tmdb_recent_missing.csv')
        self.filepath_movie_list_tmdb_not_found = os.path.join(self.output_directory,'movie_list_tdmb_not_found.txt')
        self.filepath_api_config = os.path.join(self.src_directory,"..", "config","api.config")
        self.filepath_movie_tmdb_ids = os.path.join(self.output_directory,'movies',"movie_tmdb_ids.json")
        self.filepath_series_ids = os.path.join(self.output_directory,"alexandria_series_ids.json")
        self.filepath_series_data = os.path.join(self.output_directory,"alexandria_series_data.json")
        self.filepath_statistics = os.path.join(self.output_directory,"alexandria_media_statistics.json")
        self.drive_hieracrchy_filepath = os.path.join(self.src_directory,"..", "config","alexandria_drives.config")
        self.drive_config = read_json(self.drive_hieracrchy_filepath)
        self.api_config = read_json(self.filepath_api_config)
        self.tmdb_api_url_base_search = self.api_config['tmdb']['api_url_base_search']
        self.tmdb_api_url_base_query = self.api_config['tmdb']['api_url_base_query']
        self.tmdb_api_url_base_discover = self.api_config['tmdb']['api_url_base_discover']
        self.tmdb_api_key = self.api_config['tmdb']['api_key']
        self.open_library_api_url_base = self.api_config['open-library']['api_url_base']
        self.emby_api_key = self.api_config['emby']['api_key']
        self.emby_url = self.api_config['emby']['api_url']
        self.headers_tmdb = {
            "accept": "application/json",
            "Authorization": f"Bearer {self.tmdb_api_key}"
            }
        self.tvdb_api_key = self.api_config['tvdb']['api_key']

    def tmdb_movies_fetch(self, auto_delete=False):
        """Fetch and update TMDB movie data, with optional auto-deletion.

        Args:
            auto_delete (bool): If True, bypasses user confirmation for deleting movies.
        """
        from analysis.update_media_list import update_media_list
        # Update movie list
        movie_list = update_media_list('movies')
        movie_list += update_media_list('anime_movies')

        # Read current movies in local TMDB database
        tmdb_current_movies = [x['Title_Alexandria'] for x in read_csv(self.filepath_tmdb_csv)]

        # Generate list of movies to query
        movie_list_adjusted = [movie for movie in movie_list if movie not in tmdb_current_movies]

        # Define CSV headers and load existing data
        csv_headers = [
            'Title_Alexandria', 'Title_TMDb', 'Release_Date', 'Release_Year', 'Parental Rating',
            'Runtime_Min', 'Runtime_Hrs', 'Rating', 'Budget', 'Revenue', 'Genres',
            'Production_Companies', 'Overview', 'TMDb_ID', 'IMDb_ID'
        ]
        csv_rows = [list(x.values()) for x in read_csv(self.filepath_tmdb_csv)]

        # Load or initialize movie TMDB IDs
        movie_tmdb_ids = read_json(self.filepath_movie_tmdb_ids) if os.path.exists(
            self.filepath_movie_tmdb_ids) else {}
        current_movie_id_titles = list(movie_tmdb_ids.keys())

        movie_list_bypass_list = []
        movie_list_not_found = []

        for movie_with_year in movie_list_adjusted:
            if movie_with_year in movie_list_bypass_list:
                continue

            print(f"{Fore.GREEN}{Style.BRIGHT}Downloading data{Style.RESET_ALL} for "
                f"{Fore.BLUE}{Style.BRIGHT}{movie_with_year}{Style.RESET_ALL}")

            movie = '('.join(movie_with_year.split('(')[:-1])
            year = movie_with_year.split('(')[-1].split(')')[0]

            if movie_with_year not in current_movie_id_titles:
                params_tmdb_movie_query = {
                    'query': movie,
                    'include_adult': 'false',
                    'language': 'en-US',
                    'page': '1',
                    'primary_release_year': year
                }
                response_search = requests.get(
                    self.tmdb_api_url_base_search,
                    params=params_tmdb_movie_query,
                    headers=self.headers_tmdb
                )
            else:
                params_tmdb_movie_query = {'language': 'en-US'}
                url = f"{self.tmdb_api_url_base_query}{movie_tmdb_ids[movie_with_year]}?"
                response_search = requests.get(url, params=params_tmdb_movie_query, headers=self.headers_tmdb)

            if response_search.status_code == 200:
                data_search = response_search.json()
                try:
                    id_tmdb = data_search['results'][0]['id']
                except IndexError:
                    print(f"{Fore.RED}{Style.BRIGHT}Error{Style.RESET_ALL} with "
                        f"{Fore.BLUE}{Style.BRIGHT}{movie_with_year}{Style.RESET_ALL}")
                    movie_list_not_found.append(movie_with_year)
                    continue
                except KeyError:
                    id_tmdb = data_search['id']

                url_query = f"{self.tmdb_api_url_base_query}{id_tmdb}?language=en-US"
                response_query = requests.get(url_query, headers=self.headers_tmdb)

                if response_query.status_code == 200:
                    data_query = response_query.json()
                    movie_data = {
                        'title_alexandria': movie_with_year,
                        'title_tmdb': data_query['title'],
                        'release_date': data_query['release_date'],  # YYYY-MM-DD
                        'release_year': data_query['release_date'].split('-')[0],
                        'rating_certification': self._fetch_parental_rating(id_tmdb).strip(),
                        'runtime_min': data_query['runtime'],
                        'runtime_hrs': f'{data_query["runtime"]/60:.2f}',
                        'rating': data_query['vote_average'],
                        'tmdb_id': id_tmdb,
                        'imdb_id': data_query['imdb_id'],
                        'budget': data_query['budget'],
                        'revenue': data_query['revenue'],
                        'genres': [x['name'] for x in data_query['genres']],
                        'production_companies': [x['name'] for x in data_query['production_companies']],
                        'overview': data_query['overview']
                    }
                    csv_row = [
                        movie_data['title_alexandria'], movie_data['title_tmdb'], movie_data['release_date'],
                        movie_data['release_year'], movie_data['rating_certification'], movie_data['runtime_min'],
                        movie_data['runtime_hrs'], movie_data['rating'], movie_data['budget'],
                        movie_data['revenue'], movie_data['genres'], movie_data['production_companies'],
                        movie_data['overview'], movie_data['tmdb_id'], movie_data['imdb_id']
                    ]
                    csv_rows.append(csv_row)

        # Check for movies to delete
        original_csv_movies = {x['Title_Alexandria'] for x in read_csv(self.filepath_tmdb_csv)}
        movies_to_delete = original_csv_movies - set(movie_list)

        perform_deletion = False
        if movies_to_delete:
            if auto_delete:
                perform_deletion = True
                print(f"{Fore.YELLOW}{Style.BRIGHT}Auto-deleting {len(movies_to_delete)} movies: {movies_to_delete}{Style.RESET_ALL}")
            else:
                print(f"\n{Fore.YELLOW}{Style.BRIGHT}The following movies will be deleted from the CSV:{Style.RESET_ALL}")
                for movie in movies_to_delete:
                    print(f"{movie}")
                confirm = input(f"{Fore.YELLOW}Confirm deletion of these {len(movies_to_delete)} movies? (y/n): {Style.RESET_ALL}")
                if confirm.lower() == 'y':
                    perform_deletion = True
                else:
                    print(f"{Fore.RED}Deletion skipped, but CSV will still be updated.{Style.RESET_ALL}")

        # Filter out rows for deleted movies only if confirmed or auto_delete is True
        if perform_deletion:
            csv_rows = [row for row in csv_rows if row[0] in movie_list]

        # Sort and update CSV
        csv_rows = sorted(csv_rows, key=lambda x: x[0], reverse=False)

        # Update movie_tmdb_ids
        for row in csv_rows:
            if row[0] not in current_movie_id_titles and len(row) > 10:
                movie_tmdb_ids[row[0]] = str(row[-2])

        # Write to CSV (always, regardless of deletion)
        write_to_csv(self.filepath_tmdb_csv, csv_rows, csv_headers)

        # Write updated movie_tmdb_ids to JSON
        movie_tmdb_ids = dict(sorted(movie_tmdb_ids.items()))
        with open(self.filepath_movie_tmdb_ids, 'w') as json_file:
            json.dump(movie_tmdb_ids, json_file, indent=4)

        print(f"{Fore.GREEN}{Style.BRIGHT}TMDB Movie data refreshed{Style.RESET_ALL}")

    def tmdb_movies_pull_catalog(self,min_votes=200):

        """
        Add discriminator the saves files that I have in a different file than those that I don't have. Also, change file names. 
        """
        tmdb_csv = read_csv(self.filepath_tmdb_csv)
        current_tmdb_titles_with_year = [x["Title_TMDb"]+f' ({x["Release_Year"]})' for x in tmdb_csv]
        csv_headers = ['Title_TMDb','Release_Date','Release_Year','Rating','Overview','TMDb_ID']
        csv_rows = []
        pages_min = 1; pages_max = 628
        for num_page in range(pages_min,pages_max+1):
            print(f'{Fore.GREEN}{Style.BRIGHT}Searching for movies{Style.RESET_ALL} in {Fore.YELLOW}{Style.BRIGHT}Page {num_page}{Style.RESET_ALL}')
            params_tmdb_movie_discover = {
                'include_adult': 'false',
                'include_video': 'false',
                'language': 'en-US',
                'page': num_page,
                'sort_by': 'vote_average.desc',
                'without_genres': '99,10755',
                'vote_count.gte': min_votes
            }
            response_search = requests.get(self.tmdb_api_url_base_discover, params=params_tmdb_movie_discover, headers=self.headers_tmdb)
            if response_search.status_code == 200:
                results = response_search.json()['results']
                for result in results:
                    if result['original_language'] == 'en':
                        print(f'{Fore.GREEN}{Style.BRIGHT}Storing: {Fore.BLUE}{Style.BRIGHT}{result['title']}{Style.RESET_ALL}')
                        movie_data_title_tmdb = result['title']
                        movie_data_release_date = result['release_date'] # YYYY-MM-DD
                        movie_data_release_year = result['release_date'].split('-')[0]
                        movie_data_tmdb_id = result['id']
                        movie_data_rating = result['vote_average']
                        movie_data_overview = result['overview']
                        csv_row = [movie_data_title_tmdb,movie_data_release_date,movie_data_release_year,
                                movie_data_rating,movie_data_overview,movie_data_tmdb_id]
                        csv_rows.append(csv_row)
        pulled_tmdb_titles_with_year = [f"{x[0]} ({x[2]})" for x in csv_rows]
        existing_title_csv_rows = []; missing_title_csv_rows = []
        for i,pttwy in enumerate(pulled_tmdb_titles_with_year):
            if pttwy in current_tmdb_titles_with_year:
                existing_title_csv_rows.append(csv_rows[i])
            else:
                missing_title_csv_rows.append(csv_rows[i])
        existing_top_rated_csv_rows = sorted(existing_title_csv_rows, key=lambda x: x[3],reverse=True)
        write_to_csv(self.filepath_tmdb_top_rated_current_csv,existing_top_rated_csv_rows,csv_headers)
        missing_top_rated_csv_rows = sorted(missing_title_csv_rows, key=lambda x: x[3],reverse=True)
        write_to_csv(self.filepath_tmdb_top_rated_missing_csv,missing_top_rated_csv_rows,csv_headers)
        existing_recent_csv_rows = sorted(existing_title_csv_rows, key=lambda x: x[1],reverse=True)
        write_to_csv(self.filepath_tmdb_recent_current_csv,existing_recent_csv_rows,csv_headers)
        missing_recent_csv_rows = sorted(missing_title_csv_rows, key=lambda x: x[1],reverse=True)
        write_to_csv(self.filepath_tmdb_recent_missing_csv,missing_recent_csv_rows,csv_headers)        
    
    def fetch_tvdb_series_ids(self) -> Dict[str, str]:
        """
        Fetch TVDB series IDs for TV shows and anime titles, storing them in a JSON file.
        
        Returns:
            Dict[str, str]: Dictionary mapping series titles with years to their TVDB IDs.
        """
        # Load media statistics
        media_stats = read_json(self.filepath_statistics)
        titles = (
            media_stats["TV Shows"]["Show Titles"] +
            media_stats["Anime"]["Anime Titles"]
        )
        omit_series = ["Das Boot - Die Komplette (1985)"]

        # Load or initialize series IDs
        series_ids = read_json(self.filepath_series_ids, default={})
        current_titles = set(series_ids.keys())
        tvdb = tvdb_v4_official.TVDB(self.tvdb_api_key)

        for title_with_year in titles:
            # Extract title and year
            title_parts = title_with_year.split()
            base_title = " ".join(title_parts[:-1])
            year = title_parts[-1][1:-1]  # Extract year from (YYYY)
            formatted_title = base_title.replace(" - ", ": ")
            title_with_year = f"{base_title} ({year})"
            if title_with_year in omit_series:
                continue
            if title_with_year in current_titles:
                continue
            
            # Search TVDB
            try:
                search_results = tvdb.search(formatted_title)
            except Exception as e:
                print(f"Error searching for {title_with_year}: {e}")
                continue

            if not search_results:
                print(f"{title_with_year} not found in TVDB search")
                continue

            # Find matching series
            for result in search_results:
                if not result.get("id", "").lower().startswith("series"):
                    continue

                try:
                    series_year = result.get("year")
                    if series_year == year:
                        series_id = result["id"].split("-")[-1]
                        print(f"{title_with_year}: {series_id}")
                        series_ids[title_with_year] = series_id
                        break
                except KeyError:
                    continue
            else:
                print(f"Correct version of {title_with_year} not found")

        # Sort and save series IDs
        series_ids = dict(sorted(series_ids.items(), key=lambda item: item[0].lower()))
        if self.filepath_series_ids:
            write_json(self.filepath_series_ids, series_ids)

        return series_ids

    def fetch_tvdb_series_info(self,series_num):
        import tvdb_v4_official
        tvdb = tvdb_v4_official.TVDB(self.tvdb_api_key)
        # series = tvdb.get_series(series_num)
        # series_extended = tvdb.get_series_extended(series_num)
        series_episodes_info = tvdb.get_series_episodes(series_num, page=0, lang='en')
        try:
            series_title = series_episodes_info['series']["name"]
            series_overview = series_episodes_info['series']["overview"]
            series_year = series_episodes_info['series']['year']
            series_firstAired = series_episodes_info['series']['firstAired']
            series_lastAired = series_episodes_info['series']['lastAired']
            series_status = series_episodes_info['series']['status']['name']
        except KeyError:
            series_title = series_episodes_info["name"]
            series_overview = series_episodes_info["overview"]
            series_year = series_episodes_info['year']
            series_firstAired = series_episodes_info['firstAired']
            series_lastAired = series_episodes_info['lastAired']
            series_status = series_episodes_info['status']['name']     
        episode_list = series_episodes_info['episodes']
        series_dict = {} ; series_episode_dict = {}
        for episode in episode_list:
            episode_dict = {}
            episode_name = episode['name']
            episode_aired_date = episode['aired']
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
            "Series First Aired" : series_firstAired,
            "Series Last Aired" : series_lastAired,
            "Series Status" : series_status,
            "Series Overview" : series_overview,
            "Series Episodes" : series_episode_dict,
            "Series ID" : series_num
        })
        return series_dict
    
    def update_series_data(self) -> Dict[str, Dict]:
        self.fetch_tvdb_series_ids()
        series_ids = read_json(self.filepath_series_ids)
        macro_series_data = read_json(self.filepath_series_data)

        for idx, series_name in enumerate(series_ids):
            series_id = series_ids[series_name]
            series_data = macro_series_data.get(series_id, {})

            try:
                if series_data['Series Status'] == "Ended":
                    print(f"{YELLOW}Skipping{RESET} {series_name} [{series_id}] | {GREEN}Series ended & is already processed.{RESET}")
                    continue
            except KeyError:
                pass

            series_data = self.fetch_tvdb_series_info(series_id)
            if series_data is None:
                print(f"{RED}Failed to fetch data for series{RESET}: {series_name} [{series_id}]")
                continue
            
            macro_series_data[series_id] = series_data
            print(f"{GREEN}Processed{RESET} {idx + 1}/{len(series_ids)}: {series_name} [{series_id}]")
            if idx % 10 == 0:
                # Write progress to file every 10 iterations
                write_json(self.filepath_series_data, macro_series_data)
            write_json(self.filepath_series_data, macro_series_data)
        return macro_series_data

    def open_library_search(self, 
                            title: str, 
                            year: str = None,
                            author: str = None
                            ) -> dict:
        # Set your Open Library API URL
        open_library_url = self.open_library_api_url_base
        # Example: Search for books by title

        params = {
            'q': title.replace(' ','+'),
            'limit': 10,  # Limit the number of results
            'lang': 'eng'
        }
        response = requests.get(open_library_url, params=params)
        # Check if the request was successful
        if response.status_code == 200:
            data = response.json()
            for book in data['docs']:
                title = book.get('title', 'Unknown Title')
                authors = book.get('author_name', ['Unknown Author'])
                first_publish_year = book.get('first_publish_year', 'Unknown Year')
                cover_id = book.get('cover_i', None)
                cover_edition_key = book.get('cover_edition_key', None)
                author_keys = book.get('author_key', [])
                cover_url = f'http://covers.openlibrary.org/b/id/{cover_id}-L.jpg' if cover_id else None
                print(f"Title: {title}, Authors: {', '.join(authors)}, Year: {first_publish_year}")
            if not data['docs']:
                print(f"No results found for '{title}'")
                return None
            book_info = data['docs']
            if year:
                for book in book_info:
                    if 'first_publish_year' in book and book['first_publish_year'] == year:
                        print(f"Found book from {year}: {book['title']}")
                        return book
                    if 'author_name' in book and author and author in book['author_name']:
                        print(f"Found book by {author}: {book['title']}")
                        return book
            return book_info[0]
        else:
            print(f"Error: {response.status_code} - {response.text}")

    def emby_api(self):
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

    def _fetch_parental_rating(self,tmdb_id):
        tmdb_api_key = self.tmdb_api_key
        # url = f"https://api.themoviedb.org/3/tv/{tmdb_id}/content_ratings"
        url = f'https://api.themoviedb.org/3/movie/{tmdb_id}/release_dates'
        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {tmdb_api_key}"
        }
        preferred_countries = ['US', 'CA', 'GB', 'FR', 'GR', 'ES', 'DE', 'CH', 'JP']
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
            data = response.json()

            ratings = data.get('results', [])
            if not ratings:
                print("No parental ratings found.")
                return None

            # Try preferred countries first
            for country in preferred_countries:
                for rating in ratings:
                    if rating.get('iso_3166_1') == country:
                        rating_certification = rating.get('release_dates')[0]['certification']
                        if rating_certification != '' and rating_certification != 'NR':
                            # print(f"Parental rating for TMDb ID {tmdb_id}: {rating_certification} ({country})")
                            return rating_certification

            # Fallback to any available rating if preferred countries not found
            first_certification = ratings[0].get('release_dates')[0]['certification']
            if first_certification != '':
                print(f"FALLBACK: Parental rating for TMDb ID {tmdb_id}: {first_certification} ({ratings[0].get('iso_3166_1')})")
                return first_certification
            else:
                print(f"Parental rating for TMDb ID {tmdb_id}: NR (No certification available)")
                return 'NR'

        except requests.RequestException as e:
            print(f"Request failed: {e}")
        except ValueError:
            print("Failed to decode JSON from response.")
        return None

import os
if __name__ == '__main__':
    # instantiate API handler
    api_handler = API()
    drive_config = read_json(api_handler.drive_hieracrchy_filepath)
    primary_drives_dict, backup_drives_dict, extensions_dict = read_alexandria_config(drive_config)
    primary_drive_letter_dict = {}
    for key,value in primary_drives_dict.items(): primary_drive_letter_dict[key] = [get_drive_letter(x) for x in value]
    series_data = api_handler.fetch_tvdb_series_info(378609)
    pass
    # series_ids = api_handler.tvdb_show_fetch_ids()
    # api_handler.tmdb_movies_fetch()
    # api_handler.tmdb_movies_pull_popular()
    # api_handler.tvdb_fetch_all_series_info(series_ids)
    # api_handler.tvdb_show_fetch_info(series_ids[0])
    # api_handler._fetch_parental_rating(4951)
    data = api_handler.open_library_search("The Great Gatsby","1920")
    # with open(os.path.join(api_handler.output_directory, "temp", "open_library_search_results.json"), "w", encoding="utf-8") as f:
    #     json.dump(data, f, indent=4, ensure_ascii=False)