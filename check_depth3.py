import os
import sys
import re
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
    
    # Low priority: generic camera dumps, generic duplicates, root loose folders
    if tf in ('102D7100', 'Photo', 'Photos_2001', 'film 錄影檔', 'movies-2011Tailand', '2011Tailand', '2011Tailand2', '2010-02吳哥窟', '2013-01-25 廣州_香港六日行', '2013-07北海道-東京'):
        return 10
    if tf in ('Casico', '00放在Apple的照片', 'Bronson在木棉庄的相片'):
        return 20
    if tf == 'D7100':
        if sub in ('101D7100', '102D7100', '104D7100', '105D7100', '110D7100', '111D7100', '112D7100', '2023Europe2'):
            return 25
        return 75
    if tf == 'Travel' and sub == 'Croatia2025':
        # Home\2025Europe has 4878 files and rich day-by-day subfolders? Wait, let's check subfolders of Home\2025Europe vs Travel\Croatia2025!
        return 60
    if tf == 'Home' and sub == '2025Europe':
        return 70
    if tf.startswith('Photos_') or tf.startswith('photos_'):
        # Check if internal duplicate subfolder like "2014-02Travel_Taipei" vs "2014-02-05 台北淡水3日遊"
        if sub in ('2014-02Travel_Taipei', '2013 photos', '104_PANA', '2008-08 苗栗'):
            return 50
        return 85
    if tf in ('00新莊國小', '2019北一女中三十重聚', '00 CTS', 'Company&Business', '106這些年的回憶_潔英'):
        return 80
    return 60

# Let's inspect depth-3 of Home\2025Europe and Travel\Croatia2025 and Travel\2026Japan first!
c.execute("SELECT rel_path, size FROM files WHERE top_folder IN ('Home', 'Travel', 'D7100')")
sub3 = defaultdict(lambda: [0, 0])
for rp, sz in c.fetchall():
    if is_junk(rp, rp.split('\\')[-1], ''): continue
    parts = rp.split('\\')
    if parts[0] in ('Home', 'Travel', 'D7100') and len(parts) >= 3:
        k = "\\".join(parts[:3])
        sub3[k][0] += 1
        sub3[k][1] += sz

print("=== DEPTH-3 STRUCTURE OF Home, Travel, D7100 ===")
for k, (cnt, sz) in sorted(sub3.items()):
    if cnt > 5 or sz > 100*1024*1024:
        print(f"  {k:<65} | {cnt:>5}f | {sz/(1024**3):>6.2f} GB")

conn.close()
