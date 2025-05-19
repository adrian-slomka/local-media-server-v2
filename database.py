
import os
import json
import sqlite3
from datetime import datetime

class Database:
    def __init__(self, **kwargs):
        self.localdb = 'localdb.db'

        for key, value in kwargs.items():
            setattr(self, key, value)

    def timestamp(self):
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def db_connect(self):
        conn = sqlite3.connect(self.localdb)
        conn.row_factory = sqlite3.Row  
        return conn

    def new_database(self):
        conn = sqlite3.connect(self.localdb)
        conn.execute("PRAGMA foreign_keys = ON;")
        cursor = conn.cursor()

        # Table for Movies and TV Series Combined
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS media_items (
                id INTEGER PRIMARY KEY,
                category TEXT,
                title TEXT,
                tmdb_title TEXT,
                original_title TEXT,
                release_date TEXT,
                description TEXT,
                tagline TEXT,
                origin_country TEXT,
                spoken_languages TEXT,
                studio TEXT,
                production_countries TEXT,
                popularity REAL,
                vote_average REAL,
                vote_count INTEGER,
                status TEXT,
                poster_path TEXT,
                backdrop_path TEXT,
                title_hash_key TEXT UNIQUE,
                tmdb_id TEXT,
                imdb_id TEXT,
                entry_created TEXT DEFAULT (datetime('now')),
                api_updated TEXT
            )
        ''')

        # Table for Movies specific (budget, revenue etc...)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS movie_details (
                id INTEGER PRIMARY KEY,
                media_items_id INTEGER UNIQUE,
                budget INTEGER,
                revenue INTEGER,
                duration INTEGER,
                FOREIGN KEY (media_items_id) REFERENCES media_items(id) ON DELETE CASCADE
            )
        ''')

        # Table for TV Series Details (additional info to specific serie)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tv_series_details (
                id INTEGER PRIMARY KEY,
                media_items_id INTEGER UNIQUE,
                created_by TEXT, 
                first_air_date TEXT,  
                last_air_date TEXT,
                next_episode_to_air TEXT,  
                number_of_episodes INTEGER, 
                number_of_seasons INTEGER,
                in_production BOOLEAN,            
                FOREIGN KEY (media_items_id) REFERENCES media_items(id) ON DELETE CASCADE
            )
        ''')

        # Table for Seasons of the TV Series
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tv_seasons (
                id INTEGER PRIMARY KEY,
                media_items_id INTEGER,
                season INTEGER,
                air_date TEXT,
                episode_count INTEGER,
                tmdb_id INTEGER UNIQUE,
                season_name TEXT,
                overview TEXT,
                season_poster_path TEXT,       
                latest_episode_entry TEXT,     
                FOREIGN KEY (media_items_id) REFERENCES media_items(id) ON DELETE CASCADE
            )
        ''')

        # Table for Episodes (For TV Series only)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tv_episodes (
                id INTEGER PRIMARY KEY,
                media_items_id INTEGER,
                season INTEGER,
                episode INTEGER,
                episode_title TEXT,
                air_date TEXT,
                duration TEXT
            )
        ''')


        # Table for Metadata (For movies and episodes)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS media_metadata (
                id INTEGER PRIMARY KEY,
                media_items_id INTEGER, 
                season INTEGER,
                episode INTEGER,
                resolution TEXT,
                extension TEXT,
                path TEXT,
                file_size TEXT,
                duration TEXT,
                audio_codec TEXT,
                video_codec TEXT,
                bitrate TEXT,
                frame_rate TEXT,
                width TEXT,
                height TEXT,
                aspect_ratio TEXT,
                file_hash_key TEXT NOT NULL UNIQUE,
                key_frame TEXT,                   
                FOREIGN KEY (media_items_id) REFERENCES media_items(id) ON DELETE CASCADE
            )
        ''')

        # Table for Genres
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS media_genres (
                media_items_id INTEGER,
                genre_id INTEGER,
                PRIMARY KEY (media_items_id, genre_id),
                FOREIGN KEY (media_items_id) REFERENCES media_items(id) ON DELETE CASCADE,
                FOREIGN KEY (genre_id) REFERENCES genres(id) ON DELETE CASCADE
            )
        ''')

        # Table for Genres
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS genres (
                id INTEGER PRIMARY KEY,
                genre TEXT UNIQUE
            )
        ''')

        # Table for Subtitles (For movies and episodes)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS media_subtitles (
                id INTEGER PRIMARY KEY,
                media_metadata_id INTEGER,  -- References media_items
                path TEXT UNIQUE,
                lang TEXT,
                label TEXT,   
                FOREIGN KEY (media_metadata_id) REFERENCES media_metadata(id) ON DELETE CASCADE
            )
        ''')

        # Table for User related data
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_profile (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL, 
                media_items_id INTEGER,    -- References media_items id
                rating INTEGER,                    -- Rating given by the user
                watchlist INTEGER,                 -- 1 for added to watchlist, 0 for not
                FOREIGN KEY (media_items_id) REFERENCES media_items(id) -- Enforce foreign key constraint
            )
        ''')

        # Table for User related data
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_profile_items (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL, 
                media_items_id INTEGER,
                media_metadata_id INTEGER,
                watched INTEGER,                        
                current_time INTEGER DEFAULT 0,
                watchtime INTEGER DEFAULT 0,                          
                FOREIGN KEY (media_items_id) REFERENCES media_items(id), -- Enforce foreign key constraint
                FOREIGN KEY (media_metadata_id) REFERENCES media_metadata(id) -- Enforce foreign key constraint
            )
        ''')




        # Trigger to Delete Movie If No More Metadata Exists
        cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS delete_movie_if_no_metadata
            AFTER DELETE ON media_metadata
            FOR EACH ROW
            BEGIN
                DELETE FROM media_items
                WHERE id = OLD.media_items_id
                AND OLD.episode IS NULL -- Ensure it's a movie (episode is NULL for movies)
                AND NOT EXISTS (SELECT 1 FROM media_metadata WHERE media_items_id = OLD.media_items_id);
            END;
        ''')

        # Trigger to Delete TV Series if No More Metadata Exists for All Episodes
        cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS delete_tv_series_if_no_metadata
            AFTER DELETE ON media_metadata
            FOR EACH ROW
            BEGIN
                DELETE FROM media_items
                WHERE id = OLD.media_items_id
                AND OLD.episode IS NOT NULL -- Ensure it's a TV series episode (episode is NOT NULL)
                AND NOT EXISTS (
                    SELECT 1 FROM media_metadata
                    WHERE media_items_id = OLD.media_items_id
                    AND season = OLD.season
                    AND episode = OLD.episode
                )
                AND NOT EXISTS (SELECT 1 FROM media_metadata WHERE media_items_id = OLD.media_items_id);
            END;
        ''')

        # Trigger to update ENTRY_CREATED in media_items whenver there's new item inserted into metadata table with it's id
        cursor.execute('''
            CREATE TRIGGER update_entry_created
            AFTER INSERT ON media_metadata
            BEGIN
                UPDATE media_items 
                SET entry_created = datetime('now') 
                WHERE id = NEW.media_items_id;
            END;
        ''')

        conn.commit()
        conn.close()

    def create_database(self):
        if not os.path.exists(self.localdb):  
            self.new_database()

    def get_hash_list(self):
        conn = self.db_connect()
        cursor = conn.cursor()
        results = cursor.execute('SELECT file_hash_key FROM media_metadata').fetchall()
        conn.close()
        hash_list = [row[0] for row in results]
        return hash_list

    def remove_from_metadata_table(self, items):
        """
        remove rows from media_metadata table via matching to file_hash_key column
        """
        conn = self.db_connect()
        cursor = conn.cursor()
        for item in items:
            cursor.execute("DELETE FROM media_metadata WHERE file_hash_key = ?", (item,))
        conn.commit()
        conn.close()

    def insert_movie(self, item):
        conn = self.db_connect()
        cursor = conn.cursor()

        existing_item = cursor.execute("SELECT id FROM media_items WHERE title_hash_key = ?", (item["title_hash_key"],)).fetchone()
        if not existing_item:
            cursor.execute(''' 
                INSERT OR IGNORE INTO media_items (
                    category,
                    title,
                    release_date,
                    title_hash_key
                )
                VALUES (?, ?, ?, ?)
            ''', (
                item.get('category', None),
                item.get('title', None),
                item.get('release_date', None),
                item.get('title_hash_key', None)
            ))
            existing_item_id = cursor.lastrowid
        else:
            existing_item_id = existing_item[0]

        
        cursor.execute('''
            INSERT OR IGNORE INTO media_metadata (
                media_items_id,
                season,
                episode,
                resolution, 
                extension, 
                path, 
                file_size,
                duration,
                audio_codec,
                video_codec,
                bitrate,
                frame_rate,
                width,
                height,
                aspect_ratio,    
                file_hash_key,
                key_frame
            ) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (
            existing_item_id, 
            item.get('season', None),
            item.get('episode', None),
            item.get('resolution', None), 
            item.get('extension', None), 
            item.get('path', None), 
            item.get('file_size', None),
            item.get('duration', None),
            item.get('audio_codec', None),
            item.get('video_codec', None),
            item.get('bitrate', None),
            item.get('frame_rate', None),
            item.get('width', None),
            item.get('height', None),
            item.get('aspect_ratio', None),
            item.get('file_hash_key', None),
            item.get('key_frame', None)
        ))

        metadata_row_id = cursor.lastrowid
        subtitles = item.get('subtitles', [])
        if subtitles:
            for subs in subtitles:
                cursor.execute('''
                    INSERT OR IGNORE INTO media_subtitles (
                        media_metadata_id,
                        path,
                        lang,
                        label
                    ) 
                    VALUES (?, ?, ?, ?)''', (
                    metadata_row_id, 
                    subs.get('path'),
                    subs.get('lang'),
                    subs.get('label')
                ))

        conn.commit()
        conn.close() 

    def insert_tv_series(self, item):
        # serie input: [{'title': 'Gen V', 'season': 1, 'episode': 1, 'path': 'D:/Lib/series/Gen V/Season 01/gen v s01e01.mkv', ...}]
        conn = self.db_connect()
        cursor = conn.cursor()    
        existing_metadata_item = cursor.execute("SELECT media_items_id FROM media_metadata WHERE file_hash_key = ?", (item["file_hash_key"],)).fetchone()
        if existing_metadata_item:
            return
        
        existing_item = cursor.execute("SELECT id FROM media_items WHERE title_hash_key = ?", (item["title_hash_key"],)).fetchone()
        if not existing_item:
            cursor.execute(''' 
                INSERT OR IGNORE INTO media_items (
                    category,
                    title,
                    release_date,
                    title_hash_key
                )
                VALUES (?, ?, ?, ?)
            ''', (
                item.get('category', None),
                item.get('title', None),
                item.get('release_date', None),
                item.get('title_hash_key', None)
            ))
            existing_item_id = cursor.lastrowid
        else:
            existing_item_id = existing_item[0]

        cursor.execute('''
            INSERT OR IGNORE INTO media_metadata (
                media_items_id,
                season,
                episode,
                resolution, 
                extension, 
                path, 
                file_size,
                duration,
                audio_codec,
                video_codec,
                bitrate,
                frame_rate,
                width,
                height,
                aspect_ratio,    
                file_hash_key,
                key_frame
            ) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (
            existing_item_id, 
            item.get('season', None),
            item.get('episode', None),
            item.get('resolution', None), 
            item.get('extension', None), 
            item.get('path', None), 
            item.get('file_size', None),
            item.get('duration', None),
            item.get('audio_codec', None),
            item.get('video_codec', None),
            item.get('bitrate', None),
            item.get('frame_rate', None),
            item.get('width', None),
            item.get('height', None),
            item.get('aspect_ratio', None),
            item.get('file_hash_key', None),
            item.get('key_frame', None)
        ))


        metadata_row_id = cursor.lastrowid
        subtitles = item.get('subtitles', [])
        if subtitles:
            for subs in subtitles:
                cursor.execute('''
                    INSERT OR IGNORE INTO media_subtitles (
                        media_metadata_id,
                        path,
                        lang,
                        label
                    ) 
                    VALUES (?, ?, ?, ?)''', (
                    metadata_row_id, 
                    subs.get('path'),
                    subs.get('lang'),
                    subs.get('label')
                ))


        existing_season = cursor.execute("SELECT id FROM tv_seasons WHERE media_items_id = ? AND season = ?", (existing_item_id, item["season"])).fetchone()
        if not existing_season: 
            cursor.execute('''
                INSERT OR IGNORE INTO tv_seasons (
                    media_items_id,
                    season
                ) 
                VALUES (?, ?)''', (
                existing_item_id, 
                item.get('season', None)
            ))


        existing_episode = cursor.execute("SELECT id FROM tv_episodes WHERE media_items_id = ? AND season = ? AND episode = ?", (existing_item_id, item["season"], item["episode"])).fetchone()
        if not existing_episode:
            cursor.execute('''
                    INSERT OR IGNORE INTO tv_episodes (
                        media_items_id,
                        season,
                        episode
                    ) 
                    VALUES (?, ?, ?)''', (
                    existing_item_id, 
                    item.get('season', None),
                    item.get('episode', None)
                ))

        conn.commit()
        conn.close()    
   
    def get_item_by_hash(self, hash_key):
        conn = self.db_connect()
        cursor = conn.cursor()
        item = cursor.execute("""
            SELECT mi.id, mi.category, mi.title, mi.release_date, mi.title_hash_key, mi.api_updated
            FROM media_items mi
            JOIN media_metadata mm ON mi.id = mm.media_items_id
            WHERE mm.file_hash_key = ?""", 
            (hash_key,)).fetchone()
        conn.close()
        return item
    
    def get_seasons_data(self, item_id):
        conn = self.db_connect()
        cursor = conn.cursor()
        seasons_data = cursor.execute("""
            SELECT s.media_items_id, s.season, s.latest_episode_entry
            FROM tv_seasons s
            JOIN media_items mm ON s.media_items_id = mm.id
            WHERE mm.id = ?""", 
            (item_id,)).fetchall()
        conn.close()
        return seasons_data
    
    def api_insert_metadata(self, item_data, item_id, category, year):
        conn = self.db_connect()
        cursor = conn.cursor()
        if item_data:
            cursor.execute('''
                UPDATE media_items
                SET 
                    tmdb_title = ?,
                    original_title = ?,
                    release_date = ?, 
                    description = ?, 
                    tagline = ?, 
                    origin_country = ?, 
                    spoken_languages = ?, 
                    studio = ?, 
                    production_countries = ?, 
                    popularity = ?, 
                    vote_average = ?, 
                    vote_count = ?, 
                    status = ?, 
                    poster_path = ?,
                    backdrop_path = ?, 
                    tmdb_id = ?, 
                    imdb_id = ?, 
                    api_updated = ?
                WHERE id = ?
            ''', (
                item_data.get('name'),
                item_data.get('original_title'),
                item_data.get('release_date', year) if category == 'movie' else item_data.get('first_air_date', ''),
                item_data.get('overview', ''),
                item_data.get('tagline', ''),
                ', '.join(item_data.get('origin_country', [])),  # Ensure it's a comma-separated string
                ', '.join([lang.get('name', '') for lang in item_data.get('spoken_languages', [])]),  
                ', '.join([studio.get('name', '') for studio in item_data.get('production_companies', [])]),  
                ', '.join([country.get('name', '') for country in item_data.get('production_countries', [])]),  
                item_data.get('popularity', ''),
                round(item_data.get('vote_average', 0.0), 1),
                item_data.get('vote_count', ''),
                item_data.get('status', ''),
                item_data.get('poster_path', ''),
                item_data.get('backdrop_path', ''),
                item_data.get('id', ''),
                item_data.get('imdb_id', ''),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                item_id
            ))

            # If it's a movie, insert movie details
            if category == 'movie':
                cursor.execute('''
                    INSERT OR IGNORE INTO movie_details (
                        media_items_id, 
                        budget, 
                        revenue, 
                        duration
                    )
                    VALUES (?, ?, ?, ?)''', (
                    item_id,
                    "{:,}".format(int(item_data.get('budget', 0) or 0)),
                    "{:,}".format(int(item_data.get('revenue', 0) or 0)),
                    item_data.get('runtime', 0)
                ))
                # Update if already exists
                cursor.execute('''
                    UPDATE movie_details 
                    SET budget = ?, revenue = ?, duration = ?
                    WHERE media_items_id = ?''', (
                    "{:,}".format(int(item_data.get('budget', 0) or 0)),
                    "{:,}".format(int(item_data.get('revenue', 0) or 0)),
                    item_data.get('runtime', 0),
                    item_id
                ))

            # If it's a TV series, insert TV series details
            if category == 'tv':
                next_episode_air_date = item_data.get('next_episode_to_air', None)
                if next_episode_air_date:
                    next_episode_air_date = next_episode_air_date.get('air_date', '')
                else:
                    next_episode_air_date = ''
                cursor.execute('''
                    INSERT OR IGNORE INTO tv_series_details (
                        media_items_id, 
                        created_by, 
                        first_air_date, 
                        last_air_date, 
                        next_episode_to_air, 
                        number_of_episodes, 
                        number_of_seasons, 
                        in_production
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', (
                    item_id,
                    json.dumps([creator['name'] for creator in item_data.get('created_by', [])]),  # Convert to JSON
                    item_data.get('first_air_date', ''),
                    item_data.get('last_air_date', ''),
                    next_episode_air_date,
                    item_data.get('number_of_episodes', 0),
                    item_data.get('number_of_seasons', 0),
                    int(item_data.get('in_production', False))
                ))
                # Update if already exists
                cursor.execute('''
                    UPDATE tv_series_details 
                    SET 
                        created_by = ?, 
                        first_air_date = ?, 
                        last_air_date = ?, 
                        next_episode_to_air = ?, 
                        number_of_episodes = ?, 
                        number_of_seasons = ?, 
                        in_production = ?
                    WHERE media_items_id = ?
                ''', (
                    json.dumps([creator['name'] for creator in item_data.get('created_by', [])]),  # Convert to JSON
                    item_data.get('first_air_date', ''),
                    item_data.get('last_air_date', ''),
                    next_episode_air_date,
                    item_data.get('number_of_episodes', 0),
                    item_data.get('number_of_seasons', 0),
                    int(item_data.get('in_production', False)),
                    item_id  # Must be last in the parameter list to match the WHERE clause
                ))

                # Process each season from API data
                for season in item_data['seasons']:
                    season_number = season['season_number']

                    # Check if the season already exists
                    cursor.execute('''
                        SELECT id FROM tv_seasons WHERE media_items_id = ? AND season = ?
                    ''', (item_id, season_number))
                    
                    existing_season = cursor.fetchone()

                    if existing_season:
                        # Update existing season
                        cursor.execute('''
                            UPDATE tv_seasons
                            SET air_date = ?, episode_count = ?, tmdb_id = ?, season_name = ?, 
                                overview = ?, season_poster_path = ?, latest_episode_entry = datetime('now')
                            WHERE media_items_id = ? AND season = ?
                        ''', (
                            season['air_date'],
                            season['episode_count'],
                            season['id'],
                            season['name'],
                            season['overview'],
                            season['poster_path'],
                            item_id,
                            season_number
                        ))
            # Handle genres
            for genre in item_data.get('genres', []) or []:
                genre_name = genre.get('name', '')

                # Insert each genre into the genres table (if not already exists)
                cursor.execute('''INSERT OR IGNORE INTO genres (genre) VALUES (?)''', (genre_name,))

                # Get the genre_id for the genre
                result = cursor.execute('''SELECT id FROM genres WHERE genre = ?''', (genre_name,)).fetchone()

                if result:  # Ensure result is not None
                    genre_id = result[0]
                    cursor.execute('''INSERT OR IGNORE INTO media_genres (media_items_id, genre_id) VALUES (?, ?)''', (item_id, genre_id))
                else:
                    print(f"[ tmdb.api warning ] Genre '{genre_name}' not found in database.")
        conn.commit()
        conn.close()

    @classmethod
    def fetch_item_data(cls, item_id):
        """
        Returns:
            object
        """
        with Database().db_connect() as conn:
            item_data = conn.execute('''
                SELECT * 
                FROM media_items 
                WHERE id = ?''', (item_id,)).fetchone()
            if not item_data:
                # print(f'[{Database().timestamp()}] [INFO    ] database.Database: no media item found with id: {item_id}')
                return
            # print(f"[{Database().timestamp()}] [INFO    ] database.Database: media item found: {item_data['title']}")

            # Fetch associated genres
            genres_data = conn.execute('''
                SELECT g.genre 
                FROM media_genres mg
                JOIN genres g ON mg.genre_id = g.id
                WHERE mg.media_items_id = ?''', (item_id,)).fetchall()
            genres = [genre['genre'] for genre in genres_data]

            # Movie details (if category is movie)
            movie_details = None
            if item_data['category'] == "movie":
                movie_details = conn.execute('''
                    SELECT * 
                    FROM movie_details 
                    WHERE media_items_id = ?''', (item_id,)).fetchone()
                movie_details = {key: movie_details[key] for key in movie_details.keys()}

            # TV series details (if category is series)
            tv_series_details = None
            if item_data['category'] == "series":
                tv_series_details = conn.execute('''
                    SELECT * 
                    FROM tv_series_details 
                    WHERE media_items_id = ?''', (item_id,)).fetchone()
                tv_series_details = {key: tv_series_details[key] for key in tv_series_details.keys()}

            # Fetch TV seasons (if it's a TV series)
            tv_seasons = []
            if item_data['category'] == 'series':
                seasons_data = conn.execute('''
                    SELECT * 
                    FROM tv_seasons 
                    WHERE media_items_id = ?''', (item_id,)).fetchall()
                for season in seasons_data:
                    tv_seasons.append({
                        'season': season['season'],
                        'air_date': season['air_date'],
                        'episode_count': season['episode_count'],
                        'season_name': season['season_name'],
                        'overview': season['overview'],
                        'season_poster_path': season['season_poster_path'],
                        'latest_episode_entry': season['latest_episode_entry']
                    })

            # Fetch media metadata (both for movies and episodes)
            media_metadata = []
            metadata_data = conn.execute('''
                SELECT * 
                FROM media_metadata 
                WHERE media_items_id = ?''', (item_id,)).fetchall()
    
            for metadata in metadata_data:
                # grab subs for the corresponding metadata id from subtitles table
                subtitles_list = conn.execute('''SELECT * FROM media_subtitles WHERE media_metadata_id = ?''', (metadata['id'],)).fetchall()
                subtitles = [dict(row) for row in subtitles_list]
                # dict
                media_metadata.append({
                    'id': metadata['id'],
                    'media_items_id': metadata['media_items_id'],
                    'season': metadata['season'],
                    'episode': metadata['episode'],
                    'resolution': metadata['resolution'],
                    'extension': metadata['extension'],
                    'path': metadata['path'],
                    'file_size': metadata['file_size'],
                    'duration': metadata['duration'],
                    'audio_codec': metadata['audio_codec'],
                    'video_codec': metadata['video_codec'],
                    'bitrate': metadata['bitrate'],
                    'frame_rate': metadata['frame_rate'],
                    'width': metadata['width'],
                    'height': metadata['height'],
                    'aspect_ratio': metadata['aspect_ratio'],
                    'file_hash_key': metadata['file_hash_key'],
                    'key_frame': metadata['key_frame'],
                    'subtitles': subtitles
                })

            return cls(
                **item_data,
                movie_details=movie_details or {},
                tv_series_details=tv_series_details or {},
                genres=genres or [],
                tv_seasons=sorted(tv_seasons or [], key=lambda x: x['season']),  # Sort by season numbers before passing
                media_metadata=media_metadata or []
            )

    @classmethod
    def fetch_item(cls, item_id):
        """
        Fetches data only from main table media_items

        Returns:
            object
        """
        with Database().db_connect() as conn:
            item_data = conn.execute('''
                SELECT * 
                FROM media_items 
                WHERE id = ?''', (item_id,)).fetchone()
            return cls(**item_data) if item_data else None

    @classmethod
    def fetch_items(cls):
        """
        Returns:
            list of objects data
        """
        with Database().db_connect() as conn:
            items_data = conn.execute('''SELECT * FROM media_items''').fetchall()
            return [cls(**item) for item in items_data] if items_data else []

    @classmethod
    def fetch_item_metadata(cls, metadata_id):
        """
        Fetches row id data from metadata table

        Returns:
            object
        """
        with Database().db_connect() as conn:
            item_data = conn.execute('''
                SELECT * 
                FROM media_metadata
                WHERE id = ?''', (metadata_id,)).fetchone()
            if not item_data:
                return None
            
            subtitles_list = conn.execute('''SELECT * FROM media_subtitles WHERE media_metadata_id = ?''', (metadata_id,)).fetchall()
            subtitles = [dict(row) for row in subtitles_list]
            return cls(**item_data, subtitles=subtitles)       

    @classmethod
    def fetch_items_from_metadata(cls, item_id):
        """
        fetch all from metadata table via item id

        Returns:
            object
        """
        with Database().db_connect() as conn:
            items_data = conn.execute('''
                SELECT * 
                FROM media_metadata
                WHERE media_items_id = ?''', (item_id,)).fetchall()
            
            return [cls(**item) for item in items_data] if items_data else []      


    @classmethod
    def fetch_items_with_limit(cls, limit, category=None):
        """
        Fetch a limited set of media items, up to a specified limit.

        Returns:
            object
        """
        with Database().db_connect() as conn:
            if category:
                media_items = conn.execute('SELECT * FROM media_items WHERE category = ? ORDER BY entry_created DESC LIMIT ?', (category, limit,)).fetchall()
            else:
                media_items = conn.execute('SELECT * FROM media_items ORDER BY entry_created DESC LIMIT ?', (limit,)).fetchall()
            
            items = []
            for item in media_items:
                media_item = cls(**item)
                # Get genres for this media item (joining media_genres and genres)
                genres_data = conn.execute('''
                    SELECT g.genre 
                    FROM media_genres mg
                    JOIN genres g ON mg.genre_id = g.id
                    WHERE mg.media_items_id = ?''', (media_item.id,)).fetchall()
                genres = [genre['genre'] for genre in genres_data]
                media_item.genres = genres

                items.append(media_item)
            return items

    @classmethod
    def fetch_user_data(cls, user_id):
        """
        Returns:
            object
        """
        with Database().db_connect() as conn:
            user_data = conn.execute('''SELECT * FROM user_profile WHERE user_id = ?''', (user_id,)).fetchall()
        return [cls(**row) for row in user_data] if user_data else []

    def update_user_data(self, user_id, item_id, data):
        conn = self.db_connect()
        cursor = conn.cursor()

        watchlistStatus = data.get('watchlistStatus', None)
        if watchlistStatus in (0,1):
            cursor.execute('''
                UPDATE user_profile
                SET watchlist = ? WHERE user_id = ? AND media_items_id = ?
            ''', (watchlistStatus, user_id, item_id))

            # Check if any rows were updated
            if cursor.rowcount == 0:
                # If no row was updated, insert a new row with the watchlist status
                cursor.execute('''
                    INSERT INTO user_profile (user_id, media_items_id, watchlist)
                    VALUES (?, ?, ?)
                ''', (user_id, item_id, watchlistStatus))

        rating = data.get('rating', None)
        if rating in (1,2,3,4,5):
            cursor.execute('''
                UPDATE user_profile
                SET rating = ? WHERE user_id = ? AND media_items_id = ?
            ''', (rating, user_id, item_id))

            # Check if any rows were updated
            if cursor.rowcount == 0:
                # If no row was updated, insert a new row with the rating
                cursor.execute('''
                    INSERT INTO user_profile (user_id, media_items_id, rating)
                    VALUES (?, ?, ?)
                ''', (user_id, item_id, rating))

        conn.commit()
        conn.close()

    @classmethod
    def fetch_user_data_details(cls, user_id):
        """
        Returns:
            object
        """
        with Database().db_connect() as conn:
            user_data = conn.execute('''SELECT * FROM user_profile_items WHERE user_id = ?''', (user_id,)).fetchall()
        return [cls(**row) for row in user_data] if user_data else []

    def update_user_data_details(self, user_id, item_id, metadata_id, data):
        conn = self.db_connect()
        cursor = conn.cursor()

        watched = data.get('watchedStatus', None)
        if watched in (0,1):
            cursor.execute('''
                UPDATE user_profile_items
                SET watched = ? WHERE user_id = ? AND media_metadata_id = ?
            ''', (watched, user_id, metadata_id))

            # Check if any rows were updated
            if cursor.rowcount == 0:
                # If no row was updated, insert a new row with the watchlist status
                cursor.execute('''
                    INSERT INTO user_profile_items (user_id, media_items_id, media_metadata_id, watched)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, item_id, metadata_id, watched))

        current_time = data.get('currentTime', None)
        if current_time:
            cursor.execute('''
                UPDATE user_profile_items
                SET current_time = ? WHERE user_id = ? AND media_metadata_id = ?
            ''', (current_time, user_id, metadata_id))

            # Check if any rows were updated
            if cursor.rowcount == 0:
                # If no row was updated, insert a new row with the watchlist status
                cursor.execute('''
                    INSERT INTO user_profile_items (user_id, media_items_id, media_metadata_id, current_time)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, item_id, metadata_id, current_time))

        conn.commit()
        conn.close()

    def search(self, input_str):
        """
        Returns:
            dictionary
        """
        conn = self.db_connect()
        cursor = conn.cursor()
        items = cursor.execute("SELECT * FROM media_items WHERE title LIKE ?", ('%' + input_str + '%',)).fetchall()
        items_list = []
        for item in items:
            media_item = dict(item)
            # Get genres for this media item (joining media_genres and genres)
            genres_data = conn.execute('''
                SELECT g.genre 
                FROM media_genres mg
                JOIN genres g ON mg.genre_id = g.id
                WHERE mg.media_items_id = ?''', (media_item['id'],)).fetchall()
            genres = [genre['genre'] for genre in genres_data]
            media_item["genres"] = genres
            items_list.append(media_item)
        conn.close()
        return items_list

    def get_total_media_count(self, category=None):
        with self.db_connect() as conn:
            if category:
                # If category is provided, filter by category
                query = 'SELECT COUNT(*) FROM media_items WHERE category = ?'
                result = conn.execute(query, (category,)).fetchone()
            else:
                # If no category is provided, count all media items
                query = 'SELECT COUNT(*) FROM media_items'
                result = conn.execute(query).fetchone()

        return result[0] if result else 0

    @classmethod
    def fetch_items_with_pagination(cls, limit, offset, type=1):
        with Database().db_connect() as conn:
            if type == 1: # all sorted by most recent
                media_items = conn.execute(
                    'SELECT * '
                    'FROM media_items ORDER BY entry_created DESC LIMIT ? OFFSET ?',
                    (limit, offset)
                ).fetchall()
                items = []
                for item in media_items:
                    media_item = cls(**dict(item))

                    genres_data = conn.execute('''
                        SELECT g.genre 
                        FROM media_genres mg
                        JOIN genres g ON mg.genre_id = g.id
                        WHERE mg.media_items_id = ?''', (media_item.id,)).fetchall()
                    genres = [genre['genre'] for genre in genres_data]
                    media_item.genres = genres
                    items.append(media_item)   

            if type == 2: # all movies only sorted by title a-z
                media_items = conn.execute(
                    'SELECT * '
                    'FROM media_items WHERE category = "movie" ORDER BY title DESC LIMIT ? OFFSET ?',
                    (limit, offset)
                ).fetchall()
                items = []
                for item in media_items:
                    media_item = cls(**dict(item))

                    genres_data = conn.execute('''
                        SELECT g.genre 
                        FROM media_genres mg
                        JOIN genres g ON mg.genre_id = g.id
                        WHERE mg.media_items_id = ?''', (media_item.id,)).fetchall()
                    genres = [genre['genre'] for genre in genres_data]
                    media_item.genres = genres
                    items.append(media_item) 

            if type == 3: # all series only sorted by title a-z
                media_items = conn.execute(
                    'SELECT * '
                    'FROM media_items WHERE category = "series" ORDER BY title DESC LIMIT ? OFFSET ?',
                    (limit, offset)
                ).fetchall()
                items = []
                for item in media_items:
                    media_item = cls(**dict(item))

                    genres_data = conn.execute('''
                        SELECT g.genre 
                        FROM media_genres mg
                        JOIN genres g ON mg.genre_id = g.id
                        WHERE mg.media_items_id = ?''', (media_item.id,)).fetchall()
                    genres = [genre['genre'] for genre in genres_data]
                    media_item.genres = genres
                    items.append(media_item) 

        return items

    @staticmethod
    def swap_title(item):
        """
        Swaps title from user's folder name to official from tmdb.

        Parameters:
            item (object):
        
        Returns:
            item (object):
        """
        if item.tmdb_title:
            item.title = item.tmdb_title
        elif item.original_title:
            item.title = item.original_title

        if item.poster_path:
            path = f"static/images/posters/w400_{item.poster_path.lstrip('/')}"
            if not os.path.exists(path):
                item.poster_path = ''

        return item
    
    @staticmethod
    def swap_title_dict(item: dict) -> dict:
        """
        Swaps title from user's folder name to official from tmdb.

        Parameters:
            item (dict):
        
        Returns:
            item (dict):
        """
        if item.get('tmdb_title'):
            item['title'] = item.get('tmdb_title')
        elif item.get('original_title'):
            item['title'] = item.get('original_title')

        #temporary poster path check solution
        if item.get('poster_path'):
            path = f"static/images/posters/w400_{item.get('poster_path').lstrip('/')}"
            if not os.path.exists(path):
                item['poster_path'] = ''
        return item

    def __repr__(self):
        kwargs_repr = ",\n".join(f"{key}={repr(value)}" for key, value in self.__dict__.items() if key != "localdb")
        return f"{self.__class__.__name__}({kwargs_repr})"
