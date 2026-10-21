import sqlite3
import sys
import hashlib
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')
DB_PATH = r"c:\Users\mingc\OneDrive\文件\ATG\Photo-Review\photo_index.db"

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Build P:\ lookup by (LOWER(name), size) and by size
c.execute("SELECT id, LOWER(name), size, quick_hash, rel_path FROM files WHERE size > 0 AND top_folder != '#recycle'")
p_by_name_size = defaultdict(list)
p_by_size = defaultdict(list)
for fid, lname, sz, qh, rp in c.fetchall():
    parts = [p.lower() for p in rp.split('\\')]
    if '.@__thumb' in parts or lname in ('thumbs.db', '.ds_store', 'desktop.ini', 'zbthumbnail.info', 'picasa.ini', '.picasa.ini'):
        continue
    p_by_name_size[(lname, sz)].append((fid, qh, rp))
    p_by_size[sz].append((fid, lname, qh, rp))

# Inspect all directories in h_files that have > 10 media files
c.execute("SELECT id, path, top_folder, parent_rel_dir, rel_path, name, ext, size, mtime, is_media FROM h_files")
dir_files = defaultdict(list)
for r in c.fetchall():
    dir_files[r[3]].append(r)

qualifying_dirs = {}
for pdir, items in dir_files.items():
    media_items = [x for x in items if x[9] == 1]
    if len(media_items) <= 10:
        continue
    dup_media = [x for x in media_items if (x[5].lower(), x[7]) in p_by_name_size]
    if len(dup_media) > 0:
        qualifying_dirs[pdir] = {
            'all': items,
            'media': media_items,
            'dup_media': dup_media,
            'unique_media': [x for x in media_items if (x[5].lower(), x[7]) not in p_by_name_size],
            'non_media': [x for x in items if x[9] == 0]
        }

print(f"Total qualifying directories (media > 10 and dup_media >= 1): {len(qualifying_dirs)}")

# Categorize qualifying directories by duplication ratio:
# A) 100% of media files are in P:\ (or >= 95%)
# B) Partial overlap (some media files in P:\, some media files NOT in P:\)
full_dup_dirs = []
partial_dup_dirs = []

for pdir, info in sorted(qualifying_dirs.items()):
    med_cnt = len(info['media'])
    dup_cnt = len(info['dup_media'])
    uniq_cnt = len(info['unique_media'])
    tot_sz = sum(x[7] for x in info['all']) / (1024**3)
    dup_sz = sum(x[7] for x in info['dup_media']) / (1024**3)
    uniq_sz = sum(x[7] for x in info['unique_media']) / (1024**3)
    if uniq_cnt == 0:
        full_dup_dirs.append((pdir, med_cnt, dup_cnt, uniq_cnt, len(info['non_media']), tot_sz, dup_sz, uniq_sz))
    else:
        partial_dup_dirs.append((pdir, med_cnt, dup_cnt, uniq_cnt, len(info['non_media']), tot_sz, dup_sz, uniq_sz))

print(f"\n1. 100% Media-Duplicated Directories (0 unique media files): {len(full_dup_dirs)} dirs")
print(f"   Total media: {sum(x[1] for x in full_dup_dirs)}, Total non-media: {sum(x[4] for x in full_dup_dirs)}, Total GB: {sum(x[5] for x in full_dup_dirs):.2f} GB")

print(f"\n2. Partially Duplicated Directories (>=1 unique media file): {len(partial_dup_dirs)} dirs")
print(f"   Total media: {sum(x[1] for x in partial_dup_dirs)}, Dup media: {sum(x[2] for x in partial_dup_dirs)} ({sum(x[6] for x in partial_dup_dirs):.2f} GB), Unique media: {sum(x[3] for x in partial_dup_dirs)} ({sum(x[7] for x in partial_dup_dirs):.2f} GB), Non-media: {sum(x[4] for x in partial_dup_dirs)}")

print("\n=== ALL PARTIALLY DUPLICATED DIRECTORIES (SORTED BY DUP COUNT DESC) ===")
print(f"{'Directory':<78} | {'Med':>5} | {'Dup':>5} | {'Uniq':>5} | {'NonM':>4} | {'TotGB':>6} | {'DupGB':>6} | {'UniqGB':>6}")
print("-" * 135)
for pdir, med_cnt, dup_cnt, uniq_cnt, non_m, tot_sz, dup_sz, uniq_sz in sorted(partial_dup_dirs, key=lambda x: x[6], reverse=True):
    print(f"{pdir:<78} | {med_cnt:>5} | {dup_cnt:>5} | {uniq_cnt:>5} | {non_m:>4} | {tot_sz:>6.2f} | {dup_sz:>6.2f} | {uniq_sz:>6.2f}")

conn.close()
