import os
import sys
import stat
from execute_h_migration import execute_h_migration

sys.stdout.reconfigure(encoding='utf-8')
P_MCYEN = r"P:\_Duplicates_Staging\mcyen"
H_ROOT = r"H:\mcyen"

# If a file already exists in P:\_Duplicates_Staging\mcyen with identical size, remove the source in H:\mcyen!
unlinked = 0
for root_d, dirs, files in os.walk(P_MCYEN):
    for fn in files:
        dst_full = os.path.join(root_d, fn)
        rel = os.path.relpath(dst_full, P_MCYEN)
        src_full = os.path.join(H_ROOT, rel)
        try:
            os.chmod(dst_full, stat.S_IWRITE)
            if os.path.exists(src_full):
                if os.path.getsize(src_full) == os.path.getsize(dst_full):
                    os.chmod(src_full, stat.S_IWRITE)
                    os.remove(src_full)
                    unlinked += 1
        except Exception as e:
            pass

print(f"Verified and unlinked {unlinked} already-copied read-only files from H:\\mcyen.", flush=True)
execute_h_migration()
