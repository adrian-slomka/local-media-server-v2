# Local Media Server

A Python-based web application powered by Flask that serves as a local media server similar to Plex or Jellyfin.

## Preview

![App Screenshot](https://raw.githubusercontent.com/adrian-slomka/local-media-server-v2/main/____preview/desktop_homepage.png)

![App Screenshot](https://raw.githubusercontent.com/adrian-slomka/local-media-server-v2/main/____preview/desktop_seriespage.png)

![App Screenshot](https://raw.githubusercontent.com/adrian-slomka/local-media-server-v2/main/____preview/mobile.png)


## Features

- **Web UI**: Easy to use and responsive web UI with a dynamic search and watchlist features.
- **Resume Playback Across Devices**: Begin watching a video on your desktop and seamlessly continue from the last watched minute on your mobile device, with your viewing progress saved automatically.
- **Lightweight Database**: Movies and series are saved into light-weight sqlite3 database for simplicity and easy access.
- **Automatic API Updates**: Integrated tmdb api requests that will enhance the UI/UX with some basic info and neat movie and series posters and their backdrops.
- **No Tracking**: Unlike Plex, the app doesn't save device's physical address, nor it's name and does not have any kind of cookies or ads.

## Requirements

- **NVIDIA GPU**: This application is optmized to run **exclusively on NVIDIA-powered machines for the faster NVENC encoding.
- **NVIDIA Drivers**: The most recent NVIDIA drivers are required to ensure compatibility with the re-encoding and media processing functions.
- **Python 3.8+**: Make sure Python is installed on your system. If not, you can download it from [python.org](https://www.python.org/downloads/).
- **FFmpeg**: A multimedia framework that handles video and audio conversions. This app relies on FFmpeg for re-encoding media files.

**with minor changes to the code it will encode on cpu instead.

## Installation

1. Clone the repository:

    ```bash
    git clone https://github.com/adrian-slomka/local-media-server-v2.git
    ```

2. Create a [virtual environment](https://docs.python.org/3/library/venv.html) (optional but recommended):

3. Install the required dependencies:

    ```bash
    pip install -r requirements.txt
    ```

4. Make sure you have the latest **NVIDIA drivers** installed or check FAQ.

5. Download **FFmpeg**: From [FFmpeg's official website](https://ffmpeg.org/download.html) download pre-compiled exe (builds from gyan.dev). Extract FFprobe.exe and FFmpeg.exe inside the app's main folder.

6. Acquire TMDB API KEY from [TMDB](https://developer.themoviedb.org/docs/getting-started). Next, create .env in main app folder and paste the API KEY there like so: API_KEY=YourKey

7. (optional) Create .bat for start up convinience:

    ```bash
    @echo off
    :: Activate the virtual environment
    call "%~dp0YourEnvName\Scripts\activate.bat"

    :: Run the main.py using the Python
    python "%~dp0main.py"

    pause
    ```

## Usage

1. Start the app:

    ```bash
    python main.py
    ```

    or via .bat file

2. The web application will be accessible on [http://localhost:8000](http://localhost:8000). Open this URL in your web browser. 
Additioanly, the app can be accessed on mobile devices when connected to the same wi-fi network:
- Get your hosting PC's local ip4 adress (open cmd and type: ipcofing and look for ipv4). 
- Next, on your mobile device connected to the same Wi-Fi network type that ip adress followed by :8000, example: 192.168.0.100:8000

3. To add your media files first create folder where you will store your movies or series. 
        
4. In the main_folder/static, open settings.json and paste your path/s like so: ```"libraries": {"series": ["D:/Lib/series", "F:/Lib/series2"], "movies": ["D:/Lib/movies"] },``` (don't forget comma between paths)

5. The app will scan new files on launch. To scan for new files without restarting the app go to the website, open menu and go to settings and re-scan and update your library for new or removed entries.

## Known Limitations

- **No User Profiles**: All watch progress, playlists, and marked episodes are saved in a single shared database without individual user accounts. This means that if multiple people use the app, they will share the same watch history and progress. Separate personalized tracking for different users is WIP.
- **Re-encoding Performance**: Since the app uses GPU acceleration (unless chagned, look FAQ), re-encoding large files or a large number of files may take a while and can put a significant load on your system.
- **Subtitle Extraction**: The app supports subtitle extraction for embedded subtitles in video files. Additionally, some subtitle formats in containers may not be extracted perfectly.
- **File Types**: While the app supports common video formats, it may have limited support for niche or less common file types. We recommend using **MP4** files for the best compatibility with the subtitle extraction and re-encoding features.
- **Library Path Selection**: At the moment, main library path selection via website is WIP and has to be set up manually via copy and paste to settings.json in main_folder/static.

## FAQ

### Does the app support other video formats besides MP4?
Yes, but **MP4** x264, aac is the most reliable format for compatibility with html. Other formats may work depending on a browser.

### Can I run this app on a non-NVIDIA machine?
Yes. However it requries a small code change. Head to main.py and look for function called "transcode_to_mp4_264_aac()" change "h264_nvenc" to "libx264" (libx264 is a CPU-based software encoder, it's way slower on large files compared to h264_nvenc).

### What do I do if subtitles aren't being extracted properly?
If subtitles aren't extracted correctly from the embedded container (.mp4, .mkv etc): 
1) If the app is running: temporarily move that video file.mp4 outside of the library and start re-scan and update in the website settings.
2) Download subtitles from openSubtitles or similar site and rename subtitle file so that it has the same name as video file. Example: video file -> "My_video.mp4", subtitle file -> "My_video.srt" or "My_video.vtt" *Capital letters matter*
3) Move back file.mp4 and file.srt/vtt into the library and re-scan library.

### Will the app run without TMDB API?
Yes. However extended info, poster and backdrops will be missing.

### Will the app run without FFmpeg?
Yes. Incompatible file formats, meaning anything other than .mp4 x264, aac will most likely not be playable.


**Note1:** This application is intended for use within your local Wi-Fi network only. As I am not a web security expert, I cannot guarantee protection against potential vulnerabilities when port forwarded and accessed externally.
**Note2:** This is strictly a learning project. Eexpect bugs and un-optimized code.


