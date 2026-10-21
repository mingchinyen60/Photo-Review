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

from move_h_mcyen import is_real_media, is_web_or_software_asset_dir, map_h_unique_to_p

def execute_h_migration():
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

    # Also build set of existing relative paths on P:\ to prevent any path overwrite
    c.execute("SELECT rel_path FROM files")
    existing_p_paths = set()
    if os.path.exists(r"c:\Users\mingc\OneDrive\文件\ATG\Photo-Review\migration_manifest.jsonl"):
        with open(r"c:\Users\mingc\OneDrive\文件\ATG\Photo-Review\migration_manifest.jsonl", 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    obj = json.loads(line)
                    existing_p_paths.add(obj['dst'].lower())
                except Exception:
                    pass

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

    # Also include D7100\102D7100\NKSC_PARAM since its parent D7100\102D7100 is 100% duplicated in P:\
    if 'D7100\\102D7100\\NKSC_PARAM' in dir_files:
        qualifying_dirs.append(('D7100\\102D7100\\NKSC_PARAM', dir_files['D7100\\102D7100\\NKSC_PARAM']))

    print(f"Total qualifying H:\\mcyen directories (>10 photo files & has duplicates in P:\\): {len(qualifying_dirs)}", flush=True)

    planned_moves = [] # (action, fid, src_rel, dst_rel, size)
    seen_new_p_sigs = set(p_name_size)

    for pdir, items in qualifying_dirs:
        is_gdrive_root = (pdir == 'GoogleDrive')
        for r in items:
            fid, fpath, tf, parent_rel, rel_path, name, ext, size, mtime, is_med = r
            sig = (name.lower(), size)
            if is_gdrive_root:
                # For H:\mcyen\GoogleDrive root, only move the 103 duplicated photos that exist in P:\!
                # Keep all 548 non-media documents and 14 non-duplicate videos/images in H:\mcyen\GoogleDrive.
                if is_real_media(name, ext, size, is_med) and sig in p_name_size:
                    dst_rel = os.path.normpath(os.path.join('_Duplicates_Staging', 'mcyen', rel_path))
                    planned_moves.append(('STAGE_MCYEN_DUP', fid, rel_path, dst_rel, size))
                continue

            if is_real_media(name, ext, size, is_med):
                if sig in seen_new_p_sigs:
                    dst_rel = os.path.normpath(os.path.join('_Duplicates_Staging', 'mcyen', rel_path))
                    planned_moves.append(('STAGE_MCYEN_DUP', fid, rel_path, dst_rel, size))
                else:
                    seen_new_p_sigs.add(sig)
                    dst_rel = map_h_unique_to_p(pdir, rel_path, name, ext, mtime)
                    if dst_rel.lower() in existing_p_paths:
                        base, extension = os.path.splitext(dst_rel)
                        dst_rel = f"{base}_mcyen{extension}"
                        idx = 2
                        while dst_rel.lower() in existing_p_paths:
                            dst_rel = f"{base}_mcyen_{idx}{extension}"
                            idx += 1
                    existing_p_paths.add(dst_rel.lower())
                    planned_moves.append(('ORGANIZE_TO_P', fid, rel_path, dst_rel, size))
            else:
                dst_rel = os.path.normpath(os.path.join('_Duplicates_Staging', 'mcyen', rel_path))
                planned_moves.append(('STAGE_MCYEN_AUX', fid, rel_path, dst_rel, size))

    cnt_dup = sum(1 for x in planned_moves if x[0] == 'STAGE_MCYEN_DUP')
    gb_dup = sum(x[4] for x in planned_moves if x[0] == 'STAGE_MCYEN_DUP') / (1024**3)
    cnt_org = sum(1 for x in planned_moves if x[0] == 'ORGANIZE_TO_P')
    gb_org = sum(x[4] for x in planned_moves if x[0] == 'ORGANIZE_TO_P') / (1024**3)
    cnt_aux = sum(1 for x in planned_moves if x[0] == 'STAGE_MCYEN_AUX')
    gb_aux = sum(x[4] for x in planned_moves if x[0] == 'STAGE_MCYEN_AUX') / (1024**3)

    print(f"Executing {len(planned_moves)} file moves from H:\\mcyen to P:\\ ...", flush=True)
    print(f"  - STAGE_MCYEN_DUP (to P:\\_Duplicates_Staging\\mcyen): {cnt_dup} files ({gb_dup:.2f} GB)", flush=True)
    print(f"  - ORGANIZE_TO_P   (unique photos -> P:\\01_Chronological & 02_Collections): {cnt_org} files ({gb_org:.2f} GB)", flush=True)
    print(f"  - STAGE_MCYEN_AUX (aux/sidecars -> P:\\_Duplicates_Staging\\mcyen): {cnt_aux} files ({gb_aux:.2f} GB)", flush=True)

    # Pre-create destination directories on P:\
    dest_dirs = set(os.path.join(P_ROOT, os.path.dirname(op[3])) for op in planned_moves)
    print(f"Ensuring {len(dest_dirs)} destination directories exist on P:\\ ...", flush=True)
    for d in sorted(dest_dirs):
        os.makedirs(d, exist_ok=True)

    start_t = time.time()
    moved_counts = defaultdict(int)
    moved_bytes = 0
    errors = []

    with open(H_MANIFEST_PATH, 'w', encoding='utf-8') as mf:
        for i, (action, fid, src_rel, dst_rel, size) in enumerate(planned_moves, 1):
            src_full = os.path.join(H_ROOT, src_rel)
            dst_full = os.path.join(P_ROOT, dst_rel)
            try:
                if not os.path.exists(src_full):
                    if os.path.exists(dst_full):
                        moved_counts[action] += 1
                        continue
                    else:
                        errors.append((src_rel, "Source not found"))
                        continue
                os.makedirs(os.path.dirname(dst_full), exist_ok=True)
                shutil.move(src_full, dst_full)
                moved_counts[action] += 1
                moved_bytes += size
                mf.write(json.dumps({
                    'id': fid, 'action': action, 'src_h': src_rel, 'dst_p': dst_rel, 'size': size
                }, ensure_ascii=False) + '\n')
            except Exception as e:
                errors.append((src_rel, str(e)))

            if i % 1000 == 0:
                elapsed = time.time() - start_t
                print(f"Processed {i}/{len(planned_moves)} files ({moved_bytes/(1024**3):.2f} GB, DUP={moved_counts['STAGE_MCYEN_DUP']}, ORG={moved_counts['ORGANIZE_TO_P']}, AUX={moved_counts['STAGE_MCYEN_AUX']}, err={len(errors)}) in {elapsed:.1f}s...", flush=True)

    # Also remove any .@__thumb or Thumbs.db or .DS_Store inside the moved H:\mcyen directories so empty directories can be cleanly removed
    removed_dirs = 0
    all_target_dirs = sorted(set(pdir for pdir, _ in qualifying_dirs), key=lambda x: len(x), reverse=True)
    for pdir in all_target_dirs:
        if pdir == 'GoogleDrive':
            continue
        full_dir = os.path.join(H_ROOT, pdir)
        if os.path.exists(full_dir):
            # Check if only junk files remain (.@__thumb, Thumbs.db, .DS_Store)
            for root_d, dirs, files in os.walk(full_dir, topdown=False):
                for fn in files:
                    if fn.lower() in ('thumbs.db', '.ds_store', 'desktop.ini', 'zbthumbnail.info', 'picasa.ini', '.picasa.ini') or '.@__thumb' in root_d.lower():
                        try:
                            os.remove(os.path.join(root_d, fn))
                        except Exception:
                            pass
                if not os.listdir(root_d):
                    try:
                        os.rmdir(root_d)
                        removed_dirs += 1
                    except Exception:
                        pass
            # Also try removing parent if now empty
            parent_d = os.path.dirname(full_dir)
            while parent_d and len(parent_d) > len(H_ROOT):
                try:
                    if not os.listdir(parent_d):
                        os.rmdir(parent_d)
                        removed_dirs += 1
                        parent_d = os.path.dirname(parent_d)
                    else:
                        break
                except Exception:
                    break

    elapsed = time.time() - start_t
    print(f"Finished H:\\mcyen migration in {elapsed:.1f}s!", flush=True)
    print(f"Summary: STAGE_MCYEN_DUP={moved_counts['STAGE_MCYEN_DUP']}, ORGANIZE_TO_P={moved_counts['ORGANIZE_TO_P']}, STAGE_MCYEN_AUX={moved_counts['STAGE_MCYEN_AUX']}, Empty dirs cleaned={removed_dirs}, Errors={len(errors)}", flush=True)
    if errors:
        print("First 10 errors:", errors[:10], flush=True)
    conn.close()

if __name__ == '__main__':
    execute_h_migration()
