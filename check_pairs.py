import sqlite3
import sys
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

# Check specific folder pairs to see what is unique in each
def compare_folders(prefix1, prefix2):
    f1 = [r for r in real_files if r[3].startswith(prefix1 + "\\") or r[3] == prefix1]
    f2 = [r for r in real_files if r[3].startswith(prefix2 + "\\") or r[3] == prefix2]
    s1 = set((r[4].lower(), r[6]) for r in f1 if r[6] > 0)
    s2 = set((r[4].lower(), r[6]) for r in f2 if r[6] > 0)
    common = s1 & s2
    only1 = s1 - s2
    only2 = s2 - s1
    print(f"Compare [{prefix1}] ({len(f1)} files, {len(s1)} unique) vs [{prefix2}] ({len(f2)} files, {len(s2)} unique):")
    print(f"  Common unique files: {len(common)} | Only in [{prefix1}]: {len(only1)} | Only in [{prefix2}]: {len(only2)}")

print("=== PAIRWISE SUBFOLDER CONTAINMENT CHECKS ===")
compare_folders("Home\\2025Europe", "Travel\\Croatia2025")
compare_folders("D7100\\112D7100", "Home\\2025Europe")
compare_folders("D7100\\112D7100", "Travel\\Croatia2025")
compare_folders("D7100\\112D7100", "D7100\\2024_Loveland_US")
compare_folders("D7100\\111D7100", "00新莊國小\\2023_dec_運動會")
compare_folders("D7100\\2023Europe", "D7100\\2023Europe2")
compare_folders("D7100\\2023Europe", "D7100\\2023Europe_JPG")
compare_folders("102D7100", "D7100\\102D7100")
compare_folders("D7100\\102D7100", "D7100\\西安_加州")
compare_folders("2010-02吳哥窟", "Photos_2010-02吳哥窟")
compare_folders("2011Tailand", "Photos_2011Tailand")
compare_folders("2011Tailand2", "Photos_2011Tailand2")
compare_folders("movies-2011Tailand", "Photos_2011Tailand-movies")
compare_folders("2013-01-25 廣州_香港六日行", "Photos_2013\\2013-01-25 廣州_香港六日行")
compare_folders("2013-07北海道-東京", "Photos_2013-07東京北海道自遊行")
compare_folders("Casico", "photos_2004")
compare_folders("Casico", "photos_2006")
compare_folders("00放在Apple的照片", "Photos_2010 USA")
compare_folders("film 錄影檔", "Home")

# Distribution of unique real files by year (based on folder year or mtime year)
print("\n=== UNIQUE REAL FILES BY YEAR (MTIME) ===")
seen_sigs = set()
year_stats = defaultdict(lambda: [0, 0])
for r in real_files:
    sig = (r[4].lower(), r[6])
    if r[6] > 0:
        if sig in seen_sigs:
            continue
        seen_sigs.add(sig)
    yr = datetime.fromtimestamp(r[7]).strftime('%Y')
    year_stats[yr][0] += 1
    year_stats[yr][1] += r[6]

for yr in sorted(year_stats.keys()):
    print(f"  {yr}: {year_stats[yr][0]:>6} unique files | {year_stats[yr][1]/(1024**3):>7.2f} GB")

conn.close()
