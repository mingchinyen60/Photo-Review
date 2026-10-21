import os
import sys
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

def map_destination(rel_path, name, ext, mtime):
    """
    Maps a source relative path to its clean destination relative path under P:\
    (either 01_Chronological\... or 02_Collections\...), BEFORE applying the RAW\ suffix rule.
    """
    parts = rel_path.split('\\')
    tf = parts[0]
    sub1 = parts[1] if len(parts) > 1 else ""
    rest = "\\".join(parts[1:-1]) if len(parts) > 2 else ""
    rest2 = "\\".join(parts[2:-1]) if len(parts) > 3 else ""
    fname = parts[-1]
    dt = datetime.fromtimestamp(mtime)
    yr_str = dt.strftime('%Y')
    ym_str = dt.strftime('%Y-%m')

    # --- 1. COLLECTIONS (02_Collections) ---
    if tf == '2019北一女中三十重聚':
        return os.path.join('02_Collections', 'Reunion_2019北一女中三十重聚', rest, fname)

    if tf == '00新莊國小':
        if sub1 == '2023_dec_運動會':
            return os.path.join('01_Chronological', '2023', '2023-12_新莊國小運動會', rest2, fname)
        elif sub1 == '2014-07左營國小_教師專業評鑑初階實體研習':
            return os.path.join('02_Collections', 'School_新莊國小', '2014-07_左營國小_教師專業評鑑研習', rest2, fname)
        elif sub1 == '2016-05 聽聽本土客家競賽':
            return os.path.join('02_Collections', 'School_新莊國小', '2016-05_聽聽本土客家競賽', rest2, fname)
        elif sub1 == '2011-2012 2年10班':
            return os.path.join('02_Collections', 'School_新莊國小', '2011-2012_2年10班', rest2, fname)
        else:
            return os.path.join('02_Collections', 'School_新莊國小', 'Misc_Photos', rest, fname)

    if tf == 'Company&Business':
        return os.path.join('02_Collections', 'Work_Company_CTS', 'Company_Business', rest, fname)

    if tf == '00 CTS':
        return os.path.join('02_Collections', 'Work_Company_CTS', 'CTS', rest, fname)

    if tf == '106這些年的回憶_潔英':
        return os.path.join('02_Collections', 'Family_Albums', '106這些年的回憶_潔英', rest, fname)

    if tf == 'Bronson在新加坡':
        return os.path.join('02_Collections', 'Family_Albums', 'Bronson_在新加坡_2003-2004', rest, fname)

    if tf == 'Bronson在木棉庄的相片':
        return os.path.join('02_Collections', 'Family_Albums', 'Bronson_在木棉庄_2007-2008', rest, fname)

    if tf == 'film 錄影檔':
        return os.path.join('02_Collections', 'Family_Albums', '伯勳_成長相簿', 'film', rest, fname)

    if tf == 'Chin的旅遊相片':
        if sub1 == '2010-02吳哥窟錄音檔':
            return os.path.join('01_Chronological', '2010', '2010-02_吳哥窟', '2010-02吳哥窟錄音檔', rest2, fname)
        elif sub1 == '2013 CTS 員工旅遊':
            return os.path.join('02_Collections', 'Work_Company_CTS', 'CTS', '2013_CTS員工旅遊', rest2, fname)
        else:
            return os.path.join('02_Collections', 'Family_Albums', 'Chin的旅遊相片', rest, fname)

    if tf in ('D70', 'D80'):
        return os.path.join('02_Collections', 'Camera_Manuals_and_Tools', tf, rest, fname)

    if tf == 'Photes_x270_laptop':
        return os.path.join('02_Collections', 'Family_Albums', 'X270_Laptop_Backup', rest, fname)

    if tf == 'ForShare':
        return os.path.join('01_Chronological', '2006', '2006-07_ForShare', rest, fname)

    if tf == '00放在Apple的照片':
        if sub1 == '2010July西南巨環七日遊':
            return os.path.join('01_Chronological', '2010', '2010-07_USA_西南巨環', '2010July西南巨環七日遊_Apple', rest2, fname)
        else:
            return os.path.join('02_Collections', 'Family_Albums', 'Apple_My_Pictures_2009-2011', rest2 if sub1 == 'My Pictures' else rest, fname)

    # --- 2. HOME FOLDER (SPLIT BETWEEN CHRONOLOGICAL EVENTS & FAMILY ALBUMS) ---
    if tf == 'Home':
        if sub1 == '2025Europe':
            return os.path.join('01_Chronological', '2025', '2025-07_Europe_Croatia', rest2, fname)
        elif sub1 == '伯勳':
            sub2 = parts[2] if len(parts) > 2 else ""
            if sub2 == 'Bali 2003':
                rest3 = "\\".join(parts[3:-1]) if len(parts) > 4 else ""
                return os.path.join('01_Chronological', '2003', '2003_Bali_巴里島', rest3, fname)
            elif sub2 == '2012_Oct_BronsonBirthday':
                rest3 = "\\".join(parts[3:-1]) if len(parts) > 4 else ""
                return os.path.join('01_Chronological', '2012', '2012-10_Bronson_Birthday', rest3, fname)
            else:
                return os.path.join('02_Collections', 'Family_Albums', '伯勳_成長相簿', rest2, fname)
        elif sub1 == '2001-12貨櫃節':
            return os.path.join('01_Chronological', '2001', '2001-12_貨櫃節', rest2, fname)
        elif sub1 == '20020621生日':
            return os.path.join('01_Chronological', '2002', '2002-06-21_生日', rest2, fname)
        elif sub1 == '20020721柴山泡茶':
            return os.path.join('01_Chronological', '2002', '2002-07-21_柴山泡茶', rest2, fname)
        elif sub1 == '20020810台糖':
            return os.path.join('01_Chronological', '2002', '2002-08-10_台糖', rest2, fname)
        elif sub1 == '200306菲律賓出差':
            return os.path.join('01_Chronological', '2003', '2003-06_菲律賓出差', rest2, fname)
        elif sub1 == '爸媽92日本行':
            return os.path.join('01_Chronological', '2003', '2003-05_爸媽日本行', rest2, fname)
        elif sub1 == '2012-02':
            return os.path.join('01_Chronological', '2012', '2012-02_生活隨拍', rest2, fname)
        elif sub1 == '2012_TongHwa':
            return os.path.join('01_Chronological', '2012', '2012-04_TongHwa', rest2, fname)
        elif sub1 == 'SmallJen':
            return os.path.join('02_Collections', 'Family_Albums', 'SmallJen', rest2, fname)
        elif sub1 in ('Kevin', 'Winnie', '韋勳', '守慧', '薇娟', 'LILY', 'BALLOONS', '相片集', '桌面', '輸出', 'DCIM'):
            return os.path.join('02_Collections', 'Family_Albums', f'Home_{sub1}', rest2, fname)
        else:
            return os.path.join('02_Collections', 'Family_Albums', 'Home_Misc', rest, fname)

    # --- 3. TRAVEL & D7100 & 102D7100 ---
    if tf == 'Travel':
        if sub1 == 'Croatia2025':
            return os.path.join('01_Chronological', '2025', '2025-07_Europe_Croatia', rest2, fname)
        elif sub1 == '2026Japan':
            return os.path.join('01_Chronological', '2026', '2026-07_Japan', rest2, fname)
        else:
            return os.path.join('01_Chronological', yr_str, f'{yr_str}_Travel_{sub1}', rest2, fname)

    if tf == '102D7100':
        return os.path.join('01_Chronological', '2014-2017_D7100_西安_加州', rest, fname)

    if tf == 'D7100':
        if sub1 in ('2023Europe', '2023Europe2', '2023Europe_JPG'):
            tag = 'JPG_Export' if sub1 == '2023Europe_JPG' else rest2
            return os.path.join('01_Chronological', '2023', '2023-07_Europe', tag, fname)
        elif sub1 == 'China2023':
            return os.path.join('01_Chronological', '2023', '2023-10_China', rest2, fname)
        elif sub1 == '2023_Nov_墾丁恆春':
            return os.path.join('01_Chronological', '2023', '2023-11_墾丁恆春', rest2, fname)
        elif sub1 == '110D7100':
            return os.path.join('01_Chronological', '2023', '2023-11_D7100_110', rest2, fname)
        elif sub1 == '111D7100':
            return os.path.join('01_Chronological', '2023', '2023-12_新莊國小運動會', rest2, fname)
        elif sub1 == '2024_Loveland_US':
            return os.path.join('01_Chronological', '2024', '2024-05_Loveland_US', rest2, fname)
        elif sub1 == '112D7100':
            # 112D7100 spans late 2023 to 2025-07; route remaining unique files by their capture year/month!
            if yr_str == '2025':
                return os.path.join('01_Chronological', '2025', '2025-07_Europe_Croatia', '112D7100', rest2, fname)
            elif yr_str == '2024':
                return os.path.join('01_Chronological', '2024', f'{ym_str}_D7100_112', rest2, fname)
            else:
                return os.path.join('01_Chronological', yr_str, f'{ym_str}_D7100_112', rest2, fname)
        elif sub1 == 'CPCDA':
            return os.path.join('01_Chronological', '2019', '2019-10_CPCDA', rest2, fname)
        elif sub1 in ('西安_加州', '102D7100'):
            # Route by year or keep in 2014-2017_西安_加州? Let's check years inside 西安_加州!
            return os.path.join('01_Chronological', yr_str, f'{yr_str}_西安_加州_D7100', rest2, fname)
        elif sub1 in ('101D7100', '104D7100', '105D7100'):
            return os.path.join('01_Chronological', yr_str, f'{ym_str}_D7100_{sub1[:3]}', rest2, fname)
        else:
            return os.path.join('01_Chronological', yr_str, f'{ym_str}_D7100', rest, fname)

    # --- 4. YEAR & EVENT FOLDERS AT ROOT ---
    if tf == 'Photos_2001':
        return os.path.join('01_Chronological', '2001', '2001-12_貨櫃節', rest2 if sub1 else '', fname)

    if tf == 'photos_2001 新加坡旅遊':
        return os.path.join('01_Chronological', '2001', '2001-07_新加坡旅遊', rest, fname)

    if tf == 'Casico':
        if sub1 in ('2004', '2005', '2006'):
            return os.path.join('01_Chronological', sub1, f'{sub1}_Casio_Camera', rest2, fname)
        return os.path.join('01_Chronological', yr_str, f'{yr_str}_Casio_Camera', rest, fname)

    if tf in ('photos_2004', 'photos_2005', 'photos_2006', 'photos_2007', 'photos_2008', 'photos_2009', 'photos_2010', 'Photos_2011', 'Photos_2012', 'Photos_2014'):
        year_num = tf.split('_')[1]
        return os.path.join('01_Chronological', year_num, rest if rest else f'{year_num}_Misc', fname)

    if tf == 'Photos_2010 USA':
        return os.path.join('01_Chronological', '2010', '2010-07_USA_西南巨環', rest, fname)

    if tf in ('2010-02吳哥窟', 'Photos_2010-02吳哥窟'):
        return os.path.join('01_Chronological', '2010', '2010-02_吳哥窟', rest, fname)

    if tf in ('2011Tailand', 'Photos_2011Tailand'):
        return os.path.join('01_Chronological', '2011', '2011-07_Thailand', 'Part1', rest, fname)

    if tf in ('2011Tailand2', 'Photos_2011Tailand2'):
        return os.path.join('01_Chronological', '2011', '2011-07_Thailand', 'Part2', rest, fname)

    if tf in ('movies-2011Tailand', 'Photos_2011Tailand-movies'):
        return os.path.join('01_Chronological', '2011', '2011-07_Thailand', 'Movies', rest, fname)

    if tf == '2013-01-25 廣州_香港六日行':
        return os.path.join('01_Chronological', '2013', '2013-01-25 廣州_香港六日行', rest, fname)

    if tf == 'Photos_2013':
        return os.path.join('01_Chronological', '2013', rest if rest else '2013_Misc', fname)

    if tf in ('2013-07北海道-東京', 'Photos_2013-07東京北海道自遊行'):
        if sub1 == 'photos_Kevin':
            return os.path.join('01_Chronological', '2013', '2013-07_東京北海道自遊行', 'Kevin', rest2, fname)
        elif not sub1 or len(parts) == 2:
            return os.path.join('01_Chronological', '2013', '2013-07_東京北海道自遊行', '00_旅遊手冊與地圖', fname)
        else:
            return os.path.join('01_Chronological', '2013', '2013-07_東京北海道自遊行', rest, fname)

    if tf == 'Photos_2014-08 Tokyo':
        return os.path.join('01_Chronological', '2014', '2014-08_Tokyo', rest, fname)

    if tf in ('2024', 'Photo'):
        return os.path.join('01_Chronological', '2024', rest if rest else '2024_Misc', fname)

    return os.path.join('01_Chronological', yr_str, tf, rest, fname)

def apply_raw_rule(dest_rel_path, ext):
    """
    If file is .nef or .nksc, place inside RAW\ subfolder of its event folder (unless already in a folder named RAW or NKSC_PARAM).
    """
    if ext in ('.nef', '.nksc'):
        dir_name, file_name = os.path.split(dest_rel_path)
        parts = dir_name.split('\\')
        # Check if 'raw' is already in the last two folder names
        if any(p.lower() == 'raw' for p in parts[-2:]):
            return dest_rel_path
        if parts[-1].upper() == 'NKSC_PARAM':
            # e.g. ...\Event\NKSC_PARAM\file.nksc -> ...\Event\RAW\NKSC_PARAM\file.nksc
            return os.path.join("\\".join(parts[:-1]), 'RAW', 'NKSC_PARAM', file_name)
        return os.path.join(dir_name, 'RAW', file_name)
    return dest_rel_path

c.execute("SELECT id, path, top_folder, rel_path, name, ext, size, mtime, quick_hash FROM files")
all_rows = c.fetchall()

# Test mapping on all real files
mapped_summary = defaultdict(lambda: [0, 0])
unhandled = []
for r in all_rows:
    fid, fpath, tf, rel_path, name, ext, size, mtime, qh = r
    if is_junk(rel_path, name, ext):
        continue
    dest = map_destination(rel_path, name, ext, mtime)
    dest = apply_raw_rule(dest, ext)
    # Normalize slashes and empty segments
    dest = os.path.normpath(dest)
    dparts = dest.split('\\')
    key = "\\".join(dparts[:3]) if len(dparts) >= 3 else dest
    mapped_summary[key][0] += 1
    mapped_summary[key][1] += size

print(f"=== SIMULATED TARGET STRUCTURE (BEFORE DEDUP FILTERING): {len(mapped_summary)} TARGET BUCKETS ===")
for k in sorted(mapped_summary.keys()):
    cnt, sz = mapped_summary[k]
    print(f"  {k:<65} | {cnt:>6}f | {sz/(1024**3):>7.2f} GB")

conn.close()
