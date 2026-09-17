import os
import threading
import uuid
import re
from yt_dlp import YoutubeDL
from backend.analyzer import platform_for
from backend.database import add_history
from backend.tools import media_info


def clean(s):
    return re.sub(r'[<>:"/\\|?*\x00-\x1F]', '_', s).strip()[:180] or 'media'


class DownloadManager:
    def __init__(self, base):
        self.base = base
        self.tasks = {}
        self.lock = threading.Lock()

    def start(self, url, quality='best', kind='video', platform='auto'):
        task_id = uuid.uuid4().hex[:12]
        task = {
            'id': task_id, 'status': 'queued', 'progress': 0, 'speed': '', 'eta': '',
            'filename': '', 'error': '', 'title': '', 'url': url, 'platform': platform,
            'kind': kind, 'paused': False, 'cancel_requested': False, 'info': {}
        }
        with self.lock:
            self.tasks[task_id] = task
        threading.Thread(target=self._run, args=(task_id, url, quality, kind, platform), daemon=True).start()
        return task

    def get(self, task_id):
        with self.lock:
            return dict(self.tasks.get(task_id)) if task_id in self.tasks else None

    def pause(self, task_id):
        with self.lock:
            if task_id not in self.tasks:
                return False
            task = self.tasks[task_id]
            if task['status'] in ('downloading', 'merging'):
                task['paused'] = True
                task['status'] = 'paused'
                return True
        return False

    def resume(self, task_id):
        with self.lock:
            if task_id not in self.tasks:
                return False
            task = self.tasks[task_id]
            if task.get('paused'):
                task['paused'] = False
                task['status'] = 'downloading'
                return True
        return False

    def cancel(self, task_id):
        with self.lock:
            if task_id not in self.tasks:
                return False
            task = self.tasks[task_id]
            task['cancel_requested'] = True
            task['paused'] = False
            task['status'] = 'cancelling'
            return True

    def _update(self, tid, **kwargs):
        with self.lock:
            if tid in self.tasks:
                self.tasks[tid].update(kwargs)

    def _is_cancelled(self, tid):
        with self.lock:
            return bool(self.tasks.get(tid, {}).get('cancel_requested'))

    def _wait_if_paused(self, tid):
        while True:
            with self.lock:
                task = self.tasks.get(tid, {})
                if task.get('cancel_requested'):
                    raise RuntimeError('Download cancelled by user.')
                paused = task.get('paused')
            if not paused:
                return
            threading.Event().wait(0.25)

    def _run(self, tid, url, quality, kind, platform):
        path = None
        try:
            self._update(tid, status='analyzing')
            # Choose a writable download directory.
            # Vercel's application filesystem is read-only, so use /tmp.
            if os.environ.get('VERCEL'):
                out_root = os.path.join('/tmp', 'mediaflow', 'downloads')
            else:
                shared = os.path.expanduser('~/storage/shared')
                if os.path.isdir(shared):
                    out_root = os.path.join(shared, 'Movies', 'MediaFlow')
                else:
                    out_root = os.path.join(self.base, 'downloads')

            os.makedirs(out_root, exist_ok=True)
            p = platform if platform not in ('auto', '') else platform_for(url)
            folder_name = clean(p or 'Unknown')
            folder = os.path.join(out_root, folder_name)
            os.makedirs(folder, exist_ok=True)

            if kind == 'audio':
                fmt = 'bestaudio/best'
                post = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]
            elif kind == 'thumbnail':
                fmt = 'best'
                post = []
            elif kind == 'all':
                fmt = 'bestvideo*+bestaudio/best'
                post = []
            else:
                if quality == 'best':
                    fmt = 'bestvideo*+bestaudio/best'
                else:
                    try:
                        h = int(str(quality).rstrip('p'))
                        fmt = f'bestvideo*[height<={h}]+bestaudio/best[height<={h}]'
                    except ValueError:
                        fmt = 'bestvideo*+bestaudio/best'
                post = []

            outtmpl = os.path.join(folder, '%(title)s.%(ext)s')
            opts = {
                'format': fmt,
                'outtmpl': outtmpl,
                'noplaylist': True,
                'merge_output_format': 'mp4',
                'retries': 3,
                'fragment_retries': 3,
                'postprocessors': post,
                'progress_hooks': [lambda d: self._hook(tid, d)],
                'quiet': True,
                'no_warnings': False,
            }
            # Vercel does not provide a system FFmpeg binary.
            # imageio-ffmpeg supplies a bundled FFmpeg executable.
            if os.environ.get('VERCEL') or os.environ.get('RENDER'):
                import imageio_ffmpeg
                opts['ffmpeg_location'] = imageio_ffmpeg.get_ffmpeg_exe()

                deno_path = os.path.join(self.base, 'bin', 'deno')
                if os.path.isfile(deno_path):
                    opts['js_runtimes'] = [f'deno:{deno_path}']

            if kind in ('thumbnail', 'all'):
                opts['writethumbnail'] = True

            self._update(tid, status='downloading')
            with YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                path = ydl.prepare_filename(info)

            if kind == 'audio':
                path = os.path.splitext(path)[0] + '.mp3'
            elif kind == 'video':
                path = os.path.splitext(path)[0] + '.mp4'
            elif kind == 'thumbnail':
                candidates = [os.path.splitext(path)[0] + ext for ext in ('.jpg', '.jpeg', '.png', '.webp')]
                path = next((x for x in candidates if os.path.isfile(x)), path)

            if self._is_cancelled(tid):
                raise RuntimeError('Download cancelled by user.')

            title = info.get('title') or os.path.basename(path or '')
            details = {}
            if kind in ('video', 'audio') and path and os.path.isfile(path):
                try:
                    details = media_info(path)
                except Exception:
                    details = {}
            size = os.path.getsize(path) if path and os.path.isfile(path) else 0
            item = {
                'title': title, 'url': url, 'platform': p, 'filepath': path or '',
                'resolution': details.get('resolution', ''), 'quality': details.get('quality', ''),
                'fps': details.get('fps', ''), 'codec': details.get('video_codec', ''),
                'duration': details.get('duration', info.get('duration') or 0),
                'filesize': size, 'status': 'Completed'
            }
            item['id'] = add_history(self.base, item)
            self._update(tid, status='completed', progress=100, filename=path, title=title,
                         info=details, history_id=item['id'], platform=p)
        except Exception as e:
            message = str(e)
            if self._is_cancelled(tid) or 'cancelled by user' in message.lower():
                self._update(tid, status='cancelled', error='Download cancelled by user.')
            else:
                self._update(tid, status='error', error=message)

    def _hook(self, tid, d):
        self._wait_if_paused(tid)
        status = d.get('status')
        if status == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            done = d.get('downloaded_bytes') or 0
            pct = (done / total * 100) if total else 0
            self._update(tid, progress=round(pct, 1), speed=d.get('_speed_str', ''),
                         eta=d.get('_eta_str', ''), filename=d.get('filename', ''), status='downloading')
        elif status == 'finished':
            self._update(tid, progress=99, status='merging')
