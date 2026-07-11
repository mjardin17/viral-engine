"""
Iron Legends render launcher.
Finds all IL_EP*.json in prompts/iron_legends/ and renders them sequentially.
"""
import subprocess, pathlib, sys

PYTHON  = r"C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe"
ROOT    = pathlib.Path(__file__).parent
PROMPTS = ROOT / "prompts" / "iron_legends"

scripts = sorted(PROMPTS.glob("IL_EP*.json"))
if not scripts:
    print("No IL_EP*.json scripts found in prompts/iron_legends/")
    sys.exit(1)

print(f"Found {len(scripts)} Iron Legends episode(s) to render:\n")
for s in scripts:
    print(f"  {s.name}")

print()
for script in scripts:
    print(f"\n{'='*60}")
    print(f"RENDERING: {script.name}")
    print(f"{'='*60}\n")
    result = subprocess.run([PYTHON, "auto_render.py", str(script)], cwd=ROOT)
    if result.returncode != 0:
        print(f"\n[ERROR] {script.name} failed with code {result.returncode}")
    else:
        print(f"\n[DONE] {script.name} complete")

print("\n\nAll Iron Legends episodes processed.")
