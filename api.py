'''========/// API's MOVIES and SERIES output: ///========
    https://developer.themoviedb.org/reference'''

import os
import time 
import json
import requests

from datetime import datetime, timedelta
from dotenv import load_dotenv
load_dotenv()

from database import Database
from queue_manager import add_to_queue

class tmdb:
    def __init__(self):
        self.tmdb_url = 'https://api.themoviedb.org/3/'
        self.headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {os.getenv('API_KEY')}"
        }

    def timestamp(self):
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def api_request(self, title, category, year = None):
        time.sleep(0.3)  # 0.2s between the requests // Rate Limiting = They sit somewhere in the 50 requests per second range for TMDB API
        query_url = f'{self.tmdb_url}search/{category}?query={title}&include_adult=false&language=en-US&page=1' + (f'&year={year}' if year else '')

        try:
            # Make the initial request to TMDB API
            response = requests.get(query_url, headers=self.headers).json()

            # Check if there are any results
            if not response.get('results'):
                return

            # Get the top result's TMDB ID
            tmdb_id = response['results'][0]['id']

            # Construct the URL for more item details
            get_item_details_url = f'{self.tmdb_url}{category}/{tmdb_id}?language=en-US'
            
            # Fetch more details about the item
            item_data = requests.get(get_item_details_url, headers=self.headers).json()

            return item_data

        except requests.exceptions.RequestException as e:
            print(f'[{self.timestamp()}] [INFO    ] api.tmdb: error fetching data ->', e)
            return
        except KeyError as e:
            print(f'[{self.timestamp()}] [INFO    ] api.tmdb: missing expected key in response ->', e)
            return
        except IndexError as e:
            print(f'[{self.timestamp()}] [INFO    ] api.tmdb: list index out of range ->', e)
            return
        
    def init_api(self, category, title, year = None, title_hash = None, api_updated = None):
        # category str of either "movie" or "tv"
        # api_updated '%Y-%m-%d %H:%M:%S'      >> check if data is recent, for example if less than "timedelta_value = 1" it will not request data that isnt older than a day
        timedelta_value = 12 # IN HOURS -- variable for is_recent()
        item_data = None

        if category == 'movie':
            if api_updated and self.is_recent(api_updated, timedelta_value):
                return None
            else:
                item_data = self.api_request(title, category, year)

        elif category == 'tv':
            if api_updated and self.is_recent(api_updated, timedelta_value):
                return None
            else:
                item_data = self.api_request(title, category, year)
                
        if not item_data:
            print(f'[{self.timestamp()}] [INFO    ] api.tmdb: api request failed, {title}.')
            return {}

        item_data = self.standardize_genres(item_data)

        # If item_data has poster_path, try to download the image
        if item_data and item_data.get('poster_path'):
            try:
                self.download_image(item_data.get('poster_path'), 'poster')
            except Exception as e:
                print(f'[{self.timestamp()}] [INFO    ] api.tmdb: failed to download poster for {title} ->', e)

        # If item_data has backdrop_path, try to download the image        
        if item_data and item_data.get('backdrop_path'):
            try:
                self.download_image(item_data.get('backdrop_path'), 'backdrop')
            except Exception as e:
                print(f'[{self.timestamp()}] [INFO    ] api.tmdb: failed to download backdrop for {title} ->', e)
                
        # Save metadata backup if item_data is available
        # if item_data:
        #     try:
        #         self.save_metadata_backup(title, title_hash, item_data)
        #     except Exception as e:
        #         print(f'[{self.timestamp()}] [INFO    ] api.tmdb: failed to save metadata {title} ->', e)

        # print(f'[{self.timestamp()}] [INFO    ] api.tmdb: {title}, new request made: {requested}') # debug

        return item_data
    
    def is_recent(self, last_updated, timedelta_value):
        if not last_updated:
            return False
        last_updated = datetime.strptime(last_updated, '%Y-%m-%d %H:%M:%S')
        if last_updated > datetime.now() - timedelta(hours=timedelta_value):
            return True
        return False

    def is_stored_locally(self, title_hash):
        hash_filename = f"{title_hash}.json"
        # Get only the filenames from 'api_metadata/' directory
        for file in os.listdir('api_metadata/'):
            if file.split("_")[-1] == hash_filename:  # Extract last part and compare
                return True
        return False

    def get_local_data(self, title_hash):
        hash_filename = f"{title_hash}.json"
        # Get only the filenames from 'api_metadata/' directory
        for file in os.listdir('api_metadata/'):
            if file.split("_")[-1] == hash_filename:  # Extract last part and compare
                with open(f"api_metadata/{file}", "r") as f:
                    item_data = json.load(f)
                    return item_data

    def save_metadata_backup(self, title, title_hash, item_data):
        # Ensure the directory 'api_metadata' exists
        os.makedirs('api_metadata', exist_ok=True)
        filename = f'tmdb_{title.lower().replace(" ", "_")}_metadata_{title_hash}.json' 
        # Write metadata
        with open(f'api_metadata/{filename}', 'w') as file:
            json.dump(item_data, file)
                
    def download_image(self, url: str, f_type):
        # url: "/3124shfgghff32314123.jpg"
        if not url.startswith('/'):
            url = f'/{url}' 
        time.sleep(.2)
        if f_type == 'poster':
            SAVE_FOLDER = "static/images/posters"
            image_urls = [
            "https://image.tmdb.org/t/p/w400",         # 400x600px
            "https://image.tmdb.org/t/p/original",     # Original size, px not specified
            ]
        elif f_type == 'backdrop':
            SAVE_FOLDER = "static/images/backdrops"
            image_urls = [
            "https://image.tmdb.org/t/p/original",     # Original size, px not specified
            ]
        else:
            print(f'[ warning ] Could not extract image.')
            return

        os.makedirs(SAVE_FOLDER, exist_ok=True)
        for width in image_urls:
            time.sleep(.7)
            file_width = width.split("/")[-1]
            url_path = width+url
            filename = os.path.join(SAVE_FOLDER, f"{file_width}_{os.path.basename(url)}")
            if os.path.exists(filename):
                continue

            response = requests.get(url_path, stream=True) 
            if response.status_code == 200:
                with open(filename, "wb") as file:
                    for chunk in response.iter_content(1024):
                        file.write(chunk)
            else:
                print(f'[{self.timestamp()}] [INFO    ] api.tmdb: failed to download image: {url_path}')

    def standardize_genres(self, item_data):
        genre_map = {
            "Science Fiction": "Sci-Fi",
            "Sci-Fi & Fantasy": ["Sci-Fi", "Fantasy"],
            "Action & Adventure": ["Action", "Adventure"],
            "War & Politics": ["War", "Politics"],
            "Mystery & Thriller": ["Mystery", "Thriller"],
        }

        new_genres = []
        existing_ids = set()  # Avoid duplicate genres
        for genre in item_data.get("genres", []):
            name = genre["name"].strip()
            genre_id = genre["id"]
            if name in genre_map:
                mapped = genre_map[name]
                if isinstance(mapped, list):  # If it needs to be split into multiple
                    for new_name in mapped:
                        if new_name not in existing_ids:  # Prevent duplicates
                            new_genres.append({"id": None, "name": new_name})  # Assign None for new IDs
                            existing_ids.add(new_name)
                else:
                    if mapped not in existing_ids:
                        new_genres.append({"id": genre_id, "name": mapped})
                        existing_ids.add(mapped)
            else:
                if name not in existing_ids:
                    new_genres.append(genre)
                    existing_ids.add(name)

        item_data["genres"] = new_genres  # Replace the original genres

        return item_data
    
    def tmdb_api(self, hash_key):
        item = Database().get_item_by_hash(hash_key)
        if not item:
            return

        item_id = item["id"]
        category = item["category"]
        title = item["title"]
        year = item["release_date"]
        title_hash = item["title_hash_key"]
        api_updated = item["api_updated"]

        # Map the category to its string equivalent
        category = {
            "movie": "movie",
            "series": "tv"
        }.get(category, None)
        
        if not category:
            return

        item_data = self.init_api(category, title, year, title_hash, api_updated)
        if not item_data:
            return
        try:
            Database().api_insert_metadata(item_data, item_id, category, year)
        except Exception as e:
            print(f'[{self.timestamp()}] [INFO    ] api.tmdb: failed to insert to database ->', e)    

    def tmdb_update(self):
        items = Database().fetch_items() # returns list of objects item data
        print(f'[{self.timestamp()}] [INFO    ] api.tmdb: initializing scheduled database tmdb update.')
        if not items:
            return
        
        for item in items:
            item_id = item.id
            category = item.category
            title = item.title
            year = item.release_date
            title_hash = item.title_hash_key
            api_updated = item.api_updated

            if year:
                year = year.split("-")[0] # convert 2023-12-19 to 2023 if needed

            # Map the category to its string equivalent
            category = {
                "movie": "movie",
                "series": "tv"
            }.get(category, None)
            
            if not category:
                return

            item_data = self.init_api(category, title, year, title_hash, api_updated)
            if not item_data:
                continue

            try:
                add_to_queue(lambda item_data=item_data, item_id=item_id, category=category, year=year: Database().api_insert_metadata(item_data, item_id, category, year))
            except Exception as e:
                print(f'[{self.timestamp()}] [INFO    ] api.tmdb: failed to insert to database ->', e)  
        print(f'[{self.timestamp()}] [INFO    ] api.tmdb: database tmdb update completed.')