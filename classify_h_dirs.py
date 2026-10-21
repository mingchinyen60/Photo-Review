import sqlite3
import sys
import os
from collections import defaultdict
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')
DB_PATH = r"c:\Users\mingc\OneDrive\文件\ATG\Photo-Review\photo_index.db"

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Build P:\ lookup by (LOWER(name), size)
c.execute("SELECT LOWER(name), size, rel_path FROM files WHERE size > 0 AND top_folder != '#recycle'")
p_name_size = set()
for lname, sz, rp in c.fetchall():
    parts = [p.lower() for p in rp.split('\\')]
    if '.@__thumb' in parts or lname in ('thumbs.db', '.ds_store', 'desktop.ini', 'zbthumbnail.info', 'picasa.ini', '.picasa.ini'):
        continue
    p_name_size.add((lname, sz))

def is_real_media(name, ext, size, is_med):
    if not is_med:
        return False
    if name.startswith('._'): # AppleDouble resource fork
        return False
    if size == 0: # 0-byte corrupted stub
        return False
    return True

c.execute("SELECT id, path, top_folder, parent_rel_dir, rel_path, name, ext, size, mtime, is_media FROM h_files")
dir_files = defaultdict(list)
for r in c.fetchall():
    dir_files[r[3]].append(r)

# Classify all directories with > 10 real media files
cat_100_dup = []      # 100% of real media files exist in P:\ (and 0 non-media or only sidecar/junk)
cat_high_dup = []     # >= 20% of real media files exist in P:\ (partially duplicated photo albums)
cat_low_dup = []      # >0 and < 20% duplicated (e.g., iPhone backup or web assets or mostly unique photo album)
cat_zero_dup = []     # > 10 real media files, 0 in P:\

for pdir, items in sorted(dir_files.items()):
    real_med = [x for x in items if is_real_media(x[5], x[6], x[7], x[9])]
    if len(real_med) <= 10:
        continue
    dup_med = [x for x in real_med if (x[5].lower(), x[7]) in p_name_size]
    uniq_med = [x for x in real_med if (x[5].lower(), x[7]) not in p_name_size]
    non_med = [x for x in items if not is_real_media(x[5], x[6], x[7], x[9]) and not x[5].startswith('._') and x[7] > 0]
    
    tot_gb = sum(x[7] for x in items) / (1024**3)
    dup_gb = sum(x[7] for x in dup_med) / (1024**3)
    uniq_gb = sum(x[7] for x in uniq_med) / (1024**3)
    ratio = len(dup_med) / len(real_med)

    entry = (pdir, len(real_med), len(dup_med), len(uniq_med), len(non_med), tot_gb, dup_gb, uniq_gb, ratio)
    if len(dup_med) == 0:
        cat_zero_dup.append(entry)
    elif len(uniq_med) == 0:
        cat_100_dup.append(entry)
    elif ratio >= 0.15 or len(dup_med) >= 10:
        cat_high_dup.append(entry)
    else:
        cat_low_dup.append(entry)

print(f"=== A. 100% DUPLICATED PHOTO FOLDERS (>10 real media, 0 unique media): {len(cat_100_dup)} dirs ({sum(x[5] for x in cat_100_dup):.2f} GB) ===")
# Group by top-level tree
tree_100 = defaultdict(lambda: [0, 0, 0, 0])
for pdir, m, d, u, nm, tgb, dgb, ugb, r in cat_100_dup:
    parts = pdir.split('\\')
    k = "\\".join(parts[:3]) if len(parts) >= 3 else pdir
    tree_100[k][0] += 1
    tree_100[k][1] += m
    tree_100[k][2] += nm
    tree_100[k][3] += tgb
for k, (dc, m, nm, tgb) in sorted(tree_100.items(), key=lambda x: x[1][3], reverse=True):
    print(f"  {k:<65} | {dc:>3} dirs | {m:>6} media | {nm:>4} non-med | {tgb:>7.2f} GB")

print(f"\n=== B. SUBSTANTIALLY DUPLICATED PHOTO FOLDERS (>=10 dup media or >=15% dup): {len(cat_high_dup)} dirs ===")
for pdir, m, d, u, nm, tgb, dgb, ugb, r in sorted(cat_high_dup, key=lambda x: x[6], reverse=True):
    print(f"  {pdir:<70} | Med:{m:>5} | Dup:{d:>5} ({r*100:>5.1f}%) | Uniq:{u:>5} ({ugb:>5.2f}GB) | NonM:{nm:>4} | DupGB:{dgb:>6.2f}GB")

print(f"\n=== C. LOW-OVERLAP FOLDERS (<10 dup media & <15% dup, e.g. 1-5 incidental matches): {len(cat_low_dup)} dirs ===")
for pdir, m, d, u, nm, tgb, dgb, ugb, r in sorted(cat_low_dup, key=lambda x: x[2], reverse=True)[:30]:
    print(f"  {pdir:<70} | Med:{m:>5} | Dup:{d:>5} ({r*100:>5.1f}%) | Uniq:{u:>5} ({ugb:>5.2f}GB) | NonM:{nm:>4}")

conn.close()
