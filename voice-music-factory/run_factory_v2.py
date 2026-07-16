#!/usr/bin/env python3
import gradio as gr
import asyncio
from voice_music_factory_v2 import generate_speech, generate_video
import tempfile

ALL_KOKORO_VOICES = ["af_bella", "am_adam", "af_sarah", "am_michael", "af_nicole", "am_david"]

def generate_voice_ui(text, voice, speed, emotion):
    if not text.strip():
        return "Please enter text.", None
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        audio_bytes = loop.run_until_complete(generate_speech(text, voice, speed, emotion))
        loop.close()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            f.write(audio_bytes)
            return f"✅ Generated ({len(audio_bytes)} bytes) | {emotion}", f.name
    except Exception as e:
        return f"Error: {str(e)}", None

def generate_pipeline_ui(script, voice, style, emotion):
    if not script.strip():
        return "Please enter a script."
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        audio_bytes = loop.run_until_complete(generate_speech(script, voice, 1.0, emotion))
        video_path = loop.run_until_complete(generate_video(script, style))
        loop.close()

        if isinstance(video_path, str) and video_path.startswith("Video error"):
            return f"❌ Video generation failed: {video_path}"
        return f"✅ Full Video Generated!\nVideo: {video_path}\nVoice: {len(audio_bytes)} bytes"
    except Exception as e:
        return f"❌ Generation failed: {str(e)}"

with gr.Blocks(title="Voice + Music Factory") as demo:
    gr.Markdown("# 🎙️ Voice + Music Factory")
    gr.Markdown("Real Kokoro + Video Generation")

    with gr.Tabs():
        with gr.TabItem("🎤 Voice"):
            text = gr.Textbox(label="Text", lines=6)
            voice = gr.Dropdown(ALL_KOKORO_VOICES, value="af_bella")
            emotion = gr.Dropdown(["Neutral", "Energetic", "Calm", "Intense"], value="Neutral")
            speed = gr.Slider(0.7, 1.5, value=1.0)
            btn = gr.Button("Generate Voice")
            status = gr.Textbox(label="Status")
            audio = gr.Audio(label="Audio", type="filepath")
            btn.click(generate_voice_ui, [text, voice, speed, emotion], [status, audio])

        with gr.TabItem("🚀 Full Pipeline"):
            script = gr.Textbox(label="Script", lines=4)
            p_voice = gr.Dropdown(ALL_KOKORO_VOICES, value="af_bella")
            p_style = gr.Dropdown(["Cinematic", "Cartoon"], value="Cinematic")
            p_emotion = gr.Dropdown(["Neutral", "Energetic", "Calm", "Intense"], value="Neutral")
            pipeline_btn = gr.Button("🚀 Generate Full Content")
            result = gr.Textbox(label="Result", lines=8)
            pipeline_btn.click(generate_pipeline_ui, [script, p_voice, p_style, p_emotion], result)

demo.launch(server_name="0.0.0.0", server_port=7860)
