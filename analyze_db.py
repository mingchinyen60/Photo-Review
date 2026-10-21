import sqlite3
import sys
from collections import defaultdict
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')
DB_PATH = r"c:\Users\mingc\OneDrive\文件\ATG\Photo-Review\photo_index.db"

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

print("=== 1. TOP-LEVEL FOLDERS SUMMARY ===")
c.execute("""
    SELECT top_folder, COUNT(*), SUM(size)/(1024.0*1024.0*1024.0), MIN(mtime), MAX(mtime)
    FROM files
    GROUP BY top_folder
    ORDER BY top_folder
""")
for tf, cnt, sz, min_m, max_m in c.fetchall():
    dmin = datetime.fromtimestamp(min_m).strftime('%Y-%m-%d') if min_m else 'N/A'
    dmax = datetime.fromtimestamp(max_m).strftime('%Y-%m-%d') if max_m else 'N/A'
    print(f"{tf:<30} | Files: {cnt:>7} | Size: {sz:>8.2f} GB | mtime: {dmin} to {dmax}")

print("\n=== 2. FILE EXTENSIONS (TOP 30 BY SIZE & COUNT) ===")
c.execute("""
    SELECT ext, COUNT(*), SUM(size)/(1024.0*1024.0*1024.0) as sz
    FROM files
    WHERE top_folder != '#recycle'
    GROUP BY ext
    ORDER BY COUNT(*) DESC
    LIMIT 30
""")
for ext, cnt, sz in c.fetchall():
    print(f"{ext:<12} | Files: {cnt:>7} | Size: {sz:>8.2f} GB")

print("\n=== 3. DUPLICATE ANALYSIS (EXCLUDING #recycle) ===")
# Exact (name, size) duplicates
c.execute("""
    SELECT COUNT(*), SUM(dup_count - 1), SUM((dup_count - 1) * size) / (1024.0*1024.0*1024.0)
    FROM (
        SELECT name, size, COUNT(*) as dup_count
        FROM files
        WHERE top_folder != '#recycle' AND size > 0
        GROUP BY LOWER(name), size
        HAVING COUNT(*) > 1
    )
""")
groups, extra_files, wasted_gb = c.fetchone()
print(f"By (LOWER(name), size) > 0: {groups} unique groups, {extra_files} redundant file copies, {wasted_gb:.2f} GB wasted")

# Exact size duplicates (even if renamed) for files > 10KB
c.execute("""
    SELECT COUNT(*), SUM(dup_count - 1), SUM((dup_count - 1) * size) / (1024.0*1024.0*1024.0)
    FROM (
        SELECT size, COUNT(*) as dup_count
        FROM files
        WHERE top_folder != '#recycle' AND size > 10240
        GROUP BY size
        HAVING COUNT(*) > 1
    )
""")
sgroups, sextra_files, swasted_gb = c.fetchone()
print(f"By (size > 10KB): {sgroups} unique size groups, {sextra_files} candidate copies, {swasted_gb:.2f} GB potential")

print("\n=== 4. FOLDER OVERLAP MATRIX (WHICH TOP FOLDERS SHARE THE MOST (name, size) DUPLICATES) ===")
c.execute("""
    SELECT f1.top_folder, f2.top_folder, COUNT(DISTINCT f1.id), SUM(f1.size)/(1024.0*1024.0*1024.0)
    FROM files f1
    JOIN files f2 ON LOWER(f1.name) = LOWER(f2.name) AND f1.size = f2.size AND f1.id != f2.id
    WHERE f1.top_folder != '#recycle' AND f2.top_folder != '#recycle' AND f1.size > 0
    GROUP BY f1.top_folder, f2.top_folder
    HAVING COUNT(DISTINCT f1.id) > 50
    ORDER BY COUNT(DISTINCT f1.id) DESC
    LIMIT 50
""")
for tf1, tf2, cnt, sz in c.fetchall():
    print(f"{tf1:<28} <-> {tf2:<28} | Shared files: {cnt:>6} | Shared GB: {sz:>7.2f} GB")

conn.close()
