#!/usr/bin/env python3
"""
generate_documentary.py — Local Ollama Documentary Script Generator
====================================================================
Generates full Gods & Glory episode JSON scripts using Ollama locally.
Claude provides the research + scene outlines. Ollama writes the narration
and visual prompts. Zero paid API usage for generation.

Usage:
    python generate_documentary.py --episode EP001
    python generate_documentary.py --episode EP002 --model llama3:8b
    python generate_documentary.py --all              # queue all S1 episodes
    python generate_documentary.py --episode EP001 --scenes-only  # skip SEO

Output: prompts/gods_glory/scene_prompts.gg_ep001.v2.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

BASE_DIR     = Path(__file__).resolve().parent
PROMPTS_DIR  = BASE_DIR / "prompts" / "gods_glory"
OLLAMA_URL   = os.environ.get("OLLAMA_URL",  "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:7b")
BATCH_SIZE   = 8   # scenes per Ollama call (safe for 8k context models)


# ── Ollama core ───────────────────────────────────────────────────────────────

def ollama_generate(prompt: str, system: str = "", timeout: int = 300) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.75, "num_ctx": 8192}
    }
    if system:
        payload["system"] = system
    data = json.dumps(payload).encode()
    req  = urllib.request.Request(
        f"{OLLAMA_URL}/api/generate",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode()).get("response", "").strip()
    except Exception as e:
        raise RuntimeError(f"Ollama call failed: {e}")


def is_available() -> bool:
    try:
        urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=4)
        return True
    except Exception:
        return False


# ── JSON extraction ───────────────────────────────────────────────────────────

def extract_json_array(text: str) -> Optional[list]:
    """Pull first JSON array out of messy Ollama output."""
    text = text.strip()
    # Try raw parse first
    try:
        obj = json.loads(text)
        if isinstance(obj, list):
            return obj
    except Exception:
        pass
    # Find array in fenced block
    m = re.search(r"```(?:json)?\s*(\[[\s\S]*?\])\s*```", text)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    # Find any array
    m = re.search(r"(\[[\s\S]*\])", text)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    return None


# ── System prompt (Documentary Bible condensed) ───────────────────────────────

SYSTEM_NARRATOR = """You are the lead writer for Gods & Glory, a premium historical documentary channel.
Your writing standard: BBC Documentary + National Geographic + Ken Burns + Ridley Scott.

NARRATION RULES:
- Each scene narration: 110-140 words. No filler. Every sentence advances the story.
- Open with a hook. End with forward momentum or emotional impact.
- Use active voice. Short punchy sentences mixed with longer cinematic ones.
- State facts precisely. Numbers, dates, names must be historically accurate.
- Never start two consecutive scenes with the same sentence structure.

VISUAL PROMPT RULES:
- Each visual_prompt: 180-220 characters max.
- Style: "cinematic historical documentary, [description], dramatic lighting, [color palette], ultra-detailed, 8K"
- Be specific: time of day, weather, exact scene content, armor/weapons details.
- Period-accurate. No anachronisms.

BG_COLORS RULES:
- Return 2 hex colors that match the scene mood.
- Battle scenes: deep reds, dark grays.
- Diplomatic/context scenes: blues, golds.
- Night/betrayal scenes: near-black with deep purple.
- Dawn/triumph: warm ambers and oranges.

OUTPUT FORMAT — return ONLY a valid JSON array, no explanation:
[
  {
    "scene_number": 1,
    "type": "cold_open",
    "title": "Scene Title Here",
    "narration": "Full narration text here, 110-140 words...",
    "visual_prompt": "Cinematic historical prompt here...",
    "bg_colors": ["#hex1", "#hex2"],
    "duration_sec": 55
  }
]

Scene types: cold_open, context, geography, archaeology, military, buildup, battle, betrayal, last_stand, aftermath, legacy"""


# ── S1 Episode definitions ────────────────────────────────────────────────────
# Claude provides: research + ordered scene outlines
# Ollama provides: narration + visual prompts per scene

EPISODES = {
    "EP001": {
        "channel": "gods_glory",
        "episode_number": 1,
        "episode_id": "GG_EP001",
        "series_name": "Gods & Glory",
        "topic": "The Battle of Thermopylae — 480 BC",
        "title": "300 vs. The World: The Last Stand That Saved Western Civilization",
        "tagline": "Three hundred men. Three days. The fate of the free world.",
        "duration_target_min": 50,
        "aesthetic": "cinematic_epic_historical",
        "research": """
VERIFIED FACTS for Thermopylae 480 BC:
- Persian army: Herodotus claimed 2.6M; modern scholars estimate 100,000-250,000 (Lazenby, Green, Delbrück)
- Greek force: ~7,000 total (300 Spartans, 700 Thespians, 400 Thebans, others)
- Pass width: ~15 meters at narrowest point in antiquity (now 5km inland due to silting)
- Battle duration: 3 days (late August/early September 480 BC)
- Betrayer: Ephialtes of Trachis showed Persians the Anopaia mountain path
- Leonidas selected men with living sons (per Herodotus)
- Carneia festival: one reason Sparta sent only 300 initially
- Thespiae was destroyed by Persians afterward; Thespians had no reason to surrender
- Archaeological evidence: Marinatos 1939 excavation of Kolonos Hill found ~100 Persian bronze arrowheads + iron spearheads
- Simonides epigram: "Go tell the Spartans, stranger passing by, that here obedient to their laws we lie"
- Artemisium naval battle ran simultaneously; ~271 Greek triremes vs 600+ Persian
- After Thermopylae: Athens evacuated and burned; Salamis victory Sept 480 BC; Plataea 479 BC ended Persian land invasion
- Leonidas was ~60 years old at Thermopylae
- Agoge: Spartan boys entered military training at age 7, became warriors at 20
- Persian Immortals: elite 10,000-strong royal guard, always maintained at exactly 10,000 men
- Xerxes was persuaded by cousin Mardonius to invade; motivated by revenge for Marathon 490 BC
""",
        "scenes": [
            # ACT 1: HOOK
            (1,  "cold_open",  "A Bridge Made of Ships",                        "Xerxes orders 700 warships lashed hull-to-hull across the Hellespont strait so his army can walk across the water. The scale of this engineering feat and what it signals."),
            (2,  "cold_open",  "The Number Nobody Believes",                    "Herodotus counts 2.6 million Persians. Modern scholars say 100,000-250,000. Either way, it is the largest army ever assembled to that point in history, marching toward a coastal pass 15 meters wide."),
            (3,  "cold_open",  "Three Hundred Men Choose Their Ground",         "Leonidas arrives at Thermopylae. He looks at the pass. He knows exactly what is about to happen — and chooses to stay anyway. The question this episode answers: why?"),
            # ACT 2: THE WORLD IN 480 BC
            (4,  "context",    "The Persian Empire at Its Height",              "Under Xerxes, the Achaemenid Persian Empire spans from Egypt to India — the largest empire the world has ever seen. 50 million people. 23 subject nations. An annual tribute that staggers the imagination."),
            (5,  "context",    "Marathon — The Wound That Would Not Heal",      "490 BC. Darius the Great sends a Persian army to punish Athens for supporting a rebellion. At Marathon, an outnumbered Athenian force destroys the Persian army and sprints 26 miles to prevent a second landing. The humiliation burns in Persia for a decade."),
            (6,  "context",    "Xerxes Inherits His Father's Rage",             "When Darius dies, his son Xerxes inherits the throne and the grudge. His cousin Mardonius fans the flames: Greece must be punished. For three years, Xerxes prepares the greatest military campaign in the ancient world."),
            (7,  "context",    "Seven Hundred City-States — All at War",        "Greece in 480 BC is not a country. It is 700 rival city-states constantly at war with each other. Sparta and Athens have been enemies for generations. The idea that they would fight together against Persia is almost unthinkable."),
            (8,  "context",    "The Hellenic League — 31 Against the World",    "Of 700 Greek city-states, only 31 join the Hellenic League to resist Persia. The rest submit, collaborate, or do nothing. This coalition of 31 is outnumbered, outfunded, and outmanned before a single spear is thrown."),
            (9,  "context",    "The Oracle at Delphi Speaks",                   "The Athenians consult the Oracle at Delphi. The Oracle tells them their city will be destroyed. When they press for a better answer, she says: wooden walls will save you. Themistocles interprets this as the Athenian navy. It will prove to be the most consequential interpretation in Greek history."),
            (10, "context",    "Athens Builds a Fleet",                         "Themistocles convinces Athens to spend a silver windfall on 200 new warships instead of distributing the money to citizens. It is the most important financial decision Athens will ever make. Without those ships, there is no Salamis. Without Salamis, Greece falls."),
            # ACT 3: GEOGRAPHY
            (11, "geography",  "The Road South — Why Thermopylae?",             "The Persian army needs a road south through Greece. The geography forces them through a sequence of chokepoints. The narrowest is Thermopylae — where the Kallidromon mountains press almost to the sea, leaving a coastal strip barely wide enough for a cart."),
            (12, "geography",  "The Hot Gates — Terrain Analysis",              "In 480 BC, the pass at Thermopylae is about 15 meters wide at its narrowest. Hot sulphur springs bubble up from the rock — that is where the name comes from: the Hot Gates. The smell of sulfur hangs over everything. The sea is on the right, the cliff face on the left."),
            (13, "geography",  "The Wall of Phocis — A Pre-Built Defense",      "The Phocians built a defensive wall across the narrowest part of the pass years earlier to defend against Thessalian raids. The Greeks repair and man it. This wall becomes the anchor of the entire defensive line."),
            (14, "geography",  "The Anopaia Path — The Hidden Trail",           "Behind the Greek position, a goat trail snakes up the Kallidromon mountain range. It takes most of a day to walk. It emerges behind the Greek position at a village called Alpenos. The Greeks know about it. They station 1,000 Phocian soldiers to guard it. That decision will determine everything."),
            (15, "geography",  "Artemisium — The Naval Dimension",              "While the army holds Thermopylae, the Greek fleet positions at the nearby cape of Artemisium, blocking the sea lane. The land and sea battles are coordinated strategy — Thermopylae and Artemisium must hold or fall together."),
            # ACT 4: ARCHAEOLOGY
            (16, "archaeology","Herodotus — Our Best and Most Unreliable Source","Everything we know about Thermopylae comes primarily from Herodotus, writing 40-50 years after the battle. He interviewed survivors, consulted Persian records, and traveled to the site. He is meticulous and dramatic and sometimes wildly wrong. Modern historians are still arguing about which is which."),
            (17, "archaeology","The Simonides Epigram — Words Cut in Stone",    "The Greek poet Simonides wrote the most famous military inscription in history: 'Go tell the Spartans, stranger passing by, that here obedient to their laws we lie.' A version of this inscription was carved in stone and placed on Kolonos Hill. It still stands today."),
            (18, "archaeology","Kolonos Hill — What the Diggers Found",         "In 1939, Greek archaeologist Spyridon Marinatos excavated Kolonos Hill at Thermopylae. He found approximately 100 bronze Persian-style arrowheads and iron spearheads in the battle layer. This physical evidence confirmed that Herodotus's description of the final arrow assault was accurate."),
            (19, "archaeology","The Weapons Speak",                             "The arrowheads found at Kolonos Hill match the type found at Marathon and on the Acropolis — Persian military equipment. The spearheads are Greek. The artifact pattern exactly matches the literary account: a final surrounded Greek force destroyed by Persian archery from all sides."),
            (20, "archaeology","The Numbers Debate — Modern Scholarship",       "Historian Hans Delbrück was the first modern scholar to argue Herodotus's numbers were impossible — the logistics of feeding 2.6 million men across the Hellespont would be insurmountable. Modern estimates range from 100,000 to 250,000 total Persian force. Even the lower figure dwarfs the 7,000 Greeks."),
            # ACT 5: THE FORCES
            (21, "military",   "The Persian Army — A World Assembled",          "Xerxes's army is drawn from 46 subject nations: Egyptians with wicker shields, Ethiopians in lion skins, Lydians with short swords, Babylonian infantry, Indian archers. Each contingent maintains its own equipment and fighting style. It is a display of imperial power as much as a military force."),
            (22, "military",   "The Immortals — Persia's Elite Ten Thousand",   "The royal guard of the Persian empire: 10,000 soldiers permanently maintained at exactly that number. When one dies, he is immediately replaced, making them seemingly immortal. They carry gold-tipped spears and wicker shields. They are Persia's finest — and at Thermopylae they will fail."),
            (23, "military",   "Xerxes — The King of Kings",                    "Xerxes is not the monster of Hollywood. He is an educated, politically sophisticated ruler managing a complex empire. But he is also a man who flogged the Hellespont when a storm destroyed his first pontoon bridges, and who ordered the body of a Greek general's son cut in half so his army could march between the halves as a warning. He is capable of both grandeur and savagery."),
            (24, "military",   "The Greek Seven Thousand — Who Actually Came",  "The 7,000 Greeks at Thermopylae are not all Spartan. 700 men are from Thespiae, a small city that will pay a catastrophic price for its loyalty. 400 Thebans are there reluctantly — Thebes is Persian-sympathizing and only sent troops under political pressure. The Spartans are 300."),
            (25, "military",   "Leonidas — Born to This Moment",                "Leonidas is approximately 60 years old at Thermopylae. He completed the full Spartan agoge. He inherited the throne unexpectedly after both his older brothers died. When the Oracle said Sparta must either lose a king or lose the city, Leonidas — having heard the prophecy — volunteered to lead the force himself."),
            (26, "military",   "The Three Hundred — Men with Living Sons",      "Leonidas does not pick his 300 randomly. He selects only men who already have living male heirs. He is not planning for victory. He is planning for death, and he wants the men who die beside him to have sons who will carry their name forward. This selection is the most cold-blooded act of leadership in the ancient world."),
            (27, "military",   "The Spartan Agoge — Twenty Years of War",       "Every Spartan male at Thermopylae has spent his entire life preparing for this moment. Taken from his family at age seven. Trained in combat, endurance, and collective discipline for 13 years. Living in military barracks until age 30. The agoge does not just produce skilled fighters — it produces men for whom death in battle is culturally preferable to survival through retreat."),
            (28, "military",   "The Thespians — Seven Hundred Who Knew",        "The 700 Thespians at Thermopylae are volunteers who understand their situation more clearly than almost anyone else. Thespiae is the nearest major Greek city to the pass. If Thermopylae falls, the Persians will march straight through their city. When Leonidas orders the allies to leave on the third day, the Thespians refuse. They stay and fight knowing they will all die."),
            # ACT 6: BUILDUP
            (29, "buildup",    "Persia's Logistical Miracle",                   "Moving 150,000-250,000 men from Persia to Greece requires staggering logistics. Herodotus claims the army drank entire rivers dry. Modern analysis suggests pre-positioned supply dumps across 1,000 miles of march route, a fleet carrying supplies by sea alongside the army, and a sophisticated quartermaster system that is among the most advanced in the ancient world."),
            (30, "buildup",    "The Canal at Mount Athos",                      "In 483 BC, Xerxes orders his engineers to cut a canal 2 kilometers through the Mount Athos peninsula. This avoids the dangerous sea route that destroyed Mardonius's fleet in 492 BC. The canal takes three years to build. Herodotus considers it a monument to Persian arrogance. Modern archaeologists have confirmed it exists."),
            (31, "buildup",    "The Bridge of Boats — Crossing the Hellespont", "Xerxes's engineers construct two pontoon bridges across the Hellespont, using 674 warships lashed side by side and covered with wooden planks. When a storm destroys the first attempt, Xerxes orders the sea whipped 300 times and thrown chains. A man who can consider punishing the ocean is a man his army fears absolutely."),
            (32, "buildup",    "Leonidas Marches North",                        "Leonidas does not wait for the Persians to come south. He marches north from Sparta with his 300 and 900 helot support troops, gathering allies as he goes. By the time he reaches Thermopylae, the allied force numbers 7,000. He inspects the pass, rebuilds the Phocian wall, and stations the Phocians on the mountain path. He is ready."),
            (33, "buildup",    "The Persian Scouts Report Something Strange",   "Persian cavalry scouts reach Thermopylae before the main army. They report back to Xerxes: the Spartans are outside the wall. Some are exercising naked. Others are combing their long hair. Xerxes is baffled. He calls a Spartan exile named Demaratus to explain. Demaratus tells him: they are preparing to fight or die. Spartans always comb their hair before battle."),
            # ACT 7: DAY ONE
            (34, "battle",     "Xerxes Waits — Four Days of Disbelief",         "The Persian army arrives at Thermopylae and Xerxes waits four days before attacking. He sends messengers demanding the Greeks lay down their weapons. Leonidas's reply, per tradition: come and take them. Xerxes cannot comprehend that 7,000 men genuinely intend to hold a pass against his entire army. He is about to learn."),
            (35, "battle",     "The Medes Strike First",                        "On the fifth day, Xerxes sends the Medes — some of his best troops — against the Greek line. The pass is so narrow that the Medes can only advance in a column a few men wide. The Greek phalanx meets them shield-to-shield. Experienced, disciplined, fighting on chosen ground against men funneled into a killing channel. The Medes are slaughtered. Xerxes watches from his throne on the hill and rises three times in horror."),
            (36, "battle",     "The Phalanx at Thermopylae",                    "The Greek phalanx is a formation of overlapping shields seven or eight men deep. At Thermopylae, the pass is so narrow that the Persians cannot use their numbers to flank the Greeks or bring more than a few dozen men into contact at once. The Greeks also use a tactical innovation: they feign a retreat, drawing the Persians into a sprint, then wheel and destroy them. They repeat this cycle for hours."),
            (37, "battle",     "The Feigned Retreat — Drawing Them In",         "Multiple times on day one the Greek line appears to break and flee. The Persians surge forward, breaking their own formation in pursuit. The Greeks wheel as a unit and cut the disordered Persians apart. It is a technically demanding maneuver that requires the discipline only the agoge produces. The Persians are dying by the hundreds learning this lesson."),
            (38, "battle",     "The Immortals Are Stopped",                     "Xerxes's last gamble on day one: the Immortals. His most elite soldiers. Their assault fails like all the others. In the narrow pass, their superior numbers are irrelevant. Their equipment — lighter wicker shields — is worse than the Greek bronze aspis. Night falls on the first day. The Greeks have barely lost a man. Xerxes is learning what Thermopylae means."),
            # ACT 8: DAY TWO
            (39, "battle",     "Day Two — The Same Ground, The Same Wall",      "At dawn of the second day, Xerxes tries the same approach with fresh troops. The result is identical. Wave after wave of Persian infantry advances into the pass, is met by the Greek phalanx, and is destroyed or driven back. The Greeks rotate their contingents — Spartans fight, then Thespians rest them, then Thebans. The killing ground in front of the wall is piled with Persian dead."),
            (40, "battle",     "The Mathematics of the Chokepoint",             "Military historians have calculated what happens in a chokepoint 15 meters wide with an 8-deep phalanx. The front of the Greek line consists of perhaps 15-20 men. No matter how many thousands of Persians press from behind, only those 15-20 can engage the Greeks at any moment. The pass has turned Persia's greatest advantage — numbers — into a liability."),
            (41, "battle",     "Artemisium — The Naval Battle Rages",           "Simultaneously at the cape of Artemisium, 271 Greek triremes are fighting 600 Persian warships. The Greeks adopt a circular defensive formation at night and break it aggressively at dawn. Storms have already damaged the Persian fleet. On day two of the naval battle, the Greeks destroy 30 Persian ships using the diekplous ramming tactic. Themistocles is proving his worth at sea."),
            (42, "battle",     "Xerxes' Rage Builds",                           "The Persian king has watched two days of assault and accomplished nothing. His divine authority, his empire's prestige, the entire purpose of this campaign is to crush Greece quickly and return home in triumph. Instead he is being held by 7,000 men in a mountain pass. The pressure on Xerxes to find a solution is existential. Then, at dusk of the second day, a man approaches his camp."),
            # ACT 9: THE BETRAYAL
            (43, "betrayal",   "Ephialtes Comes Forward",                       "His name is Ephialtes of Trachis. He is a local man who knows the mountain. He comes to Xerxes' camp and offers to show the Persians a path over the mountain that emerges behind the Greek position. Herodotus does not tell us why Ephialtes betrays Greece. Perhaps money. Perhaps old grudges. Perhaps simple opportunism. Whatever his reason, he has just decided the battle."),
            (44, "betrayal",   "Hydarnes Moves at Midnight",                    "Xerxes dispatches Hydarnes, commander of the Immortals, with a force estimated at 10,000-20,000 men. They move out at dusk, guided by Ephialtes up the Anopaia path. The trail is narrow, difficult, heavily forested. They march through the night in silence. Ephialtes knows every turn. By dawn they have nearly completed the crossing."),
            (45, "betrayal",   "The Phocians Fail",                             "The 1,000 Phocian soldiers guarding the mountain path hear the Persians approaching before they see them — the sound of feet on oak leaves. They scramble to arm themselves on high ground. The Persians pause, fire a volley of arrows into the Phocians, and simply bypass them to continue their march. The Phocians retreat to a hilltop and play no further role in the battle."),
            (46, "betrayal",   "The Runner Arrives at Dawn",                    "At first light on the third day, a runner reaches the Greek camp behind the wall. The Persians are on the mountain. They will be behind the Greek position within hours. The news spreads through the allied camp with the speed of terror. Leonidas calls a council of war. Every commander in the Hellenic force knows what this means."),
            (47, "betrayal",   "Leonidas Sends Them Away",                      "Leonidas orders most of the allied contingents to retreat south immediately. Historians still debate why: perhaps he wants to preserve the army for the battles to come; perhaps the Oracle's prophecy has made this moment a planned sacrifice; perhaps the Spartans simply will not leave and the others cannot stay without them. The Thespians refuse to go. The 400 Thebans are kept, possibly by force. 300 Spartans remain."),
            # ACT 10: THE LAST STAND
            (48, "last_stand", "The Final Morning — What Remains",              "As dawn breaks on the third day, the position at Thermopylae holds approximately 300 Spartans, 700 Thespians who chose to stay, and 400 Theban hoplites who may not have had a choice. Roughly 1,400 men know they are surrounded, that the Persian army advancing from both ends of the pass numbers in the hundreds of thousands, and that they will not survive the day."),
            (49, "last_stand", "Leonidas Advances",                             "Leonidas does not wait behind the wall. He leads his force out in front of it, advancing into the open ground beyond the pass where there is more space. He intends to kill as many Persians as possible before the end. The Greek force charges into the Persian front with a ferocity that, according to Herodotus, shocks the Persian soldiers, many of whom are driven into the sea."),
            (50, "last_stand", "Leonidas Falls",                                "In the fighting, Leonidas is killed. The Spartans fight to recover his body with extraordinary violence — four times Persian forces try to take the corpse and four times the Spartans drive them back. For the Spartans, the body of their king is not coming home without them, and they are not going home. Both facts are already known."),
            (51, "last_stand", "The Thespians — Choosing Their Ground",         "The 700 Thespians fighting alongside the Spartans are not just brave — they are making a strategic calculation. Thespiae is the nearest Greek city to the pass. The Persians will march through it regardless. The Thespians have sent essentially their entire available fighting force to Thermopylae. Every man here knows his home is going to burn whether he lives or dies. They have chosen to die fighting."),
            (52, "last_stand", "Retreat to Kolonos Hill",                       "The surviving Greeks are forced back to Kolonos Hill, a small rise at the eastern end of the pass. Here, surrounded on all sides, they make their final stand. The Thebans reportedly surrender at this point, claiming they had fought unwillingly. The Spartans and Thespians continue."),
            (53, "last_stand", "The Sky Darkens With Arrows",                   "Herodotus records a Spartan warrior named Dieneces who, when told the Persian arrows would be so numerous they would block out the sun, replied: 'Then we shall fight in the shade.' Xerxes ends the close combat. He orders his archers forward from all sides. The arrows fall like rain on the surrounded Greeks on Kolonos Hill. When they stop, nothing at Thermopylae is alive."),
            (54, "last_stand", "Three Days — The Final Count",                  "The pass has held for three full days. The Greeks have killed an estimated 10,000-20,000 Persians, including two of Xerxes' own brothers. Thermopylae has cost Persia weeks of time, enormous casualties, and — most importantly — it has shown every Greek city that Persian soldiers can be beaten by Greek soldiers, even when outnumbered a hundred to one."),
            # ACT 11: AFTERMATH
            (55, "aftermath",  "Xerxes on the Battlefield",                     "Xerxes tours Thermopylae after the battle. He finds the body of Leonidas and, in an act almost without parallel in Persian military culture, orders it decapitated and the head placed on a stake. Herodotus says this betrays how much the Spartan king has angered him. A Persian king who violates the norms of warfare is a Persian king who has been genuinely frightened."),
            (56, "aftermath",  "Athens Evacuates and Burns",                    "The Athenians, reading the situation correctly, evacuate their entire civilian population to the island of Salamis. When the Persian army marches into Athens, they find an empty city except for a small force on the Acropolis. The Persians burn the Acropolis and everything else. Athens is destroyed. But the people of Athens are alive, and their fleet is intact."),
            (57, "aftermath",  "Salamis — The Trap Closes",                     "September 480 BC. Themistocles lures the Persian fleet into the narrow strait between Salamis island and the mainland — another chokepoint, the same principle as Thermopylae. 380 Greek triremes destroy over 200 Persian ships. Xerxes watches from a throne on the shore as his fleet dissolves. He retreats to Asia with the core of his army, leaving Mardonius in Greece with perhaps 100,000 men."),
            (58, "aftermath",  "Plataea — 479 BC — The Land War Ends",         "The following year, a Greek army of 40,000 men under the Spartan regent Pausanias meets Mardonius's force at Plataea. The battle is tactically complex — weeks of positioning before a decisive engagement. The Greeks win. Mardonius is killed. The Persian army in Greece is destroyed. The invasion is over. Greece is free."),
            # ACT 12: LEGACY
            (59, "legacy",     "What Three Days Actually Bought",               "Thermopylae held the Persian advance long enough for the Greek fleet at Artemisium to withdraw intact. That fleet survived to fight at Salamis. Salamis destroyed Persian naval power, stranding the Persian army in Greece without reliable supply lines. Without Thermopylae, the fleet retreats earlier, the strategic situation collapses, and Salamis may never happen. Three days at a pass is the hinge point."),
            (60, "legacy",     "The Pass That Would Not Stay Silent",           "The monument at Thermopylae still stands. Travelers still stop to read the epigram Simonides wrote. The word 'Thermopylae' has entered every Western language as shorthand for a small force standing against impossible odds for a cause larger than themselves. Leonidas did not win the battle. He won something longer-lasting: the permanent idea that some things are worth dying for, and that how you face death defines what you were."),
        ]
    },
}

# Register additional S1 episodes (outlines to be completed)
EPISODES["EP002"] = {
    "channel": "gods_glory", "episode_number": 2, "episode_id": "GG_EP002",
    "series_name": "Gods & Glory", "topic": "The Battle of Gaugamela — 331 BC",
    "title": "The Last King: How Alexander the Great Ended an Empire",
    "tagline": "One battle. One man. The end of 200 years of Persian power.",
    "duration_target_min": 50, "aesthetic": "cinematic_epic_historical",
    "research": "Alexander vs Darius III. Oct 1, 331 BC. Modern Iraq near Erbil. Persian force: 200,000-250,000. Macedonian: 47,000. Darius prepared flat ground to neutralize Macedonian cavalry advantage. Alexander's oblique attack. The gap in the Persian line. Alexander charges directly at Darius. Darius flees. Persian Empire collapses.",
    "scenes": []  # Will use Ollama to generate full outline via dedicated call
}

EPISODES["EP003"] = {
    "channel": "gods_glory", "episode_number": 3, "episode_id": "GG_EP003",
    "series_name": "Gods & Glory", "topic": "The Battle of Cannae — 216 BC",
    "title": "The Perfect Battle: How Hannibal Destroyed Rome's Greatest Army",
    "tagline": "70,000 Romans walked into a trap. None walked out.",
    "duration_target_min": 50, "aesthetic": "cinematic_epic_historical",
    "research": "Aug 2, 216 BC. Apulia, southern Italy. Hannibal Barca vs Roman consuls Paullus and Varro. Roman force: 86,000. Carthaginian: 50,000. Double envelopment — military history's most studied encirclement. Center bows, wings close. 70,000 Romans killed in one afternoon. Still studied at every military academy worldwide.",
    "scenes": []
}

EPISODES["EP004"] = {
    "channel": "gods_glory", "episode_number": 4, "episode_id": "GG_EP004",
    "series_name": "Gods & Glory", "topic": "The Mongol War Machine — 1206-1279 AD",
    "title": "The Mongol War Machine: How 100,000 Men Conquered the World",
    "tagline": "In 70 years they conquered more territory than Rome did in 500.",
    "duration_target_min": 50, "aesthetic": "cinematic_epic_historical",
    "research": "Genghis Khan unifies Mongol tribes 1206. Psychological warfare: surrender or annihilation. Communication via yam relay system. Horse archer tactics. Feigned retreats. Siege engineering adopted from conquered peoples. 40 million deaths from Mongol conquests. Largest contiguous land empire in history.",
    "scenes": []
}

EPISODES["EP005"] = {
    "channel": "gods_glory", "episode_number": 5, "episode_id": "GG_EP005",
    "series_name": "Gods & Glory", "topic": "The Fall of Constantinople — 1453 AD",
    "title": "Constantinople 1453: The End of an Age",
    "tagline": "The city that held for 1,000 years fell in 53 days.",
    "duration_target_min": 50, "aesthetic": "cinematic_epic_historical",
    "research": "Ottoman Sultan Mehmed II. 80,000 Ottoman troops vs ~7,000 Byzantine defenders. The Theodosian Walls — greatest fortification in history. Mehmed's giant cannons, designed by Hungarian engineer Urban. The chain blocking the Golden Horn — Ottomans drag ships overland. May 29, 1453: final assault. Constantine XI dies fighting. End of the Eastern Roman Empire, 1,000 years after Western Rome fell.",
    "scenes": []
}


# ── Scene generation via Ollama ───────────────────────────────────────────────

def build_batch_prompt(ep: dict, batch: list, batch_index: int, total_batches: int) -> str:
    """Build Ollama prompt for a batch of scenes."""
    ep_title = ep["title"]
    ep_topic = ep["topic"]
    research = ep.get("research", "")

    scene_specs = ""
    for num, stype, title, brief in batch:
        scene_specs += f'\n  Scene {num} | type: "{stype}" | title: "{title}"\n  Brief: {brief}\n'

    return f"""Documentary: "{ep_title}"
Topic: {ep_topic}

RESEARCH NOTES (use these facts — do not invent others):
{research.strip()}

Write narration and visual prompts for these {len(batch)} scenes (batch {batch_index+1} of {total_batches}).
Each narration must be 110-140 words. Historically accurate. No filler.
The scene titles and types are fixed — do not change them.
Scene briefs describe what to cover — expand them into cinematic narration.

SCENES TO WRITE:
{scene_specs}

Return ONLY a valid JSON array with exactly {len(batch)} scene objects.
Each object MUST have: scene_number, type, title, narration, visual_prompt, bg_colors (2-hex array), duration_sec."""


def generate_scenes_batch(ep: dict, batch: list, batch_idx: int, total_batches: int,
                           retries: int = 3) -> list:
    """Generate one batch of scenes via Ollama. Returns list of scene dicts."""
    prompt = build_batch_prompt(ep, batch, batch_idx, total_batches)

    for attempt in range(retries):
        try:
            print(f"  [Ollama] Batch {batch_idx+1}/{total_batches} attempt {attempt+1}...", end=" ", flush=True)
            t0 = time.time()
            raw = ollama_generate(prompt, system=SYSTEM_NARRATOR, timeout=300)
            elapsed = time.time() - t0
            scenes = extract_json_array(raw)
            if scenes and len(scenes) >= len(batch) // 2:
                # Validate and fix scene numbers
                for i, s in enumerate(scenes):
                    expected_num = batch[i][0] if i < len(batch) else batch[-1][0]
                    if "scene_number" not in s:
                        s["scene_number"] = expected_num
                    if "type" not in s:
                        s["type"] = batch[i][1] if i < len(batch) else "context"
                    if "title" not in s:
                        s["title"] = batch[i][2] if i < len(batch) else f"Scene {expected_num}"
                    if "bg_colors" not in s or not isinstance(s["bg_colors"], list):
                        s["bg_colors"] = ["#1a1a2e", "#16213e"]
                    if "duration_sec" not in s:
                        s["duration_sec"] = 55
                print(f"✓ ({elapsed:.0f}s, {len(scenes)} scenes)")
                return scenes
            else:
                print(f"✗ bad JSON ({len(raw)} chars)")
        except Exception as e:
            print(f"✗ error: {e}")
        if attempt < retries - 1:
            time.sleep(5)

    # Fallback: return placeholder scenes for this batch
    print(f"  [WARN] Batch {batch_idx+1} failed all retries — using placeholders")
    return [
        {
            "scene_number": num,
            "type": stype,
            "title": title,
            "narration": f"[NEEDS GENERATION] {brief}",
            "visual_prompt": f"Cinematic historical documentary scene: {title}, dramatic lighting, ultra-detailed, 8K",
            "bg_colors": ["#1a1a2e", "#16213e"],
            "duration_sec": 55
        }
        for num, stype, title, brief in batch
    ]


def generate_seo_package(ep: dict) -> dict:
    """Generate full SEO package via Ollama."""
    prompt = f"""Documentary episode:
Title: {ep['title']}
Topic: {ep['topic']}
Tagline: {ep['tagline']}
Duration: ~50 minutes
Channel: Gods & Glory (premium historical documentary)

Generate a complete YouTube SEO package. Return ONLY valid JSON:
{{
  "title_options": ["main title", "alt1", "alt2", "alt3", "alt4"],
  "description": "Full 2000-char YouTube description with timestamps placeholder, hooks, keywords, CTA...",
  "tags": ["tag1","tag2",...50 tags...],
  "chapters": [
    {{"time": "0:00", "title": "Introduction"}},
    ...12-15 chapters...
  ],
  "thumbnail_concepts": [
    {{"concept": "description", "text_overlay": "text on thumb", "mood": "dramatic"}},
    {{"concept": "description", "text_overlay": "text on thumb", "mood": "intense"}},
    {{"concept": "description", "text_overlay": "text on thumb", "mood": "cinematic"}}
  ],
  "shorts_ideas": [
    {{"title": "short title", "hook": "first line", "scene_ref": "scene 50"}},
    ...5 ideas...
  ],
  "social_captions": {{
    "twitter": "tweet text under 280 chars",
    "instagram": "IG caption with hashtags",
    "tiktok": "TikTok hook caption"
  }}
}}"""

    print("  [Ollama] Generating SEO package...", end=" ", flush=True)
    try:
        t0 = time.time()
        raw = ollama_generate(prompt, system="You are a YouTube SEO expert for historical documentary channels. Return only valid JSON.", timeout=240)
        # extract JSON object
        m = re.search(r"\{[\s\S]*\}", raw)
        if m:
            seo = json.loads(m.group(0))
            print(f"✓ ({time.time()-t0:.0f}s)")
            return seo
    except Exception as e:
        print(f"✗ ({e})")
    return {
        "title_options": [ep["title"]],
        "description": f"{ep['topic']}\n\n{ep['tagline']}",
        "tags": ["history", "documentary", "ancient history", "battle", "war"],
        "chapters": [],
        "thumbnail_concepts": [],
        "shorts_ideas": [],
        "social_captions": {}
    }


# ── Main episode generator ────────────────────────────────────────────────────

def generate_episode(ep_key: str, scenes_only: bool = False) -> Path:
    """Generate a full episode JSON and save it. Returns output path."""
    if ep_key not in EPISODES:
        raise ValueError(f"Unknown episode key: {ep_key}. Options: {list(EPISODES.keys())}")

    ep = EPISODES[ep_key]
    ep_id = ep["episode_id"].lower()
    out_path = PROMPTS_DIR / f"scene_prompts.{ep_id}.v2.json"

    print(f"\n{'='*60}")
    print(f"GENERATING: {ep['title']}")
    print(f"  Model:    {OLLAMA_MODEL} @ {OLLAMA_URL}")
    print(f"  Scenes:   {len(ep['scenes'])}")
    print(f"  Output:   {out_path}")
    print(f"{'='*60}\n")

    if not is_available():
        print("ERROR: Ollama not reachable. Start Ollama and retry.")
        print(f"  Expected: {OLLAMA_URL}")
        sys.exit(1)

    scene_outline = ep["scenes"]
    all_scenes = []

    if scene_outline:
        # Use pre-built Claude outline — Ollama fills in narration/visuals
        batches = [scene_outline[i:i+BATCH_SIZE] for i in range(0, len(scene_outline), BATCH_SIZE)]
        total_batches = len(batches)

        for idx, batch in enumerate(batches):
            scenes = generate_scenes_batch(ep, batch, idx, total_batches)
            all_scenes.extend(scenes)
            # Brief pause between batches
            if idx < total_batches - 1:
                time.sleep(2)
    else:
        # No outline provided — ask Ollama to generate full outline + content
        print("  [INFO] No pre-built outline. Generating structure via Ollama...")
        all_scenes = generate_episode_from_scratch(ep)

    # Generate SEO package
    seo = {}
    if not scenes_only:
        seo = generate_seo_package(ep)

    # Assemble final episode JSON
    episode_json = {
        "channel":             ep["channel"],
        "episode_number":      ep["episode_number"],
        "episode_id":          ep["episode_id"],
        "series_name":         ep["series_name"],
        "topic":               ep["topic"],
        "title":               ep["title"],
        "tagline":             ep["tagline"],
        "duration_target_min": ep["duration_target_min"],
        "aesthetic":           ep["aesthetic"],
        "_version":            "2.0",
        "_generated_by":       "generate_documentary.py (Ollama local)",
        "_model":              OLLAMA_MODEL,
        "_generated_at":       time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "_scene_count":        len(all_scenes),
        "_est_runtime_min":    round(sum(s.get("duration_sec", 55) for s in all_scenes) / 60, 1),
        "seo":                 seo,
        "scenes":              all_scenes,
    }

    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(episode_json, indent=2, ensure_ascii=False), encoding="utf-8")

    est_min = episode_json["_est_runtime_min"]
    print(f"\n{'='*60}")
    print(f"SAVED: {out_path}")
    print(f"Scenes: {len(all_scenes)} | Est. runtime: {est_min} min")
    if est_min < 45:
        print(f"[WARN] Runtime {est_min} min is below 45-min minimum. Run ollama_bridge.py to expand narration.")
    print(f"{'='*60}\n")

    return out_path


def generate_episode_from_scratch(ep: dict) -> list:
    """For episodes without a pre-built outline, ask Ollama to generate 60 scenes."""
    print("  Generating 60-scene outline from topic...")
    outline_prompt = f"""Documentary: "{ep['title']}"
Topic: {ep['topic']}
Research: {ep.get('research', '')}

Create a 60-scene documentary outline for a premium historical documentary.
Required sections: hook (3 scenes), world context (8 scenes), geography (5 scenes),
archaeology (5 scenes), military forces (8 scenes), buildup (5 scenes),
battle phases (12 scenes), betrayal/turning point (5 scenes), aftermath (5 scenes),
legacy (4 scenes).

Return ONLY a JSON array of 60 objects:
[{{"scene_number":1,"type":"cold_open","title":"Title","brief":"What this scene covers"}}]"""

    raw = ollama_generate(outline_prompt, timeout=300)
    outline = extract_json_array(raw) or []

    if not outline:
        print("  [WARN] Could not generate outline. Creating minimal placeholder.")
        return []

    # Convert outline format to scene tuple format for batch generation
    ep_copy = dict(ep)
    ep_copy["scenes"] = [(s["scene_number"], s.get("type","context"), s.get("title",""), s.get("brief","")) for s in outline]

    all_scenes = []
    batches = [ep_copy["scenes"][i:i+BATCH_SIZE] for i in range(0, len(ep_copy["scenes"]), BATCH_SIZE)]
    for idx, batch in enumerate(batches):
        scenes = generate_scenes_batch(ep_copy, batch, idx, len(batches))
        all_scenes.extend(scenes)
        if idx < len(batches) - 1:
            time.sleep(2)
    return all_scenes


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="Generate Gods & Glory episode scripts via Ollama")
    ap.add_argument("--episode",     default=None, help="Episode key: EP001-EP005")
    ap.add_argument("--all",         action="store_true", help="Generate all S1 episodes sequentially")
    ap.add_argument("--scenes-only", action="store_true", help="Skip SEO package generation")
    ap.add_argument("--model",       default=None, help="Ollama model override")
    ap.add_argument("--list",        action="store_true", help="List available episodes")
    args = ap.parse_args()

    if args.model:
        global OLLAMA_MODEL
        OLLAMA_MODEL = args.model

    if args.list:
        for k, v in EPISODES.items():
            print(f"  {k}: {v['title']}")
        return

    if args.all:
        keys = list(EPISODES.keys())
    elif args.episode:
        keys = [args.episode.upper()]
    else:
        ap.print_help()
        sys.exit(1)

    results = []
    for key in keys:
        try:
            out = generate_episode(key, scenes_only=args.scenes_only)
            results.append((key, "OK", str(out)))
        except Exception as e:
            results.append((key, "FAIL", str(e)))
            print(f"\n[ERROR] {key}: {e}")

    print("\n=== GENERATION SUMMARY ===")
    for key, status, detail in results:
        print(f"  {key}: {status} — {detail}")


if __name__ == "__main__":
    main()
