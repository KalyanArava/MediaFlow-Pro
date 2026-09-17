import sqlite3, os
from datetime import datetime


def db_path(base):
    return os.path.join(base, 'database', 'mediaflow.db')


def connect(base):
    conn = sqlite3.connect(db_path(base))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(base):
    os.makedirs(os.path.dirname(db_path(base)), exist_ok=True)
    with connect(base) as c:
        c.execute('''CREATE TABLE IF NOT EXISTS downloads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT, url TEXT, platform TEXT, filepath TEXT,
            resolution TEXT, quality TEXT, fps TEXT, codec TEXT,
            duration REAL, filesize INTEGER, status TEXT, created_at TEXT
        )''')
        c.commit()


def add_history(base, item):
    with connect(base) as c:
        cur = c.execute('''INSERT INTO downloads
            (title,url,platform,filepath,resolution,quality,fps,codec,duration,filesize,status,created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''', (
                item.get('title',''), item.get('url',''), item.get('platform',''), item.get('filepath',''),
                item.get('resolution',''), item.get('quality',''), item.get('fps',''), item.get('codec',''),
                item.get('duration',0), item.get('filesize',0), item.get('status','Completed'),
                datetime.now().isoformat(timespec='seconds')))
        c.commit()
        return cur.lastrowid


def list_history(base):
    with connect(base) as c:
        rows = c.execute('SELECT * FROM downloads ORDER BY id DESC LIMIT 100').fetchall()
        return [dict(r) for r in rows]


def get_history_item(base, item_id):
    with connect(base) as c:
        row = c.execute('SELECT * FROM downloads WHERE id=?', (item_id,)).fetchone()
        return dict(row) if row else None


def delete_history(base, item_id):
    with connect(base) as c:
        c.execute('DELETE FROM downloads WHERE id=?', (item_id,))
        c.commit()
