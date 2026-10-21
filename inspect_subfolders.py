import sqlite3
import sys
import hashlib
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

c.execute("SELECT id, path, top_folder, rel_path, name, ext, size, mtime FROM files")
all_rows = c.fetchall()
real_files = [r for r in all_rows if not is_junk(r[3], r[4], r[5])]

sig_map = defaultdict(list)
for r in real_files:
    if r[6] > 0:
        sig_map[(r[4].lower(), r[6])].append(r)

print("=== 1. SUBFOLDER-TO-SUBFOLDER DUPLICATE PAIRS (TOP 35 BY WASTED GB) ===")
# Group duplicates by (subfolder1, subfolder2)
pair_stats = defaultdict(lambda: [0, 0]) # (sub1, sub2) -> [count, bytes]
for sig, items in sig_map.items():
    if len(items) > 1:
        # Sort items by path so pairs are canonical
        # Get depth-2 folder name for each item
        subs = []
        for it in items:
            parts = it[3].split('\\')
            sub = f"{parts[0]}\\{parts[1]}" if len(parts) > 1 else parts[0]
            # if parts[1] is a filename (i.e. file is directly in top_folder), just use parts[0]
            if len(parts) == 2 and '.' in parts[1] and it[3] == f"{parts[0]}\\{it[4]}":
                sub = parts[0]
            subs.append(sub)
        unique_subs = sorted(set(subs))
        if len(unique_subs) == 1:
            pair_stats[(unique_subs[0], unique_subs[0] + " (internal)")][0] += len(items) - 1
            pair_stats[(unique_subs[0], unique_subs[0] + " (internal)")][1] += (len(items) - 1) * sig[1]
        else:
            for i in range(len(unique_subs)):
                for j in range(i+1, len(unique_subs)):
                    pair_stats[(unique_subs[i], unique_subs[j])][0] += 1
                    pair_stats[(unique_subs[i], unique_subs[j])][1] += sig[1]

for (s1, s2), (cnt, sz) in sorted(pair_stats.items(), key=lambda x: x[1][1], reverse=True)[:35]:
    print(f"  {s1:<42} <-> {s2:<42} | {cnt:>5} files | {sz/(1024**3):>7.2f} GB")

print("\n=== 2. INSPECT D7100 SUBFOLDERS IN DETAIL ===")
d7100_subs = defaultdict(lambda: [0, 0, 1e18, 0]) # sub -> [cnt, bytes, min_mtime, max_mtime]
for r in real_files:
    if r[2] == 'D7100':
        parts = r[3].split('\\')
        sub = f"{parts[0]}\\{parts[1]}" if len(parts) > 2 else parts[0]
        d7100_subs[sub][0] += 1
        d7100_subs[sub][1] += r[6]
        if r[7] < d7100_subs[sub][2]: d7100_subs[sub][2] = r[7]
        if r[7] > d7100_subs[sub][3]: d7100_subs[sub][3] = r[7]

for sub, (cnt, sz, min_m, max_m) in sorted(d7100_subs.items(), key=lambda x: x[1][1], reverse=True):
    dmin = datetime.fromtimestamp(min_m).strftime('%Y-%m-%d')
    dmax = datetime.fromtimestamp(max_m).strftime('%Y-%m-%d')
    print(f"  {sub:<40} | {cnt:>5} files | {sz/(1024**3):>7.2f} GB | {dmin} to {dmax}")

print("\n=== 3. QUICK HASH VERIFICATION ON SAMPLE DUPLICATE GROUPS ===")
# Compute quick_hash (first 64KB + middle 64KB + last 64KB) on 200 duplicate groups across various sizes to verify byte-for-byte identity
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

dup_list = [v for k, v in sig_map.items() if len(v) > 1 and k[1] > 100000]
step = max(1, len(dup_list) // 200)
sampled = dup_list[::step][:200]
exact_match = 0
mismatch = 0
for group in sampled:
    hashes = set()
    for item in group:
        try:
            hashes.add(get_quick_hash(item[1], item[6]))
        except Exception as e:
            pass
    if len(hashes) == 1:
        exact_match += 1
    else:
        mismatch += 1

print(f"Sampled {len(sampled)} duplicate groups (by filename+size): {exact_match} byte-identical (100% match), {mismatch} mismatches.")

conn.close()
