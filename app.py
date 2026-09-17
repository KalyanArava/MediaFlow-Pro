from flask import Flask, render_template, request, jsonify, send_file
from backend.database import init_db, list_history, add_history, delete_history, get_history_item
from backend.downloader import DownloadManager
from backend.analyzer import analyze_url, platform_for
from backend.settings import load_settings, save_settings
from backend.tools import media_info, convert_to_mp3, extract_thumbnail
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__)
manager = DownloadManager(BASE_DIR)
init_db(BASE_DIR)

@app.route('/')
def index():
    return render_template('index.html', settings=load_settings(BASE_DIR))

@app.route('/api/analyze', methods=['POST'])
def api_analyze():
    data = request.get_json(silent=True) or {}
    url = (data.get('url') or '').strip()
    if not url:
        return jsonify({'ok': False, 'error': 'Please enter a URL.'}), 400
    try:
        result = analyze_url(url)
        result['platform'] = platform_for(url, result)
        return jsonify({'ok': True, 'data': result})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400

@app.route('/api/download', methods=['POST'])
def api_download():
    data = request.get_json(silent=True) or {}
    url = (data.get('url') or '').strip()
    if not url:
        return jsonify({'ok': False, 'error': 'URL is required.'}), 400
    quality = data.get('quality', 'best')
    kind = data.get('kind', 'video')
    platform = data.get('platform', 'auto')
    task = manager.start(url, quality=quality, kind=kind, platform=platform)
    return jsonify({'ok': True, 'task_id': task['id']})

@app.route('/api/progress/<task_id>')
def api_progress(task_id):
    task = manager.get(task_id)
    if not task:
        return jsonify({'ok': False, 'error': 'Task not found.'}), 404
    return jsonify({'ok': True, 'data': task})

@app.route('/api/progress/<task_id>/pause', methods=['POST'])
def api_pause(task_id):
    return jsonify({'ok': manager.pause(task_id), 'data': manager.get(task_id)})

@app.route('/api/progress/<task_id>/resume', methods=['POST'])
def api_resume(task_id):
    return jsonify({'ok': manager.resume(task_id), 'data': manager.get(task_id)})

@app.route('/api/progress/<task_id>/cancel', methods=['POST'])
def api_cancel(task_id):
    return jsonify({'ok': manager.cancel(task_id), 'data': manager.get(task_id)})

@app.route('/api/history')
def api_history():
    return jsonify({'ok': True, 'data': list_history(BASE_DIR)})

@app.route('/api/history/<int:item_id>', methods=['DELETE'])
def api_delete_history(item_id):
    item = get_history_item(BASE_DIR, item_id)
    if item and item.get('filepath') and os.path.isfile(item['filepath']):
        try:
            os.remove(item['filepath'])
        except OSError:
            pass
    delete_history(BASE_DIR, item_id)
    return jsonify({'ok': True})

@app.route('/api/settings', methods=['GET', 'POST'])
def api_settings():
    if request.method == 'GET':
        return jsonify({'ok': True, 'data': load_settings(BASE_DIR)})
    data = request.get_json(silent=True) or {}
    settings = load_settings(BASE_DIR)
    settings.update({k: v for k, v in data.items() if k in settings})
    save_settings(BASE_DIR, settings)
    return jsonify({'ok': True, 'data': settings})

@app.route('/api/media-info', methods=['POST'])
def api_media_info():
    data = request.get_json(silent=True) or {}
    try:
        return jsonify({'ok': True, 'data': media_info(data.get('path', ''))})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400

@app.route('/api/convert-mp3', methods=['POST'])
def api_convert_mp3():
    data = request.get_json(silent=True) or {}
    try:
        return jsonify({'ok': True, 'data': convert_to_mp3(data.get('path', ''))})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400

@app.route('/api/thumbnail', methods=['POST'])
def api_thumbnail():
    data = request.get_json(silent=True) or {}
    try:
        return jsonify({'ok': True, 'data': extract_thumbnail(data.get('path', ''))})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400

@app.route('/api/file/<int:item_id>')
def api_file(item_id):
    item = get_history_item(BASE_DIR, item_id)
    if not item or not os.path.isfile(item['filepath']):
        return jsonify({'ok': False, 'error': 'File not found.'}), 404
    return send_file(item['filepath'], as_attachment=True, download_name=os.path.basename(item['filepath']))

@app.route('/api/file/<int:item_id>/view')
def api_file_view(item_id):
    item = get_history_item(BASE_DIR, item_id)
    if not item or not os.path.isfile(item['filepath']):
        return jsonify({'ok': False, 'error': 'File not found.'}), 404
    return send_file(item['filepath'], as_attachment=False, conditional=True)

@app.route('/api/task/<task_id>/file')
def api_task_file(task_id):
    task = manager.get(task_id)
    if not task or task.get('status') != 'completed' or not task.get('filename'):
        return jsonify({'ok': False, 'error': 'File is not ready.'}), 404
    path = task['filename']
    if not os.path.isfile(path):
        return jsonify({'ok': False, 'error': 'File not found.'}), 404
    return send_file(path, as_attachment=True, download_name=os.path.basename(path))

@app.route('/api/status')
def api_status():
    import shutil
    import sys

    return jsonify({
        'ok': True,
        'data': {
            'python': sys.version,

            'yt_dlp': True,
            'yt_dlp_ejs': True,

            'node': bool(shutil.which('node')),
            'node_path': shutil.which('node') or '',

            'deno': bool(shutil.which('deno')),
            'deno_path': shutil.which('deno') or '',

            'ffmpeg': bool(shutil.which('ffmpeg')),
            'ffmpeg_path': shutil.which('ffmpeg') or '',

            'ffprobe': bool(shutil.which('ffprobe')),
            'ffprobe_path': shutil.which('ffprobe') or '',

            'internet': True,
            'storage': True
        }
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
