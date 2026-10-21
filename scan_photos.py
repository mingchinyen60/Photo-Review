import os
import sys
import time
import json
import sqlite3
import hashlib
from pathlib import Path
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

ROOT = r"P:\\"
DB_PATH = r"c:\Users\mingc\OneDrive\文件\ATG\Photo-Review\photo_index.db"

def scan_metadata():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DROP TABLE IF EXISTS files")
    c.execute("""
        CREATE TABLE files (
            id INTEGER PRIMARY KEY,
            path TEXT,
            top_folder TEXT,
            rel_path TEXT,
            name TEXT,
            ext TEXT,
            size INTEGER,
            mtime REAL,
            ctime REAL,
            quick_hash TEXT,
            full_hash TEXT
        )
    """)
    c.execute("CREATE INDEX idx_size ON files(size)")
    c.execute("CREATE INDEX idx_top ON files(top_folder)")
    c.execute("CREATE INDEX idx_ext ON files(ext)")
    c.execute("CREATE INDEX idx_name_size ON files(name, size)")

    start_time = time.time()
    batch = []
    total_files = 0
    total_bytes = 0
    errors = 0

    def walk_dir(current_path, top_folder=None):
        nonlocal total_files, total_bytes, errors
        try:
            with os.scandir(current_path) as it:
                for entry in it:
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            tf = top_folder if top_folder is not None else entry.name
                            walk_dir(entry.path, tf)
                        elif entry.is_file(follow_symlinks=False):
                            st = entry.stat(follow_symlinks=False)
                            tf = top_folder if top_folder is not None else "<ROOT>"
                            rel = os.path.relpath(entry.path, ROOT)
                            ext = os.path.splitext(entry.name)[1].lower()
                            batch.append((
                                entry.path, tf, rel, entry.name, ext,
                                st.st_size, st.st_mtime, st.st_ctime
                            ))
                            total_files += 1
                            total_bytes += st.st_size
                            if len(batch) >= 5000:
                                c.executemany("""
                                    INSERT INTO files (path, top_folder, rel_path, name, ext, size, mtime, ctime)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                                """, batch)
                                conn.commit()
                                batch.clear()
                                elapsed = time.time() - start_time
                                print(f"Scanned {total_files} files ({total_bytes / (1024**3):.2f} GB) in {elapsed:.1f}s...", flush=True)
                    except Exception as e:
                        errors += 1
        except Exception as e:
            errors += 1

    print("Starting metadata scan of P:\\ ...", flush=True)
    walk_dir(ROOT)
    if batch:
        c.executemany("""
            INSERT INTO files (path, top_folder, rel_path, name, ext, size, mtime, ctime)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, batch)
        conn.commit()
        batch.clear()

    elapsed = time.time() - start_time
    print(f"Finished metadata scan! Total files: {total_files}, Total size: {total_bytes / (1024**3):.2f} GB, Errors: {errors}, Time: {elapsed:.1f}s", flush=True)
    conn.close()

if __name__ == "__main__":
    scan_metadata()
