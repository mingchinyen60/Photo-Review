import sqlite3
import sys
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')
DB_PATH = r"c:\Users\mingc\OneDrive\文件\ATG\Photo-Review\photo_index.db"

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Build set of (LOWER(name), size) and set of sizes from P:\ real files
c.execute("SELECT LOWER(name), size, rel_path FROM files WHERE size > 0 AND top_folder != '#recycle'")
p_name_size = set()
p_sizes = set()
for lname, sz, rp in c.fetchall():
    parts = [p.lower() for p in rp.split('\\')]
    if '.@__thumb' in parts or lname in ('thumbs.db', '.ds_store', 'desktop.ini', 'zbthumbnail.info', 'picasa.ini', '.picasa.ini'):
        continue
    p_name_size.add((lname, sz))
    if sz > 10240:
        p_sizes.add(sz)

print(f"Loaded {len(p_name_size)} unique (name, size) signatures from P:\\")

# Analyze H:\mcyen top_folders
c.execute("SELECT top_folder, parent_rel_dir, name, ext, size, is_media FROM h_files")
tf_stats = defaultdict(lambda: [0, 0, 0, 0, 0, 0]) # [total_f, total_sz, media_f, media_sz, dup_media_f, dup_media_sz]
dir_stats = defaultdict(lambda: [0, 0, 0, 0, 0, 0]) # per parent_rel_dir

for tf, pdir, name, ext, sz, is_med in c.fetchall():
    lname = name.lower()
    is_dup = (lname, sz) in p_name_size if sz > 0 else False
    
    st = tf_stats[tf]
    st[0] += 1
    st[1] += sz
    if is_med:
        st[2] += 1
        st[3] += sz
        if is_dup:
            st[4] += 1
            st[5] += sz

    dst = dir_stats[pdir]
    dst[0] += 1
    dst[1] += sz
    if is_med:
        dst[2] += 1
        dst[3] += sz
        if is_dup:
            dst[4] += 1
            dst[5] += sz

print("\n=== 1. H:\\mcyen TOP-LEVEL FOLDERS OVERVIEW ===")
print(f"{'Top Folder':<30} | {'Total Files':>11} | {'Total GB':>8} | {'Media Files':>11} | {'Media GB':>8} | {'Dup Media in P:':>15} | {'Dup Media GB':>12} | {'% Media Dup'}")
print("-" * 130)
for tf in sorted(tf_stats.keys()):
    tf_f, tf_sz, med_f, med_sz, dup_f, dup_sz = tf_stats[tf]
    pct = (dup_f / med_f * 100) if med_f else 0
    print(f"{tf:<30} | {tf_f:>11} | {tf_sz/(1024**3):>8.2f} | {med_f:>11} | {med_sz/(1024**3):>8.2f} | {dup_f:>15} | {dup_sz/(1024**3):>12.2f} | {pct:>9.1f}%")

# Filter directories with > 10 media files that have duplicates in P:\
qualifying_dirs = []
for pdir, (tf_f, tf_sz, med_f, med_sz, dup_f, dup_sz) in dir_stats.items():
    if med_f > 10 and dup_f > 0:
        qualifying_dirs.append((pdir, tf_f, tf_sz, med_f, med_sz, dup_f, dup_sz))

print(f"\n=== 2. DIRECTORIES IN H:\\mcyen WITH >10 MEDIA FILES & DUPLICATES IN P:\\ ===")
print(f"Total qualifying directories: {len(qualifying_dirs)}")
tot_q_files = sum(x[1] for x in qualifying_dirs)
tot_q_gb = sum(x[2] for x in qualifying_dirs) / (1024**3)
tot_q_med = sum(x[3] for x in qualifying_dirs)
tot_q_dup = sum(x[5] for x in qualifying_dirs)
tot_q_dupgb = sum(x[6] for x in qualifying_dirs) / (1024**3)
print(f"Total files in these directories: {tot_q_files} ({tot_q_gb:.2f} GB) | Media: {tot_q_med} | Dup Media in P:\\: {tot_q_dup} ({tot_q_dupgb:.2f} GB)")

# Group qualifying_dirs by top_folder
by_tf = defaultdict(lambda: [0, 0, 0, 0, 0]) # [dir_count, total_f, total_sz, med_f, dup_f]
for pdir, tf_f, tf_sz, med_f, med_sz, dup_f, dup_sz in qualifying_dirs:
    tf = pdir.split('\\')[0]
    by_tf[tf][0] += 1
    by_tf[tf][1] += tf_f
    by_tf[tf][2] += tf_sz
    by_tf[tf][3] += med_f
    by_tf[tf][4] += dup_f

print("\nBreakdown of qualifying (>10 media files & has P:\\ dup) directories by Top Folder:")
for tf, (dcnt, tf_f, tf_sz, med_f, dup_f) in sorted(by_tf.items(), key=lambda x: x[1][2], reverse=True):
    print(f"  {tf:<30} | {dcnt:>5} dirs | {tf_f:>7} files ({tf_sz/(1024**3):>7.2f} GB) | Media: {med_f:>6} | Dup in P: {dup_f:>6} ({dup_f/med_f*100:.1f}%)")

print("\nTop 60 Largest Qualifying Directories (by GB):")
for pdir, tf_f, tf_sz, med_f, med_sz, dup_f, dup_sz in sorted(qualifying_dirs, key=lambda x: x[2], reverse=True)[:60]:
    pct = dup_f / med_f * 100
    print(f"  {pdir:<75} | Tot:{tf_f:>5} ({tf_sz/(1024**3):>6.2f}GB) | Med:{med_f:>5} | Dup:{dup_f:>5} ({pct:>5.1f}%)")

conn.close()
