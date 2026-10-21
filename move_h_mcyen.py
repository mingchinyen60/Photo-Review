import os
import sys
import time
import json
import shutil
import sqlite3
from collections import defaultdict
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

H_ROOT = r"H:\mcyen"
P_ROOT = r"P:\\"
DB_PATH = r"c:\Users\mingc\OneDrive\文件\ATG\Photo-Review\photo_index.db"
H_MANIFEST_PATH = r"c:\Users\mingc\OneDrive\文件\ATG\Photo-Review\h_mcyen_migration_manifest.jsonl"

from simulate_plan import apply_raw_rule

def is_real_media(name, ext, size, is_med):
    if not is_med or name.startswith('._') or size == 0:
        return False
    return True

def is_web_or_software_asset_dir(pdir):
    lp = pdir.lower()
    if lp.endswith('_files') or lp.endswith('.files'):
        return True
    if 'e-book-hp-piggy' in lp or 'program files' in lp or 'janeyoffice' in lp:
        return True
    return False

def map_h_unique_to_p(pdir, rel_path, name, ext, mtime):
    """
    Maps a unique photo/video file from a partially duplicated H:\mcyen photo folder
    into the clean P:\01_Chronological or P:\02_Collections structure.
    """
    dt = datetime.fromtimestamp(mtime)
    yr_str = dt.strftime('%Y')
    ym_str = dt.strftime('%Y-%m')

    if pdir == 'CTS\\103_PANA' or pdir == 'old_pc\\Chin_Data\\Chin_NB_D\\CTS\\MyDocuments\\Photo\\103_PANA':
        dest = os.path.join('02_Collections', 'Work_Company_CTS', 'CTS', '2008', name)
    elif 'Roadshow\\Photo' in pdir:
        dest = os.path.join('02_Collections', 'Work_Company_CTS', 'Company_Business', 'TV500_Roadshow_2004', name)
    elif 'My Document\\My Pictures' in pdir:
        dest = os.path.join('02_Collections', 'Family_Albums', 'Chin_NB_My_Pictures', name)
    elif pdir == 'Data\\Personal\\Photo\\2010_Jun_Nanto\\2010_Bronson' or pdir == 'Data_2020\\Personal\\105_PANA':
        dest = os.path.join('01_Chronological', '2010', '2010-04_Nanto_Bronson', name)
    elif pdir in ('Data\\Personal\\Photo\\Chicago\\Japan_Sakura', 'Data_2020\\Personal\\100_PANA'):
        dest = os.path.join('01_Chronological', '2010', '2010-04 明晉_日本美國出差', name)
    elif pdir == 'Data\\Photo\\100ANDRO':
        dest = os.path.join('01_Chronological', '2012', '2012_100ANDRO', name)
    elif pdir == 'Data\\Photo\\100KHH07':
        dest = os.path.join('01_Chronological', '2007', '2007-02  NeiMen內門', name)
    elif pdir == 'Data\\Photo\\FX01':
        dest = os.path.join('01_Chronological', '2007', '2007-02_FX01', name)
    elif pdir == 'Data\\Photo\\Sapporo':
        dest = os.path.join('01_Chronological', '2007', '2007-05_Sapporo', name)
    elif pdir == 'Data\\Photo\\Shanghai\\Dinner\\100_PANA':
        dest = os.path.join('02_Collections', 'Work_Company_CTS', 'Company_Business', 'Lea_Charless_farewell', name)
    elif pdir == 'Data\\Photo\\Shanghai\\Nanjing\\Small':
        dest = os.path.join('01_Chronological', '2006', '2006-06_Nanjing', name)
    elif pdir == 'Data\\Photo\\Shanghai\\TongLi' or '101TONLI' in pdir:
        sub = pdir.split('\\')[-1] if '101TONLI' in pdir else ''
        dest = os.path.join('01_Chronological', '2007', '2007-03_Shanghai_TongLi', sub, name)
    elif 'XinJiang' in pdir:
        sub = "\\".join(pdir.split('\\')[3:])
        dest = os.path.join('01_Chronological', '2007', '2007-10_XinJiang新彊', sub, name)
    elif pdir.startswith('Data\\Photo\\D70'):
        sub = "\\".join(pdir.split('\\')[3:])
        dest = os.path.join('01_Chronological', yr_str, f'{yr_str}_D70_{sub.replace("\\", "_")}' if sub else f'{yr_str}_D70', name)
    elif pdir == 'Photos\\MobileBackup\\iPhone\\2025\\07':
        dest = os.path.join('01_Chronological', '2025', '2025-07_Europe_Croatia', 'iPhone_2025_07', name)
    elif pdir == 'Photos\\MobileBackup\\iPhone\\2026\\07':
        dest = os.path.join('01_Chronological', '2026', '2026-07_Japan', 'iPhone_2026_07', name)
    elif pdir.startswith('USB2\\Thai'):
        sub = pdir.split('\\')[2] if len(pdir.split('\\')) > 2 else ''
        dest = os.path.join('01_Chronological', '2011', '2011-07_Thailand', sub, name)
    elif pdir == 'USB\\Photo\\Bronson':
        dest = os.path.join('01_Chronological', '2010', '2010-07_USA_西南巨環', 'Bronson_USB', name)
    elif pdir == 'USB\\Photo\\OutingPhoto':
        dest = os.path.join('02_Collections', 'Work_Company_CTS', 'CTS', '2009 員工旅遊', 'OutingPhoto', name)
    elif 'temp-output' in pdir:
        sub = pdir.split('\\')[-1]
        dest = os.path.join('01_Chronological', yr_str, f'{yr_str}_{sub}', name)
    else:
        dest = os.path.join('01_Chronological', yr_str, f'{ym_str}_From_mcyen', name)

    return os.path.normpath(apply_raw_rule(dest, ext))

def plan_and_execute(dry_run=True):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Load all existing P:\ (LOWER(name), size) signatures
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

    qualifying_dirs = []
    for pdir, items in sorted(dir_files.items()):
        if is_web_or_software_asset_dir(pdir):
            continue
        real_med = [x for x in items if is_real_media(x[5], x[6], x[7], x[9])]
        if len(real_med) <= 10:
            continue
        dup_med = [x for x in real_med if (x[5].lower(), x[7]) in p_name_size]
        if not dup_med:
            continue
        qualifying_dirs.append((pdir, items))

    print(f"Total qualifying H:\\mcyen directories (>10 photo files & has duplicates in P:\\): {len(qualifying_dirs)}")

    # Plan file actions across all qualifying directories
    # Watch out for GoogleDrive root: only move media files in GoogleDrive root, leave its 548 non-media docs in place!
    # For pure photo folders, move non-media sidecars/junk in those folders to P:\_Duplicates_Staging\mcyen as well so the folder in H:\mcyen is completely moved out.
    planned_moves = [] # (action, fid, src_rel, dst_rel, size)
    seen_new_p_sigs = set(p_name_size)

    for pdir, items in qualifying_dirs:
        is_gdrive_root = (pdir == 'GoogleDrive')
        for r in items:
            fid, fpath, tf, parent_rel, rel_path, name, ext, size, mtime, is_med = r
            if is_gdrive_root and not is_med:
                # Keep non-media work documents in H:\mcyen\GoogleDrive root untouched!
                continue
            sig = (name.lower(), size)
            if is_real_media(name, ext, size, is_med):
                if sig in seen_new_p_sigs:
                    # Already in P:\ (or already queued to be kept in P:\ from an earlier H:\mcyen folder) -> stage to P:\_Duplicates_Staging\mcyen
                    dst_rel = os.path.normpath(os.path.join('_Duplicates_Staging', 'mcyen', rel_path))
                    planned_moves.append(('STAGE_MCYEN_DUP', fid, rel_path, dst_rel, size))
                else:
                    # Unique photo/video from a duplicated folder (>10 photos) -> organize into P:\ according to our rules!
                    seen_new_p_sigs.add(sig)
                    dst_rel = map_h_unique_to_p(pdir, rel_path, name, ext, mtime)
                    planned_moves.append(('ORGANIZE_TO_P', fid, rel_path, dst_rel, size))
            else:
                # Non-media sidecar / AppleDouble / 0-byte stub inside a photo folder -> stage to P:\_Duplicates_Staging\mcyen
                dst_rel = os.path.normpath(os.path.join('_Duplicates_Staging', 'mcyen', rel_path))
                planned_moves.append(('STAGE_MCYEN_AUX', fid, rel_path, dst_rel, size))

    cnt_dup = sum(1 for x in planned_moves if x[0] == 'STAGE_MCYEN_DUP')
    gb_dup = sum(x[4] for x in planned_moves if x[0] == 'STAGE_MCYEN_DUP') / (1024**3)
    cnt_org = sum(1 for x in planned_moves if x[0] == 'ORGANIZE_TO_P')
    gb_org = sum(x[4] for x in planned_moves if x[0] == 'ORGANIZE_TO_P') / (1024**3)
    cnt_aux = sum(1 for x in planned_moves if x[0] == 'STAGE_MCYEN_AUX')
    gb_aux = sum(x[4] for x in planned_moves if x[0] == 'STAGE_MCYEN_AUX') / (1024**3)

    print(f"Planned Operations Summary:")
    print(f"  - STAGE_MCYEN_DUP (to P:\\_Duplicates_Staging\\mcyen): {cnt_dup} files ({gb_dup:.2f} GB)")
    print(f"  - ORGANIZE_TO_P   (unique photos in those folders -> P:\\01_Chronological & 02_Collections): {cnt_org} files ({gb_org:.2f} GB)")
    print(f"  - STAGE_MCYEN_AUX (sidecars/stubs in those photo folders -> P:\\_Duplicates_Staging\\mcyen): {cnt_aux} files ({gb_aux:.2f} GB)")
    print(f"  - Total files to move out of H:\\mcyen: {len(planned_moves)} ({gb_dup + gb_org + gb_aux:.2f} GB)")

    conn.close()
    return qualifying_dirs, planned_moves

if __name__ == '__main__':
    plan_and_execute(dry_run=True)
