from yt_dlp import YoutubeDL
from urllib.parse import urlparse


def platform_for(url, info=None):
    host = urlparse(url).netloc.lower()
    if 'instagram.' in host:
        return 'Instagram'
    if 'youtube.' in host or 'youtu.be' in host:
        return 'YouTube'
    return (info or {}).get('extractor_key', 'Unknown')


def analyze_url(url):
    opts = {'quiet': True, 'no_warnings': True, 'skip_download': True, 'noplaylist': True}
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    formats = []
    for f in info.get('formats') or []:
        h = f.get('height')
        if h:
            formats.append({'format_id': f.get('format_id'), 'height': h, 'fps': f.get('fps'), 'ext': f.get('ext'), 'vcodec': f.get('vcodec'), 'acodec': f.get('acodec')})
    heights = sorted({x['height'] for x in formats if x['height']}, reverse=True)
    return {
        'id': info.get('id'), 'title': info.get('title') or info.get('fulltitle') or 'Untitled',
        'thumbnail': info.get('thumbnail'), 'duration': info.get('duration'),
        'uploader': info.get('uploader') or info.get('channel'), 'webpage_url': info.get('webpage_url', url),
        'platform': platform_for(url, info), 'webpage_url_domain': urlparse(url).netloc,
        'qualities': heights, 'formats': formats[-100:], 'description': (info.get('description') or '')[:500]
    }
