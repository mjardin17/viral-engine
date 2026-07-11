import asyncio
import hashlib
from pathlib import Path

# Import at top level — fails loudly if kokoro missing
from kokoro import KPipeline
import numpy as np
import soundfile as sf
import tempfile

CACHE_DIR = Path("./cache")
CACHE_DIR.mkdir(exist_ok=True)

async def generate_speech(text: str, voice: str = "af_bella", speed: float = 1.0) -> bytes:
    cache_key = hashlib.md5(f"{text}_{voice}_{speed}".encode()).hexdigest()
    cache_file = CACHE_DIR / f"{cache_key}.wav"

    if cache_file.exists():
        return cache_file.read_bytes()

    pipeline = KPipeline(lang_code='a')
    generator = pipeline(text, voice=voice, speed=speed)
    audio_chunks = [audio for (_, _, audio) in generator]
    audio_array = np.concatenate(audio_chunks)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        sf.write(f.name, audio_array, 24000)
        with open(f.name, 'rb') as f2:
            audio_bytes = f2.read()

    if len(audio_bytes) > 1000:
        cache_file.write_bytes(audio_bytes)

    return audio_bytes
