#!/usr/bin/env python3
"""
little_olympus_render.py — Kids cartoon renderer for Little Olympus channel.
Bright, colorful, chunky. Completely different aesthetic from documentary/mech.
"""
import json, subprocess, shutil, sys, math, datetime
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

FFMPEG   = "/usr/bin/ffmpeg"
BASE     = Path("/sessions/eloquent-amazing-shannon/mnt/claude/video-bot-pipeline")
PROMPTS  = BASE / "prompts"
RENDERS  = BASE / "renders" / "little_olympus"
BACKUPS  = BASE / "_backups"
W, H     = 1920, 1080

# Little Olympus color palette — bright, warm, kids
C_ZEUS_YELLOW  = (255, 215, 0)
C_SKY_BLUE     = (100, 180, 255)
C_CLOUD_WHITE  = (240, 245, 255)
C_PURPLE_DEEP  = (40, 20, 100)
C_STORM_GREY   = (80, 80, 130)
C_GREEN_GRASS  = (100, 200, 100)
C_ORANGE_WARM  = (255, 140, 40)

def _run(cmd, label=""):
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=42)
        if r.returncode != 0:
            print(f"[ERR:{label}] {r.stderr[-300:].decode(errors='ignore')}")
            return False
        return True
    except subprocess.TimeoutExpired:
        print(f"[TIMEOUT:{label}]")
        return False

def _probe(p):
    r = subprocess.run(
        [FFMPEG,"-v","quiet","-show_entries","format=duration","-of",
         "default=noprint_wrappers=1:nokey=1","-i",str(p)],
        capture_output=True)
    try: return float(r.stdout.strip())
    except: return 0.0

def _backup(src):
    ts  = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    nm  = Path(src).name
    shutil.copy2(src, BACKUPS / f"{nm}.{ts}")
    shutil.copy2(src, BACKUPS / f"{nm}.latest")

def draw_star(draw, cx, cy, r, color, alpha=255):
    pts = []
    for i in range(10):
        angle = math.pi/2 + i * 2*math.pi/10
        rad   = r if i%2==0 else r*0.45
        pts.append((cx + rad*math.cos(angle), cy - rad*math.sin(angle)))
    draw.polygon(pts, fill=(*color[:3], alpha))

def make_sky_background(scene, out):
    img  = Image.new("RGBA", (W, H), (30, 20, 80, 255))
    draw = ImageDraw.Draw(img, "RGBA")

    bgs = scene.get("bg_colors", ["#87CEEB", "#1A1060", "#FFFFFF"])
    def hx(c):
        c=c.lstrip("#"); return tuple(int(c[i:i+2],16) for i in (0,2,4))

    top_col = hx(bgs[0])
    bot_col = hx(bgs[-1]) if len(bgs)>1 else (20,10,60)

    for y in range(H):
        t = y/H
        r = int(top_col[0]*(1-t) + bot_col[0]*t)
        g = int(top_col[1]*(1-t) + bot_col[1]*t)
        b = int(top_col[2]*(1-t) + bot_col[2]*t)
        draw.line([(0,y),(W,y)], fill=(r,g,b,255))

    # Clouds
    for cx, cy, cr in [(200,150,80),(500,100,60),(1400,130,90),(1700,200,70),(900,80,50)]:
        draw.ellipse([cx-cr,cy-cr,cx+cr,cy+cr], fill=(240,245,255,180))
        draw.ellipse([cx-cr*0.7,cy-cr*1.1,cx+cr*0.7,cy+cr*0.3], fill=(245,250,255,160))

    # Stars / sparkles
    import random; random.seed(42)
    for _ in range(30):
        sx = random.randint(50, W-50)
        sy = random.randint(20, H//2)
        draw_star(draw, sx, sy, random.randint(4,10), C_ZEUS_YELLOW, alpha=random.randint(60,180))

    # Bottom ground (fluffy clouds / mount olympus)
    for cx, cy, cr in [(300,900,120),(700,920,100),(1200,910,130),(1600,890,110),(960,940,150)]:
        draw.ellipse([cx-cr,cy-cr//2,cx+cr,cy+cr//2], fill=(255,255,255,200))

    img.save(str(out))
    return out

def make_character_card(char_type, out, scene):
    """Draw a cute character silhouette appropriate to the scene type."""
    bg_path = Path(str(out).replace("_char.png", "_bg.png"))
    img  = Image.open(str(bg_path)).copy()
    draw = ImageDraw.Draw(img, "RGBA")

    scene_type = scene.get("type","")

    if scene_type in ("hook","resolution","lesson_and_cta"):
        # Little Zeus — center
        cx, cy = 960, 700
        # Body
        draw.ellipse([cx-60,cy-160,cx+60,cy+60], fill=(255,230,180,240))  # head/body
        draw.ellipse([cx-50,cy-170,cx+50,cy-100], fill=(255,230,180,240)) # head
        # Crown
        draw.polygon([(cx-35,cy-170),(cx-25,cy-190),(cx,cy-195),(cx+25,cy-190),(cx+35,cy-170)],
                     fill=(*C_ZEUS_YELLOW, 255))
        # Toga
        draw.polygon([(cx-60,cy-80),(cx+60,cy-80),(cx+80,cy+120),(cx-80,cy+120)],
                     fill=(240,240,255,240))
        draw.rectangle([cx-80,cy+60,cx+80,cy+120], fill=(200,200,240,200))
        # Thunderbolt
        bolt_pts = [(cx+70,cy-120),(cx+50,cy-60),(cx+70,cy-60),(cx+45,cy+20)]
        draw.polygon(bolt_pts, fill=(*C_ZEUS_YELLOW,255))
        # Eyes
        draw.ellipse([cx-25,cy-155,cx-5,cy-135], fill=(255,255,255,255))
        draw.ellipse([cx+5,cy-155,cx+25,cy-135], fill=(255,255,255,255))
        draw.ellipse([cx-18,cy-148,cx-10,cy-140], fill=(30,100,200,255))
        draw.ellipse([cx+10,cy-148,cx+18,cy-140], fill=(30,100,200,255))
        # Smile
        draw.arc([cx-20,cy-130,cx+20,cy-115], start=0, end=180, fill=(180,100,80,255), width=4)

    elif scene_type == "setup":
        # Baby Hercules with mountain
        cx, cy = 960, 680
        # Body (chubby)
        draw.ellipse([cx-80,cy-120,cx+80,cy+80], fill=(255,220,170,240))
        # Head
        draw.ellipse([cx-65,cy-190,cx+65,cy-100], fill=(255,220,170,240))
        # Arms raised holding mountain
        draw.ellipse([cx-130,cy-180,cx-70,cy-80], fill=(255,220,170,240))
        draw.ellipse([cx+70,cy-180,cx+130,cy-80], fill=(255,220,170,240))
        # Mini mountain
        draw.polygon([(cx-120,cy-190),(cx,cy-320),(cx+120,cy-190)], fill=(150,180,120,240))
        draw.polygon([(cx-60,cy-250),(cx,cy-320),(cx+60,cy-250)], fill=(220,230,240,220))
        # Lion cape
        draw.polygon([(cx-80,cy-110),(cx-100,cy+40),(cx+100,cy+40),(cx+80,cy-110)],
                     fill=(200,160,80,220))
        # Eyes (happy confused)
        draw.ellipse([cx-28,cy-175,cx-8,cy-155], fill=(255,255,255,255))
        draw.ellipse([cx+8,cy-175,cx+28,cy-155], fill=(255,255,255,255))
        draw.ellipse([cx-20,cy-170,cx-12,cy-162], fill=(100,60,20,255))
        draw.ellipse([cx+12,cy-170,cx+20,cy-162], fill=(100,60,20,255))

    elif scene_type in ("clue","solution"):
        # Athena pointing
        cx, cy = 960, 700
        draw.ellipse([cx-55,cy-190,cx+55,cy-100], fill=(255,230,195,240))
        draw.ellipse([cx-65,cy-100,cx+65,cy+80], fill=(150,140,200,240))
        # Pointing arm
        draw.ellipse([cx+60,cy-170,cx+150,cy-90], fill=(255,230,195,240))
        # Tiny owl on shoulder
        draw.ellipse([cx-80,cy-160,cx-50,cy-120], fill=(180,150,80,240))
        draw.ellipse([cx-72,cy-170,cx-58,cy-150], fill=(60,40,20,240))
        # Hair
        draw.ellipse([cx-55,cy-230,cx+55,cy-150], fill=(100,90,80,240))
        draw.polygon([(cx-20,cy-235),(cx,cy-260),(cx+20,cy-235)], fill=(100,90,80,240))
        # Glasses
        draw.ellipse([cx-38,cy-168,cx-8,cy-148], outline=(80,80,80,255), width=3)
        draw.ellipse([cx+8,cy-168,cx+38,cy-148], outline=(80,80,80,255), width=3)
        draw.line([cx-8,cy-158,cx+8,cy-158], fill=(80,80,80,255), width=2)

    elif scene_type == "problem":
        # Stormy the storm cloud
        cx, cy = 960, 500
        # Main cloud body
        for ox, oy, r in [(0,0,160),(120,-40,120),(-120,-40,120),(0,-80,100),(80,-100,80),(-80,-100,80)]:
            draw.ellipse([cx+ox-r,cy+oy-r,cx+ox+r,cy+oy+r], fill=(90,90,140,230))
        # Grumpy face
        draw.arc([cx-60,cy-30,cx+60,cy+30], start=200, end=340, fill=(50,50,90,255), width=8)
        draw.ellipse([cx-55,cy-80,cx-25,cy-50], fill=(30,30,70,255))
        draw.ellipse([cx+25,cy-80,cx+55,cy-50], fill=(30,30,70,255))
        # Eyebrows (angry)
        draw.line([cx-60,cy-95,cx-20,cy-85], fill=(30,30,70,255), width=6)
        draw.line([cx+20,cy-85,cx+60,cy-95], fill=(30,30,70,255), width=6)
        # Thunderbolt in cloud arm
        draw.polygon([(cx+160,cy-20),(cx+140,cy+30),(cx+155,cy+30),(cx+135,cy+80)],
                     fill=(*C_ZEUS_YELLOW, 255))
        # Lightning bolts around
        for bx, by in [(-150,100),(150,120),(0,150),(-100,160)]:
            draw.polygon([(cx+bx,cy+by-30),(cx+bx-10,cy+by+10),(cx+bx,cy+by+5),(cx+bx-15,cy+by+40)],
                         fill=(*C_ZEUS_YELLOW, 180))

    img.save(str(out))

def still_to_video(still, out, duration, mode="push_in"):
    if duration <= 12.0:
        zoom_step = 0.0003
        zoom_end  = 1.0 + zoom_step * duration * 25
        fps       = 25
        frames    = int(duration * fps)
        if mode == "pull_back":
            vf = (f"zoompan=z='max(1,{zoom_end:.4f}-{zoom_step:.6f}*on)'"
                  f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
                  f":d={frames}:s=1920x1080:fps={fps},setsar=1,format=yuv420p")
        else:
            vf = (f"zoompan=z='min(zoom+{zoom_step:.6f},{zoom_end:.4f})'"
                  f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
                  f":d={frames}:s=1920x1080:fps={fps},setsar=1,format=yuv420p")
        return _run([FFMPEG,"-y","-loop","1","-i",str(still),
                     "-t",str(duration),"-vf",vf,
                     "-c:v","libx264","-preset","fast","-crf","22",
                     "-pix_fmt","yuv420p","-movflags","+faststart",str(out)], "zoompan")
    else:
        return _run([FFMPEG,"-y","-loop","1","-i",str(still),
                     "-t",str(duration),
                     "-vf","scale=1920:1080,setsar=1,format=yuv420p",
                     "-c:v","libx264","-preset","ultrafast","-crf","22",
                     "-pix_fmt","yuv420p","-movflags","+faststart",str(out)], "static")

def generate_kids_music(duration, out):
    """Bouncy xylophone-style synth music for kids show."""
    import numpy as np, struct, wave, tempfile, os
    sr    = 44100
    n     = int(sr * duration)
    t     = np.linspace(0, duration, n)
    audio = np.zeros(n)

    # Happy key C major: C D E G A
    notes = [261.63, 293.66, 329.63, 392.00, 440.00, 523.25]
    tempo = 120; beat = 60/tempo

    def xyl(freq, start, dur, amp=0.25):
        nonlocal audio
        s = int(start*sr); e = min(int((start+dur)*sr), n)
        if s>=n: return
        seg_t = np.linspace(0, dur, e-s)
        env   = np.exp(-4.0 * seg_t/dur)
        wave_ = np.sin(2*np.pi*freq*seg_t) * 0.7 + np.sin(4*np.pi*freq*seg_t) * 0.3
        audio[s:e] += amp * env * wave_

    # Melody pattern
    melody = [0,2,4,2,0,4,5,4,2,0,1,2,4,5,4,2]
    for i, idx in enumerate(melody * 20):
        if i*beat > duration: break
        xyl(notes[idx % len(notes)], i*beat, beat*0.7)
        # Bass note every 2 beats
        if i%2==0:
            xyl(notes[0]*0.5, i*beat, beat*1.5, amp=0.15)

    audio = np.clip(audio * 32767, -32767, 32767).astype(np.int16)
    tmp   = str(out).replace(".aac",".wav")
    with wave.open(tmp, "w") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr)
        wf.writeframes(audio.tobytes())
    _run([FFMPEG,"-y","-i",tmp,"-c:a","aac","-b:a","128k",str(out)],"music_enc")
    try: os.remove(tmp)
    except: pass

def generate_narration_srt(scene, out_srt):
    narration = scene.get("narration","")
    words = narration.split()
    dur   = scene.get("duration_sec", 9)

    chunks, chunk, n = [], [], 0
    for w in words:
        chunk.append(w); n+=1
        if n >= 8 or w.endswith((".", "!", "?", "—")):
            chunks.append(" ".join(chunk)); chunk=[]; n=0
    if chunk: chunks.append(" ".join(chunk))

    dt = dur / max(len(chunks), 1)
    lines = []
    for i, c in enumerate(chunks):
        s = i*dt; e = min((i+1)*dt, dur-0.1)
        def ts(x):
            mm=int(x//60); ss=int(x%60); ms=int((x%1)*1000)
            return f"00:{mm:02d}:{ss:02d},{ms:03d}"
        lines.append(f"{i+1}\n{ts(s)} --> {ts(e)}\n{c}\n")

    with open(str(out_srt),"w") as f: f.write("\n".join(lines))

def render_scene(scene, work_dir, episode_id):
    n    = scene["scene_number"]
    print(f"  Scene {n:02d}: {scene['title']}")
    fin  = work_dir / f"scene_{n:02d}_final.mp4"
    if fin.exists():
        print(f"    ✓ already done")
        return fin

    bg_still = work_dir / f"scene_{n:02d}_bg.png"
    ch_still = work_dir / f"scene_{n:02d}_char.png"
    clip     = work_dir / f"scene_{n:02d}_clip.mp4"
    music    = work_dir / f"scene_{n:02d}_music.aac"
    srt      = work_dir / f"scene_{n:02d}.srt"
    subbed   = work_dir / f"scene_{n:02d}_subbed.mp4"

    dur = scene.get("duration_sec", 9)

    # Background
    if not bg_still.exists():
        make_sky_background(scene, bg_still)

    # Character composite (draw on top of bg)
    if not ch_still.exists():
        shutil.copy2(str(bg_still), str(ch_still))
        make_character_card(scene.get("type",""), ch_still, scene)

    # Motion clip
    if not clip.exists():
        still_to_video(ch_still, clip, dur, scene.get("camera","push_in"))

    # Music
    if not music.exists():
        generate_kids_music(dur, music)

    # SRT
    if not srt.exists():
        generate_narration_srt(scene, srt)

    # Subtitles
    if not subbed.exists() and clip.exists():
        vf_subs = f"subtitles={srt}:force_style='FontName=Arial,FontSize=22,PrimaryColour=&HFFFFFF,OutlineColour=&H002060,Bold=1,Outline=3,Alignment=2'"
        ok = _run([FFMPEG,"-y","-i",str(clip),"-vf",vf_subs,
                   "-c:v","libx264","-preset","fast","-crf","22",
                   "-c:a","copy",str(subbed)],"subs")
        if not ok:
            shutil.copy2(str(clip), str(subbed))
    elif clip.exists():
        shutil.copy2(str(clip), str(subbed))

    # Mux audio
    if subbed.exists() and music.exists():
        _run([FFMPEG,"-y","-i",str(subbed),"-i",str(music),
              "-c:v","copy","-c:a","aac","-shortest",
              "-map","0:v","-map","1:a",str(fin)],"mux")

    if fin.exists():
        print(f"    ✓ {_probe(fin):.1f}s")
    else:
        print(f"    ✗ FAILED")
    return fin

def make_title_card(title, tagline, ep_id, out):
    img  = Image.new("RGB", (W,H), (26,16,80))
    draw = ImageDraw.Draw(img, "RGBA")
    # Deep purple bg with stars
    for _ in range(60):
        import random; random.seed(_*17)
        sx=random.randint(0,W); sy=random.randint(0,H)
        draw_star(draw, sx, sy, random.randint(3,8), C_ZEUS_YELLOW, alpha=random.randint(40,140))
    # Channel name
    draw.text((W//2, H//2-120), "LITTLE OLYMPUS", fill=C_ZEUS_YELLOW,
              anchor="mm", font=ImageFont.load_default())
    draw.text((W//2, H//2-40), title, fill=(255,255,255),
              anchor="mm", font=ImageFont.load_default())
    draw.text((W//2, H//2+40), tagline, fill=(180,170,240),
              anchor="mm", font=ImageFont.load_default())
    img.save(str(out))

def make_end_card(ep_id, next_preview, out):
    img  = Image.new("RGB", (W,H), (26,16,80))
    draw = ImageDraw.Draw(img)
    draw.text((W//2, H//2-80), "LITTLE OLYMPUS", fill=C_ZEUS_YELLOW, anchor="mm")
    draw.text((W//2, H//2), "SUBSCRIBE for more adventures! ⚡", fill=(255,255,255), anchor="mm")
    if next_preview:
        draw.text((W//2, H//2+80), f"Next: {next_preview}", fill=(180,170,240), anchor="mm")
    img.save(str(out))

TITLE_DUR = 5
END_DUR   = 5

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--ep", default="lo_ep001")
    parser.add_argument("--scenes", type=str)
    parser.add_argument("--concat", action="store_true")
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()

    ep_id = args.ep.upper()
    ep_file = PROMPTS / f"scene_prompts.{args.ep}.final.json"
    ep = json.load(open(str(ep_file)))

    RENDERS.mkdir(parents=True, exist_ok=True)
    work = RENDERS / f"_work_{args.ep}"
    work.mkdir(parents=True, exist_ok=True)

    if args.status:
        for s in ep["scenes"]:
            n  = s["scene_number"]
            fp = work / f"scene_{n:02d}_final.mp4"
            print(f"  {n:02d} {s['title'][:40]:<40} {'✓' if fp.exists() else '·'}")
        print(f"  Final: {'✓' if (RENDERS/f'{args.ep}.mp4').exists() else '·'}")
        sys.exit(0)

    if args.concat:
        clips = []
        title_fin = work/"title_final.mp4"
        end_fin   = work/"end_final.mp4"
        # title
        if not title_fin.exists():
            ts = work/"title_still.png"; tv = work/"title_vid.mp4"; ta=work/"title_audio.aac"
            make_title_card(ep["title"], ep.get("tagline",""), ep_id, ts)
            still_to_video(ts, tv, TITLE_DUR, "push_in")
            generate_kids_music(TITLE_DUR, ta)
            _run([FFMPEG,"-y","-i",str(tv),"-i",str(ta),"-c:v","copy","-c:a","copy",
                  "-shortest","-map","0:v","-map","1:a",str(title_fin)],"title_mux")
        if title_fin.exists(): clips.append(title_fin)
        for s in ep["scenes"]:
            n=s["scene_number"]; fp=work/f"scene_{n:02d}_final.mp4"
            if fp.exists(): clips.append(fp)
        # end
        if not end_fin.exists():
            es=work/"end_still.png"; ev=work/"end_vid.mp4"; ea=work/"end_audio.aac"
            make_end_card(ep_id, ep.get("next_episode_preview",""), es)
            still_to_video(es, ev, END_DUR, "pull_back")
            generate_kids_music(END_DUR, ea)
            _run([FFMPEG,"-y","-i",str(ev),"-i",str(ea),"-c:v","copy","-c:a","copy",
                  "-shortest","-map","0:v","-map","1:a",str(end_fin)],"end_mux")
        if end_fin.exists(): clips.append(end_fin)

        concat_txt = work/"concat.txt"
        with open(str(concat_txt),"w") as f:
            for c in clips: f.write(f"file '{c}'\n")
        final_out = RENDERS / f"{args.ep}.mp4"
        _run([FFMPEG,"-y","-f","concat","-safe","0","-i",str(concat_txt),
              "-c","copy","-movflags","+faststart",str(final_out)],"concat")
        if final_out.exists():
            d = _probe(final_out)
            sz = final_out.stat().st_size/1024/1024
            print(f"\n✓ {final_out.name}  {d:.1f}s  {sz:.1f}MB")
            _backup(final_out)
        sys.exit(0)

    if args.scenes:
        parts = args.scenes.split("-")
        lo = int(parts[0]); hi = int(parts[1]) if len(parts)>1 else lo
        for s in ep["scenes"]:
            if lo <= s["scene_number"] <= hi:
                render_scene(s, work, ep_id)
