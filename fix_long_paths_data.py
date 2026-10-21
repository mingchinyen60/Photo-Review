import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
H_ROOT = r"\\?\H:\mcyen"
DATA_DIR = os.path.join(H_ROOT, "Data")
STAGING_DIR = os.path.join(H_ROOT, "_Duplicate_Storage")

for yr in ["Data_2020", "Data_2021"]:
    yr_dir = os.path.join(H_ROOT, yr)
    if not os.path.exists(yr_dir):
        continue
    for root, dirs, files in os.walk(yr_dir):
        for f in files:
            src = os.path.join(root, f)
            rel = os.path.relpath(src, yr_dir)
            dst_data = os.path.join(DATA_DIR, rel)
            dst_stage = os.path.join(STAGING_DIR, yr, rel)
            try:
                if not os.path.exists(dst_data):
                    os.makedirs(os.path.dirname(dst_data), exist_ok=True)
                    os.rename(src, dst_data)
                    print(f"Moved unique: {rel[:60]} -> Data")
                else:
                    os.makedirs(os.path.dirname(dst_stage), exist_ok=True)
                    os.rename(src, dst_stage)
                    print(f"Moved duplicate: {rel[:60]} -> _Duplicate_Storage")
            except Exception as e:
                print(f"Error on {rel[:60]}: {e}")

# Clean empty directories
for yr in ["Data_2020", "Data_2021"]:
    yr_dir = os.path.join(H_ROOT, yr)
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
            print(f"Removed emptied folder {yr}")
    except Exception as e:
        print(f"Notice on {yr}: {e}")
