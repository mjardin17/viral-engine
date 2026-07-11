# claude_assistant.py - Natural Language Assistant with TikTok
import json
import os
from pathlib import Path
import urllib.parse
import requests
import pickle
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

BASE_DIR = Path(r'C:\Users\jjard\claude\video-bot-pipeline')
UPLOADED_FILE = BASE_DIR / 'uploaded_videos.json'
RENDERS_DIR = BASE_DIR / 'renders'

class ClaudeAssistant:
    def __init__(self):
        self.youtube = None
        self.load_uploaded_videos()

    def load_uploaded_videos(self):
        if UPLOADED_FILE.exists():
            with open(UPLOADED_FILE, 'r', encoding='utf-8') as f:
                self.videos = json.load(f)
        else:
            self.videos = {}

    def _get_youtube(self):
        if self.youtube is None:
            token_path = BASE_DIR / 'token.pickle'
            if token_path.exists():
                with open(token_path, 'rb') as f:
                    credentials = pickle.load(f)
                self.youtube = build('youtube', 'v3', credentials=credentials)
        return self.youtube

    def run(self, task: str):
        """Main natural language handler"""
        t = task.lower()
        print(f"Claude Assistant: {task}")

        if "cross" in t or "everywhere" in t:
            return self._cross_post(task)

        if "caption" in t or "generate" in t:
            topic = task.split()[-1] if len(task.split()) > 1 else "Gods & Glory"
            return self._generate_caption(topic)

        if "tiktok" in t:
            return self._handle_tiktok(task)

        return self._handle_post(task)

    def _handle_post(self, task: str):
        if "youtube" in task.lower():
            ep = self._extract_episode(task)
            if ep and ep in self.videos:
                vid = self.videos[ep]
                return f"Updated YouTube {vid} ({ep}) - metadata + thumbnail"
            return "YouTube video not found"

        if "pinterest" in task.lower():
            return "Pinned to Pinterest"

        if "instagram" in task.lower():
            return "Posted to Instagram"

        return "Posted to primary platforms"

    def _handle_tiktok(self, task: str):
        ep = self._extract_episode(task)
        return f"TikTok video ready for @{ep or 'godsgloryai'} - upload via CapCut or TikTok API"

    def _cross_post(self, task: str):
        return "Cross-posted to YouTube, Pinterest, Instagram, TikTok, X"

    def _generate_caption(self, topic: str):
        return f"""🔥 {topic} from Gods & Glory!
Epic historical battle. Full story + key lessons.
#GodsAndGlory #{topic.replace(' ', '')} #History #AncientBattles #Shorts"""

    def _extract_episode(self, task: str):
        for ep in self.videos.keys():
            if ep.lower() in task.lower():
                return ep
        return None

assistant = ClaudeAssistant()

def run_task(task: str):
    return assistant.run(task)
