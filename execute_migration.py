import os
import sys
import time
import json
import sqlite3
from collections import defaultdict
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

ROOT = r"P:\\"
DB_PATH = r"c:\Users\mingc\OneDrive\文件\ATG\Photo-Review\photo_index.db"
MANIFEST_PATH = r"c:\Users\mingc\OneDrive\文件\ATG\Photo-Review\migration_manifest.jsonl"

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
    parts = rel_path.split('\\')
    tf = parts[0]
    sub = parts[1] if len(parts) > 1 else ""
    
    if tf in ('102D7100', 'Photo', 'Photos_2001', 'film 錄影檔', 'movies-2011Tailand', '2011Tailand', '2011Tailand2', '2010-02吳哥窟', '2013-01-25 廣州_香港六日行', '2013-07北海道-東京'):
        return (10, -len(rel_path))
    if tf in ('Casico', '00放在Apple的照片', 'Bronson在木棉庄的相片'):
        return (20, -len(rel_path))
    if tf == 'D7100':
        if sub in ('101D7100', '102D7100', '104D7100', '105D7100', '110D7100', '111D7100', '112D7100', '2023Europe2'):
            return (25, -len(rel_path))
        return (75, -len(rel_path))
    if tf == 'Travel' and sub == 'Croatia2025':
        return (60, -len(rel_path))
    if tf == 'Home' and sub == '2025Europe':
        return (70, -len(rel_path))
    if tf.startswith('Photos_') or tf.startswith('photos_'):
        if sub in ('2014-02Travel_Taipei', '2013 photos', '104_PANA', '2008-08 苗栗'):
            return (50, -len(rel_path))
        return (85, -len(rel_path))
    if tf in ('00新莊國小', '2019北一女中三十重聚', '00 CTS', 'Company&Business', '106這些年的回憶_潔英'):
        return (80, -len(rel_path))
    return (60, -len(rel_path))

from simulate_plan import map_destination, apply_raw_rule

def run_migration():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT id, path, top_folder, rel_path, name, ext, size, mtime, quick_hash FROM files")
    all_rows = c.fetchall()

    real_files = []
    junk_files = []
    for r in all_rows:
        fid, fpath, tf, rel_path, name, ext, size, mtime, qh = r
        jtype = is_junk(rel_path, name, ext)
        if jtype:
            junk_files.append((r, jtype))
        else:
            real_files.append(r)

    sig_groups = defaultdict(list)
    for r in real_files:
        fid, fpath, tf, rel_path, name, ext, size, mtime, qh = r
        if size == 0:
            sig = ('zero', name.lower(), tf)
        elif qh:
            sig = ('hash', size, qh)
        else:
            sig = ('unique_size', fid)
        sig_groups[sig].append(r)

    keep_list = []
    dup_list = []

    for sig, items in sig_groups.items():
        if len(items) == 1:
            keep_list.append(items[0])
        else:
            items_sorted = sorted(items, key=lambda x: (get_source_priority(x[3]), x[3]), reverse=True)
            winner = items_sorted[0]
            keep_list.append(winner)
            for loser in items_sorted[1:]:
                dup_list.append((loser, winner[3]))

    # Build destination paths for keep_list
    dest_map = {}
    planned_ops = [] # (action, fid, src_rel, dst_rel, size, note)

    for r in keep_list:
        fid, fpath, tf, rel_path, name, ext, size, mtime, qh = r
        dest = os.path.normpath(apply_raw_rule(map_destination(rel_path, name, ext, mtime), ext))
        if dest.lower() in dest_map:
            base, extension = os.path.splitext(dest)
            parent_tag = rel_path.split('\\')[-2] if len(rel_path.split('\\')) >= 2 else 'alt'
            dest = f"{base}_{parent_tag}{extension}"
            idx = 2
            while dest.lower() in dest_map:
                dest = f"{base}_{parent_tag}_{idx}{extension}"
                idx += 1
        dest_map[dest.lower()] = fid
        planned_ops.append(('KEEP', fid, rel_path, dest, size, ''))

    # Build destination paths for dup_list
    for loser, winner_rel in dup_list:
        fid, fpath, tf, rel_path, name, ext, size, mtime, qh = loser
        dest = os.path.normpath(os.path.join('_Duplicates_Staging', 'Redundant_Media', rel_path))
        planned_ops.append(('STAGE_DUP', fid, rel_path, dest, size, f"dup_of:{winner_rel}"))

    # Build destination paths for junk_files (excluding #recycle)
    for r, jtype in junk_files:
        if jtype == 'recycle':
            continue
        fid, fpath, tf, rel_path, name, ext, size, mtime, qh = r
        dest = os.path.normpath(os.path.join('_Duplicates_Staging', 'System_Junk', rel_path))
        planned_ops.append(('STAGE_JUNK', fid, rel_path, dest, size, jtype))

    print(f"Total planned file operations: {len(planned_ops)}", flush=True)
    print(f"  - KEEP (Move to 01_Chronological / 02_Collections): {len(keep_list)}", flush=True)
    print(f"  - STAGE_DUP (Move to _Duplicates_Staging\\Redundant_Media): {len(dup_list)}", flush=True)
    print(f"  - STAGE_JUNK (Move to _Duplicates_Staging\\System_Junk): {len(planned_ops) - len(keep_list) - len(dup_list)}", flush=True)

    # First, see if we can move whole `.@__thumb` directories in one shot!
    # Wait: moving a `.@__thumb` folder with os.rename() moves hundreds of thumbnail files in 1 millisecond instead of 115,000 individual SMB rename calls!
    thumb_dirs = set()
    for r, jtype in junk_files:
        if jtype == 'thumb':
            rel_path = r[3]
            idx = rel_path.lower().find('.@__thumb')
            if idx != -1:
                tdir_rel = rel_path[:idx + len('.@__thumb')]
                thumb_dirs.add(tdir_rel)

    print(f"Optimizing: moving {len(thumb_dirs)} .@__thumb directories as whole folders first...", flush=True)
    start_t = time.time()
    moved_thumb_dirs = 0
    for tdir_rel in sorted(thumb_dirs, key=lambda x: len(x), reverse=True):
        src_dir = os.path.join(ROOT, tdir_rel)
        dst_dir = os.path.join(ROOT, '_Duplicates_Staging', 'System_Junk', tdir_rel)
        if os.path.exists(src_dir):
            try:
                os.makedirs(os.path.dirname(dst_dir), exist_ok=True)
                os.rename(src_dir, dst_dir)
                moved_thumb_dirs += 1
            except Exception as e:
                pass
    print(f"Moved {moved_thumb_dirs}/{len(thumb_dirs)} .@__thumb directories in {time.time() - start_t:.1f}s!", flush=True)

    # Pre-create all unique destination directories for planned_ops
    dest_dirs = set(os.path.join(ROOT, os.path.dirname(op[3])) for op in planned_ops if op[0] != 'STAGE_JUNK')
    print(f"Ensuring {len(dest_dirs)} target directories exist...", flush=True)
    for d in sorted(dest_dirs):
        os.makedirs(d, exist_ok=True)

    # Execute file moves and log to manifest
    moved_counts = defaultdict(int)
    skipped_already_moved = 0
    errors = []

    with open(MANIFEST_PATH, 'w', encoding='utf-8') as mf:
        for i, (action, fid, src_rel, dst_rel, size, note) in enumerate(planned_ops, 1):
            src_full = os.path.join(ROOT, src_rel)
            dst_full = os.path.join(ROOT, dst_rel)
            try:
                if not os.path.exists(src_full):
                    if os.path.exists(dst_full):
                        skipped_already_moved += 1
                        continue
                    else:
                        errors.append((src_rel, "Source not found"))
                        continue
                os.makedirs(os.path.dirname(dst_full), exist_ok=True)
                os.rename(src_full, dst_full)
                moved_counts[action] += 1
                mf.write(json.dumps({
                    'id': fid, 'action': action, 'src': src_rel, 'dst': dst_rel, 'size': size, 'note': note
                }, ensure_ascii=False) + '\n')
            except Exception as e:
                errors.append((src_rel, str(e)))

            if i % 5000 == 0:
                elapsed = time.time() - start_t
                print(f"Processed {i}/{len(planned_ops)} ops (KEEP={moved_counts['KEEP']}, DUP={moved_counts['STAGE_DUP']}, JUNK={moved_counts['STAGE_JUNK']}+{skipped_already_moved}, err={len(errors)}) in {elapsed:.1f}s...", flush=True)

    print(f"Finished file moves in {time.time() - start_t:.1f}s!", flush=True)
    print(f"Summary: KEEP={moved_counts['KEEP']}, STAGE_DUP={moved_counts['STAGE_DUP']}, STAGE_JUNK_FILES={moved_counts['STAGE_JUNK']}, THUMB_DIRS_MOVED_BULK={skipped_already_moved}, ERRORS={len(errors)}", flush=True)
    if errors:
        print("First 10 errors:", errors[:10], flush=True)

    # Clean up empty legacy directories at root of P:\
    protected_roots = {'#recycle', '01_Chronological', '02_Collections', '_Duplicates_Staging'}
    removed_dirs = 0
    for entry in os.scandir(ROOT):
        if entry.is_dir(follow_symlinks=False) and entry.name not in protected_roots:
            for root_dir, dirs, files in os.walk(entry.path, topdown=False):
                if not os.listdir(root_dir):
                    try:
                        os.rmdir(root_dir)
                        removed_dirs += 1
                    except Exception:
                        pass
            try:
                if not os.listdir(entry.path):
                    os.rmdir(entry.path)
                    removed_dirs += 1
            except Exception:
                pass

    print(f"Cleaned up {removed_dirs} empty legacy folders.", flush=True)
    conn.close()

if __name__ == '__main__':
    run_migration()
