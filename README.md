# MediaFlow

A polished Flask + yt-dlp + FFmpeg media downloader UI designed for Windows/VS Code and Android/Termux.

## Features
- Glassmorphism/neumorphic responsive UI
- YouTube and public Instagram URL analysis/download through yt-dlp
- Best available or capped quality selection
- Video, audio and thumbnail modes
- Real-time download progress, speed and ETA
- FFmpeg merge and MP3 conversion
- Actual media metadata: resolution, FPS, codecs, duration, size, bitrate
- SQLite download history
- Organized platform folders
- Batch URL page
- Settings page
- Tools page for MP3 conversion, thumbnail extraction and media information
- System status checks

## Requirements
- Python 3.10+
- FFmpeg/ffprobe installed and available on PATH
- yt-dlp installed from requirements.txt

## Windows / VS Code
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -r requirements.txt
python run.py
```
Open http://127.0.0.1:5000

## Android / Termux
```bash
pkg update && pkg upgrade
pkg install python ffmpeg
termux-setup-storage
python -m pip install -U pip
pip install -r requirements.txt
python run.py
```
Open http://127.0.0.1:5000 in the phone browser.

For Android storage, the project can be placed under `~/storage/shared/` or another accessible location. The default project download folder is `downloads/`; you can change the browser-facing storage workflow in a future configuration update.

## Notes
- Instagram extraction can require authentication for some content. Do not use this app to bypass access controls or download private content without authorization.
- YouTube/Instagram extraction behavior can change as platforms change their websites.
- A JavaScript runtime may be needed by yt-dlp for some current YouTube extraction paths.
