# =============================================
# EASY SOCIAL PLUGIN FOR CLAUDE
# Drop-in ready for Empire OS
# =============================================
from claude_assistant import assistant
from pathlib import Path

class EasySocial:
    """The easiest way for Claude to control all your social channels"""

    def post(self, task: str):
        """Claude gives a natural command"""
        print("Running task:", task)
        return assistant.run(task)

    def cross(self, message: str):
        """Cross-post to all platforms"""
        return assistant.run(f"Cross post {message} everywhere")

    def caption(self, topic: str):
        """Generate good caption"""
        return assistant.run(f"Generate caption for {topic}")

    def open_latest(self):
        """Open latest render/thumbnail"""
        return assistant.run("Open latest thumbnail")

    def status(self):
        """Quick status"""
        return "All channels ready. Use .post() to publish."

# Create one easy instance
social = EasySocial()

# =============================================
# HOW CLAUDE USES IT (Super Simple)
# =============================================
"""
from easy_social_plugin import social
social.post("Post EP001 Thermopylae to YouTube and Pinterest")
social.cross("New Gods & Glory episode is out!")
social.caption("Battle of Cannae")
social.open_latest()
"""

print("Easy Social Plugin Loaded - Ready for Claude!")
