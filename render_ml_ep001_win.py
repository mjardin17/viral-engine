#!/usr/bin/env python3
"""
render_ml_ep001_win.py — Windows-native render for Mech Legends EP001: The Signal
Run from PowerShell:
    python render_ml_ep001_win.py
Output: output/ML_EP001_final.mp4
"""
import json, subprocess, shutil, sys, math, wave, os, datetime, urllib.request, urllib.parse
from pathlib import Path

# ── Paths (all relative to this script) ───────────────────────────────────────
BASE    = Path(__file__).parent
PROMPTS = BASE / "prompts" / "mech_legends"
OUTDIR  = BASE / "output"
WORK    = OUTDIR / "_work_ml_ep001"
FINAL   = OUTDIR / "ML_EP001_final.mp4"
JSON    = PROMPTS / "scene_prompts.ml_ep001.final.json"

W, H    = 1920, 1080

# ── Find FFmpeg ────────────────────────────────────────────────────────────────
def find_ffmpeg():
    f = shutil.which("ffmpeg")
    if f: return f
    candidates = [
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",
        str(Path.home() / "ffmpeg" / "bin" / "ffmpeg.exe"),
    ]
    for c in candidates:
        if Path(c).exists(): return c
    return None

FFMPEG = find_ffmpeg()
if not FFMPEG:
    print("ERROR: ffmpeg not found. Run: winget install ffmpeg  then reopen PowerShell.")
    sys.exit(1)
print(f"FFmpeg: {FFMPEG}")

# ── Colors ─────────────────────────────────────────────────────────────────────
C_BLAZE   = (255,  50,  20)
C_STORM   = (0,   153, 255)
C_GRANITE = (40,  200,  80)
C_NOVA    = (200, 200, 230)
C_RUMBLE  = (140,   0, 220)
C_ELDER7  = (200, 160,  20)   # ancient gold
C_DARK    = (8,     6,  18)

# ── Helpers ───────────────────────────────────────────────────────────────────
def _run(cmd, label=""):
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=120)
        if r.returncode != 0:
            print(f"  [ERR:{label}] {r.stderr[-300:].decode(errors='ignore')}")
            return False
        return True
    except subprocess.TimeoutExpired:
        print(f"  [TIMEOUT:{label}]"); return False

def _probe(p):
    try:
        # Find ffprobe in the same folder as ffmpeg
        ff_dir = Path(FFMPEG).parent
        ffprobe = str(ff_dir / "ffprobe.exe")
        if not Path(ffprobe).exists():
            ffprobe = str(ff_dir / "ffprobe.EXE")
        if not Path(ffprobe).exists():
            ffprobe = shutil.which("ffprobe") or FFMPEG.replace(
                Path(FFMPEG).stem, "ffprobe")
        r = subprocess.run(
            [ffprobe,"-v","quiet",
             "-show_entries","format=duration",
             "-of","default=noprint_wrappers=1:nokey=1","-i",str(p)],
            capture_output=True, timeout=30)
        return float(r.stdout.strip())
    except Exception:
        return 0.0

def _hx(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i+2], 16) for i in (0, 2, 4))

# ── PIL drawing ────────────────────────────────────────────────────────────────
try:
    from PIL import Image, ImageDraw
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "Pillow", "-q"])
    from PIL import Image, ImageDraw

def draw_mech(draw, cx, cy, color, scale=1.0, style="hero"):
    s = scale; c = color  # c is always a plain RGB tuple
    if style == "villain":
        s *= 1.4
        draw.rectangle([cx-int(90*s),cy-int(160*s),cx+int(90*s),cy+int(90*s)],fill=c)
        draw.rectangle([cx-int(50*s),cy-int(220*s),cx+int(50*s),cy-int(165*s)],fill=c)
        draw.ellipse([cx-int(35*s),cy-int(210*s),cx-int(12*s),cy-int(188*s)],fill=(255,30,30))
        draw.ellipse([cx+int(12*s),cy-int(210*s),cx+int(35*s),cy-int(188*s)],fill=(255,30,30))
        draw.rectangle([cx-int(185*s),cy-int(150*s),cx-int(90*s),cy-int(70*s)],fill=c)
        draw.rectangle([cx+int(90*s),cy-int(150*s),cx+int(185*s),cy-int(70*s)],fill=c)
        draw.rectangle([cx-int(165*s),cy-int(55*s),cx-int(90*s),cy+int(35*s)],fill=c)
        draw.rectangle([cx+int(90*s),cy-int(55*s),cx+int(165*s),cy+int(35*s)],fill=c)
        draw.rectangle([cx-int(70*s),cy+int(90*s),cx-int(18*s),cy+int(200*s)],fill=c)
        draw.rectangle([cx+int(18*s),cy+int(90*s),cx+int(70*s),cy+int(200*s)],fill=c)
        for sx2 in [-35,-17,0,17,35]:
            draw.polygon([(cx+int(sx2*s),cy-int(220*s)),(cx+int((sx2-9)*s),cy-int(250*s)),(cx+int((sx2+9)*s),cy-int(250*s))],
                        fill=(min(c[0]+60,255),c[1],min(c[2]+20,255)))
    elif style == "elder":
        s *= 1.05
        draw.rectangle([cx-int(45*s),cy-int(200*s),cx+int(45*s),cy+int(100*s)],fill=c)
        draw.polygon([(cx-int(45*s),cy-int(50*s)),(cx-int(90*s),cy+int(100*s)),(cx+int(90*s),cy+int(100*s)),(cx+int(45*s),cy-int(50*s))],
                    fill=(max(c[0]-40,0),max(c[1]-40,0),max(c[2]-40,0)))
        draw.rectangle([cx-int(35*s),cy-int(270*s),cx+int(35*s),cy-int(205*s)],fill=c)
        draw.ellipse([cx-int(25*s),cy-int(258*s),cx-int(8*s),cy-int(240*s)],fill=(255,220,50))
        draw.ellipse([cx+int(8*s),cy-int(258*s),cx+int(25*s),cy-int(240*s)],fill=(255,220,50))
        for dx in [-20,-10,0,10,20]:
            draw.rectangle([cx+int(dx*s)-int(4*s),cy-int(290*s),cx+int(dx*s)+int(4*s),cy-int(270*s)],fill=(min(c[0]+40,255),c[1],c[2]))
        draw.rectangle([cx-int(90*s),cy-int(180*s),cx-int(45*s),cy-int(60*s)],fill=c)
        draw.rectangle([cx+int(45*s),cy-int(180*s),cx+int(90*s),cy-int(60*s)],fill=c)
        draw.ellipse([cx-int(25*s),cy-int(75*s),cx+int(25*s),cy-int(25*s)],fill=(255,220,80))
        draw.ellipse([cx-int(18*s),cy-int(68*s),cx+int(18*s),cy-int(32*s)],fill=(255,240,120))
    else:
        # Hero
        draw.rectangle([cx-int(55*s),cy-int(110*s),cx+int(55*s),cy+int(55*s)],fill=c)
        draw.rectangle([cx-int(100*s),cy-int(110*s),cx-int(55*s),cy-int(45*s)],fill=c)
        draw.rectangle([cx+int(55*s),cy-int(110*s),cx+int(100*s),cy-int(45*s)],fill=c)
        draw.rectangle([cx-int(90*s),cy-int(45*s),cx-int(55*s),cy+int(55*s)],fill=c)
        draw.rectangle([cx+int(55*s),cy-int(45*s),cx+int(90*s),cy+int(55*s)],fill=c)
        draw.ellipse([cx-int(95*s),cy+int(35*s),cx-int(55*s),cy+int(72*s)],fill=(min(c[0]+30,255),min(c[1]+20,255),min(c[2]+20,255)))
        draw.ellipse([cx+int(55*s),cy+int(35*s),cx+int(95*s),cy+int(72*s)],fill=(min(c[0]+30,255),min(c[1]+20,255),min(c[2]+20,255)))
        draw.rectangle([cx-int(36*s),cy-int(165*s),cx+int(36*s),cy-int(114*s)],fill=c)
        draw.polygon([(cx-int(13*s),cy-int(165*s)),(cx,cy-int(188*s)),(cx+int(13*s),cy-int(165*s))],
                    fill=(min(c[0]+60,255),min(c[1]+40,255),min(c[2]+40,255)))
        draw.rectangle([cx-int(27*s),cy-int(155*s),cx+int(27*s),cy-int(137*s)],fill=(100,220,255))
        draw.ellipse([cx-int(18*s),cy-int(72*s),cx+int(18*s),cy-int(36*s)],fill=(255,255,255))
        draw.ellipse([cx-int(12*s),cy-int(66*s),cx+int(12*s),cy-int(42*s)],fill=c)
        draw.rectangle([cx-int(45*s),cy+int(55*s),cx-int(9*s),cy+int(165*s)],fill=c)
        draw.rectangle([cx+int(9*s),cy+int(55*s),cx+int(45*s),cy+int(165*s)],fill=c)
        draw.rectangle([cx-int(54*s),cy+int(151*s),cx-int(4*s),cy+int(184*s)],fill=c)
        draw.rectangle([cx+int(4*s),cy+int(151*s),cx+int(54*s),cy+int(184*s)],fill=c)

def fetch_pollinations(prompt, out, scene_num=1):
    """Download AI image from Pollinations. Returns True if successful."""
    try:
        safe = urllib.parse.quote(prompt, safe="")
        url  = f"https://image.pollinations.ai/prompt/{safe}?width=1920&height=1080&nologo=true&seed={scene_num * 7}&model=flux"
        print(f"    [AI image] fetching scene {scene_num}...", flush=True)
        req = urllib.request.Request(url, headers={"User-Agent": "MechLegends/1.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
        if len(data) < 5000:   # too small = error page
            return False
        out.write_bytes(data)
        print(f"    [AI image] saved ({len(data)//1024}KB)", flush=True)
        return True
    except Exception as e:
        print(f"    [AI image] failed: {e}", flush=True)
        return False

def make_background(bg_colors, out):
    img  = Image.new("RGB",(W,H))
    draw = ImageDraw.Draw(img)
    top  = _hx(bg_colors[0]); bot = _hx(bg_colors[-1])
    for y in range(H):
        t = y/H
        r = int(top[0]*(1-t)+bot[0]*t)
        g = int(top[1]*(1-t)+bot[1]*t)
        b = int(top[2]*(1-t)+bot[2]*t)
        draw.line([(0,y),(W,y)],fill=(r,g,b))
    import random; random.seed(42)
    for _ in range(180):
        sx=random.randint(0,W); sy=random.randint(0,H//2)
        br=random.randint(80,255)
        draw.ellipse([sx-1,sy-1,sx+1,sy+1],fill=(br,br,br))
    img.save(str(out))

# Scene type → visual layout
def make_scene_still(scene, out):
    bg_path = Path(str(out).replace("_still.png","_bg.png"))
    if not bg_path.exists():
        make_background(scene.get("bg_colors",["#0A0A1F","#1A1A3E"]), bg_path)
    img  = Image.open(str(bg_path)).convert("RGB")
    draw = ImageDraw.Draw(img)
    t    = scene.get("type","")
    n    = scene.get("scene_number", 1)
    acc  = _hx(scene.get("accent","#FF6600"))

    if t == "hook" or n == 1:
        # ELDER-7 alone, centered, ominous
        draw_mech(draw, W//2, H//2+40, C_ELDER7, 1.0, "elder")
        # Glow rings (RGB only — no alpha)
        for ri in range(10,120,18):
            draw.ellipse([W//2-ri,H//2-ri,W//2+ri,H//2+ri],outline=C_ELDER7,width=1)

    elif t == "reveal" and n == 2:
        # Signal pulse — energy lines
        for i in range(10):
            x1=W//2+(i-5)*45; x2=W//2+(i-5)*22
            draw.line([(x1,0),(x2,H)],fill=(255,50,0),width=2)
        draw_mech(draw, W//2, H//2+60, C_ELDER7, 0.85, "elder")

    elif t == "action" and n == 3:
        # BLAZE arrives solo
        draw_mech(draw, W//2, H//2+40, C_BLAZE, 1.15, "hero")
        # Speed lines
        for i in range(8):
            y = H//2 - 150 + i*40
            draw.line([(0,y),(W//3,y+20)],fill=(255,80,20),width=2)

    elif t == "action" and n == 4:
        # Full team assembles
        draw_mech(draw, W//2-480, H//2+50, C_STORM,   0.85, "hero")
        draw_mech(draw, W//2-240, H//2+40, C_GRANITE, 0.90, "hero")
        draw_mech(draw, W//2,     H//2+30, C_BLAZE,   1.0,  "hero")
        draw_mech(draw, W//2+240, H//2+40, C_NOVA,    0.90, "hero")
        draw_mech(draw, W//2+480, H//2+50, C_RUMBLE,  0.85, "hero")

    elif t == "reveal" and n == 5:
        # ELDER-7 reveals Xerxes name — red tint, ominous
        draw_mech(draw, W//2, H//2+40, C_ELDER7, 1.0, "elder")
        for ri in range(20, 200, 25):
            draw.ellipse([W//2-ri,H//2-ri+40,W//2+ri,H//2+ri+40],outline=(200,0,0),width=2)

    elif t == "reveal" and n == 6:
        # Data streams — NOVA at center
        draw_mech(draw, W//2, H//2+50, C_NOVA, 1.0, "hero")
        for i in range(12):
            x = 80 + i*(W-160)//11
            draw.line([(x,20),(x+20,H//2-60)],fill=(0,200,255),width=1)

    elif t == "emotional":
        # Archive — ELDER-7 with fallen records feeling
        draw_mech(draw, W//2, H//2+40, C_ELDER7, 1.0, "elder")
        # Falling data lines
        import random; random.seed(7)
        for _ in range(30):
            rx=random.randint(50,W-50); ry1=random.randint(0,H//3); ry2=ry1+random.randint(40,120)
            draw.line([(rx,ry1),(rx,ry2)],fill=(200,160,20),width=1)

    elif t == "action" and n == 8:
        # BLAZE steps forward — heroic pose with glow
        draw_mech(draw, W//2, H//2+40, C_BLAZE, 1.2, "hero")
        for ri in range(15, 180, 22):
            draw.ellipse([W//2-ri,H//2-ri+40,W//2+ri,H//2+ri+40],outline=(255,60,0),width=2)

    elif t == "action" and n == 9:
        # Full team + ELDER-7 locks in
        draw_mech(draw, W//2-520, H//2+50, C_STORM,   0.80, "hero")
        draw_mech(draw, W//2-280, H//2+40, C_GRANITE, 0.85, "hero")
        draw_mech(draw, W//2-60,  H//2+30, C_BLAZE,   0.95, "hero")
        draw_mech(draw, W//2+160, H//2+40, C_NOVA,    0.85, "hero")
        draw_mech(draw, W//2+360, H//2+50, C_RUMBLE,  0.80, "hero")
        draw_mech(draw, W//2+560, H//2+30, C_ELDER7,  0.85, "elder")

    elif t == "climax":
        # ELDER-7 front and center, dramatic
        draw_mech(draw, W//2, H//2+20, C_ELDER7, 1.1, "elder")
        # Dramatic rings outward
        for ri in range(30, 300, 40):
            draw.ellipse([W//2-ri,H//2-ri+20,W//2+ri,H//2+ri+20],outline=C_ELDER7,width=3)

    img.convert("RGB").save(str(out))

# ── Synth music ────────────────────────────────────────────────────────────────
def generate_synth_music(duration, out):
    try:
        import numpy as np
    except ImportError:
        subprocess.run([sys.executable,"-m","pip","install","numpy","-q"])
        import numpy as np
    sr=44100; n=int(sr*duration); t=np.linspace(0,duration,n); audio=np.zeros(n)
    def synth(freq,start,dur,amp=0.2,wtype="saw"):
        s=int(start*sr); e=min(int((start+dur)*sr),n)
        if s>=n: return
        seg=np.linspace(0,dur,e-s)
        env=np.exp(-1.5*seg/dur)*(1-np.exp(-20*seg))
        w=(2*(seg*freq-np.floor(seg*freq+0.5))) if wtype=="saw" else np.sign(np.sin(2*np.pi*freq*seg))
        audio[s:e]+=amp*env*w
    beat=60/140
    bass=[55,55,65.4,55,49,55,65.4,73.4]
    for i,f in enumerate(bass*40):
        if i*beat>duration: break
        synth(f,i*beat,beat*0.8,0.28,"saw")
    lead=[220,261.6,329.6,261.6,220,196,220,246.9]
    for i,f in enumerate(lead*20):
        if i*beat*2>duration: break
        synth(f,i*beat*2,beat*1.5,0.13,"square")
    for i in range(int(duration/beat)):
        if i%4==0:
            kt=np.linspace(0,0.1,int(0.1*sr))
            k=np.sin(2*np.pi*60*kt)*np.exp(-30*kt)
            s=int(i*beat*sr); audio[s:s+len(k)]+=0.38*k
    audio=np.clip(audio*32767,-32767,32767).astype(np.int16)
    tmp=str(out).replace(".aac",".wav")
    with wave.open(tmp,"w") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr)
        wf.writeframes(audio.tobytes())
    _run([FFMPEG,"-y","-i",tmp,"-c:a","aac","-b:a","128k",str(out)],"music")
    try: os.remove(tmp)
    except: pass

def generate_tts(text, out_wav):
    """Generate voiceover via Windows SAPI (pyttsx3). Returns True if wav written."""
    try:
        import pyttsx3
    except ImportError:
        subprocess.run([sys.executable,"-m","pip","install","pyttsx3","-q"],
                       capture_output=True, timeout=30)
        try:
            import pyttsx3
        except ImportError:
            print("  [TTS] pyttsx3 not available — voiceover skipped (music only)")
            return False
    try:
        eng = pyttsx3.init()
        # Prefer a deeper/male voice for narrator feel
        voices = eng.getProperty("voices") or []
        for v in voices:
            n = (v.name or "").lower()
            if any(k in n for k in ("david","mark","george","zira")):
                eng.setProperty("voice", v.id); break
        eng.setProperty("rate", 148)    # slightly slower = drama
        eng.setProperty("volume", 1.0)
        eng.save_to_file(text, str(out_wav))
        eng.runAndWait()
        return Path(out_wav).stat().st_size > 100 if Path(out_wav).exists() else False
    except Exception as e:
        print(f"  [TTS error] {e}")
        return False

def generate_srt(narration, duration, out):
    words=narration.split(); chunks=[]; chunk=[]; n=0
    for w in words:
        chunk.append(w); n+=1
        if n>=7 or w.endswith((".",  "!", "?", "—")):
            chunks.append(" ".join(chunk)); chunk=[]; n=0
    if chunk: chunks.append(" ".join(chunk))
    dt=duration/max(len(chunks),1)
    lines=[]
    for i,c in enumerate(chunks):
        s=i*dt; e=min((i+1)*dt,duration-0.1)
        def ts(x): mm=int(x//60); ss=int(x%60); ms=int((x%1)*1000); return f"00:{mm:02d}:{ss:02d},{ms:03d}"
        lines.append(f"{i+1}\n{ts(s)} --> {ts(e)}\n{c}\n")
    with open(str(out),"w",encoding="utf-8") as f: f.write("\n".join(lines))

def still_to_video(still, out, duration):
    fps=25; frames=int(duration*fps)
    step=0.0003; end=1.0+step*duration*fps
    vf=f"zoompan=z='min(zoom+{step:.6f},{end:.4f})':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1920x1080:fps={fps},setsar=1,format=yuv420p"
    return _run([FFMPEG,"-y","-loop","1","-i",str(still),"-t",str(duration),
                 "-vf",vf,"-c:v","libx264","-preset","fast","-crf","22",
                 "-pix_fmt","yuv420p","-movflags","+faststart",str(out)],"zoompan")

def render_scene(scene, work):
    n=scene["scene_number"]
    fin=work/f"scene_{n:02d}_final.mp4"
    if fin.exists(): print(f"  Scene {n:02d} cached ✓"); return fin

    print(f"  Scene {n:02d}: {scene['title']}", flush=True)
    bg    = work/f"scene_{n:02d}_bg.png"
    st    = work/f"scene_{n:02d}_still.png"
    cl    = work/f"scene_{n:02d}_clip.mp4"
    mu    = work/f"scene_{n:02d}_music.aac"
    vo    = work/f"scene_{n:02d}_voice.wav"
    mixed = work/f"scene_{n:02d}_audio.aac"
    sr    = work/f"scene_{n:02d}.srt"
    sub   = work/f"scene_{n:02d}_subbed.mp4"
    dur   = scene.get("duration_sec",9)
    narr  = scene.get("narration","")

    if not bg.exists(): make_background(scene.get("bg_colors",["#0A0A1F","#1A1A3E"]),bg)
    if not st.exists():
        vp = scene.get("visual_prompt","")
        got_ai = False
        if vp:
            got_ai = fetch_pollinations(vp, st, n)
        if not got_ai:
            make_scene_still(scene, st)
    if not cl.exists(): still_to_video(st,cl,dur)
    if not mu.exists(): generate_synth_music(dur,mu)
    if not vo.exists() and narr: generate_tts(narr, vo)
    if not sr.exists(): generate_srt(narr,dur,sr)

    # Mix voice (100%) + music (25%) → mixed audio track
    if not mixed.exists():
        if vo.exists() and mu.exists():
            _run([FFMPEG,"-y","-i",str(mu),"-i",str(vo),
                  "-filter_complex",
                  "[0:a]volume=0.25[m];[1:a]volume=1.0[v];[m][v]amix=inputs=2:duration=first[a]",
                  "-map","[a]","-c:a","aac","-b:a","128k",str(mixed)],"audiomix")
        elif vo.exists():
            _run([FFMPEG,"-y","-i",str(vo),"-c:a","aac","-b:a","128k",str(mixed)],"vo2aac")
        elif mu.exists():
            shutil.copy2(str(mu), str(mixed))

    if not sub.exists() and cl.exists():
        srt_safe=str(sr).replace("\\","/").replace(":","\\:")
        vf=f"subtitles='{srt_safe}':force_style='FontName=Arial,FontSize=26,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Bold=1,Outline=3,Alignment=2'"
        ok=_run([FFMPEG,"-y","-i",str(cl),"-vf",vf,"-c:v","libx264",
                 "-preset","fast","-crf","22",str(sub)],"subs")
        if not ok: shutil.copy2(str(cl),str(sub))

    audio = mixed if mixed.exists() else mu
    if sub.exists() and audio.exists():
        _run([FFMPEG,"-y","-i",str(sub),"-i",str(audio),"-c:v","copy","-c:a","aac",
              "-shortest","-map","0:v","-map","1:a",str(fin)],"mux")
    if fin.exists():
        dur_val = _probe(fin)
        status = f"{dur_val:.1f}s"
    else:
        status = "FAILED"
    print(f"    -> {status}", flush=True)
    return fin

def make_title_card(work):
    out=work/"title_still.png"
    if out.exists(): return out
    img=Image.new("RGB",(W,H),C_DARK); draw=ImageDraw.Draw(img)
    for i in range(60):
        draw.line([(0,i*3),(W,i*3)],fill=(min(C_BLAZE[0],i*4),0,0))
    # Red glow bar
    for y in range(H//2-120,H//2-80):
        draw.line([(W//4,y),(3*W//4,y)],fill=(200,30,0))
    try:
        from PIL import ImageFont
        font_big = ImageFont.truetype("arialbd.ttf",90)
        font_med = ImageFont.truetype("arial.ttf",52)
        font_sm  = ImageFont.truetype("arial.ttf",36)
    except:
        font_big = font_med = font_sm = None
    draw.text((W//2,H//2-100),"MECH LEGENDS",fill=C_BLAZE,anchor="mm",font=font_big)
    draw.text((W//2,H//2+10),"THE SIGNAL",fill=(255,255,255),anchor="mm",font=font_med)
    draw.text((W//2,H//2+90),"Season 1 · Episode 1",fill=(180,180,200),anchor="mm",font=font_sm)
    draw.text((W//2,H//2+148),"What wakes ELDER-7 after 2,800 years of silence?",fill=(130,130,160),anchor="mm",font=font_sm)
    out.parent.mkdir(parents=True,exist_ok=True)
    img.save(str(out)); return out

def make_end_card(work):
    out=work/"end_still.png"
    if out.exists(): return out
    img=Image.new("RGB",(W,H),C_DARK); draw=ImageDraw.Draw(img)
    try:
        from PIL import ImageFont
        font_big=ImageFont.truetype("arialbd.ttf",72)
        font_med=ImageFont.truetype("arial.ttf",44)
        font_sm =ImageFont.truetype("arial.ttf",32)
    except:
        font_big=font_med=font_sm=None
    draw.text((W//2,H//2-100),"MECH LEGENDS",fill=C_BLAZE,anchor="mm",font=font_big)
    draw.text((W//2,H//2),"SUBSCRIBE — new episode every week!",fill=(255,255,255),anchor="mm",font=font_med)
    draw.text((W//2,H//2+80),"Next: EP002 — The Hunt Begins",fill=(180,180,200),anchor="mm",font=font_sm)
    img.save(str(out)); return out

# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    OUTDIR.mkdir(exist_ok=True)
    WORK.mkdir(exist_ok=True)

    ep = json.loads(JSON.read_text(encoding="utf-8"))
    scenes = ep["scenes"]

    print(f"\n{'='*50}")
    print(f"  MECH LEGENDS EP001 — {ep['title']}")
    print(f"  {len(scenes)} scenes  |  {sum(s.get('duration_sec',9) for s in scenes)}s raw")
    print(f"{'='*50}\n")

    # ── 1. Render all scenes ───────────────────────────────────────────────────
    clips = []

    # Title card (5s)
    tf = WORK/"title_final.mp4"
    if not tf.exists():
        print("  Title card...")
        ts = WORK/"title_still.png"
        if not ts.exists():
            title_prompt = "Cinematic sci-fi title card, ancient bronze giant robot ELDER-7 silhouette against massive glowing red archive wall filled with names all reading FALLEN, six small mech warriors in foreground, dramatic red and black atmosphere, epic movie poster style, 4k"
            if not fetch_pollinations(title_prompt, ts, 0):
                ts = make_title_card(WORK)
        tv = WORK/"title_vid.mp4"
        ta = WORK/"title_audio.aac"
        still_to_video(ts, tv, 5)
        generate_synth_music(5, ta)
        _run([FFMPEG,"-y","-i",str(tv),"-i",str(ta),"-c:v","copy","-c:a","copy",
              "-shortest","-map","0:v","-map","1:a",str(tf)],"title_mux")
    if tf.exists(): clips.append(tf)

    for scene in scenes:
        f = render_scene(scene, WORK)
        if f and f.exists(): clips.append(f)

    # End card (5s)
    ef = WORK/"end_final.mp4"
    if not ef.exists():
        print("  End card...")
        es = make_end_card(WORK)
        ev = WORK/"end_vid.mp4"
        ea = WORK/"end_audio.aac"
        still_to_video(es, ev, 5)
        generate_synth_music(5, ea)
        _run([FFMPEG,"-y","-i",str(ev),"-i",str(ea),"-c:v","copy","-c:a","copy",
              "-shortest","-map","0:v","-map","1:a",str(ef)],"end_mux")
    if ef.exists(): clips.append(ef)

    # ── 2. Concatenate ─────────────────────────────────────────────────────────
    print(f"\nConcatenating {len(clips)} clips...")
    concat_txt = WORK/"concat.txt"
    with open(str(concat_txt),"w") as f:
        for c in clips: f.write(f"file '{str(c).replace(chr(92),chr(47))}'\n")

    _run([FFMPEG,"-y","-f","concat","-safe","0","-i",str(concat_txt),
          "-c","copy","-movflags","+faststart",str(FINAL)],"concat")

    if FINAL.exists():
        dur=_probe(FINAL); sz=FINAL.stat().st_size/1024/1024
        print(f"\n{'='*50}")
        print(f"  ✓ ML_EP001_final.mp4")
        print(f"  Duration: {dur:.1f}s  |  Size: {sz:.1f}MB")
        print(f"  Location: {FINAL}")
        print(f"{'='*50}")
        # 3x backup
        ts=datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        bk=BASE/"_backups"
        bk.mkdir(exist_ok=True)
        shutil.copy2(str(FINAL),str(bk/f"ML_EP001_final.mp4.{ts}"))
        shutil.copy2(str(FINAL),str(bk/"ML_EP001_final.mp4.latest"))
        print(f"  Backed up to _backups/")
    else:
        print("\n  ✗ Final concat failed — check individual scenes in output\\_work_ml_ep001\\")

if __name__ == "__main__":
    main()
