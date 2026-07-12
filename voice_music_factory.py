import asyncio
import hashlib
from pathlib import Path
import numpy as np
import tempfile
import os

CACHE_DIR = Path("./cache")
CACHE_DIR.mkdir(exist_ok=True)
OUTPUT_DIR = Path("./output")
OUTPUT_DIR.mkdir(exist_ok=True)

async def generate_speech(text: str, voice: str = "af_bella", speed: float = 1.0, emotion: str = "Neutral") -> bytes:
    # Emotion effect via speed modulation (Kokoro has no native emotion API)
    if emotion == "Energetic":
        speed = min(1.3, speed * 1.2)
    elif emotion == "Calm":
        speed = max(0.8, speed * 0.8)
    cache_key = hashlib.md5(f"{text}_{voice}_{speed}_{emotion}".encode()).hexdigest()
    cache_file = CACHE_DIR / f"{cache_key}.wav"
    if cache_file.exists():
        return cache_file.read_bytes()
    from kokoro import KPipeline
    pipeline = KPipeline(lang_code='a')
    generator = pipeline(text, voice=voice, speed=speed)
    audio_chunks = [audio for (_, _, audio) in generator]
    audio_array = np.concatenate(audio_chunks)
    import soundfile as sf
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        sf.write(f.name, audio_array, 24000)
        with open(f.name, 'rb') as f2:
            audio_bytes = f2.read()
    if len(audio_bytes) > 1000:
        cache_file.write_bytes(audio_bytes)
    return audio_bytes

async def generate_video(script: str, style: str = "cinematic") -> str:
    """Stable Video Diffusion: text → image → animated video"""
    try:
        from diffusers import StableDiffusionPipeline, StableVideoDiffusionPipeline
        import imageio

        image_pipe = StableDiffusionPipeline.from_pretrained("stabilityai/stable-diffusion-2-1")
        image = image_pipe(f"A {style} scene: " + script[:100]).images[0]

        video_pipe = StableVideoDiffusionPipeline.from_pretrained(
            "stabilityai/stable-video-diffusion-img2vid-xt"
        )
        video_pipe.enable_model_cpu_offload()

        frames = video_pipe(image, num_frames=25, fps=7).frames[0]
        video_path = OUTPUT_DIR / f"video_{hashlib.md5(script.encode()).hexdigest()}.mp4"
        imageio.mimsave(str(video_path), frames, fps=7)
        return str(video_path)
    except Exception as e:
        return f"Video error: {str(e)}"
