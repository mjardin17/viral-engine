# easy_cleaner.py - Really Easy for Claude
from pathlib import Path
import shutil

BASE = Path(r'C:\Users\jjard\claude\video-bot-pipeline')

class EasyClean:
    def go(self, dry_run=True):
        """Claude just says 'go' and it cleans everything"""
        print("Cleaning all files...")

        folders = ["videos", "thumbnails", "renders", "archives", "old"]
        for f in folders:
            (BASE / f).mkdir(exist_ok=True)

        moved = 0
        for file in BASE.iterdir():
            if file.is_file():
                if file.suffix.lower() in ['.mp4', '.mov']:
                    dest = BASE / "videos" / file.name
                elif any(x in file.name.lower() for x in ['thumb', 'render', 'jpg', 'png']):
                    dest = BASE / "thumbnails" / file.name
                else:
                    dest = BASE / "old" / file.name

                if not dry_run:
                    shutil.move(str(file), str(dest))
                    moved += 1
                else:
                    print(f"-> {file.name}")

        return f"Done! Moved {moved} files. (dry_run={dry_run}) Use dry_run=False when ready."

clean = EasyClean()

print("Super Easy Cleaner Ready!")
print("Claude just does: clean.go()")
