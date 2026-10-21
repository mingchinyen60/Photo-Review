import sqlite3
import sys
from collections import defaultdict
from datetime import datetime
from move_h_mcyen import is_real_media, is_web_or_software_asset_dir

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

c.execute("SELECT id, path, top_folder, parent_rel_dir, rel_path, name, ext, size, mtime, is_media FROM h_files")
dir_files = defaultdict(list)
for r in c.fetchall():
    dir_files[r[3]].append(r)

print("=== CHECK GoogleDrive UNIQUE MEDIA ===")
for r in dir_files['GoogleDrive']:
    if is_real_media(r[5], r[6], r[7], r[9]):
        if (r[5].lower(), r[7]) not in p_name_size:
            dt = datetime.fromtimestamp(r[8]).strftime('%Y-%m-%d')
            print(f"  {r[5]:<55} | {r[7]/(1024**2):>8.2f} MB | {dt}")

print("\n=== CHECK OTHER FOLDERS IN H:\\mcyen\\Photos, Data\\Photo, Data\\Personal\\Photo, USB, USB2 (>10 MEDIA, 0 DUP IN P:\\) ===")
for pdir, items in sorted(dir_files.items()):
    if is_web_or_software_asset_dir(pdir):
        continue
    if not any(pdir.startswith(pref) for pref in ('Photos', 'D7100', 'Data\\Photo', 'Data\\Personal\\Photo', 'Data_2020\\Personal', 'USB\\Photo', 'USB2\\Disk_Backup\\Photos', 'USB2\\Thai')):
        continue
    real_med = [x for x in items if is_real_media(x[5], x[6], x[7], x[9])]
    if len(real_med) <= 10:
        continue
    dup_med = [x for x in real_med if (x[5].lower(), x[7]) in p_name_size]
    if len(dup_med) == 0:
        tot_gb = sum(x[7] for x in real_med) / (1024**3)
        print(f"  [0-DUP] {pdir:<70} | Med: {len(real_med):>5} | {tot_gb:>6.2f} GB")

conn.close()
