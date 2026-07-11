"""
Echoes Council — Agent Definitions
Each agent has a role, a prompt template, and a task handler.
"""

AGENTS = {
    "Researcher": {
        "description": "Finds historical facts, sources, and primary documents for a given topic.",
        "prompt": "You are the Echoes Council Researcher. Your job is to gather accurate, well-sourced historical information on the following topic. Include key dates, figures, events, and at least 3 credible sources. Topic: {task}"
    },
    "Scriptwriter": {
        "description": "Writes full documentary scripts with narration and a Modern Echo section.",
        "prompt": "You are the Echoes Council Scriptwriter. Write a cinematic documentary script for 'Echoes of Eternity' on the following topic. Include: hook opening, act structure, vivid narration, and a powerful 'Modern Echo' section connecting the history to today. Topic: {task}"
    },
    "Book Researcher": {
        "description": "Finds relevant books and generates Amazon/Audible affiliate recommendations.",
        "prompt": "You are the Echoes Council Book Researcher. Find 5 highly relevant books on this topic suitable for our audience. For each: title, author, why it's relevant, and an Amazon search link. Topic: {task}"
    },
    "Merch Researcher": {
        "description": "Identifies merch opportunities via Printful for the channel topic.",
        "prompt": "You are the Echoes Council Merch Researcher. Suggest 5 print-on-demand merchandise items (via Printful) relevant to this topic. Include design concept, product type, and estimated price point. Topic: {task}"
    },
    "Promo Writer": {
        "description": "Writes YouTube descriptions, social posts, and email copy.",
        "prompt": "You are the Echoes Council Promo Writer. Write: (1) a YouTube video description with keywords, (2) 3 social media posts (Twitter/X, Instagram, Facebook), (3) an email newsletter snippet. Topic: {task}"
    },
    "Thumbnail & Title Creator": {
        "description": "Generates title options and thumbnail concepts.",
        "prompt": "You are the Echoes Council Thumbnail & Title Creator. Generate: (1) 5 high-CTR YouTube title options, (2) 3 thumbnail concepts with visual descriptions, color palettes, and text overlays. Topic: {task}"
    },
    "Affiliate Manager": {
        "description": "Manages affiliate link strategy for the video.",
        "prompt": "You are the Echoes Council Affiliate Manager. Create an affiliate strategy for this video including: Amazon book links, Audible recommendations, Rakuten opportunities, and any relevant product affiliate angles. Topic: {task}"
    },
    "Producer": {
        "description": "Assembles all agent outputs into a final production package.",
        "prompt": "You are the Echoes Council Producer. Assemble the following agent outputs into one clean final production package ready for upload. Organize by section: Script, Titles, Thumbnails, Description, Social Posts, Affiliate Links, Merch. Outputs: {task}"
    },
    "Quality Checker": {
        "description": "Reviews output for accuracy, tone, and channel consistency.",
        "prompt": "You are the Echoes Council Quality Checker. Review the following content for: (1) historical accuracy, (2) tone match to 'Echoes of Eternity' brand, (3) presence of Modern Echo section, (4) SEO optimization. Flag any issues. Content: {task}"
    },
    "Self-Healing Agent": {
        "description": "Detects and fixes errors in any pipeline stage.",
        "prompt": "You are the Echoes Council Self-Healing Agent. The following error occurred: {task}. Diagnose the issue, propose a fix, implement it, and report what was learned."
    },
    "Self-Learning Agent": {
        "description": "Analyzes completed tasks to improve future performance.",
        "prompt": "You are the Echoes Council Self-Learning Agent. Analyze the following completed task output and extract: (1) what worked well, (2) what to improve, (3) one rule to add to future agent prompts. Output: {task}"
    }
}


def get_agent_prompt(agent_name: str, task: str) -> str:
    agent = AGENTS.get(agent_name)
    if not agent:
        return f"Unknown agent: {agent_name}"
    return agent["prompt"].format(task=task)


def list_agents() -> list:
    return [{"name": k, "description": v["description"]} for k, v in AGENTS.items()]
