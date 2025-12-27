# Echoes of the Paleolithic: AI Context & Roadmap
This project is a modular evolution simulation of early humans using a Dual-Brain Cognitive Architecture.
🧠 AI Coding Guidelines (For Codex/Copilot)
When generating code for this project, please adhere to these architectural rules:
1. The Dual-Brain System
System 1 (Automatic/Python): Fast, instinctive logic. Handled in the main game loop (update()). Includes pathfinding, immediate survival (eating food on the current tile), and movement.
System 2 (Conscious/Ollama): Slower, strategic reasoning. Handled via threading to prevent UI freezing. It uses the qwen2.5:1.5b model. It is only triggered by "Novelty Events" (finding tools, combat, social encounters).
2. Implementation Rules
Non-Blocking AI: Never call the LLM in the main thread. Always use the trigger_thinking() method which spawns a background thread.
Modular Items: Items are represented by emojis (🍎, 🦴, 🥢). Add new items by updating the Simulation.__init__ weights and the draw_world_tile function.
Stat-Driven Personality: Agents have aggression, hunger, and hp. These should always be passed to the LLM prompt to influence its "Thought" and "Speech."
🛠 Technical Stack
Engine: pygame-ce (Python 3.12+)
AI Backend: Ollama running qwen2.5:1.5b
Communication: requests to http://localhost:11434/api/generate
🗺 Feature Roadmap (The 30 Tasks)
Day/Night Cycle: Implement a 24-minute clock.
Temperature: Agents lose HP if cold at night without fire.
Fire Discovery: LLM-driven discovery when holding Stone + Stick.
Tool Durability: Items should have a limited use count.
Memory Journal: Agents should store the last 5 thoughts to maintain personality.
[...Insert the rest of the 30 tasks here...]
🎨 Visual Dictionary
Sun Tribe: Peach/Orange skin.
Moon Tribe: Purple/Pale skin.
🍎 Apple: Red, restores hunger.
🦴 Stone: White, crafting component.
🥢 Stick: Brown, crafting component.
Spear: A line drawn through the agent when crafted.
