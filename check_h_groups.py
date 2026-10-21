import sqlite3
import sys
import hashlib
import os
from collections import defaultdict
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')
DB_PATH = r"c:\Users\mingc\OneDrive\文件\ATG\Photo-Review\photo_index.db"

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Check all directories under H:\mcyen\D7100, H:\mcyen\Photos, H:\mcyen\Data\Photo, H:\mcyen\Data\Personal\Photo, H:\mcyen\Data_2020\Personal, H:\mcyen\USB2\Disk_Backup\Photos, H:\mcyen\USB2\Thai, H:\mcyen\GoogleDrive
c.execute("SELECT LOWER(name), size FROM files WHERE size > 0 AND top_folder != '#recycle'")
p_name_size = set(c.fetchall())

c.execute("SELECT id, path, top_folder, parent_rel_dir, rel_path, name, ext, size, mtime, is_media FROM h_files")
dir_files = defaultdict(list)
for r in c.fetchall():
    dir_files[r[3]].append(r)

print("=== 1. ALL D7100 SUBFOLDERS IN H:\\mcyen ===")
for pdir, items in sorted(dir_files.items()):
    if pdir.startswith("D7100"):
        med = [x for x in items if x[9] == 1]
        dup = [x for x in med if (x[5].lower(), x[7]) in p_name_size]
        uniq = [x for x in med if (x[5].lower(), x[7]) not in p_name_size]
        print(f"  {pdir:<55} | Total: {len(items):>5} | Med: {len(med):>5} | Dup in P: {len(dup):>5} | Uniq: {len(uniq):>5}")
        if uniq:
            for u in uniq[:10]:
                print(f"     -> Unique file: {u[4]} ({u[7]} bytes)")

print("\n=== 2. ALL 281 100%-DUPLICATED FOLDERS (GROUPED BY TOP PREFIX) ===")
prefix_summary = defaultdict(lambda: [0, 0, 0]) # [dirs, files, bytes]
for pdir, items in sorted(dir_files.items()):
    med = [x for x in items if x[9] == 1]
    if len(med) <= 10:
        continue
    dup = [x for x in med if (x[5].lower(), x[7]) in p_name_size]
    if len(dup) == len(med):
        parts = pdir.split('\\')
        pref = "\\".join(parts[:3]) if len(parts) >= 3 else pdir
        prefix_summary[pref][0] += 1
        prefix_summary[pref][1] += len(items)
        prefix_summary[pref][2] += sum(x[7] for x in items)

for pref, (dcnt, fcnt, sz) in sorted(prefix_summary.items(), key=lambda x: x[1][2], reverse=True):
    print(f"  {pref:<65} | {dcnt:>4} dirs | {fcnt:>6} files | {sz/(1024**3):>7.2f} GB")

print("\n=== 3. CHECKING GoogleDrive AND GoogleDrive\\YenFamily ===")
for pdir in ('GoogleDrive', 'GoogleDrive\\YenFamily'):
    items = dir_files[pdir]
    med = [x for x in items if x[9] == 1]
    dup = [x for x in med if (x[5].lower(), x[7]) in p_name_size]
    uniq = [x for x in med if (x[5].lower(), x[7]) not in p_name_size]
    non_m = [x for x in items if x[9] == 0]
    print(f"  [{pdir}]: Med={len(med)}, Dup={len(dup)}, UniqMed={len(uniq)}, NonMed={len(non_m)}")
    for d in dup[:5]:
        print(f"     sample dup media: {d[5]} ({d[7]/(1024**2):.2f} MB)")
    for u in uniq[:5]:
        print(f"     sample uniq media: {u[5]} ({u[7]/(1024**2):.2f} MB)")

conn.close()
