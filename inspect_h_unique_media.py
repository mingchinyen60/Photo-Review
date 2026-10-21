import sqlite3
import sys
import os
from collections import defaultdict
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')
DB_PATH = r"c:\Users\mingc\OneDrive\文件\ATG\Photo-Review\photo_index.db"

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

c.execute("SELECT LOWER(name), size, rel_path FROM files WHERE size > 0 AND top_folder != '#recycle'")
p_name_size = set()
for lname, sz, rp in c.fetchall():
    parts = [p.lower() for p in rp.split('\\')]
    if '.@__thumb' in parts or lname in ('thumbs.db', '.ds_store', 'desktop.ini', 'zbthumbnail.info', 'picasa.ini', '.picasa.ini'):
        continue
    p_name_size.add((lname, sz))

def is_real_media(name, ext, size, is_med):
    if not is_med or name.startswith('._') or size == 0:
        return False
    return True

c.execute("SELECT id, path, top_folder, parent_rel_dir, rel_path, name, ext, size, mtime, is_media FROM h_files")
dir_files = defaultdict(list)
for r in c.fetchall():
    dir_files[r[3]].append(r)

# Exclude web-design e-book, saved HTML _files, and JaneyOffice web-design customer image assets
def is_web_or_software_asset_dir(pdir):
    lp = pdir.lower()
    if lp.endswith('_files') or lp.endswith('.files'):
        return True
    if 'e-book-hp-piggy' in lp or 'program files' in lp or 'janeyoffice' in lp:
        return True
    return False

print("=== PHOTO DIRECTORIES IN H:\\mcyen (>10 REAL MEDIA & >=1 DUP IN P:\\) ===")
photo_dirs = []
for pdir, items in sorted(dir_files.items()):
    if is_web_or_software_asset_dir(pdir):
        continue
    real_med = [x for x in items if is_real_media(x[5], x[6], x[7], x[9])]
    if len(real_med) <= 10:
        continue
    dup_med = [x for x in real_med if (x[5].lower(), x[7]) in p_name_size]
    if not dup_med:
        continue
    uniq_med = [x for x in real_med if (x[5].lower(), x[7]) not in p_name_size]
    non_med = [x for x in items if not is_real_media(x[5], x[6], x[7], x[9]) and not x[5].startswith('._') and x[7] > 0]
    photo_dirs.append((pdir, real_med, dup_med, uniq_med, non_med, items))

print(f"Total genuine photo directories (>10 media & >=1 dup in P:\\): {len(photo_dirs)}")

# Also check if any unique media in these photo_dirs are duplicated among each other (e.g. Data vs Data_2020)!
uniq_sigs = defaultdict(list)
for pdir, real_med, dup_med, uniq_med, non_med, items in photo_dirs:
    if uniq_med:
        min_dt = datetime.fromtimestamp(min(x[8] for x in uniq_med)).strftime('%Y-%m-%d')
        max_dt = datetime.fromtimestamp(max(x[8] for x in uniq_med)).strftime('%Y-%m-%d')
        ugb = sum(x[7] for x in uniq_med) / (1024**3)
        dgb = sum(x[7] for x in dup_med) / (1024**3)
        print(f"  [PARTIAL] {pdir:<65} | Med:{len(real_med):>4} | Dup:{len(dup_med):>4} ({dgb:>5.2f}GB) | Uniq:{len(uniq_med):>4} ({ugb:>5.2f}GB) | NonM:{len(non_med):>3} | UniqDates: {min_dt}..{max_dt}")
        for u in uniq_med:
            uniq_sigs[(u[5].lower(), u[7])].append((pdir, u))

print(f"\nTotal unique (name, size) media files across all partial folders: {len(uniq_sigs)} ({sum(k[1] for k in uniq_sigs)/(1024**3):.2f} GB)")

conn.close()
