"""
Gods & Glory EP001 Ad — Download all clips + audio
Double-click this file to run. Files save to the same folder as this script.
"""

import urllib.request
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

FILES = [
    ("clip1_spartan_lone.mp4",     "https://d8j0ntlcm91z4.cloudfront.net/user_3D9eVQycjqBmIClt0W6gUnVzpEA/hf_20260706_143653_3976f7ad-5254-4b85-907d-7f99fbcdf2a9.mp4"),
    ("clip2_persian_army.mp4",     "https://d8j0ntlcm91z4.cloudfront.net/user_3D9eVQycjqBmIClt0W6gUnVzpEA/hf_20260706_155756_9d32df9a-107f-49e5-8a4e-f2fe6790f6ca.mp4"),
    ("clip3_spartan_phalanx.mp4",  "https://d8j0ntlcm91z4.cloudfront.net/user_3D9eVQycjqBmIClt0W6gUnVzpEA/hf_20260706_155758_8579988b-6f97-4239-ade3-df59692c6591.mp4"),
    ("clip4_gods_glory_reveal.mp4","https://d8j0ntlcm91z4.cloudfront.net/user_3D9eVQycjqBmIClt0W6gUnVzpEA/hf_20260706_155759_80eaa4fa-3bef-4985-a573-190cf78e4e96.mp4"),
    ("narration_roman.wav",        "https://d8j0ntlcm91z4.cloudfront.net/user_3D9eVQycjqBmIClt0W6gUnVzpEA/hf_20260706_143611_cd166e82-5aaf-4735-9dce-36f3eb9adb3a.wav"),
]

def download(filename, url):
    dest = os.path.join(SCRIPT_DIR, filename)
    print(f"Downloading {filename}...")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as resp, open(dest, "wb") as f:
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = downloaded * 100 // total
                    print(f"  {pct}%", end="\r")
        size = os.path.getsize(dest)
        print(f"  Done — {size // 1024}KB saved to {dest}")
        return True
    except Exception as e:
        print(f"  FAILED: {e}")
        return False

print("=" * 50)
print("Gods & Glory EP001 Ad — Clip Downloader")
print("=" * 50)

ok = 0
for fname, url in FILES:
    if download(fname, url):
        ok += 1

print()
print(f"{ok}/{len(FILES)} files downloaded to: {SCRIPT_DIR}")
if ok == len(FILES):
    print("\nAll done! Now run assemble_gg_ep001_ad.bat to combine them.")
else:
    print("\nSome files failed. The CDN URLs may have expired.")
    print("Go to app.higgsfield.ai > Generations to download manually.")

input("\nPress Enter to close...")
