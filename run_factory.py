#!/usr/bin/env python3
import asyncio
import tempfile
import gradio as gr
from voice_music_factory import generate_speech

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
            return f"✅ Generated ({len(audio_bytes)} bytes)", f.name
    except Exception as e:
        return f"Error: {str(e)}", None

def generate_pipeline_ui(script, voice, style, emotion):
    if not script.strip():
        return "Please enter a script."
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        audio_bytes = loop.run_until_complete(generate_speech(script, voice, 1.0, emotion))
        loop.close()
        return f"✅ Voice Generated ({len(audio_bytes)} bytes)\nVoice: {voice} | Emotion: {emotion}"
    except Exception as e:
        return f"❌ Generation failed: {str(e)}"

with gr.Blocks(title="Voice + Music Factory") as demo:
    gr.Markdown("# 🎙️ Voice + Music Factory")
    gr.Markdown("Real Kokoro integration — Empire OS")
    with gr.Tabs():
        with gr.TabItem("🎤 Voice"):
            text = gr.Textbox(label="Text", lines=6)
            voice = gr.Dropdown(["af_bella", "am_adam"], value="af_bella")
            emotion = gr.Dropdown(["Neutral", "Energetic"], value="Neutral")
            speed = gr.Slider(0.7, 1.5, value=1.0)
            btn = gr.Button("Generate Voice")
            status = gr.Textbox(label="Status")
            audio = gr.Audio(label="Audio", type="filepath")
            btn.click(generate_voice_ui, [text, voice, speed, emotion], [status, audio])
        with gr.TabItem("🚀 Full Pipeline"):
            script = gr.Textbox(label="Script", lines=4)
            p_voice = gr.Dropdown(["af_bella", "am_adam"], value="af_bella")
            p_style = gr.Dropdown(["Cinematic"], value="Cinematic")
            p_emotion = gr.Dropdown(["Neutral", "Energetic"], value="Energetic")
            pipeline_btn = gr.Button("🚀 Generate")
            result = gr.Textbox(label="Result", lines=8)
            pipeline_btn.click(generate_pipeline_ui, [script, p_voice, p_style, p_emotion], result)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
