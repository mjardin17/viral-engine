"""
GODS & GLORY - Full 45-Min Render Launcher
Renders EP001-EP025 overnight. Bypasses bat file PATH issues.
"""
import subprocess
import sys
import os

# Change to script directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

PYTHON = r"C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe"
FFMPEG_BIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg_bin")

# Prepend local ffmpeg to PATH
os.environ["PATH"] = FFMPEG_BIN + os.pathsep + os.environ.get("PATH", "")

EPISODES = [f"GG_EP{i:03d}" for i in range(1, 26)]

print("=" * 52)
print("  GODS & GLORY - Full 45-Min Render Run")
print(f"  Python: {PYTHON}")
print("=" * 52)
print()

# Install deps once
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
print("  ALL DONE - 25 episodes attempted")
if failed:
    print(f"  FAILED: {', '.join(failed)}")
else:
    print("  All episodes completed successfully!")
print("  Check renders/ folder for finals")
print("=" * 52)
input("\nPress Enter to close...")
