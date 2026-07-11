"""Little Olympus Studio — Adapter Registry"""

from .base import BaseAdapter, AdapterStatus
from .ollama_adapter import OllamaAdapter
from .openai_adapter import OpenAIAdapter
from .higgsfield import HiggsFieldAdapter
from .storyforge import StoryForgeAdapter
from .crosspost import CrossPostAdapter
from .empire_os import EmpireOSAdapter
from .video_factory import VideoFactoryAdapter

__all__ = [
    "BaseAdapter",
    "AdapterStatus",
    "OllamaAdapter",
    "OpenAIAdapter",
    "HiggsFieldAdapter",
    "StoryForgeAdapter",
    "CrossPostAdapter",
    "EmpireOSAdapter",
    "VideoFactoryAdapter",
]
