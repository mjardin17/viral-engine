import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import google.generativeai as genai
from core.agents import get_agent_prompt, list_agents, AGENTS
from core.self_healing import SelfHealingSystem

# Load system prompt
SYSTEM_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "core", "system_prompt.txt")
with open(SYSTEM_PROMPT_PATH, "r") as f:
    SYSTEM_PROMPT = f.read()

app = FastAPI(title="Echoes Council – Autonomous Agent System v2.3")
healing = SelfHealingSystem()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=SYSTEM_PROMPT
)

class TaskRequest(BaseModel):
    agent: str
    task: str

class CouncilRequest(BaseModel):
    request: str  # Free-form request to the Council Leader

@app.get("/")
async def root():
    return {
        "status": "Echoes Council v2.3 ready",
        "channel": "Echoes of Eternity",
        "tagline": "The stories that shaped us – told like never before",
        "agents": len(AGENTS)
    }

@app.get("/agents")
async def get_agents():
    return {"agents": list_agents()}

@app.post("/spawn")
async def spawn_agent(req: TaskRequest):
    """Spawn a specific agent with a task."""
    try:
        prompt = get_agent_prompt(req.agent, req.task)
        response = model.generate_content(prompt)
        healing.learn(f"Agent '{req.agent}' completed task: {req.task[:50]}...")
        return {
            "agent": req.agent,
            "task": req.task,
            "output": response.text
        }
    except Exception as e:
        action = healing.report_error(e, req.task)
        raise HTTPException(status_code=500, detail={"error": str(e), "healing_action": action})

@app.post("/council")
async def council_request(req: CouncilRequest):
    """Send a free-form request to the Council Leader."""
    try:
        response = model.generate_content(req.request)
        return {
            "council_response": response.text,
            "lessons_so_far": len(healing.get_lessons())
        }
    except Exception as e:
        action = healing.report_error(e, req.request)
        raise HTTPException(status_code=500, detail={"error": str(e), "healing_action": action})

@app.post("/run_plan")
async def run_plan(plan_name: str, topic: str):
    """Run a full 30-day plan end-to-end for a given topic."""
    try:
        stages = ["Researcher", "Scriptwriter", "Thumbnail & Title Creator",
                  "Promo Writer", "Book Researcher", "Affiliate Manager",
                  "Quality Checker", "Producer"]
        outputs = {}
        for agent_name in stages:
            prompt = get_agent_prompt(agent_name, topic)
            resp = model.generate_content(prompt)
            outputs[agent_name] = resp.text
            healing.learn(f"Plan '{plan_name}' — {agent_name} done for: {topic[:40]}")

        # Self-learning pass
        learn_prompt = get_agent_prompt("Self-Learning Agent", str(outputs)[:2000])
        learn_resp = model.generate_content(learn_prompt)
        outputs["Self-Learning"] = learn_resp.text

        return {"plan": plan_name, "topic": topic, "outputs": outputs}
    except Exception as e:
        action = healing.report_error(e, topic)
        raise HTTPException(status_code=500, detail={"error": str(e), "healing_action": action})

@app.get("/lessons")
async def get_lessons():
    return {"lessons_learned": healing.get_lessons()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001, workers=1)
