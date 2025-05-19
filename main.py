import os
import re
import json
import time
import socket
import hashlib
import datetime
import schedule
import threading
import subprocess

from multiprocessing import Process
from datetime import datetime
from waitress import serve
from pprint import pprint
from flask import Flask, request, render_template, send_from_directory, jsonify

from queue_manager import start_worker_queue, stop_worker, add_to_queue
from database import Database
from api import tmdb



class DirectoryManager:
    def __init__(self):
        self.PATH = 'static/settings.json'
        self.METADATA = 'api_metadata'

    def create_settings(self):
        if not os.path.exists(self.PATH):
            with open(self.PATH, 'w', encoding="utf-8") as f:
                json.dump({"libraries": {"series": [], "movies": []}, "api_updates_auto": 0}, f, indent=4)

        # if not os.path.exists(self.METADATA):
        #     os.makedirs(self.METADATA)

    def load_paths(self):
        try:
            with open(self.PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {"libraries": {}}



class LibraryManager:
    def __init__(self):
        self.SETTINGS = DirectoryManager().load_paths()

    def timestamp(self):
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def scanner(self, path):
        items = []
        for root, _, files in os.walk(path):
            for file in files:
                if not file.endswith((".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv", ".webm")):
                    continue
                full_path = os.path.join(root, file)
                norm_path = os.path.normpath(full_path)
                items.append(norm_path)
                
        return items   

    def initialize_scanner(self):
        if not self.SETTINGS:
            return
        libraries = self.SETTINGS.get("libraries", {})
        categories = libraries.keys()
        all_items = {}
        for category in categories:
            paths = libraries.get(category)
            category_results = []
            for path in paths:
                results = self.scanner(os.path.normpath(path))
                if results:
                    category_results.extend(results)

            if category_results:
                all_items[category] = category_results
            else:
                all_items[category] = []

        return all_items

    def verify_library_integrity(self):
        try:
            items = self.initialize_scanner()
            localdb_hash_list = Database().get_hash_list()
            local_hash_list = []
            new_entries_list = []
            missing_entries_list = []
            if items:
                for category, items in items.items():
                    for path in items:
                        hash = MetadataExtract().get_file_hash(path)
                        local_hash_list.append(hash)
                        if hash in localdb_hash_list:
                            continue
                        new_entries_list.append((category, path))
            
                for hash in localdb_hash_list:
                    if hash not in local_hash_list:
                        missing_entries_list.append(hash)

            return new_entries_list, missing_entries_list
        except Exception as e:
            print('failed. ->', e)
            return [], []

    def check_entries_compatibility(self, items):
        compatible_files = []
        incompatible_files = []
        for file in items:
            category, path = file
            results = MetadataExtract().get_video_metadata(path)
            video_codec = results.get('video_codec')
            audio_codec = results.get('audio_codec')
            extension = os.path.splitext(path)[1].replace(".","")

            if not (video_codec == 'h264' and audio_codec == 'aac' and extension == 'mp4'):
                incompatible_files.append((category, path))
                continue
            compatible_files.append((category, path))
        

        return compatible_files, incompatible_files

    def remove_missing(self, items):
        add_to_queue(lambda: Database().remove_from_metadata_table(items))

    def process_compatible(self, compatible_files):
        movie_items_list = []
        series_items_list = []

        # first, extract and collect all items data
        for file in compatible_files:
            category, path = file

            subtitles = MetadataExtract().get_subtitles(path)
            if category == 'movies':
                item_data = MetadataExtract().get_movie_metadata(path)
                if subtitles:
                    item_data['subtitles'] = subtitles
                movie_items_list.append(item_data)
            if category == 'series':
                item_data = MetadataExtract().get_series_metadata(path)
                if subtitles:
                    item_data['subtitles'] = subtitles
                series_items_list.append(item_data)

        hash_list = []
        # second, insert to database movies and series data   and append it's hash key to a list  
        for item_data in movie_items_list:
            add_to_queue(lambda item_data=item_data: Database().insert_movie(item_data))
            
            hash_key = item_data.get('file_hash_key')
            hash_list.append(hash_key)
        for item_data in series_items_list:
            add_to_queue(lambda item_data=item_data: Database().insert_tv_series(item_data))
            
            hash_key = item_data.get('file_hash_key')
            hash_list.append(hash_key)

        # third, loop thru hash list and api request additioanl data 
        for hash_key in hash_list:
            add_to_queue(lambda hash_key=hash_key: tmdb().tmdb_api(hash_key))     

    def process_incompatible(self, incompatible_files):
        movie_items_list = []
        series_items_list = []

        # first, extract and collect all items data
        for file in incompatible_files:
            category, path = file
            subtitles = MetadataExtract().get_subtitles(path) # extarct subs before transcode // subs lost on transcode
            path = Transcode().transcode_to_mp4_264_aac(path)
            if category == 'movies':
                item_data = MetadataExtract().get_movie_metadata(path)
                if subtitles:
                    item_data['subtitles'] = subtitles
                movie_items_list.append(item_data)
            if category == 'series':
                item_data = MetadataExtract().get_series_metadata(path)
                if subtitles:
                    item_data['subtitles'] = subtitles
                series_items_list.append(item_data)

        hash_list = []
        # second, insert to database movies and series data   and append it's hash key to a list  
        for item_data in movie_items_list:
            add_to_queue(lambda item_data=item_data: Database().insert_movie(item_data))
            
            hash_key = item_data.get('file_hash_key')
            hash_list.append(hash_key)
        for item_data in series_items_list:
            add_to_queue(lambda item_data=item_data: Database().insert_tv_series(item_data))
            
            hash_key = item_data.get('file_hash_key')
            hash_list.append(hash_key)

        # third, loop thru hash list and api request additioanl data 
        for hash_key in hash_list:
            add_to_queue(lambda hash_key=hash_key: tmdb().tmdb_api(hash_key))
            
    def verify(self):
        print(f'[{self.timestamp()}] [INFO    ] main.LibraryManager: Initializing library verification...')
        new_entries_list, missing_entries_list = self.verify_library_integrity()
        
        if missing_entries_list:
            print(f'[{self.timestamp()}] [INFO    ] main.LibraryManager: Detected {len(missing_entries_list)} missing entries. Removing...', end=' ')
            self.remove_missing(missing_entries_list)
            print('completed.')

        if new_entries_list:
            print(f'[{self.timestamp()}] [INFO    ] main.LibraryManager: {len(new_entries_list)} new entries detected. Checking compatibility...')
            compatible_files, incompatible_files = self.check_entries_compatibility(new_entries_list)
            
            if compatible_files:
                print(f'[{self.timestamp()}] [INFO    ] main.LibraryManager: Processing {len(compatible_files)} compatible files...', end=' ')
                self.process_compatible(compatible_files)
                print(f'completed.')

            if incompatible_files:
                print(f'[{self.timestamp()}] [INFO    ] main.LibraryManager: Processing {len(incompatible_files)} incompatible files...')
                self.process_incompatible(incompatible_files)
                print(f'[{self.timestamp()}] [INFO    ] main.LibraryManager: Incompatible files processing completed.')

        print(f'[{self.timestamp()}] [INFO    ] main.LibraryManager: Library verification completed.')
 


class MetadataExtract:
    def timestamp(self):
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def get_file_hash(self, path, portion_size=2 * 1024 * 1024):
        hash_func = hashlib.md5()
        with open(path, 'rb') as f:
            chunk = f.read(portion_size)
            hash_func.update(chunk)
        return hash_func.hexdigest()
    
    def get_video_metadata(self, video_path):
        ffprobe_path = os.path.join(os.getcwd(), 'ffprobe.exe') 

        # Check if ffprobe binary exists
        if not os.path.exists(ffprobe_path):
            raise FileNotFoundError(f'[{self.timestamp()}] [INFO    ] main.metadataextract: ffprobe binary not found.')
        
        cmd = [
            ffprobe_path,
            '-v', 'error', 
            '-show_entries', 'format=duration,bit_rate', 
            '-show_entries', 'stream=codec_name,width,height,avg_frame_rate,codec_type', 
            '-of', 'json', 
            video_path
        ]

        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        metadata = json.loads(result.stdout.decode('utf-8'))
        
        # Extract general metadata
        duration = metadata.get('format', {}).get('duration', None)
        bitrate = metadata.get('format', {}).get('bit_rate', None)
        
        # Extract video stream metadata
        video_stream = next((stream for stream in metadata.get('streams', []) if stream['codec_type'] == 'video'), None)
        width = video_stream.get('width', None) if video_stream else None
        height = video_stream.get('height', None) if video_stream else None
        frame_rate = video_stream.get('avg_frame_rate', None) if video_stream else None
        codec_video = video_stream.get('codec_name', None) if video_stream else None
        
        # Extract audio stream metadata
        audio_stream = next((stream for stream in metadata.get('streams', []) if stream['codec_type'] == 'audio'), None)
        codec_audio = audio_stream.get('codec_name', None) if audio_stream else None
        
        # Calculate Aspect Ratio (Width / Height)
        aspect_ratio = None
        if width and height:
            aspect_ratio = round(width / height, 2)
        
        # If frame rate exists, convert it to float
        frame_rate_float = None
        if frame_rate:
            frame_rate_float = self.frame_rate_to_float(frame_rate)

        duration_ = None
        if duration:
            duration_ = self.convert_duration(float(duration))

        # Return the video metadata in the desired format
        return {
            'resolution': f"{width}x{height}",
            'duration': duration_,
            'audio_codec': codec_audio,
            'video_codec': codec_video,
            'bitrate': "{:.2f} kbps".format(self.bitrate_to_kbps(bitrate)),
            'frame_rate': "{:.3f}".format(frame_rate_float) if frame_rate_float else None,
            'width': width,
            'height': height,
            'aspect_ratio': aspect_ratio,
        }
    
    def frame_rate_to_float(self, frame_rate):
        # Assuming frame_rate is in the form of "num/den" like "25/1"
        try:
            numerator, denominator = map(int, frame_rate.split('/'))
            return numerator / denominator
        except ValueError:
            return float(frame_rate)  # Fallback if it's already a decimal value
        
    def bitrate_to_kbps(self, bitrate):
        # Assuming bitrate is in bps (bits per second)
        try:
            bitrate = int(bitrate)
            return bitrate / 1000  # Convert to kbps
        except (ValueError, TypeError):
            return 0  # Return 0 if the bitrate is invalid
        
    def convert_duration(self, duration):
        # Assuming duration is in seconds and converting it to HH:MM:SS format
        hours = int(duration // 3600)
        minutes = int((duration % 3600) // 60)
        seconds = int(duration % 60)
        return f'{hours:02}:{minutes:02}:{seconds:02}'  
    
    def time_to_seconds(self, time_str):
        hours, minutes, seconds = map(int, time_str.split(':'))
        return hours * 3600 + minutes * 60 + seconds

    def ffmpeg_key_frame(self, video_path, hash_key, duration):
        ffmpeg_path = os.path.join(os.getcwd(), 'ffmpeg.exe') 

        SAVE_FOLDER = "static/images/keyFrames/"
        output_name = f'keyframe_{hash_key}.jpg'
        output_path = os.path.join(SAVE_FOLDER, output_name)

        if os.path.exists(output_path):
            return output_name

        # Check if ffprobe binary exists
        if not os.path.exists(ffmpeg_path):
            raise FileNotFoundError("ffmpeg binary not found. Please ensure ffmpeg is bundled with the application.")
        
        # Ensure the folder exists
        os.makedirs(SAVE_FOLDER, exist_ok=True)

        if not duration:
            return None
        
        duration_seconds = self.time_to_seconds(duration)
        offset_seconds = duration_seconds * 1/11
        
        # Convert the offset back to HH:MM:SS format
        hours = offset_seconds // 3600
        minutes = (offset_seconds % 3600) // 60
        seconds = int(offset_seconds % 60)
        offset_time = f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"
        

        cmd = [
            ffmpeg_path,
            '-ss', offset_time, 
            '-i', video_path,
            '-frames:v', '1',
            '-vf', "scale='if(gt(a,16/9),-1,1280*1.35)':'if(gt(a,16/9),720*1.35,-1)',crop=1280:720",
            output_path
        ]
        # 'scale=1280:720:force_original_aspect_ratio=increase, crop=iw*0.75:ih*0.75'
        subprocess.run(
            cmd, 
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            encoding='utf-8', errors='replace'
        )

        if output_name:
            return output_name
        else:
            return None  

    def get_movie_metadata(self, path):
        # file output: Example.Media.2024.1080p.WEBRip.1400MB.DD5.1.x264-GalaxyRG.mp4
        # root output: D:/Lib/movies\Example Media\
        # media_file_path output: D:/Lib/movies/Example Media/Example.Media.2024.1080p.WEBRip.1400MB.DD5.1.x264-GalaxyRG.mp4 
        file = os.path.basename(path)
        root = os.path.dirname(path)

        results = self.get_video_metadata(path)
        file_hash_key = self.get_file_hash(path)

        movie_entry = {
            'category': 'movie',
            'title': self.get_title(file),
            'title_hash_key': self.get_title_hash(file, 'movie'),
            'release_date': self.get_release_date(file, root),
            'extension': os.path.splitext(file)[1].replace(".",""),
            'path': path,
            'file_size': os.path.getsize(path),
            'file_hash_key': file_hash_key,
            # video_metadata
            'resolution': results.get('resolution'),
            'duration': results.get('duration'),
            'audio_codec': results.get('audio_codec'),
            'video_codec': results.get('video_codec'),
            'bitrate': results.get('bitrate'),
            'frame_rate': results.get('frame_rate'),
            'width': results.get('width'),
            'height': results.get('height'),
            'aspect_ratio': results.get('aspect_ratio'),
            'key_frame': self.ffmpeg_key_frame(path, file_hash_key, results.get('duration'))
        }
        return movie_entry

    def get_title(self, file):
        # file output: Example.Media.2024.1080p.WEBRip.1400MB.DD5.1.x264-GalaxyRG.mp4
        pattern_title = r'^(?P<title>.+?)\.*(\b\d{4}\b|\d{3,4}p|mp4|mkv|avi|mov|flv|wmv|webm)'
        file = file.replace("(", "").replace(")", "").replace(".", " ").replace('_', ' ')
        # Collapse multiple spaces into one
        file = re.sub(r'\s+', ' ', file).strip()  # Replaces multiple spaces with a single space
        file_title = re.match(pattern_title, file)
        if file_title:
            return file_title.group('title').strip()
        return 'Unknown'

    def get_title_hash(self, file, media_type):
        unique_title = media_type + file
        hash_func = hashlib.md5()
        hash_func.update(unique_title.encode('utf-8'))
        return hash_func.hexdigest()

    def get_release_date(self, file, root):
        pattern = r'(?P<year>\b\d{4}\b)'
        year_match = re.search(pattern, file)
        if year_match:
            return year_match.group('year')
        
        if not year_match:
            year_match = re.search(pattern, root)
            if year_match:
                return year_match.group('year')
            return None

    def get_series_metadata(self, path):
        file = os.path.basename(path)
        root = os.path.dirname(path)        
        
        results = self.get_video_metadata(path)
        file_hash_key = self.get_file_hash(path)

        # series_title, season, episode = get_series_info(file)  # output: str The Simpsons, int 1, int 20
        series_title = self.get_series_title(path)
        season = self.get_series_season(file, root)
        episode = self.get_series_episode(file)

        # Find or create the series entry
        series_metadata = []
        series_entry = next((s for s in series_metadata if s["title"] == series_title), None)

        if not series_entry:
            series_entry = {
                'category': 'series',
                'title': series_title,
                'season': season,
                'episode': episode,
                'title_hash_key': self.get_title_hash(series_title, 'series'), 
                'release_date': self.get_release_date(file, root),
                'extension': os.path.splitext(file)[1].replace(".",""),
                'path': path,
                'file_size': os.path.getsize(path),
                'file_hash_key': file_hash_key,
                # video_metadata
                'resolution': results.get('resolution'),
                'duration': results.get('duration'),
                'audio_codec': results.get('audio_codec'),
                'video_codec': results.get('video_codec'),
                'bitrate': results.get('bitrate'),
                'frame_rate': results.get('frame_rate'),
                'width': results.get('width'),
                'height': results.get('height'),
                'aspect_ratio': results.get('aspect_ratio'),
                'key_frame': self.ffmpeg_key_frame(path, file_hash_key, results.get('duration'))
            }

            series_metadata.append(series_entry)
        else:
            # If the series already exists, update the existing entry with new season/episode data
            series_entry['season'] = season
            series_entry['episode'] = episode
            series_entry['path'] = path
            
        return series_metadata[0] if series_metadata else {}

    def get_series_title(self, path: str) -> str:
        """
        Get series title from it's folder name. Backup name from .mp4 file.

        Parameters:
            Path (str): should be already norm before passing it to this fun()

        Returns:
            series_title (str):
        """
        try:
            paths = DirectoryManager().load_paths()
        except Exception as e:
            print('get_series_title() --> issue with loading paths', e)
            return 'Unknown'
        
        series_library_paths = paths.get("libraries", {}).get('series', [])
        if not series_library_paths:
            return 'Unknown'

        # check in which series library path the title is located
        series_library: str = None
        for lib_path in series_library_paths:
            if not path.startswith(os.path.normpath(lib_path)):
                continue
            series_library = os.path.normpath(lib_path)
        if not series_library:
            return 'Unknown'

        relpath = os.path.relpath(path, series_library)    # relpath = r"Andor Season 2\andor.s02e01.1080p.web.h264-successfulcrab[EZTVx.to].mp4"
        relpath_list: list = relpath.split(os.sep)

        if not relpath_list[0]:
            series_folder_name = relpath # means file has no folder, its in main library dir
        else: 
            series_folder_name = relpath_list[0] # file's folder

        #   CLEAN UP
        series_folder_name = series_folder_name.lower()
        # Remove any urls
        series_folder_name = re.sub(r'https?://\S+|www\.\S+', '', series_folder_name).strip()
        series_folder_name = series_folder_name.replace("(", "").replace(")", "").replace(".", " ").replace('_', ' ').replace("-", " ")
        # Match pattern to extract title
        pattern = r"^(?P<title>.+?)\.*((\sseason\s\d{1,2})|(\ss\d{1,2})|(2160p|1080p|720p|480p|360p)|(\s\b\d{4}\b)|\s(mp4|mkv|avi|mov|flv|wmv|webm))"
        match = re.match(pattern, series_folder_name)
        if match:
            series_title = match.group('title').strip().title()
            return series_title
        
        extensions = ['mp4', 'mkv', 'avi', 'mov', 'flv', 'wmv', 'webm']
        for ext in extensions:
            if not series_folder_name.endswith(ext):
                series_title = series_folder_name.strip().title()
                return series_title
        
        return 'Unknown'

    def get_series_season(self, file: str, root: str) -> int:
        pattern = r'([sS])(?P<season>\d{1,3})'    # Match: S01
        
        series_season = re.search(pattern, file)
        if series_season:
            season = int(series_season.group('season'))
            return season
        return 999

    def get_series_episode(self, file: str) -> int:
        pattern = r'(?:[sS]\d{1,3}[eE]|[eE]|part|episode)\s?(?P<episode>\d{1,3})'

        series_episode = re.search(pattern, file.lower())
        if series_episode:
            episode = int(series_episode.group('episode'))
            return episode
        
        pattern_special = r'(?P<episode>\d{1,3})'
        name = os.path.splitext(file)[0]

        series_episode = re.search(pattern_special, name)
        episode = int(series_episode.group('episode'))
        if episode:
            return episode
        return 999

    def get_subtitles(self, path: str):
            vtt, srt = self.find_existing_subtitles(path)
            if vtt:
                vtt = self.norm_sub_data(vtt)
                return vtt
            if srt:
                vtt = self.convert_to_vtt(srt)
                vtt = self.norm_sub_data(vtt)
                return vtt
            
            # subs files not found, try to extract from video file container
            vtt = self.extract_subtitles(path)
            if vtt:
                return vtt
            return []

    def find_existing_subtitles(self, path: str) -> list[dict]:
            filename = os.path.splitext(os.path.basename(path))[0] # filename without .mp4 extension
            dir_path = os.path.dirname(path) # folder where the .mp4 is
            vtt = []
            srt = []
            # go thru all files in the path dir
            for root, folders, files in os.walk(dir_path):
                # check if there are subs in the whole dir that have the same name as video file
                for file in files:
                    if file.endswith(".vtt") and os.path.splitext(file)[0] == filename:
                        sub_path = os.path.normpath(os.path.join(root, file))
                        vtt.append({'path': sub_path})
                    if file.endswith(".srt") and os.path.splitext(file)[0] == filename:
                        sub_path = os.path.normpath(os.path.join(root, file))
                        srt.append({'path': sub_path})

                # go thru all subfolders in that dir
                for folder in folders:
                    # check for any subfolders within that dir that have folder name same as video file and grab all subs from that folder
                    if folder == filename:
                        folder_path = os.path.join(root, folder)
                        for file in os.listdir(folder_path):
                            if file.endswith(".vtt"):
                                sub_path = os.path.normpath(os.path.join(folder_path, file))
                                vtt.append({'path': sub_path})
                            if file.endswith(".srt"):
                                sub_path = os.path.normpath(os.path.join(folder_path, file))
                                srt.append({'path': sub_path})

                    # check for "subs" folder within dir and grab all the subs from that folder
                    if folder == 'subs':
                        folder_path = os.path.join(root, folder)
                        for file in os.listdir(folder_path):
                            if file.endswith(".vtt"):
                                sub_path = os.path.normpath(os.path.join(folder_path, file))
                                vtt.append({'path': sub_path})
                            if file.endswith(".srt"):
                                sub_path = os.path.normpath(os.path.join(folder_path, file))
                                srt.append({'path': sub_path})
            return vtt, srt                   

    def convert_to_vtt(self, srt: list[dict]) -> list[dict]:
        vtt = []
        for subtitles in srt:
            path = subtitles.get('path')
            new_vtt_path = f'{os.path.splitext(path)[0]}.vtt' # remove extension .srt and add .vtt extensions (dont use .replace)

            with open(path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            with open(new_vtt_path, 'w', encoding='utf-8') as f:
                f.write("WEBVTT\n\n")
                for line in lines:
                    line = line.replace(',', '.')
                    f.write(line)

            vtt.append({'path': new_vtt_path})

            # # Delete the original SRT file after conversion
            # if os.path.exists(path):
            #     os.remove(path)
        return vtt

    def norm_sub_data(self, subtitles: list[dict]) -> list[dict]:
        ALIAS_MAP = {
            "eng": "en",
            "spa": "es",
            "esp": "es",
            "fre": "fr",
            "fra": "fr",
            "ger": "de",
            "deu": "de",
            "ita": "it",
            "pol": "pl",
            "por": "pt",
            "rus": "ru",
            "рус": "ru",
            "jpn": "ja",
            "jap": "ja",
            "日本語": "ja",
            "kor": "ko",
            "한국어": "ko",
            "chi": "zh",
            "dut": "nl",
            "ned": "nl",
            "cze": "cs",
            "češ": "cs",
            "dan": "da",
            "hun": "hu",
            "mag": "hu",
            "tur": "tr",
            "tür": "tr",
            "ara": "ar",
            "heb": "he",
            "fas": "fa",
            "hin": "hi",
            "ben": "bn",
            "tam": "ta",
            "tha": "th",
            "ไทย": "th",
            "vie": "vi",
            "tiế": "vi",
            "gre": "el",
            "ελλ": "el",
            "suo": "fi",
            "fin": "fi",
            "nor": "no",
            "rom": "ro",
            "ron": "ro",
            "slo": "sk",
            "slk": "sk",
            "sve": "sv",
            "swe": "sv"
        }

        LANGUAGE_MAP = {
            "en": "English",
            "es": "Spanish",
            "fr": "French",
            "de": "German",
            "it": "Italian",
            "pl": "Polish",
            "pt": "Portuguese",
            "ru": "Russian",
            "ja": "Japanese",
            "ko": "Korean",
            "zh": "Chinese",
            "nl": "Dutch",
            "da": "Danish",
            "hu": "Hungarian",
            "cs": "Czech",
            "tr": "Turkish",
            "ar": "Arabic",
            "he": "Hebrew",
            "fa": "Persian",
            "hi": "Hindi",
            "bn": "Bengali",
            "ta": "Tamil",
            "th": "Thai",
            "vi": "Vietnamese",
            "fi": "Finnish",
            "el": "Greek",
            "no": "Norwegian",
            "ro": "Romanian",
            "sk": "Slovak",
            "sv": "Swedish"
        }
        subtitles_norm = []

        for subs in subtitles:
            path = subs.get('path')
            name = os.path.basename(path).lower()

            # Regex to extract potential language code or full name
            match = re.search(r"([^\d_]+)(?=\.vtt$)", name)
            label = match.group(1) if match else 'unknown'
            srclang = 'unknown'
            # Normalize to lowercase and limit to 2-3 characters for `srclang`
            if len(label) == 2:
                srclang = label if label in LANGUAGE_MAP else 'unknown'
                label = LANGUAGE_MAP.get(label, label)
            if len(label) > 2:
                lang = label[:3]
                srclang = ALIAS_MAP.get(lang) if lang in ALIAS_MAP else 'unknown'
                label = LANGUAGE_MAP.get(srclang, 'unknown')

            data = {
                'path': path,
                'lang': srclang,
                'label': label
            }
            subtitles_norm.append(data)
        return subtitles_norm

    def extract_subtitles(self, video_path: str) -> list[dict]:
        ffprobe_path = os.path.join(os.getcwd(), 'ffprobe.exe')
        ffmpeg_path = os.path.join(os.getcwd(), 'ffmpeg.exe')

        if not os.path.exists(ffprobe_path):
            raise FileNotFoundError(f'[{self.timestamp()}] [INFO    ] main.metadataextract: ffprobe binary not found.')
        if not os.path.exists(ffmpeg_path):
            raise FileNotFoundError(f'[{self.timestamp()}] [INFO    ] main.metadataextract: ffmpeg binary not found.')
        
        # Get subtitle streams info using ffprobe
        probe_cmd = [
            ffprobe_path,
            '-v', 'error',
            '-select_streams', 's', 
            '-show_entries', 'stream=index:stream_tags=title,language', 
            '-of', 'json',
            video_path
        ]
        result = subprocess.run(probe_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace')

        # Parse the ffprobe output and extract subtitle streams
        try:
            subtitles = json.loads(result.stdout).get("streams", [])
        except json.JSONDecodeError as e:
            print(f'[{self.timestamp()}] [INFO    ] main.metadataextract: error parsing ffprobe output.', e)
            return []
        if not subtitles:
            return []
        
        output_folder = f'{os.path.dirname(video_path)}/{os.path.splitext(os.path.basename(video_path))[0]}' 
        output_folder_norm = os.path.normpath(output_folder)
        os.makedirs(output_folder_norm, exist_ok=True)  # Ensure output folder exists

        extracted_subs = []    
        for adjusted_index, subs in enumerate(subtitles):
            index = subs.get('index') # Original Index
            label = subs.get('tags').get('title')
            lang = subs.get('tags').get('language')
            # Create an output directory based on the video file name
            output_path = os.path.join(output_folder_norm, f"{index}_{label}.vtt") if label else os.path.join(output_folder_norm, f"{index}_{lang}.vtt")

            # ffmpeg command to extract the subtitles
            extract_cmd = [
                ffmpeg_path,
                '-i', video_path,
                F'-map', f'0:s:{adjusted_index}',     # Map subtitle stream by index
                '-c:s', 'webvtt',           # Convert to VTT format
                '-y',                       # Overwrite if already exists
                output_path
            ]   
            subprocess.run(extract_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace')

            data = {
                'index': index,
                'path': output_path,
                'lang': lang,
                'label': label
            }
            extracted_subs.append(data)
        return extracted_subs
    


class Transcode:
    def __init__(self):
        self.ffmpeg_path = os.path.join(os.getcwd(), 'ffmpeg.exe')

    def timestamp(self):
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def remove_file_with_retry(self, file_path, retries=5, delay=2):
        for attempt in range(retries):
            try:
                os.remove(file_path)
                return
            except PermissionError:
                if attempt < retries - 1:
                    print(f'[{self.timestamp()}] [INFO    ] main.transcode: file is being used, retrying in {delay} seconds...')
                    time.sleep(delay)
                else:
                    print(f'[{self.timestamp()}] [INFO    ] main.transcode: failed to remove file after {retries} attempts: {file_path}')
                    raise

    def transcode_to_mp4_264_aac(self, file_path):
        file = os.path.basename(file_path)
        root = os.path.dirname(file_path)
        output_file = os.path.splitext(file_path)[0] + ".mp4"
        
        # Ensure the output file doesn't already exist
        if os.path.exists(output_file):
            # If the output file exists, add a unique timestamp to avoid overwriting
            output_file = os.path.splitext(file_path)[0] + f"_{self.timestamp()}.mp4"
            print(f'[{self.timestamp()}] [INFO    ] main.transcode: output file exists, using a unique filename: {output_file}')
        
        print(f'[{self.timestamp()}] [INFO    ] main.transcode: transcoding to mp4 x264 aac, {file}...')
        # Command for FFmpeg to convert the video, audio, and subtitle streams
        # Using NVENC (NVIDIA GPU acceleration) for video and AAC for audio encoding
        command = [
            self.ffmpeg_path,
            '-i', file_path,
            '-c:v', 'h264_nvenc',       # Video codec using NVENC (GPU acceleration for NVIDIA), for CPU encoding change "h264_nvenc" to "libx264"
            '-preset', 'fast',          # Encoding speed preset
            '-cq:v', '19',              # Set quality level (lower is better quality)
            '-pix_fmt', 'yuv420p',      # Force 8-bit color (no 10-bit support)
            '-c:a', 'aac',              # Audio codec (AAC)
            '-ac', '2',                 # Number of audio channels (stereo)
            '-f', 'mp4',                # Output format (MP4)
            output_file                 # Output file (MP4)
        ]

        try:
            # Using subprocess.Popen to get real-time progress updates from stderr
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace')
            # Read stderr for progress info
            while True:
                stderr_line = process.stderr.readline()
                if stderr_line == '' and process.poll() is not None:
                    break  

                if stderr_line:
                    # Check for FFmpeg progress lines containing frame, time, fps, bitrate, etc.
                    if 'frame=' in stderr_line:
                        try:
                            # Extract frame, fps, time, and bitrate info
                            frame_info = stderr_line.split('frame=')[-1].split(' ')[0]  # frame count
                            time_info = stderr_line.split('time=')[-1].split(' ')[0]   # time information
                            fps_info = stderr_line.split('fps=')[-1].split(' ')[0]     # fps value
                            bitrate_info = stderr_line.split('bitrate=')[-1].split(' ')[0]  # bitrate info
                            # Format the output to match your desired format
                            print(f'frame={frame_info} fps={fps_info} time={time_info} bitrate={bitrate_info} speed={stderr_line.split("speed=")[-1].split("x")[0]}x -- {file}')
                        except Exception as e:
                            pass
        except Exception as e:
            print()
            print(f"[{self.timestamp()}] [INFO    ] main.transcode: an error occurred -> {e}")

        self.remove_file_with_retry(file_path)
        return output_file



class FlaskWeb:
    def __init__(self):
        self.app = Flask(__name__)

        @self.app.route('/favicon.ico')
        def favicon():
            return send_from_directory(
                os.path.join(self.app.root_path, 'static'),
                '4304.webp', 
                mimetype='image/vnd.microsoft.icon'
            )
        
        @self.app.route('/')
        def index():
            try:
                items = Database.fetch_items_with_limit(20)
                media_items = []
                for item in items:
                    media_items.append(Database().swap_title(item))

                movies = Database.fetch_items_with_limit(20, 'movie')
                movies_list = []
                for item in movies:
                    movies_list.append(Database().swap_title(item))

                series = Database.fetch_items_with_limit(20, 'series')
                series_list = []
                for item in series:
                    series_list.append(Database().swap_title(item))

            except Exception as e:
                return render_template('500.html', message=e)
            return render_template('index.html', media_items=media_items, movies=movies_list, series=series_list)

        @self.app.route('/<int:item_id>/<string:title>')
        def details_page(item_id, title):
            try:    
                media_items = Database.fetch_item_data(int(item_id))
                media_items = Database().swap_title(media_items)
            except Exception as e:
                return render_template('500.html', message=e)
            if not media_items:
                return render_template('404.html'), 404
            try:
                duration = FlaskWeb().calculate_duration_avg(media_items.media_metadata)
            except Exception as e:
                print(e)
                duration = 0
            return render_template('item_page.html', media_items=media_items, duration=duration)

        @self.app.route('/watch/<int:metadata_id>/<string:title>')
        def watch_page(metadata_id, title):
            try:
                item_metadata = Database.fetch_item_metadata(metadata_id)
                user_data = Database.fetch_user_data_details(0)
                item_id = item_metadata.media_items_id
                item = Database.fetch_item(item_id)
                item = Database().swap_title(item)
                episodes_data = Database.fetch_items_from_metadata(item_id)
                
                episode_count = 0
                for ep in episodes_data:
                    if ep.season == item_metadata.season:
                        episode_count += 1
                
                next_episode_data = []
                if item_metadata.episode and item_metadata.episode < episode_count:
                    next_ep = item_metadata.episode + 1
                    for episode in episodes_data:
                        if episode.season == item_metadata.season:
                            if episode.episode == next_ep:
                                next_episode_data = episode
            except Exception as e:
                print('error (1) -> main.FlaskWeb.watch_page() -->', e)

            subtitles = item_metadata.subtitles if item_metadata.subtitles else []
            current_time = 0
            try:
                for item_data in user_data:
                    if item_data.media_metadata_id == metadata_id:
                        current_time = item_data.current_time
            except Exception as e:
                print('error (2) -> main.FlaskWeb.watch_page() -->', e)
            
            return render_template('watch_page.html', item_id=item_id, metadata_id=metadata_id, title=title, subtitles=subtitles, start_time=current_time, item=item, metadata=item_metadata, next_episode_data=next_episode_data)
        
        @self.app.route('/play/<int:metadata_id>/<string:title>')
        def play(metadata_id, title):
            try:
                item_metadata = Database.fetch_item_metadata(metadata_id)
            except Exception as e:
                return render_template('404.html'), 404
            if item_metadata:
                path = item_metadata.path
                directory = os.path.dirname(path)
                filename = os.path.basename(path)
                return send_from_directory(directory, filename)
            return render_template('404.html'), 404
    
        @self.app.route('/subtitles/<int:metadata_id>/<string:title>/<string:path>')
        def subtitles(metadata_id, title, path):
            directory = os.path.dirname(path)
            filename = os.path.basename(path)
            return send_from_directory(directory, filename)

        @self.app.route('/watchlist')
        def watchlist():
            try:
                user_data = Database.fetch_user_data(0)
                media_items = []
                for row in user_data:
                    if row.watchlist == 1:
                        item_id = row.media_items_id
                        item = Database.fetch_item(item_id)
                        item = Database().swap_title(item)
                        media_items.append(item)
            except Exception as e:
                return render_template('500.html', message=e)           
            return render_template('watchlist_page.html', media_items=media_items)

        @self.app.route('/settings', methods=['GET', 'POST'])
        def settings():
            if request.method == 'POST':  # Check if the request is POST
                settings_value = int(request.form.get('settings_value'))
                # 1 -- LibraryManager().verify()
                if settings_value == 1:
                    verify_process = threading.Thread(target=run_verify, daemon=True)
                    verify_process.start()
                    return render_template('settings_page.html')

                if settings_value == 2:
                    with open('static/settings.json', 'r+') as file:
                        settings = json.load(file)
                        if settings['api_updates_auto'] == 0:
                            new_value = 1
                        else:
                            new_value = 0

                        settings['api_updates_auto'] = new_value
                        file.seek(0)
                        json.dump(settings, file, indent=4)
                        file.truncate()
                    return render_template('settings_page.html')
            return render_template('settings_page.html')

        @self.app.route('/search', methods=['GET'])
        def search_page():
            return render_template('search_page.html')

        @self.app.route('/search/results', methods=['GET'])
        def search_results():
            query = request.args.get('query', '')
            if query:
                results = Database().search(query)
                out = []
                for result in results:
                    out.append(Database().swap_title_dict(result))
            return jsonify(results=out)
        
        @self.app.errorhandler(404)
        def page_not_found(e):
            return render_template('404.html'), 404
        
        @self.app.route('/get_user_item_data/<int:item_id>', methods=['GET'])
        def get_user_data(item_id):
            user_account_data = Database.fetch_user_data(0) #atm user 0 is default
            results = {}
            for data in user_account_data:
                if data.media_items_id == item_id:
                    results = {
                        'watchlistStatus': data.watchlist, 
                        'rating': data.rating
                    }
            return jsonify(results), 200

        @self.app.route('/set_user_item_data/<int:item_id>', methods=['POST'])
        def set_user_data(item_id):
            data = request.get_json()
            watchlistStatus = data.get('watchlistStatus')
            rating = data.get('rating')
            data = {
                'watchlistStatus': watchlistStatus,
                'rating': rating,
            }
            add_to_queue(lambda user_id=0, item_id=item_id, data=data: Database().update_user_data(user_id, item_id, data))
            
            return jsonify({"message": "user data changed."}), 200

        @self.app.route('/get_user_item_data_details/<int:item_id>', methods=['GET'])
        def get_user_data_details(item_id):
            user_account_data = Database.fetch_user_data_details(0) #atm user 0 is default
            results = []
            for data in user_account_data:
                if data.media_items_id == item_id:
                    result = {
                        'media_items_id': data.media_items_id,
                        'media_metadata_id': data.media_metadata_id,
                        'watchedStatus': data.watched, 
                    }
                    results.append(result)
            # Unpack the results into separate lists
            metadata_item_ids = [x['media_metadata_id'] for x in results]
            watched_statuses = [x['watchedStatus'] for x in results]
            return jsonify({"watched": watched_statuses, "metadata_item_ids": metadata_item_ids}), 200

        @self.app.route('/set_user_item_data_details', methods=['POST'])
        def set_user_data_details():
            data = request.get_json()
            item_id = data.get('item_id')
            metadata_id = data.get('metadata_id')
            watchedStatus = data.get('watched')
            time_left = data.get('time_left')
            data = {
                'watchedStatus': watchedStatus,
                'time_left': time_left,
            }
            add_to_queue(lambda user_id=0, item_id=item_id, metadata_id=metadata_id, data=data: Database().update_user_data_details(user_id, item_id, metadata_id, data))
            
     
            return jsonify({"message": "user data details changed."}), 200

        @self.app.route('/recent')
        def recently_added_page():
            try:
                page = int(request.args.get('page', 1)) # Get the current page number from the query parameter
                items_per_page = 20 # Limit the number of media items per page
                offset = (page - 1) * items_per_page

                # Fetch media items for the current page, limiting the results
                total_items = Database().get_total_media_count() # calculate the number of pages
                items = Database.fetch_items_with_pagination(items_per_page, offset)
                media_items = []
                for item in items:
                    media_items.append(Database().swap_title(item))
                total_pages = (total_items // items_per_page) + (1 if total_items % items_per_page else 0)
            except Exception as e:
                media_items = []
                total_pages = 1  # Set at least one page if something fails
            if page > total_pages:
                return render_template('404.html'), 404
            return render_template('recently_added_page.html', media_items=media_items, total_pages=total_pages, current_page=page)

        @self.app.route('/movies')
        def movies_page():
            try:
                page = int(request.args.get('page', 1)) # Get the current page number from the query parameter
                items_per_page = 20 # Limit the number of media items per page
                offset = (page - 1) * items_per_page

                # Fetch media items for the current page, limiting the results
                total_items = Database().get_total_media_count('movie') # calculate the number of pages
                items = Database.fetch_items_with_pagination(items_per_page, offset, 2)
                media_items = []
                for item in items:
                    media_items.append(Database().swap_title(item))
                total_pages = (total_items // items_per_page) + (1 if total_items % items_per_page else 0)
            except Exception as e:
                media_items = []
                total_pages = 1  # Set at least one page if something fails
            if page > total_pages:
                return render_template('404.html'), 404
            return render_template('movies_page.html', media_items=media_items, total_pages=total_pages, current_page=page)

        @self.app.route('/series')
        def series_page():
            try:
                page = int(request.args.get('page', 1)) # Get the current page number from the query parameter
                items_per_page = 20 # Limit the number of media items per page
                offset = (page - 1) * items_per_page

                # Fetch media items for the current page, limiting the results
                total_items = Database().get_total_media_count('series') # calculate the number of pages
                items = Database.fetch_items_with_pagination(items_per_page, offset, 3)
                media_items = []
                for item in items:
                    media_items.append(Database().swap_title(item))
                total_pages = (total_items // items_per_page) + (1 if total_items % items_per_page else 0)
            except Exception as e:
                media_items = []
                total_pages = 1  # Set at least one page if something fails
            if page > total_pages:
                return render_template('404.html'), 404
            return render_template('series_page.html', media_items=media_items, total_pages=total_pages, current_page=page)

        @self.app.route('/update_watchtime', methods=['POST'])
        def update_watchtime_route():

            data = request.get_json()
            user_id = 0  # placeholder
            item_id = data.get('item_id')
            metadata_id = data.get('metadata_id')
            current_time = data.get('currentTime')
            video_duration = data.get('videoDuration')

            # Percentage thresholds
            short_video_percentage = 0.90
            long_video_percentage = 0.85
            # Determine the applicable threshold'
            if video_duration:
                if video_duration < 300:
                    threshold = short_video_percentage
                else:
                    threshold = long_video_percentage
                # Calculate the threshold time
                if current_time >= video_duration * threshold:
                    data['watchedStatus'] = 1   # Mark as watched
            add_to_queue(lambda: Database().update_user_data_details(user_id, item_id, metadata_id, data))
            
            return jsonify({"message": "Watchtime updated successfully."}), 200

    @staticmethod
    def calculate_duration_avg(metadata):
        total_minutes = 0
        total_items = 0

        # Extract the duration and split it into hours and minutes
        for item in metadata:
            duration = item.get('duration', '')
            if duration:
                parts = duration.split(":")
                hours = int(parts[0])
                minutes = int(parts[1])
                total_minutes += (hours * 60 + minutes)
                total_items += 1

        # Calculate average if there are items
        if total_items > 0:
            average_minutes = total_minutes / total_items
            avg_hours = average_minutes // 60
            avg_remaining_minutes = average_minutes % 60
            return f"{int(avg_hours)}hr {int(avg_remaining_minutes)}min" if avg_hours > 0 else f"{int(avg_remaining_minutes)}min"        
   
    def run(self):
        print(f'[{LibraryManager().timestamp()}] [INFO    ] main: application is running... at localhost:8000, 127.0.0.1:8000, {socket.gethostbyname(socket.gethostname())}:8000')
        # self.app.run(host="0.0.0.0", port=8000, debug=True)
        serve(self.app, host="0.0.0.0", port=8000, threads=16)



def run_verify():
    LibraryManager().verify()
def api_update():
    settings = DirectoryManager().load_paths().get("api_updates_auto", 0)
    if settings != 1:
        return
    
    try:
        tmdb().tmdb_update()
    except Exception as e:
        print(f'[{LibraryManager().timestamp()}] [INFO    ] main.LibraryManager: database tmdb update failed ->.', e) 
def schedule_task():
    schedule.every().day.at("12:19").do(api_update) 
def run_api_auto_updates():
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    Database().create_database()
    DirectoryManager().create_settings()

    start_worker_queue() # Start thread queue for database writes operations
    
    verify_process = threading.Thread(target=run_verify, daemon=True)
    verify_process.start()

    schedule_task()
    api_updates_background_process = threading.Thread(target=run_api_auto_updates, daemon=True)
    api_updates_background_process.start()

    app_instance = FlaskWeb()
    app_instance.run()


    
    
