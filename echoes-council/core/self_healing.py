class SelfHealingSystem:
    def __init__(self):
        self.error_log = []
        self.lessons_learned = []
        self.rate_limiter = 0

    def report_error(self, error, context):
        entry = {"error": str(error), "context": context}
        self.error_log.append(entry)
        print(f"🛠️ Self-Healing: {error}")
        self.rate_limiter += 1
        if self.rate_limiter > 5:
            return "pause_and_alert_user"
        return "retry"

    def learn(self, lesson: str):
        self.lessons_learned.append(lesson)
        print(f"📚 Learned: {lesson}")

    def get_lessons(self):
        return self.lessons_learned
