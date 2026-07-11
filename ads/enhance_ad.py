"""
Enhance GG_EP001_ad.mp4 with title cards and text overlays — FREE, no Higgsfield.
Run after rebuild_ad_with_got.py (or works on existing 4-clip version too).
"""
import subprocess, os, sys

DIR = os.path.dirname(os.path.abspath(__file__))
INPUT = os.path.join(DIR, "GG_EP001_ad.mp4")
OUTPUT = os.path.join(DIR, "GG_EP001_ad_FINAL.mp4")

if not os.path.exists(INPUT):
    print(f"ERROR: {INPUT} not found. Run rebuild_ad_with_got.py first.")
    input("Press Enter to close..."); sys.exit(1)

# FFmpeg filter: 
# - Fade in from black (0.5s)
# - "GODS & GLORY" title overlay at start (0-3s), large centered
# - "NEW EPISODE — EVERY WEEK" at end (last 4s)
# - Fade out to black at end
# - Vignette for cinematic feel

filter_complex = (
    "[0:v]"
    "fade=t=in:st=0:d=0.5,"
    "fade=t=out:st=28:d=1.5,"
    "vignette=angle=PI/4:mode=forward,"
    "drawtext=text='GODS \\& GLORY':fontcolor=white:fontsize=72:x=(w-tw)/2:y=(h-th)/2:"
        "enable='between(t,0.5,3.5)':alpha='if(lt(t,1),t-0.5,if(gt(t,3),3.5-t,1))':"
        "shadowcolor=black:shadowx=3:shadowy=3,"
    "drawtext=text='TRUE STORIES. EPIC BATTLES. REAL HISTORY.':fontcolor=gold:fontsize=28:"
        "x=(w-tw)/2:y=h*0.62:"
        "enable='between(t,1.5,3.5)':alpha='if(lt(t,2),t-1.5,if(gt(t,3),3.5-t,1))':"
        "shadowcolor=black:shadowx=2:shadowy=2,"
    "drawtext=text='NEW EPISODES EVERY WEEK':fontcolor=white:fontsize=36:"
        "x=(w-tw)/2:y=(h-th)/2:"
        "enable='between(t,27,30)':alpha='if(lt(t,27.5),t-27,if(gt(t,29.5),30-t,1))':"
        "shadowcolor=black:shadowx=2:shadowy=2,"
    "drawtext=text='GODS & GLORY — Subscribe Now':fontcolor=gold:fontsize=26:"
        "x=(w-tw)/2:y=h*0.6:"
        "enable='between(t,27.5,30)':alpha='if(lt(t,28),t-27.5,if(gt(t,29.5),30-t,1))':"
        "shadowcolor=black:shadowx=2:shadowy=2"
    "[vout]"
)

print("Enhancing ad with title cards and overlays...")
result = subprocess.run([
    "ffmpeg", "-y",
    "-i", INPUT,
    "-filter_complex", filter_complex,
    "-map", "[vout]",
    "-map", "0:a",
    "-c:v", "libx264", "-preset", "fast", "-crf", "18",
    "-c:a", "aac", "-b:a", "192k",
    OUTPUT
], cwd=DIR)

if result.returncode == 0 and os.path.exists(OUTPUT):
    print(f"\nDone! {os.path.getsize(OUTPUT)//1024//1024}MB saved to:\n{OUTPUT}")
else:
    print("\nERROR: ffmpeg failed. Check output above.")
    
input("Press Enter to close...")
