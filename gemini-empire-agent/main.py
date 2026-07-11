import os
from fastapi import FastAPI
import uvicorn
from agent_graph import build_graph
from core.self_healing import SelfHealingSystem
import google.generativeai as genai

app = FastAPI(title="EmpireForge Agent v2.1 - Gemini")
healing = SelfHealingSystem()
graph = build_graph()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

@app.get("/")
async def root():
    return {"status": "EmpireForge Agent v2.1 ready with Gemini (bottlenecks fixed)"}

@app.post("/run")
async def run_task(task: str):
    try:
        result = graph.invoke({"messages": [task]})
        # Gemini fallback for complex tasks
        gemini_response = model.generate_content(task)
        return {"result": result.get("messages", ["Success"]), "gemini": gemini_response.text[:200]}
    except Exception as e:
        action = healing.report_error(e, task)
        return {"status": "healing", "action": action, "error": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, workers=4)
