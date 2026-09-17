import os
import subprocess
import json


def safe_path(base, p):
    if not p:
        raise ValueError('File path is required.')
    p = os.path.abspath(p)
    if not os.path.isfile(p):
        raise ValueError('File not found.')
    return p


def media_info(path):
    p = safe_path('', path)
    cmd = ['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', p]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr.strip() or 'ffprobe failed')
    data = json.loads(r.stdout)
    v = next((s for s in data.get('streams', []) if s.get('codec_type') == 'video'), {})
    a = next((s for s in data.get('streams', []) if s.get('codec_type') == 'audio'), {})
    fmt = data.get('format', {})
    fps = v.get('r_frame_rate', '')
    return {
        'resolution': f"{v.get('width', '?')} x {v.get('height', '?')}" if v else 'Audio only',
        'quality': f"{v.get('height', '?')}p" if v else 'Audio',
        'fps': fps or '—',
        'video_codec': v.get('codec_name', '—') if v else '—',
        'audio_codec': a.get('codec_name', '—') if a else '—',
        'duration': float(fmt.get('duration', 0) or 0),
        'filesize': int(fmt.get('size', 0) or 0),
        'bitrate': int(fmt.get('bit_rate', 0) or 0)
    }


def convert_to_mp3(path):
    p = safe_path('', path)
    out = os.path.splitext(p)[0] + '.mp3'
    cmd = ['ffmpeg', '-y', '-i', p, '-vn', '-codec:a', 'libmp3lame', '-q:a', '2', out]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr[-1000:])
    return {'output': out}


def extract_thumbnail(path):
    p = safe_path('', path)
    out = os.path.splitext(p)[0] + '_thumbnail.jpg'
    cmd = ['ffmpeg', '-y', '-i', p, '-frames:v', '1', out]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr[-1000:])
    return {'output': out}
