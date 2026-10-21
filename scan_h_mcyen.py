import os
import sys
import time
import sqlite3
import hashlib
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

H_ROOT = r"H:\mcyen"
DB_PATH = r"c:\Users\mingc\OneDrive\文件\ATG\Photo-Review\photo_index.db"

PHOTO_VIDEO_EXTS = {
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tif', '.tiff', '.heic', '.webp',
    '.nef', '.nrw', '.cr2', '.cr3', '.arw', '.dng', '.orf', '.rw2', '.pef', '.nksc',
    '.mov', '.mp4', '.avi', '.mpg', '.mpeg', '.wmv', '.m4v', '.mts', '.3gp', '.flv', '.mkv'
}

def is_junk(rel_path, name):
    parts = [p.lower() for p in rel_path.split('\\')]
    if '#recycle' in parts or '.@__thumb' in parts or '.ds_store' in parts:
        return True
    lname = name.lower()
    if lname in ('thumbs.db', '.ds_store', 'desktop.ini', 'zbthumbnail.info', 'picasa.ini', '.picasa.ini'):
        return True
    return False

def scan_h_mcyen():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DROP TABLE IF EXISTS h_files")
    c.execute("""
        CREATE TABLE h_files (
            id INTEGER PRIMARY KEY,
            path TEXT,
            top_folder TEXT,
            parent_rel_dir TEXT,
            rel_path TEXT,
            name TEXT,
            ext TEXT,
            size INTEGER,
            mtime REAL,
            ctime REAL,
            is_media INTEGER,
            quick_hash TEXT
        )
    """)
    c.execute("CREATE INDEX idx_h_size ON h_files(size)")
    c.execute("CREATE INDEX idx_h_dir ON h_files(parent_rel_dir)")
    c.execute("CREATE INDEX idx_h_name_size ON h_files(name, size)")

    start_time = time.time()
    batch = []
    total_files = 0
    total_media = 0
    total_bytes = 0
    errors = 0

    def walk_dir(current_path, top_folder=None):
        nonlocal total_files, total_media, total_bytes, errors
        try:
            with os.scandir(current_path) as it:
                for entry in it:
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            if entry.name.lower() in ('#recycle', '.@__thumb', 'node_modules', '.git', '.cache'):
                                continue
                            tf = top_folder if top_folder is not None else entry.name
                            walk_dir(entry.path, tf)
                        elif entry.is_file(follow_symlinks=False):
                            rel = os.path.relpath(entry.path, H_ROOT)
                            if is_junk(rel, entry.name):
                                continue
                            st = entry.stat(follow_symlinks=False)
                            tf = top_folder if top_folder is not None else "<ROOT>"
                            parent_rel = os.path.dirname(rel)
                            ext = os.path.splitext(entry.name)[1].lower()
                            is_med = 1 if ext in PHOTO_VIDEO_EXTS else 0
                            batch.append((
                                entry.path, tf, parent_rel, rel, entry.name, ext,
                                st.st_size, st.st_mtime, st.st_ctime, is_med
                            ))
                            total_files += 1
                            if is_med:
                                total_media += 1
                            total_bytes += st.st_size
                            if len(batch) >= 5000:
                                c.executemany("""
                                    INSERT INTO h_files (path, top_folder, parent_rel_dir, rel_path, name, ext, size, mtime, ctime, is_media)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """, batch)
                                conn.commit()
                                batch.clear()
                                elapsed = time.time() - start_time
                                print(f"Scanned {total_files} files ({total_media} media, {total_bytes / (1024**3):.2f} GB) in {elapsed:.1f}s...", flush=True)
                    except Exception as e:
                        errors += 1
        except Exception as e:
            errors += 1

    print("Starting scan of H:\\mcyen ...", flush=True)
    walk_dir(H_ROOT)
    if batch:
        c.executemany("""
            INSERT INTO h_files (path, top_folder, parent_rel_dir, rel_path, name, ext, size, mtime, ctime, is_media)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, batch)
        conn.commit()
        batch.clear()

    elapsed = time.time() - start_time
    print(f"Finished scan of H:\\mcyen! Total files: {total_files}, Media files: {total_media}, Total size: {total_bytes / (1024**3):.2f} GB, Errors: {errors}, Time: {elapsed:.1f}s", flush=True)
    conn.close()

if __name__ == "__main__":
    scan_h_mcyen()
