import json, os

DEFAULTS = {
    'default_quality': 'best',
    'default_kind': 'video',
    'skip_duplicates': True,
    'notifications': True,
    'animations': True,
    'theme': 'dark',
    'retries': 3,
    'concurrent_tasks': 1,
}


def path(base):
    return os.path.join(base, 'config', 'settings.json')


def load_settings(base):
    os.makedirs(os.path.dirname(path(base)), exist_ok=True)
    try:
        with open(path(base), 'r', encoding='utf-8') as f:
            data = json.load(f)
        return {**DEFAULTS, **data}
    except Exception:
        save_settings(base, DEFAULTS.copy())
        return DEFAULTS.copy()


def save_settings(base, settings):
    os.makedirs(os.path.dirname(path(base)), exist_ok=True)
    with open(path(base), 'w', encoding='utf-8') as f:
        json.dump(settings, f, indent=2)
