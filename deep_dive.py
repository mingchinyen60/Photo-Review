import sqlite3
import sys
import hashlib
import os
import time
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')
DB_PATH = r"c:\Users\mingc\OneDrive\文件\ATG\Photo-Review\photo_index.db"

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# 1. Inspect subfolder structure of major top folders: Home, D7100, Travel, 00新莊國小, Photos_2013, etc.
print("=== SUBFOLDER STRUCTURE OF MAJOR FOLDERS (Depth 2) ===")
c.execute("SELECT rel_path, size FROM files WHERE top_folder != '#recycle'")
depth2_stats = defaultdict(lambda: [0, 0])
for rel_path, size in c.fetchall():
    parts = rel_path.split('\\')
    if len(parts) >= 2:
        key = f"{parts[0]}\\{parts[1]}"
    else:
        key = parts[0]
    depth2_stats[key][0] += 1
    depth2_stats[key][1] += size

# Show top subfolders for key folders
for tf in ['Home', 'D7100', 'Travel', '00新莊國小', '102D7100', 'Casico', 'Photos_2010 USA', 'Photos_2013', 'Photos_2013-07東京北海道自遊行', '2013-07北海道-東京', '2010-02吳哥窟', 'Photos_2010-02吳哥窟', '2011Tailand', 'Photos_2011Tailand', '2011Tailand2', 'Photos_2011Tailand2', 'movies-2011Tailand', 'Photos_2011Tailand-movies']:
    print(f"\n--- Subfolders of [{tf}] ---")
    sub_items = [(k, v[0], v[1]/(1024**3)) for k, v in depth2_stats.items() if k.startswith(tf + "\\") or k == tf]
    sub_items.sort(key=lambda x: x[2], reverse=True)
    for k, cnt, gb in sub_items[:25]:
        print(f"  {k:<55} | Files: {cnt:>6} | {gb:>7.2f} GB")
    if len(sub_items) > 25:
        print(f"  ... and {len(sub_items)-25} more subfolders")

# 2. Check how many top-level folders are 100% or >80% duplicated in another folder (by name + size)
print("\n=== FOLDER CONTAINMENT / REDUNDANCY RATE (BY LOWER(NAME) + SIZE) ===")
c.execute("""
    SELECT top_folder, COUNT(*), SUM(size)
    FROM files
    WHERE top_folder != '#recycle' AND size > 0
    GROUP BY top_folder
""")
folder_totals = {r[0]: (r[1], r[2]) for r in c.fetchall()}

# Find all (LOWER(name), size) -> set of top_folders
c.execute("""
    SELECT LOWER(name), size, top_folder, id
    FROM files
    WHERE top_folder != '#recycle' AND size > 0
""")
sig_to_folders = defaultdict(set)
file_Records = []
for lname, sz, tf, fid in c.fetchall():
    sig_to_folders[(lname, sz)].add(tf)
    file_Records.append((lname, sz, tf, fid))

folder_dup_elsewhere = defaultdict(lambda: [0, 0])
folder_dup_internal = defaultdict(lambda: [0, 0])
# Also track where else it appears most
folder_best_target = defaultdict(lambda: defaultdict(lambda: [0, 0]))

# Count how many files in tf also exist in OTHER top_folders
for lname, sz, tf, fid in file_Records:
    others = sig_to_folders[(lname, sz)] - {tf}
    if others:
        folder_dup_elsewhere[tf][0] += 1
        folder_dup_elsewhere[tf][1] += sz
        for otf in others:
            folder_best_target[tf][otf][0] += 1
            folder_best_target[tf][otf][1] += sz

print(f"{'Top Folder':<28} | {'Total Files':>11} | {'Total GB':>8} | {'In Other Folders':>16} | {'% Dup Elsewhere':>15} | {'Main Overlap Folder (Files)'}")
print("-" * 120)
for tf in sorted(folder_totals.keys()):
    t_cnt, t_sz = folder_totals[tf]
    d_cnt, d_sz = folder_dup_elsewhere[tf]
    pct_cnt = (d_cnt / t_cnt * 100) if t_cnt else 0
    pct_sz = (d_sz / t_sz * 100) if t_sz else 0
    best_otf = ""
    if folder_best_target[tf]:
        top_otf = max(folder_best_target[tf].items(), key=lambda x: x[1][0])
        best_otf = f"{top_otf[0]} ({top_otf[1][0]} files, {top_otf[1][1]/(1024**3):.2f} GB)"
    print(f"{tf:<28} | {t_cnt:>11} | {t_sz/(1024**3):>8.2f} | {d_cnt:>16} | {pct_cnt:>6.1f}% ({pct_sz:>5.1f}%GB) | {best_otf}")

conn.close()
