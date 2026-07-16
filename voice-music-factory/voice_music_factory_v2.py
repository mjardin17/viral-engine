import asyncio
import hashlib
import threading
from pathlib import Path
import numpy as np
import tempfile
import os

CACHE_DIR = Path("./cache")
CACHE_DIR.mkdir(exist_ok=True)
OUTPUT_DIR = Path("./output")
OUTPUT_DIR.mkdir(exist_ok=True)

# Cache pipelines at module scope (loaded once)
image_pipe = None
video_pipe = None
_image_pipe_lock = threading.Lock()
_video_pipe_lock = threading.Lock()

async def get_image_pipe():
    global image_pipe
    if image_pipe is None:
        with _image_pipe_lock:
            if image_pipe is None:  # re-check after acquiring lock
                from diffusers import StableDiffusionPipeline
                image_pipe = StableDiffusionPipeline.from_pretrained("stabilityai/stable-diffusion-2-1")
                image_pipe.enable_model_cpu_offload()  # 8GB VRAM safe
    return image_pipe

async def get_video_pipe():
    global video_pipe
    if video_pipe is None:
        with _video_pipe_lock:
            if video_pipe is None:  # re-check after acquiring lock
                from diffusers import StableVideoDiffusionPipeline
                video_pipe = StableVideoDiffusionPipeline.from_pretrained("stabilityai/stable-video-diffusion-img2vid-xt")
                video_pipe.enable_model_cpu_offload()
    return video_pipe

async def generate_speech(text: str, voice: str = "af_bella", speed: float = 1.0, emotion: str = "Neutral") -> bytes:
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
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    try:
        sf.write(tmp.name, audio_array, 24000)
        audio_bytes = Path(tmp.name).read_bytes()
    finally:
        os.unlink(tmp.name)  # Safe cleanup (closed before unlink — Windows-safe)

    if len(audio_bytes) > 1000:
        cache_file.write_bytes(audio_bytes)

    return audio_bytes

async def generate_video(script: str, style: str = "cinematic"):
    try:
        image_pipe = await get_image_pipe()
        prompt = f"High quality {style} cinematic scene like Higsfield: {script[:150]}"
        image = image_pipe(prompt, num_inference_steps=30).images[0]

        video_pipe = await get_video_pipe()
        video = video_pipe(image, num_frames=24, fps=8, motion_bucket_id=180).frames[0]

        video_path = OUTPUT_DIR / f"video_{hashlib.md5(script.encode()).hexdigest()}.mp4"
        import imageio
        imageio.mimsave(video_path, video, fps=8)

        return str(video_path)
    except Exception as e:
        return f"Video error: {str(e)}"
