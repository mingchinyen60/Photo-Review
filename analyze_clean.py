import sqlite3
import sys
from collections import defaultdict

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

c.execute("SELECT id, top_folder, rel_path, name, ext, size, mtime FROM files")
all_rows = c.fetchall()

junk_count = 0
junk_bytes = 0
real_files = []

for r in all_rows:
    fid, tf, rel_path, name, ext, size, mtime = r
    if is_junk(rel_path, name, ext):
        junk_count += 1
        junk_bytes += size
    else:
        real_files.append(r)

print(f"Total indexed files: {len(all_rows)} ({sum(r[5] for r in all_rows)/(1024**3):.2f} GB)")
print(f"NAS / OS Junk files (#recycle, .@__thumb, Thumbs.db, .DS_Store): {junk_count} files ({junk_bytes/(1024**3):.2f} GB)")
print(f"Real user files: {len(real_files)} files ({sum(r[5] for r in real_files)/(1024**3):.2f} GB)")

# Group real files by top_folder
tf_stats = defaultdict(lambda: [0, 0])
sig_map = defaultdict(list) # (lname, size) -> list of real_file tuples
size_map = defaultdict(list) # size -> list of real_file tuples (for size > 10KB)

for r in real_files:
    fid, tf, rel_path, name, ext, size, mtime = r
    tf_stats[tf][0] += 1
    tf_stats[tf][1] += size
    if size > 0:
        sig_map[(name.lower(), size)].append(r)
    if size > 10240:
        size_map[size].append(r)

# Analyze duplicates among real files
dup_groups = {k: v for k, v in sig_map.items() if len(v) > 1}
redundant_count = sum(len(v) - 1 for v in dup_groups.values())
redundant_bytes = sum((len(v) - 1) * k[1] for k, v in dup_groups.items())
print(f"\nReal File Exact Duplicates (by filename + size): {len(dup_groups)} unique files have {redundant_count} extra copies ({redundant_bytes/(1024**3):.2f} GB wasted)")

# What about same size (>10KB) but different filename?
diff_name_same_size_groups = 0
diff_name_redundant_bytes = 0
for sz, v in size_map.items():
    if len(v) > 1:
        names = set(x[3].lower() for x in v)
        if len(names) > 1:
            diff_name_same_size_groups += 1
            # count extra copies beyond unique (name, size)
            diff_name_redundant_bytes += (len(names) - 1) * sz
print(f"Additional candidate duplicates (same exact size >10KB, different filename): {diff_name_same_size_groups} groups ({diff_name_redundant_bytes/(1024**3):.2f} GB)")

print("\n=== REAL FILES: TOP-LEVEL FOLDER CONTAINMENT / REDUNDANCY ===")
print(f"{'Top Folder':<28} | {'Real Files':>10} | {'Real GB':>8} | {'Dup Elsewhere':>13} | {'% Files Dup':>11} | {'% GB Dup':>8} | {'Dup Inside Self':>15} | {'Primary Overlap Target'}")
print("-" * 140)

for tf in sorted(tf_stats.keys()):
    t_cnt, t_sz = tf_stats[tf]
    tf_files = [r for r in real_files if r[1] == tf and r[5] > 0]
    dup_ext_cnt = 0
    dup_ext_sz = 0
    dup_int_cnt = 0
    dup_int_sz = 0
    target_counts = defaultdict(lambda: [0, 0])
    
    # Track seen signatures inside self to count internal extra copies
    seen_self = set()
    for r in tf_files:
        fid, _, rel_path, name, ext, size, mtime = r
        sig = (name.lower(), size)
        matches = sig_map[sig]
        other_tfs = set(m[1] for m in matches if m[1] != tf)
        self_matches = [m for m in matches if m[1] == tf]
        if other_tfs:
            dup_ext_cnt += 1
            dup_ext_sz += size
            for otf in other_tfs:
                target_counts[otf][0] += 1
                target_counts[otf][1] += size
        if len(self_matches) > 1:
            if sig in seen_self:
                dup_int_cnt += 1
                dup_int_sz += size
            else:
                seen_self.add(sig)

    pct_f = (dup_ext_cnt / t_cnt * 100) if t_cnt else 0
    pct_sz = (dup_ext_sz / t_sz * 100) if t_sz else 0
    best_t = ""
    if target_counts:
        top_t = max(target_counts.items(), key=lambda x: x[1][1]) # by GB or count
        best_t = f"{top_t[0]} ({top_t[1][0]}f, {top_t[1][1]/(1024**3):.2f}GB)"
    int_str = f"{dup_int_cnt}f ({dup_int_sz/(1024**3):.2f}GB)" if dup_int_cnt else "-"
    print(f"{tf:<28} | {t_cnt:>10} | {t_sz/(1024**3):>8.2f} | {dup_ext_cnt:>13} | {pct_f:>10.1f}% | {pct_sz:>7.1f}% | {int_str:>15} | {best_t}")

conn.close()
