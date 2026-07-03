#!/usr/bin/env python3
"""
mech_legends_render.py — Render engine for Mech Legends channel.
Characters: BLAZE (red), STORM (blue), GRANITE (green), RUMBLE (purple/villain), BOLT (black).
"""
import json, subprocess, shutil, sys, math, datetime
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

FFMPEG  = "/usr/bin/ffmpeg"
BASE    = Path("/sessions/eloquent-amazing-shannon/mnt/claude/video-bot-pipeline")
PROMPTS = BASE / "prompts"
RENDERS = BASE / "renders" / "mech_legends"
BACKUPS = BASE / "_backups"
W, H    = 1920, 1080

# Character color palette
C_BLAZE   = (255, 50,  20)   # BLAZE — red
C_STORM   = (0,  153, 255)   # STORM — blue
C_GRANITE = (40, 200,  80)   # GRANITE — green
C_NOVA    = (200,200,230)    # NOVA — silver
C_RUMBLE  = (140,  0, 220)   # RUMBLE — deep purple (villain)
C_BOLT    = (20,  20,  20)   # BOLT — black
C_GOLD    = (255, 214,  0)
C_DARK    = (8,   6,  18)

def _run(cmd, label=""):
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=42)
        if r.returncode != 0:
            print(f"[ERR:{label}] {r.stderr[-300:].decode(errors='ignore')}")
            return False
        return True
    except subprocess.TimeoutExpired:
        print(f"[TIMEOUT:{label}]"); return False

def _probe(p):
    r = subprocess.run(
        ["ffprobe","-v","quiet","-show_entries","format=duration",
         "-of","default=noprint_wrappers=1:nokey=1","-i",str(p)], capture_output=True)
    try: return float(r.stdout.strip())
    except: return 0.0

def _backup(src):
    ts = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    nm = Path(src).name
    shutil.copy2(src, BACKUPS / f"{nm}.{ts}")
    shutil.copy2(src, BACKUPS / f"{nm}.latest")

def _hx(c):
    c = c.lstrip("#"); return tuple(int(c[i:i+2],16) for i in (0,2,4))

def draw_mech(draw, cx, cy, color, scale=1.0, style="hero"):
    """Draw a toyetic robot silhouette."""
    s = scale
    c = color

    if style == "villain":
        # RUMBLE — massive 4-armed crusher, 2x scale
        s *= 1.6
        # Core body (huge)
        draw.rectangle([cx-int(100*s), cy-int(180*s), cx+int(100*s), cy+int(100*s)],
                       fill=(*c, 240))
        # Head
        draw.rectangle([cx-int(55*s), cy-int(250*s), cx+int(55*s), cy-int(190*s)],
                       fill=(*c, 240))
        # Red eyes
        draw.ellipse([cx-int(40*s), cy-int(240*s), cx-int(15*s), cy-int(215*s)],
                     fill=(255,30,30,255))
        draw.ellipse([cx+int(15*s), cy-int(240*s), cx+int(40*s), cy-int(215*s)],
                     fill=(255,30,30,255))
        # 4 arms — upper pair
        draw.rectangle([cx-int(200*s), cy-int(160*s), cx-int(100*s), cy-int(80*s)],
                       fill=(*c, 220))
        draw.rectangle([cx+int(100*s), cy-int(160*s), cx+int(200*s), cy-int(80*s)],
                       fill=(*c, 220))
        # Lower pair
        draw.rectangle([cx-int(180*s), cy-int(60*s), cx-int(100*s), cy+int(40*s)],
                       fill=(*c, 210))
        draw.rectangle([cx+int(100*s), cy-int(60*s), cx+int(180*s), cy+int(40*s)],
                       fill=(*c, 210))
        # Crusher fists
        for fx, fy in [(-200,-120),(200,-120),(-180,20),(180,20)]:
            draw.ellipse([cx+int((fx-25)*s), cy+int((fy-25)*s),
                         cx+int((fx+25)*s), cy+int((fy+25)*s)],
                         fill=(min(c[0]+40,255), c[1], c[2], 255))
        # Legs
        draw.rectangle([cx-int(80*s), cy+int(100*s), cx-int(20*s), cy+int(220*s)],
                       fill=(*c, 230))
        draw.rectangle([cx+int(20*s), cy+int(100*s), cx+int(80*s), cy+int(220*s)],
                       fill=(*c, 230))
        # Crown spikes
        for sx in [-40,-20,0,20,40]:
            draw.polygon([
                (cx+int(sx*s), cy-int(250*s)),
                (cx+int((sx-10)*s), cy-int(285*s)),
                (cx+int((sx+10)*s), cy-int(285*s))
            ], fill=(min(c[0]+60,255), c[1], min(c[2]+20,255), 200))

    elif style == "sidekick":
        # BOLT — thin, crackly, small
        s *= 0.6
        draw.rectangle([cx-int(30*s), cy-int(120*s), cx+int(30*s), cy+int(60*s)],
                       fill=(*c, 220))
        draw.rectangle([cx-int(20*s), cy-int(160*s), cx+int(20*s), cy-int(120*s)],
                       fill=(*c, 220))
        draw.ellipse([cx-int(12*s), cy-int(150*s), cx-int(2*s), cy-int(138*s)],
                     fill=(200,200,50,255))
        draw.ellipse([cx+int(2*s), cy-int(150*s), cx+int(12*s), cy-int(138*s)],
                     fill=(200,200,50,255))
        # Lightning bolts around
        for lx, ly in [(-50,-80),(50,-80),(-60,0),(60,0)]:
            pts = [(cx+int(lx*s), cy+int((ly-15)*s)),
                   (cx+int((lx-8)*s), cy+int(ly*s)),
                   (cx+int(lx*s), cy+int(ly*s)),
                   (cx+int((lx-12)*s), cy+int((ly+20)*s))]
            draw.polygon(pts, fill=(220,220,0,200))
        # Arms
        draw.rectangle([cx-int(60*s), cy-int(100*s), cx-int(30*s), cy-int(40*s)],
                       fill=(*c, 200))
        draw.rectangle([cx+int(30*s), cy-int(100*s), cx+int(60*s), cy-int(40*s)],
                       fill=(*c, 200))
        # Legs
        draw.rectangle([cx-int(20*s), cy+int(60*s), cx-int(5*s), cy+int(130*s)],
                       fill=(*c, 210))
        draw.rectangle([cx+int(5*s), cy+int(60*s), cx+int(20*s), cy+int(130*s)],
                       fill=(*c, 210))

    else:
        # Hero (BLAZE/STORM/GRANITE) — toyetic vehicle-transformer
        # Chest plate
        draw.rectangle([cx-int(60*s), cy-int(120*s), cx+int(60*s), cy+int(60*s)],
                       fill=(*c, 240))
        # Shoulder pads (wide, toyetic)
        draw.rectangle([cx-int(110*s), cy-int(120*s), cx-int(60*s), cy-int(50*s)],
                       fill=(*c, 230))
        draw.rectangle([cx+int(60*s), cy-int(120*s), cx+int(110*s), cy-int(50*s)],
                       fill=(*c, 230))
        # Arms
        draw.rectangle([cx-int(100*s), cy-int(50*s), cx-int(60*s), cy+int(60*s)],
                       fill=(*c, 220))
        draw.rectangle([cx+int(60*s), cy-int(50*s), cx+int(100*s), cy+int(60*s)],
                       fill=(*c, 220))
        # Fists
        draw.ellipse([cx-int(105*s), cy+int(40*s), cx-int(60*s), cy+int(80*s)],
                     fill=(min(c[0]+30,255), min(c[1]+20,255), min(c[2]+20,255), 255))
        draw.ellipse([cx+int(60*s), cy+int(40*s), cx+int(105*s), cy+int(80*s)],
                     fill=(min(c[0]+30,255), min(c[1]+20,255), min(c[2]+20,255), 255))
        # Head
        draw.rectangle([cx-int(40*s), cy-int(180*s), cx+int(40*s), cy-int(125*s)],
                       fill=(*c, 240))
        # Helmet crest
        draw.polygon([(cx-int(15*s), cy-int(180*s)),
                      (cx, cy-int(205*s)),
                      (cx+int(15*s), cy-int(180*s))],
                     fill=(min(c[0]+60,255), min(c[1]+40,255), min(c[2]+40,255), 255))
        # Visor
        draw.rectangle([cx-int(30*s), cy-int(168*s), cx+int(30*s), cy-int(148*s)],
                       fill=(100, 220, 255, 230))
        # Chest insignia (circle)
        draw.ellipse([cx-int(20*s), cy-int(80*s), cx+int(20*s), cy-int(40*s)],
                     fill=(255,255,255,180))
        draw.ellipse([cx-int(14*s), cy-int(74*s), cx+int(14*s), cy-int(46*s)],
                     fill=(*c, 255))
        # Legs
        draw.rectangle([cx-int(50*s), cy+int(60*s), cx-int(10*s), cy+int(180*s)],
                       fill=(*c, 230))
        draw.rectangle([cx+int(10*s), cy+int(60*s), cx+int(50*s), cy+int(180*s)],
                       fill=(*c, 230))
        # Feet
        draw.rectangle([cx-int(60*s), cy+int(165*s), cx-int(5*s), cy+int(200*s)],
                       fill=(*c, 220))
        draw.rectangle([cx+int(5*s), cy+int(165*s), cx+int(60*s), cy+int(200*s)],
                       fill=(*c, 220))

def make_background(scene, out):
    img  = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)
    bgs  = scene.get("bg_colors", ["#0A0A1F","#1A1A3E","#0D2040"])

    def hx(c): c=c.lstrip("#"); return tuple(int(c[i:i+2],16) for i in (0,2,4))
    top = hx(bgs[0]); bot = hx(bgs[-1])
    for y in range(H):
        t = y/H
        r = int(top[0]*(1-t) + bot[0]*t)
        g = int(top[1]*(1-t) + bot[1]*t)
        b = int(top[2]*(1-t) + bot[2]*t)
        draw.line([(0,y),(W,y)], fill=(r,g,b))

    # Stars
    import random; random.seed(99)
    for _ in range(200):
        sx = random.randint(0, W); sy = random.randint(0, H//2)
        br = random.randint(80,255)
        draw.ellipse([sx-1,sy-1,sx+1,sy+1], fill=(br,br,br))

    # Accent glow at bottom
    acc = _hx(scene.get("accent","#00D4FF"))
    for i in range(60):
        alpha = max(0, 60-i)
        y = H - i*8
        draw.line([(0,y),(W,y)], fill=(acc[0],acc[1],acc[2]))

    img.save(str(out))

def make_scene_still(scene, out):
    bg_path = Path(str(out).replace("_still.png","_bg.png"))
    if not bg_path.exists():
        make_background(scene, bg_path)
    img  = Image.open(str(bg_path)).convert("RGBA")
    draw = ImageDraw.Draw(img, "RGBA")

    stype = scene.get("type","")

    if stype == "cold_open":
        # Space energy pulse — no characters, just energy lines
        acc = _hx(scene.get("accent","#FF3300"))
        for i in range(8):
            x1 = W//2 + (i-4)*40; y1=0
            x2 = W//2 + (i-4)*20; y2=H
            draw.line([(x1,y1),(x2,y2)], fill=(*acc, 80-i*8), width=3)

    elif stype == "hero_intro":
        draw_mech(draw, W//2, H//2+50, C_BLAZE, 1.2, "hero")

    elif stype == "team_intro":
        draw_mech(draw, W//2-400, H//2+50, C_STORM, 0.9, "hero")
        draw_mech(draw, W//2, H//2+80, C_GRANITE, 1.1, "hero")
        draw_mech(draw, W//2+400, H//2+50, C_BLAZE, 0.9, "hero")

    elif stype == "villain_intro":
        draw_mech(draw, W//2, H//2-20, C_RUMBLE, 1.0, "villain")
        draw_mech(draw, W//2+350, H//2+100, C_BOLT, 0.7, "sidekick")

    elif stype == "villain_dominance":
        draw_mech(draw, W//2, H//2-60, C_RUMBLE, 1.1, "villain")

    elif stype == "crisis":
        # RUMBLE holds BLAZE
        draw_mech(draw, W//2, H//2, C_RUMBLE, 1.0, "villain")
        # Small BLAZE in hand
        draw_mech(draw, W//2-180, H//2-100, C_BLAZE, 0.5, "hero")

    elif stype == "darkest_moment":
        # Three defeated heroes
        draw_mech(draw, W//2-500, H//2+80, C_BLAZE, 0.7, "hero")
        draw_mech(draw, W//2, H//2+100, C_STORM, 0.7, "hero")
        draw_mech(draw, W//2+500, H//2+60, C_GRANITE, 0.8, "hero")
        draw_mech(draw, W//2+300, H//2-50, C_BOLT, 0.5, "sidekick")

    elif stype == "turning_point":
        draw_mech(draw, W//2, H//2+30, C_BLAZE, 1.1, "hero")
        # Glow effect
        acc = _hx("#FF3300")
        for r in range(20, 200, 20):
            draw.ellipse([W//2-r, H//2-r+30, W//2+r, H//2+r+30],
                        outline=(*acc, max(0, 80-r//3)), width=2)

    elif stype == "hero_reveal":
        draw_mech(draw, W//2-320, H//2+30, C_STORM, 1.0, "hero")
        draw_mech(draw, W//2, H//2+20, C_BLAZE, 1.1, "hero")
        draw_mech(draw, W//2+320, H//2+10, C_GRANITE, 1.05, "hero")

    elif stype == "cliffhanger":
        draw_mech(draw, W//2-380, H//2+30, C_STORM, 0.85, "hero")
        draw_mech(draw, W//2-150, H//2+20, C_BLAZE, 0.95, "hero")
        draw_mech(draw, W//2+80, H//2+10, C_GRANITE, 0.90, "hero")
        draw_mech(draw, W//2+480, H//2-80, C_RUMBLE, 0.8, "villain")
        draw_mech(draw, W//2+380, H//2+80, C_BOLT, 0.5, "sidekick")

    img.convert("RGB").save(str(out))

def still_to_video(still, out, duration, mode="push_in"):
    fps = 25; frames = int(duration * fps)
    if duration <= 12.0:
        step = 0.0003
        end  = 1.0 + step*duration*fps
        if mode == "pull_back":
            vf = f"zoompan=z='max(1,{end:.4f}-{step:.6f}*on)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1920x1080:fps={fps},setsar=1,format=yuv420p"
        else:
            vf = f"zoompan=z='min(zoom+{step:.6f},{end:.4f})':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1920x1080:fps={fps},setsar=1,format=yuv420p"
        return _run([FFMPEG,"-y","-loop","1","-i",str(still),"-t",str(duration),
                     "-vf",vf,"-c:v","libx264","-preset","fast","-crf","22",
                     "-pix_fmt","yuv420p","-movflags","+faststart",str(out)],"zoompan")
    else:
        return _run([FFMPEG,"-y","-loop","1","-i",str(still),"-t",str(duration),
                     "-vf","scale=1920:1080,setsar=1,format=yuv420p",
                     "-c:v","libx264","-preset","ultrafast","-crf","22",
                     "-pix_fmt","yuv420p","-movflags","+faststart",str(out)],"static")

def generate_synth_music(duration, out):
    import numpy as np, wave, os
    sr = 44100; n = int(sr*duration)
    t  = np.linspace(0, duration, n)
    audio = np.zeros(n)

    # Heavy synth bass + lead
    def synth(freq, start, dur, amp=0.2, wave_type="saw"):
        s=int(start*sr); e=min(int((start+dur)*sr),n)
        if s>=n: return
        seg = np.linspace(0, dur, e-s)
        env = np.exp(-1.5*seg/dur) * (1 - np.exp(-20*seg))
        if wave_type == "saw":
            w = 2*(seg*freq - np.floor(seg*freq+0.5))
        else:
            w = np.sign(np.sin(2*np.pi*freq*seg))
        audio[s:e] += amp * env * w

    # Driving bass pattern
    bass = [55, 55, 65.4, 55, 49, 55, 65.4, 73.4]
    beat = 60/140  # 140bpm action tempo
    for i, f in enumerate(bass * 30):
        if i*beat > duration: break
        synth(f, i*beat, beat*0.8, 0.3, "saw")

    # Action lead melody
    lead = [220, 261.6, 329.6, 261.6, 220, 196, 220, 246.9]
    for i, f in enumerate(lead * 15):
        if i*beat*2 > duration: break
        synth(f, i*beat*2, beat*1.5, 0.15, "square")

    # Percussion hits
    for i in range(int(duration/beat)):
        if i%4 == 0:  # kick
            kick_t = np.linspace(0, 0.1, int(0.1*sr))
            kick   = np.sin(2*np.pi*60*kick_t) * np.exp(-30*kick_t)
            s = int(i*beat*sr)
            audio[s:s+len(kick)] += 0.4 * kick

    audio = np.clip(audio * 32767, -32767, 32767).astype(np.int16)
    tmp = str(out).replace(".aac",".wav")
    with wave.open(tmp,"w") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr)
        wf.writeframes(audio.tobytes())
    _run([FFMPEG,"-y","-i",tmp,"-c:a","aac","-b:a","128k",str(out)],"music")
    try: os.remove(tmp)
    except: pass

def generate_srt(scene, out):
    words = scene.get("narration","").split()
    dur   = scene.get("duration_sec", 9)
    chunks, chunk, n = [], [], 0
    for w in words:
        chunk.append(w); n+=1
        if n>=7 or w.endswith((".",  "!", "?", "—")):
            chunks.append(" ".join(chunk)); chunk=[]; n=0
    if chunk: chunks.append(" ".join(chunk))
    dt = dur/max(len(chunks),1)
    lines = []
    for i, c in enumerate(chunks):
        s=i*dt; e=min((i+1)*dt, dur-0.1)
        def ts(x): mm=int(x//60); ss=int(x%60); ms=int((x%1)*1000); return f"00:{mm:02d}:{ss:02d},{ms:03d}"
        lines.append(f"{i+1}\n{ts(s)} --> {ts(e)}\n{c}\n")
    with open(str(out),"w") as f: f.write("\n".join(lines))

def render_scene(scene, work_dir, ep_id):
    n   = scene["scene_number"]
    fin = work_dir / f"scene_{n:02d}_final.mp4"
    if fin.exists():
        print(f"  Scene {n:02d} ✓ (cached)")
        return fin

    print(f"  Scene {n:02d}: {scene['title']}")
    bg  = work_dir / f"scene_{n:02d}_bg.png"
    st  = work_dir / f"scene_{n:02d}_still.png"
    cl  = work_dir / f"scene_{n:02d}_clip.mp4"
    mu  = work_dir / f"scene_{n:02d}_music.aac"
    sr  = work_dir / f"scene_{n:02d}.srt"
    sub = work_dir / f"scene_{n:02d}_subbed.mp4"
    dur = scene.get("duration_sec", 9)

    if not bg.exists():  make_background(scene, bg)
    if not st.exists():  make_scene_still(scene, st)
    if not cl.exists():  still_to_video(st, cl, dur, scene.get("camera","push_in"))
    if not mu.exists():  generate_synth_music(dur, mu)
    if not sr.exists():  generate_srt(scene, sr)

    if not sub.exists() and cl.exists():
        vf = f"subtitles={sr}:force_style='FontName=Arial,FontSize=24,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Bold=1,Outline=3,Alignment=2'"
        ok = _run([FFMPEG,"-y","-i",str(cl),"-vf",vf,
                   "-c:v","libx264","-preset","fast","-crf","22",str(sub)],"subs")
        if not ok: shutil.copy2(str(cl), str(sub))

    if sub.exists() and mu.exists():
        _run([FFMPEG,"-y","-i",str(sub),"-i",str(mu),"-c:v","copy","-c:a","aac",
              "-shortest","-map","0:v","-map","1:a",str(fin)],"mux")
    if fin.exists():
        print(f"    ✓ {_probe(fin):.1f}s")
    else:
        print(f"    ✗ FAILED")
    return fin

def make_title_card(title, tagline, ep_id, out):
    img  = Image.new("RGB",(W,H), C_DARK)
    draw = ImageDraw.Draw(img)
    # Red glow at top
    for i in range(60):
        draw.line([(0,i*3),(W,i*3)], fill=(min(C_BLAZE[0], i*5), 0, 0))
    draw.text((W//2, H//2-100), "MECH LEGENDS", fill=C_BLAZE, anchor="mm")
    draw.text((W//2, H//2), title, fill=(255,255,255), anchor="mm")
    draw.text((W//2, H//2+80), tagline, fill=(180,180,200), anchor="mm")
    draw.text((W//2, H//2+140), ep_id, fill=(100,100,130), anchor="mm")
    img.save(str(out))

def make_end_card(ep_id, next_ep, out):
    img  = Image.new("RGB",(W,H), C_DARK)
    draw = ImageDraw.Draw(img)
    draw.text((W//2, H//2-80), "MECH LEGENDS", fill=C_BLAZE, anchor="mm")
    draw.text((W//2, H//2), "SUBSCRIBE — new episode every week!", fill=(255,255,255), anchor="mm")
    if next_ep:
        draw.text((W//2, H//2+80), f"Next: {next_ep}", fill=(180,180,200), anchor="mm")
    img.save(str(out))

TITLE_DUR = 5; END_DUR = 5

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--ep", default="ml_ep001")
    parser.add_argument("--scenes", type=str)
    parser.add_argument("--concat", action="store_true")
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()

    ep_file = PROMPTS / f"scene_prompts.{args.ep}.final.json"
    ep = json.load(open(str(ep_file)))
    RENDERS.mkdir(parents=True, exist_ok=True)
    work = RENDERS / f"_work_{args.ep}"
    work.mkdir(parents=True, exist_ok=True)

    if args.status:
        for s in ep["scenes"]:
            n=s["scene_number"]; fp=work/f"scene_{n:02d}_final.mp4"
            print(f"  {n:02d} {s['title'][:40]:<40} {'✓' if fp.exists() else '·'}")
        print(f"  Final: {'✓' if (RENDERS/f'{args.ep}.mp4').exists() else '·'}")
        sys.exit(0)

    if args.concat:
        clips=[]
        tf=work/"title_final.mp4"; ef=work/"end_final.mp4"
        if not tf.exists():
            ts=work/"title_still.png"; tv=work/"title_vid.mp4"; ta=work/"title_audio.aac"
            make_title_card(ep["title"],ep.get("tagline",""),ep["episode_id"],ts)
            still_to_video(ts,tv,TITLE_DUR,"push_in")
            generate_synth_music(TITLE_DUR,ta)
            _run([FFMPEG,"-y","-i",str(tv),"-i",str(ta),"-c:v","copy","-c:a","copy",
                  "-shortest","-map","0:v","-map","1:a",str(tf)],"title_mux")
        if tf.exists(): clips.append(tf)
        for s in ep["scenes"]:
            n=s["scene_number"]; fp=work/f"scene_{n:02d}_final.mp4"
            if fp.exists(): clips.append(fp)
        if not ef.exists():
            es=work/"end_still.png"; ev=work/"end_vid.mp4"; ea=work/"end_audio.aac"
            make_end_card(ep["episode_id"],ep.get("next_episode_preview",""),es)
            still_to_video(es,ev,END_DUR,"pull_back")
            generate_synth_music(END_DUR,ea)
            _run([FFMPEG,"-y","-i",str(ev),"-i",str(ea),"-c:v","copy","-c:a","copy",
                  "-shortest","-map","0:v","-map","1:a",str(ef)],"end_mux")
        if ef.exists(): clips.append(ef)
        cl=work/"concat.txt"
        with open(str(cl),"w") as f:
            for c in clips: f.write(f"file '{c}'\n")
        fo=RENDERS/f"{args.ep}.mp4"
        _run([FFMPEG,"-y","-f","concat","-safe","0","-i",str(cl),
              "-c","copy","-movflags","+faststart",str(fo)],"concat")
        if fo.exists():
            d=_probe(fo); sz=fo.stat().st_size/1024/1024
            print(f"\n✓ {fo.name}  {d:.1f}s  {sz:.1f}MB")
            _backup(fo)
        sys.exit(0)

    if args.scenes:
        parts=args.scenes.split("-")
        lo=int(parts[0]); hi=int(parts[1]) if len(parts)>1 else lo
        for s in ep["scenes"]:
            if lo<=s["scene_number"]<=hi:
                render_scene(s, work, ep["episode_id"])
