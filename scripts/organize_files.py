import os
import re
import sys
import shutil
from pathlib import Path

def organize_folder(folder_path):
    target_dir = Path(folder_path)
    if not target_dir.exists():
        print(f"Error: Directory '{target_dir}' does not exist.")
        return

    before_dir = target_dir / "before"
    after_dir = target_dir / "after"

    before_dir.mkdir(exist_ok=True)
    after_dir.mkdir(exist_ok=True)

    moved_to_before = 0
    moved_to_after = 0

    for item in sorted(target_dir.iterdir()):
        # Skip subdirectories (including 'before' and 'after')
        if item.is_dir():
            continue

        filename_stem = item.stem
        # Extract digits from the filename
        numbers = re.findall(r'\d+', filename_stem)
        
        # Determine target folder: strictly before 4243 -> 'before', 4243 onwards -> 'after'
        if numbers:
            num = int(numbers[0])
            if num < 4243:
                dest = before_dir
                moved_to_before += 1
            else:
                dest = after_dir
                moved_to_after += 1
        else:
            if filename_stem < "4243":
                dest = before_dir
                moved_to_before += 1
            else:
                dest = after_dir
                moved_to_after += 1

        dest_file = dest / item.name
        print(f"Moving {item.name} -> {dest.name}/")
        shutil.move(str(item), str(dest_file))

    print("\nOrganization complete!")
    print(f"Files moved to 'before': {moved_to_before}")
    print(f"Files moved to 'after': {moved_to_after}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_folder = sys.argv[1]
    else:
        target_folder = input("Enter the folder path to organize: ").strip()
    organize_folder(target_folder)
