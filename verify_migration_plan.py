import os
import sys
import json
import sqlite3
from collections import defaultdict
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')
DB_PATH = r"c:\Users\mingc\OneDrive\文件\ATG\Photo-Review\photo_index.db"

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

def is_junk(rel_path, name, ext):
    parts = [p.lower() for p in rel_path.split('\\')]
    if '#recycle' in parts:
        return 'recycle'
    if '.@__thumb' in parts:
        return 'thumb'
    lname = name.lower()
    if lname in ('thumbs.db', '.ds_store', 'desktop.ini', 'zbthumbnail.info', 'picasa.ini', '.picasa.ini'):
        return 'os_junk'
    return None

def get_source_priority(rel_path):
    """
    Higher score = preferred canonical location to keep when deduplicating across folders.
    """
    parts = rel_path.split('\\')
    tf = parts[0]
    sub = parts[1] if len(parts) > 1 else ""
    
    # Lowest priority: root-level redundant folders & generic camera dumps
    if tf in ('102D7100', 'Photo', 'Photos_2001', 'film 錄影檔', 'movies-2011Tailand', '2011Tailand', '2011Tailand2', '2010-02吳哥窟', '2013-01-25 廣州_香港六日行', '2013-07北海道-東京'):
        return (10, -len(rel_path))
    if tf in ('Casico', '00放在Apple的照片', 'Bronson在木棉庄的相片'):
        return (20, -len(rel_path))
    if tf == 'D7100':
        if sub in ('101D7100', '102D7100', '104D7100', '105D7100', '110D7100', '111D7100', '112D7100', '2023Europe2'):
            return (25, -len(rel_path))
        return (75, -len(rel_path))
    if tf == 'Travel' and sub == 'Croatia2025':
        return (60, -len(rel_path))
    if tf == 'Home' and sub == '2025Europe':
        return (70, -len(rel_path))
    if tf.startswith('Photos_') or tf.startswith('photos_'):
        if sub in ('2014-02Travel_Taipei', '2013 photos', '104_PANA', '2008-08 苗栗'):
            return (50, -len(rel_path))
        return (85, -len(rel_path))
    if tf in ('00新莊國小', '2019北一女中三十重聚', '00 CTS', 'Company&Business', '106這些年的回憶_潔英'):
        return (80, -len(rel_path))
    return (60, -len(rel_path))

from simulate_plan import map_destination, apply_raw_rule

c.execute("SELECT id, path, top_folder, rel_path, name, ext, size, mtime, quick_hash FROM files")
all_rows = c.fetchall()

real_files = []
junk_files = []
for r in all_rows:
    fid, fpath, tf, rel_path, name, ext, size, mtime, qh = r
    jtype = is_junk(rel_path, name, ext)
    if jtype:
        junk_files.append((r, jtype))
    else:
        real_files.append(r)

# Group real files by exact content signature: (size, quick_hash) if size > 0 and qh is present,
# or if qh is None (meaning unique size across the whole drive!), it's a singleton!
sig_groups = defaultdict(list)
for r in real_files:
    fid, fpath, tf, rel_path, name, ext, size, mtime, qh = r
    if size == 0:
        # keep 0-byte files only if unique per folder, or stage duplicates
        sig = ('zero', name.lower(), tf)
    elif qh:
        sig = ('hash', size, qh)
    else:
        sig = ('unique_size', fid)
    sig_groups[sig].append(r)

keep_list = []
dup_list = []

for sig, items in sig_groups.items():
    if len(items) == 1:
        keep_list.append(items[0])
    else:
        # Sort by priority descending, then rel_path ascending for deterministic winner
        items_sorted = sorted(items, key=lambda x: (get_source_priority(x[3]), x[3]), reverse=True)
        winner = items_sorted[0]
        keep_list.append(winner)
        for loser in items_sorted[1:]:
            dup_list.append((loser, winner[3]))

print(f"Total real files: {len(real_files)}")
print(f"  -> Keep (Unique): {len(keep_list)} files ({sum(x[6] for x in keep_list)/(1024**3):.2f} GB)")
print(f"  -> Stage (Duplicates): {len(dup_list)} files ({sum(x[0][6] for x in dup_list)/(1024**3):.2f} GB)")
print(f"Total junk files (#recycle, .@__thumb, OS junk): {len(junk_files)} files ({sum(x[0][6] for x in junk_files)/(1024**3):.2f} GB)")

# Check for any destination path collisions among keep_list
dest_map = {}
collisions = 0
final_moves = [] # (fid, src_rel, dest_rel, category)

for r in keep_list:
    fid, fpath, tf, rel_path, name, ext, size, mtime, qh = r
    dest = os.path.normpath(apply_raw_rule(map_destination(rel_path, name, ext, mtime), ext))
    if dest.lower() in dest_map:
        collisions += 1
        # Disambiguate filename with parent subfolder name
        base, extension = os.path.splitext(dest)
        parent_tag = rel_path.split('\\')[-2] if len(rel_path.split('\\')) >= 2 else 'alt'
        dest = f"{base}_{parent_tag}{extension}"
        idx = 2
        while dest.lower() in dest_map:
            dest = f"{base}_{parent_tag}_{idx}{extension}"
            idx += 1
    dest_map[dest.lower()] = fid
    final_moves.append((fid, rel_path, dest, 'KEEP'))

print(f"Destination path collisions resolved with suffix: {collisions}")

# Summary of final_moves by top-2 folder levels
level2_summary = defaultdict(lambda: [0, 0])
keep_by_id = {r[0]: r for r in keep_list}
for fid, src_rel, dest_rel, cat in final_moves:
    sz = keep_by_id[fid][6]
    parts = dest_rel.split('\\')
    k = "\\".join(parts[:2])
    level2_summary[k][0] += 1
    level2_summary[k][1] += sz

print("\n=== FINAL CLEAN ORGANIZED STRUCTURE SUMMARY (UNIQUE KEPT FILES) ===")
for k in sorted(level2_summary.keys()):
    cnt, sz = level2_summary[k]
    print(f"  {k:<45} | {cnt:>6} files | {sz/(1024**3):>7.2f} GB")

conn.close()
