"""
LITTLE OLYMPUS - Full Render Launcher
Renders LO_EP001 through LO_EP040 using the existing auto_render pipeline.
Run AFTER or separately from run_render.py (GG render) to avoid API conflicts.
"""
import subprocess
import sys
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

PYTHON   = r"C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe"
FFMPEG_BIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg_bin")
os.environ["PATH"] = FFMPEG_BIN + os.pathsep + os.environ.get("PATH", "")

# All 40 LO episodes (EP001-EP040) — scripts already in prompts/little_olympus/
EPISODES = [f"LO_EP{i:03d}" for i in range(1, 41)]

print("=" * 52)
print("  LITTLE OLYMPUS - Full Episode Render Run")
print(f"  Python: {PYTHON}")
print(f"  Episodes: {len(EPISODES)} (EP001-EP040)")
print("=" * 52)
print()

print("Installing packages...")
subprocess.run([PYTHON, "-m", "pip", "install", "requests", "pillow", "edge-tts", "--quiet"], check=False)
print("Packages ready.")
print()

failed = []

for ep in EPISODES:
    print(f">>> Rendering {ep}...")
    result = subprocess.run([PYTHON, "auto_render.py", "--episode", ep])
    if result.returncode != 0:
        print(f"WARNING: {ep} exited with code {result.returncode}")
        failed.append(ep)
    print()

print("=" * 52)
print(f"  ALL DONE - {len(EPISODES)} episodes attempted")
if failed:
    print(f"  FAILED: {', '.join(failed)}")
else:
    print("  All episodes completed successfully!")
print("  Check renders/ folder for finals")
print("=" * 52)
input("\nPress Enter to close...")
