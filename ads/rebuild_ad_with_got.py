"""
Gods & Glory EP001 Ad — Add GoT ending clip and rebuild
Double-click to run. Saves GG_EP001_ad.mp4 in this same folder.
"""
import urllib.request, subprocess, os, sys

DIR = os.path.dirname(os.path.abspath(__file__))

def dl(fname, url):
    dest = os.path.join(DIR, fname)
    if os.path.exists(dest):
        print(f"  Already have {fname} ({os.path.getsize(dest)//1024}KB), skipping.")
        return True
    print(f"Downloading {fname}...")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as r, open(dest, "wb") as f:
            f.write(r.read())
        print(f"  Done — {os.path.getsize(dest)//1024}KB")
        return True
    except Exception as e:
        print(f"  FAILED: {e}"); return False

# Download GoT clip
dl("clip5_got_ending.mp4",
   "https://d8j0ntlcm91z4.cloudfront.net/user_3D9eVQycjqBmIClt0W6gUnVzpEA/hf_20260706_173016_80c37592-e074-4062-b141-7d93a09912e2.mp4")

# Check all 5 clips + audio exist
clips = ["clip1_spartan_lone.mp4","clip2_persian_army.mp4",
         "clip3_spartan_phalanx.mp4","clip4_gods_glory_reveal.mp4","clip5_got_ending.mp4"]
audio = "narration_roman.wav"
missing = [c for c in clips + [audio] if not os.path.exists(os.path.join(DIR, c))]
if missing:
    print(f"\nMissing files: {missing}")
    print("Run download_ad_clips.py first, then retry.")
    input("Press Enter to close..."); sys.exit(1)

# Write concat list
concat_path = os.path.join(DIR, "concat5.txt")
with open(concat_path, "w") as f:
    for c in clips:
        f.write(f"file '{c}'\n")

# Step 1: concat all 5 clips
print("\nConcatenating 5 clips...")
combined = os.path.join(DIR, "combined5.mp4")
subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",concat_path,"-c","copy",combined], cwd=DIR, check=True)

# Step 2: merge audio
print("Adding narration...")
out = os.path.join(DIR, "GG_EP001_ad.mp4")
subprocess.run([
    "ffmpeg","-y",
    "-i", combined,
    "-i", os.path.join(DIR, audio),
    "-map","0:v","-map","1:a",
    "-c:v","libx264","-preset","fast","-crf","18",
    "-c:a","aac","-b:a","192k",
    "-shortest", out
], cwd=DIR, check=True)

print(f"\nDone! {os.path.getsize(out)//1024//1024}MB saved to:\n{out}")
input("Press Enter to close...")
