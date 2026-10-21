import os
import sys
import time
import json
import sqlite3
import hashlib
import stat
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

H_ROOT = r"H:\mcyen"
DB_PATH = r"c:\Users\mingc\OneDrive\文件\ATG\Photo-Review\photo_index.db"
MANIFEST_PATH = r"c:\Users\mingc\OneDrive\文件\ATG\Photo-Review\h_mcyen_cleanup_manifest.jsonl"
STAGING_DIR = os.path.join(H_ROOT, "_Duplicate_Storage")

PROTECTED_TOP_FOLDERS = {"GoogleDrive", "Photos", "_Duplicate_Storage"}

def clear_readonly(path):
    try:
        os.chmod(path, stat.S_IWRITE)
    except Exception:
        pass

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

def safe_move(src, dst):
    clear_readonly(src)
    if os.path.exists(dst):
        clear_readonly(dst)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    os.rename(src, dst)

def execute_consolidation():
    start_time = time.time()
    os.makedirs(STAGING_DIR, exist_ok=True)
    mf = open(MANIFEST_PATH, 'w', encoding='utf-8')

    def log_move(action, src_rel, dst_rel, size, note=""):
        mf.write(json.dumps({
            'action': action,
            'src': src_rel,
            'dst': dst_rel,
            'size': size,
            'note': note,
            'time': time.strftime('%Y-%m-%d %H:%M:%S')
        }, ensure_ascii=False) + '\n')

    print("=== Step 1: Consolidate GDrive Backups ===", flush=True)
    # Target: H:\mcyen\GDrive_backup
    gdrive_backup_target = os.path.join(H_ROOT, "GDrive_backup")
    os.makedirs(gdrive_backup_target, exist_ok=True)

    # Empty legacy folders: GDrive_Backup_Nov2021, GDrive_Backup_Jul2022
    for empty_folder in ["GDrive_Backup_Nov2021", "GDrive_Backup_Jul2022"]:
        fp = os.path.join(H_ROOT, empty_folder)
        if os.path.exists(fp):
            try:
                os.rmdir(fp)
                print(f"Removed empty legacy folder: {empty_folder}", flush=True)
            except Exception as e:
                print(f"Notice on {empty_folder}: {e}", flush=True)

    # Move contents of GooogleDrive_backup_Jul2023
    source_gdrive_2023 = os.path.join(H_ROOT, "GooogleDrive_backup_Jul2023")
    if os.path.exists(source_gdrive_2023):
        for item in os.listdir(source_gdrive_2023):
            s = os.path.join(source_gdrive_2023, item)
            d = os.path.join(gdrive_backup_target, item)
            try:
                sz = os.path.getsize(s) if os.path.isfile(s) else 0
                safe_move(s, d)
                log_move('CONSOLIDATE_GDRIVE', os.path.relpath(s, H_ROOT), os.path.relpath(d, H_ROOT), sz)
            except Exception as e:
                print(f"Error moving {item} in GDrive backup: {e}", flush=True)
        try:
            if not os.listdir(source_gdrive_2023):
                os.rmdir(source_gdrive_2023)
                print("Removed emptied GooogleDrive_backup_Jul2023", flush=True)
        except Exception as e:
            print(f"Notice on GooogleDrive_backup_Jul2023: {e}", flush=True)

    print("\n=== Step 2: Indexing Data Folders for Consolidation ===", flush=True)
    # We consolidate Data_2019, Data_2020, Data_2021 into Data
    # For every file in Data_YYYY, its canonical path under Data is Data\<rel_inside_Data_YYYY>
    data_dir = os.path.join(H_ROOT, "Data")
    os.makedirs(data_dir, exist_ok=True)

    # Map current files in Data by rel_path (relative to Data root)
    # rel_inside_data -> (full_path, size, mtime)
    print("Scanning current files in H:\\mcyen\\Data ...", flush=True)
    data_files = {}
    for root, dirs, files in os.walk(data_dir):
        for f in files:
            fp = os.path.join(root, f)
            rel = os.path.relpath(fp, data_dir)
            try:
                st = os.stat(fp)
                data_files[rel.lower()] = {
                    'rel_path': rel,
                    'full_path': fp,
                    'size': st.st_size,
                    'mtime': st.st_mtime
                }
            except Exception:
                pass
    print(f"Found {len(data_files)} existing files in Data.", flush=True)

    # Process Data_2019, Data_2020, Data_2021 in chronological order (2019, then 2020, then 2021)
    # This allows newer years to naturally update older years
    for yr_folder in ["Data_2019", "Data_2020", "Data_2021"]:
        yr_dir = os.path.join(H_ROOT, yr_folder)
        if not os.path.exists(yr_dir):
            continue
        print(f"Processing {yr_folder} ...", flush=True)
        moved_count = 0
        staged_dup_count = 0
        staged_older_count = 0
        promoted_newer_count = 0

        # Walk yr_dir
        for root, dirs, files in os.walk(yr_dir):
            for f in files:
                src_fp = os.path.join(root, f)
                rel = os.path.relpath(src_fp, yr_dir)
                rel_key = rel.lower()
                try:
                    st_src = os.stat(src_fp)
                except Exception:
                    continue

                src_sz = st_src.st_size
                src_mtime = st_src.st_mtime

                if rel_key not in data_files:
                    # Unique file only in Data_YYYY -> Move into Data
                    dst_fp = os.path.join(data_dir, rel)
                    try:
                        safe_move(src_fp, dst_fp)
                        data_files[rel_key] = {
                            'rel_path': rel,
                            'full_path': dst_fp,
                            'size': src_sz,
                            'mtime': src_mtime
                        }
                        log_move('DATA_MERGE_UNIQUE', os.path.relpath(src_fp, H_ROOT), os.path.relpath(dst_fp, H_ROOT), src_sz, f"from {yr_folder}")
                        moved_count += 1
                    except Exception as e:
                        print(f"Error moving {src_fp} to {dst_fp}: {e}", flush=True)
                else:
                    existing = data_files[rel_key]
                    exist_sz = existing['size']
                    exist_mtime = existing['mtime']
                    exist_fp = existing['full_path']

                    # Check if exact duplicate (size match and quick hash match)
                    is_exact_dup = False
                    if src_sz == exist_sz:
                        if src_sz <= 10240:
                            is_exact_dup = True
                        else:
                            try:
                                h_src = get_quick_hash(src_fp, src_sz)
                                h_exist = get_quick_hash(exist_fp, exist_sz)
                                if h_src == h_exist:
                                    is_exact_dup = True
                            except Exception:
                                pass

                    if is_exact_dup:
                        # Exact duplicate -> Move Data_YYYY copy to _Duplicate_Storage
                        stage_dst = os.path.join(STAGING_DIR, yr_folder, rel)
                        try:
                            safe_move(src_fp, stage_dst)
                            log_move('DATA_STAGE_DUP', os.path.relpath(src_fp, H_ROOT), os.path.relpath(stage_dst, H_ROOT), src_sz, f"exact dup of Data\\{existing['rel_path']}")
                            staged_dup_count += 1
                        except Exception as e:
                            print(f"Error staging duplicate {src_fp}: {e}", flush=True)
                    else:
                        # Different content/size: Rule is keep newer version
                        if src_mtime > exist_mtime:
                            # src in Data_YYYY is newer! Move older file from Data to _Duplicate_Storage, promote src
                            older_stage_dst = os.path.join(STAGING_DIR, "Data_Older_Versions", existing['rel_path'])
                            dst_fp = os.path.join(data_dir, rel)
                            try:
                                safe_move(exist_fp, older_stage_dst)
                                log_move('DATA_STAGE_OLDER', os.path.relpath(exist_fp, H_ROOT), os.path.relpath(older_stage_dst, H_ROOT), exist_sz, f"superseded by newer {yr_folder}")
                                safe_move(src_fp, dst_fp)
                                data_files[rel_key] = {
                                    'rel_path': rel,
                                    'full_path': dst_fp,
                                    'size': src_sz,
                                    'mtime': src_mtime
                                }
                                log_move('DATA_PROMOTE_NEWER', os.path.relpath(src_fp, H_ROOT), os.path.relpath(dst_fp, H_ROOT), src_sz, f"promoted newer version from {yr_folder}")
                                promoted_newer_count += 1
                            except Exception as e:
                                print(f"Error promoting newer file {src_fp}: {e}", flush=True)
                        else:
                            # src in Data_YYYY is older or equal -> stage src to _Duplicate_Storage
                            stage_dst = os.path.join(STAGING_DIR, yr_folder, rel)
                            try:
                                safe_move(src_fp, stage_dst)
                                log_move('DATA_STAGE_OLDER', os.path.relpath(src_fp, H_ROOT), os.path.relpath(stage_dst, H_ROOT), src_sz, f"older than Data\\{existing['rel_path']}")
                                staged_older_count += 1
                            except Exception as e:
                                print(f"Error staging older file {src_fp}: {e}", flush=True)

        print(f"Finished {yr_folder}: merged_unique={moved_count}, staged_dup={staged_dup_count}, staged_older={staged_older_count}, promoted_newer={promoted_newer_count}", flush=True)
        # Clean up empty folders in yr_dir
        for root, dirs, files in os.walk(yr_dir, topdown=False):
            for d in dirs:
                dp = os.path.join(root, d)
                try:
                    if not os.listdir(dp):
                        os.rmdir(dp)
                except Exception:
                    pass
        try:
            if not os.listdir(yr_dir):
                os.rmdir(yr_dir)
                print(f"Removed emptied folder {yr_folder}", flush=True)
        except Exception:
            pass

    print("\n=== Step 3: Selective Deduplication of USB & USB2 ===", flush=True)
    # Build a lookup of all kept files in Data, GDrive_backup, and P:\ (size, quick_hash)
    # Load all signatures from Data and GDrive_backup
    print("Building reference index of kept files for USB deduplication ...", flush=True)
    ref_sigs = defaultdict(list) # (name_lower, size) -> [full_path]
    
    # 1. Add Data files
    for rk, info in data_files.items():
        nm = os.path.basename(info['rel_path']).lower()
        sz = info['size']
        if sz > 0:
            ref_sigs[(nm, sz)].append(info['full_path'])

    # 2. Add GDrive_backup files
    for root, dirs, files in os.walk(gdrive_backup_target):
        for f in files:
            fp = os.path.join(root, f)
            try:
                sz = os.stat(fp).st_size
                if sz > 0:
                    ref_sigs[(f.lower(), sz)].append(fp)
            except Exception:
                pass

    # 3. Add P:\ files from database
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT LOWER(name), size, path FROM files WHERE size > 0 AND top_folder != '#recycle'")
    for nm, sz, p_path in c.fetchall():
        ref_sigs[(nm, sz)].append(p_path)
    conn.close()

    print(f"Total reference signatures for comparison: {len(ref_sigs)}", flush=True)

    for usb_top in ["USB", "USB2"]:
        usb_dir = os.path.join(H_ROOT, usb_top)
        if not os.path.exists(usb_dir):
            continue
        print(f"Reviewing {usb_top} for duplicates ...", flush=True)
        staged_usb_count = 0
        staged_usb_bytes = 0
        kept_usb_count = 0

        for root, dirs, files in os.walk(usb_dir):
            for f in files:
                fp = os.path.join(root, f)
                rel = os.path.relpath(fp, H_ROOT)
                try:
                    sz = os.stat(fp).st_size
                except Exception:
                    continue

                if sz == 0:
                    kept_usb_count += 1
                    continue

                sig = (f.lower(), sz)
                if sig in ref_sigs:
                    # Potential match, verify with quick_hash if > 10KB
                    is_match = False
                    if sz <= 10240:
                        is_match = True
                        matched_target = ref_sigs[sig][0]
                    else:
                        try:
                            h_src = get_quick_hash(fp, sz)
                            for ref_fp in ref_sigs[sig]:
                                try:
                                    if os.path.exists(ref_fp) and os.path.getsize(ref_fp) == sz:
                                        if get_quick_hash(ref_fp, sz) == h_src:
                                            is_match = True
                                            matched_target = ref_fp
                                            break
                                except Exception:
                                    pass
                        except Exception:
                            pass

                    if is_match:
                        # Move duplicate out to _Duplicate_Storage
                        dst_fp = os.path.join(STAGING_DIR, rel)
                        try:
                            safe_move(fp, dst_fp)
                            log_move(f'{usb_top}_STAGE_DUP', rel, os.path.relpath(dst_fp, H_ROOT), sz, f"dup of {matched_target}")
                            staged_usb_count += 1
                            staged_usb_bytes += sz
                        except Exception as e:
                            print(f"Error staging {fp}: {e}", flush=True)
                    else:
                        kept_usb_count += 1
                else:
                    kept_usb_count += 1

        print(f"Finished {usb_top}: staged {staged_usb_count} duplicate files ({staged_usb_bytes/(1024**3):.2f} GB), kept {kept_usb_count} unique files in place.", flush=True)

        # Clean empty directories under USB/USB2
        for root, dirs, files in os.walk(usb_dir, topdown=False):
            for d in dirs:
                dp = os.path.join(root, d)
                try:
                    if not os.listdir(dp):
                        os.rmdir(dp)
                except Exception:
                    pass

    mf.close()
    elapsed = time.time() - start_time
    print(f"\nAll consolidation and deduplication operations completed in {elapsed:.1f}s!", flush=True)

if __name__ == '__main__':
    execute_consolidation()
