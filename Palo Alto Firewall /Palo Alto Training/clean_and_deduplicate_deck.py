import os
import glob
import subprocess
import shutil

slides_dir = "/home/nishusaini/Desktop/Innspark/Palo Alto Firewall /Palo Alto Training/extracted_slides"
backup_dir = "/tmp/extracted_slides_backup"

os.makedirs(backup_dir, exist_ok=True)
for f in glob.glob(os.path.join(slides_dir, "*.jpg")):
    shutil.copy2(f, backup_dir)

# Exact list of old duplicate filenames to remove in favor of the clean minute-by-minute ones
old_duplicates_to_remove = [
    "slide_00_05_00.jpg",
    "slide_00_12_30.jpg",
    "slide_00_15_30.jpg",
    "slide_00_22_00.jpg",
    "slide_00_32_00.jpg",
    "slide_00_45_00.jpg",
    "slide_00_55_00.jpg",
    "slide_01_08_00.jpg",
    "slide_01_18_00.jpg",
    "slide_01_35_00.jpg",
    "slide_01_48_00.jpg",
    "slide_02_02_00.jpg",
    "slide_02_15_00.jpg",
    "slide_02_25_00.jpg",
    "slide_02_35_00.jpg",
    "slide_02_48_00.jpg",
    "slide_03_00_00.jpg",
]

removed = []
for fname in old_duplicates_to_remove:
    p = os.path.join(slides_dir, fname)
    if os.path.exists(p):
        os.remove(p)
        removed.append(fname)

print(f"Removed {len(removed)} older duplicate slides.")

remaining = sorted(glob.glob(os.path.join(slides_dir, "*.jpg")))
print(f"\nRemaining clean unique slides count: {len(remaining)}")
for idx, r in enumerate(remaining, 1):
    print(f"  {idx:02d}. {os.path.basename(r)}")
