import sqlite3
import sys
import hashlib
import time
from collections import defaultdict
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')
DB_PATH = r"c:\Users\mingc\OneDrive\文件\ATG\Photo-Review\photo_index.db"

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

def is_junk(rel_path, name, ext):
    parts = [p.lower() for p in rel_path.split('\\')]
    if '#recycle' in parts or '.@__thumb' in parts or '.ds_store' in parts:
        return True
    lname = name.lower()
    if lname in ('thumbs.db', '.ds_store', 'desktop.ini', 'zbthumbnail.info', 'picasa.ini', '.picasa.ini'):
        return True
    return False

def get_quick_hash(filepath, size):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        if size <= 196608:
            h.update(f.read())
        else:
            h.update(f.read(65536))
            f.seek(size // 2)
            h.update(f.read(65536))
            f.seek(size - 65536)
            h.update(f.read(65536))
    return h.hexdigest()

c.execute("SELECT id, path, top_folder, rel_path, name, ext, size, mtime, quick_hash FROM files")
all_rows = c.fetchall()
real_files = [r for r in all_rows if not is_junk(r[3], r[4], r[5])]

# Find all files that share the same size (>0) among real_files
size_groups = defaultdict(list)
for r in real_files:
    if r[6] > 0:
        size_groups[r[6]].append(r)

candidates = []
for sz, items in size_groups.items():
    if len(items) > 1:
        for it in items:
            if not it[8]: # no quick_hash yet
                candidates.append((it[0], it[1], it[6]))

print(f"Total real files in duplicate-size groups needing quick_hash: {len(candidates)}", flush=True)
start_t = time.time()
updates = []
errors = 0
for idx, (fid, fpath, fsize) in enumerate(candidates, 1):
    try:
        qh = get_quick_hash(fpath, fsize)
        updates.append((qh, fid))
    except Exception as e:
        errors += 1
    if len(updates) >= 2000:
        c.executemany("UPDATE files SET quick_hash = ? WHERE id = ?", updates)
        conn.commit()
        updates.clear()
        print(f"Hashed {idx}/{len(candidates)} files in {time.time() - start_t:.1f}s...", flush=True)

if updates:
    c.executemany("UPDATE files SET quick_hash = ? WHERE id = ?", updates)
    conn.commit()
    updates.clear()

print(f"Done hashing in {time.time() - start_t:.1f}s (errors: {errors})", flush=True)

# Now reload and inspect exact (size, quick_hash) duplicate groups
c.execute("SELECT id, path, top_folder, rel_path, name, ext, size, mtime, quick_hash FROM files")
all_rows = c.fetchall()
real_files = [r for r in all_rows if not is_junk(r[3], r[4], r[5])]

hash_groups = defaultdict(list)
for r in real_files:
    if r[6] > 0 and r[8]:
        hash_groups[(r[6], r[8])].append(r)

exact_dup_groups = {k: v for k, v in hash_groups.items() if len(v) > 1}
total_extra = sum(len(v) - 1 for v in exact_dup_groups.values())
total_extra_gb = sum((len(v) - 1) * k[0] for k, v in exact_dup_groups.items()) / (1024**3)
print(f"Verified Byte-Identical Duplicate Groups (by size + SHA-256 quick_hash): {len(exact_dup_groups)} groups, {total_extra} redundant files, {total_extra_gb:.2f} GB")

# Also print all depth-1 and depth-2 folders of real files to design the complete mapping table
print("\n=== ALL TOP FOLDERS AND THEIR DEPTH-2 SUBFOLDERS ===")
sub_tree = defaultdict(lambda: [0, 0, 1e18, 0])
for r in real_files:
    tf = r[2]
    parts = r[3].split('\\')
    if len(parts) == 1:
        sub = "<ROOT_FILES>"
    elif len(parts) == 2:
        sub = f"{tf}\\<FILES_IN_FOLDER>"
    else:
        sub = f"{tf}\\{parts[1]}"
    sub_tree[sub][0] += 1
    sub_tree[sub][1] += r[6]
    if r[7] < sub_tree[sub][2]: sub_tree[sub][2] = r[7]
    if r[7] > sub_tree[sub][3]: sub_tree[sub][3] = r[7]

for sub in sorted(sub_tree.keys()):
    cnt, sz, min_m, max_m = sub_tree[sub]
    dmin = datetime.fromtimestamp(min_m).strftime('%Y-%m-%d')
    dmax = datetime.fromtimestamp(max_m).strftime('%Y-%m-%d')
    print(f"  {sub:<65} | {cnt:>5}f | {sz/(1024**3):>6.2f} GB | {dmin}..{dmax}")

conn.close()
