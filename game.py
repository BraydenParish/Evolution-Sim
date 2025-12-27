import pygame
import random
import sys
import requests
import threading
import math
from pathlib import Path

from simulation_core import (
    BuildingPlanner,
    ChunkManager,
    KnowledgeBase,
    MemoryChronicle,
    TribeCoordinator,
    TILE_GRASS,
    TILE_TREE,
    TILE_STONE,
    TILE_WATER,
)

# ==========================================
# CONFIGURATION
# ==========================================
MODEL_NAME = "qwen2.5:1.5b" 
TILE_SIZE = 36 
MAP_W, MAP_H = 18, 18  # viewport size; world is chunk-based and unbounded
SIDEBAR_W = 360
SCREEN_W = (MAP_W * TILE_SIZE) + SIDEBAR_W
SCREEN_H = MAP_H * TILE_SIZE
FPS = 15

# Color Palette
C_GRASS  = (100, 180, 80)
C_TREE   = (34, 139, 34)
C_WATER  = (65, 105, 225)
C_STONE_G = (120, 120, 120)
BROWN    = (100, 60, 30)
WHITE    = (255, 255, 255)
BLACK    = (20, 20, 20)
GOLD     = (255, 215, 0)
RED      = (220, 20, 60)
TRIBE_A_SKIN = (245, 200, 160)
TRIBE_B_SKIN = (160, 140, 220)

# ==========================================
# SYSTEM 2: THE BRAIN (OLLAMA)
# ==========================================
class QwenBrain:
    @staticmethod
    def call_brain(agent_name, inventory, tools, situation):
        url = "http://localhost:11434/api/generate"
        prompt = (
            f"System: Respond as a primitive human. Be brief. No meta-talk.\n"
            f"Name: {agent_name}\nInv: {inventory}\nTools: {tools}\nSituation: {situation}\n\n"
            f"Format:\nTHOUGHT: [One sentence]\nSPEECH: [One grunt]\nCRAFT: [SPEAR or NONE]"
        )
        try:
            r = requests.post(url, json={"model": MODEL_NAME, "prompt": prompt, "stream": False}, timeout=10)
            if r.status_code == 200:
                text = r.json().get('response', "")
                res = {"THOUGHT": "...", "SPEECH": "...", "CRAFT": "NONE"}
                for line in text.split('\n'):
                    if line.upper().startswith("THOUGHT:"): res["THOUGHT"] = line.split(":", 1)[-1].strip()
                    elif line.upper().startswith("SPEECH:"): res["SPEECH"] = line.split(":", 1)[-1].strip()
                    elif line.upper().startswith("CRAFT:"): res["CRAFT"] = line.split(":", 1)[-1].strip().upper()
                return res
        except: return None

# ==========================================
# AGENT CLASS
# ==========================================
class Human:
    def __init__(self, id, x, y, tribe_id):
        self.id = id
        self.tribe_id = tribe_id
        self.name = f"{'Sun' if tribe_id==0 else 'Moon'}_{id}"
        self.x, self.y = x, y
        self.hp, self.hunger = 100, 0
        self.inventory, self.tools = [], []
        self.alive = True
        self.thought = "I seek food and the light."
        self.speech = "..."
        self.is_thinking = False
        self.anim_timer = random.random() * 10
        self.attack_power = 10
        self.is_chief = False
        self.resources = {"wood": 0, "stone": 0}
        self.goal = None

    def trigger_thinking(self, situation):
        if self.is_thinking: return
        def run_ai():
            self.is_thinking = True
            res = QwenBrain.call_brain(self.name, self.inventory, self.tools, situation)
            if res:
                self.thought, self.speech = res['THOUGHT'], res['SPEECH']
                if "SPEAR" in res['CRAFT'] and "🦴" in self.inventory and "🥢" in self.inventory:
                    self.inventory.remove("🦴"); self.inventory.remove("🥢")
                    self.tools.append("SPEAR")
                    self.attack_power = 40
            self.is_thinking = False
        threading.Thread(target=run_ai, daemon=True).start()

# ==========================================
# GRAPHICS DRAWING HELPERS
# ==========================================
def draw_agent(surf, h, offset):
    x, y = (h.x - offset[0]) * TILE_SIZE, (h.y - offset[1]) * TILE_SIZE
    bob = int(math.sin(pygame.time.get_ticks() * 0.01 + h.anim_timer) * 4)
    cx, cy = x + TILE_SIZE//2, y + TILE_SIZE//2 + bob
    skin = TRIBE_A_SKIN if h.tribe_id == 0 else TRIBE_B_SKIN
    
    # Shadow
    s_rect = (cx-10, y + TILE_SIZE - 8, 20, 10)
    pygame.draw.ellipse(surf, (0, 0, 0, 60), s_rect)

    # Body & Head
    pygame.draw.ellipse(surf, skin, (cx-7, cy-5, 14, 18))
    pygame.draw.circle(surf, skin, (cx, cy-10), 6)
    # Loincloth
    pygame.draw.rect(surf, (100, 70, 40), (cx-6, cy+5, 12, 6))
    
    # Spear logic
    if "SPEAR" in h.tools:
        pygame.draw.line(surf, (180, 180, 180), (cx+8, cy-15), (cx+15, cy+10), 3)
    
    if h.is_thinking:
        pygame.draw.circle(surf, WHITE, (cx + 12, cy - 18), 3)

def draw_world_tile(surf, x, y, t_type):
    rect = (x*TILE_SIZE, y*TILE_SIZE, TILE_SIZE, TILE_SIZE)
    base = [C_GRASS, C_TREE, C_STONE_G, C_WATER][t_type]
    pygame.draw.rect(surf, base, rect)
    # Detail
    if t_type == 0: # Grass tuft
        pygame.draw.line(surf, (80, 150, 60), (x*TILE_SIZE+5, y*TILE_SIZE+10), (x*TILE_SIZE+7, y*TILE_SIZE+5), 1)
    elif t_type == 1: # Bush/Tree
        pygame.draw.circle(surf, (20, 80, 20), (x*TILE_SIZE+18, y*TILE_SIZE+18), 12)
        pygame.draw.circle(surf, (40, 100, 40), (x*TILE_SIZE+12, y*TILE_SIZE+12), 10)
    elif t_type == 3: # Shimmering water
        wave = int(math.sin(pygame.time.get_ticks()*0.005 + x)*3)
        pygame.draw.line(surf, WHITE, (x*TILE_SIZE+5, y*TILE_SIZE+15+wave), (x*TILE_SIZE+15, y*TILE_SIZE+15+wave), 1)

# ==========================================
# MAIN SIMULATION CLASS
# ==========================================
class Simulation:
    def __init__(self):
        self.chunk_manager = ChunkManager()
        self.items = {}
        self.generated_resources = set()
        self.humans = [Human(i, random.randint(0,2), random.randint(0,2), 0) for i in range(3)] + \
                      [Human(i, random.randint(10,12), random.randint(10,12), 1) for i in range(3,6)]
        self.selected = self.humans[0]
        self.tribe_knowledge = {0: KnowledgeBase(), 1: KnowledgeBase()}
        self.tribe_resources = {0: {"wood": 0, "stone": 0}, 1: {"wood": 0, "stone": 0}}
        self.buildings = []
        self.farms = {}
        self.year = 0
        self.planner = BuildingPlanner()
        self.coordinator = TribeCoordinator()
        chiefs = self.coordinator.designate_chiefs([{"id": h.id, "tribe_id": h.tribe_id} for h in self.humans])
        for h in self.humans:
            if chiefs.get(h.tribe_id) == h.id:
                h.is_chief = True
        self.chronicle = MemoryChronicle(path=Path("chronicle.json"))
        for tribe_id, chief_id in chiefs.items():
            self.coordinator.set_order(tribe_id, chief_id, "Gather wood near camp")

    def update(self):
        self.year += 1 if pygame.time.get_ticks() % 1000 < 15 else 0
        for h in self.humans:
            if not h.alive:
                continue
            h.hunger += 0.05
            if h.hunger > 100:
                h.hp -= 0.5
            if h.hp <= 0:
                h.alive = False
                continue

            tile = self.chunk_manager.get_tile(h.x, h.y)
            if (h.x, h.y) not in self.generated_resources:
                if tile == TILE_TREE:
                    self.items[(h.x, h.y)] = "🪵"
                elif tile == TILE_STONE:
                    self.items[(h.x, h.y)] = "🪨"
                elif tile == TILE_GRASS and random.random() > 0.8:
                    self.items[(h.x, h.y)] = "🍎"
                self.generated_resources.add((h.x, h.y))

            # System 1: Pickup
            item = self.items.get((h.x, h.y))
            if item:
                if item == "🍎":
                    h.hunger = 0
                    self.chronicle.log_event(self.year, f"{h.name} ate an apple at {h.x},{h.y}")
                elif item == "🪵":
                    h.resources["wood"] += 1
                    self.tribe_resources[h.tribe_id]["wood"] += 1
                elif item == "🪨":
                    h.resources["stone"] += 1
                    self.tribe_resources[h.tribe_id]["stone"] += 1
                self.items.pop((h.x, h.y))

            # Trigger knowledge checks
            resource_flags = {
                "stone_tools": h.resources["stone"] >= 1 and "🥢" in h.inventory,
                "fire": self.tribe_resources[h.tribe_id]["wood"] >= 5,
                "clothing": self.tribe_resources[h.tribe_id]["wood"] >= 2,
                "pottery": self.tribe_resources[h.tribe_id]["stone"] >= 3,
                "agriculture": len(self.farms) > 0,
            }
            self.tribe_knowledge[h.tribe_id].evaluate_progress(resource_flags)

            # Construction logic
            tribe_res = self.tribe_resources[h.tribe_id]
            if tribe_res["wood"] >= 10 and tribe_res["stone"] >= 5:
                try:
                    build = self.planner.choose_build(tribe_res, self.tribe_knowledge[h.tribe_id].tier)
                    self.buildings.append({"type": build.type, "pos": (h.x, h.y), "tribe": h.tribe_id})
                    self.chronicle.log_event(self.year, f"Tribe {h.tribe_id} built a {build.type} at {h.x},{h.y}")
                except ValueError:
                    pass

            # Agriculture
            if self.tribe_knowledge[h.tribe_id].tier >= 3 and (h.x, h.y) not in self.farms:
                if random.random() > 0.95:
                    self.farms[(h.x, h.y)] = pygame.time.get_ticks() + 5000
                    self.chronicle.log_event(self.year, f"Farm plot started at {h.x},{h.y}")

            # Farm harvest
            ready_farms = [pos for pos, t in list(self.farms.items()) if pygame.time.get_ticks() >= t]
            for pos in ready_farms:
                self.items[pos] = "🍎"
                self.farms[pos] = pygame.time.get_ticks() + 5000

            # System 2: Combat
            for other in self.humans:
                if other.alive and other.tribe_id != h.tribe_id:
                    if abs(h.x-other.x) < 2 and abs(h.y-other.y) < 2:
                        other.hp -= (h.attack_power / 10)
                        h.trigger_thinking("Combat with a stranger!")

            # Movement Logic with tribal orders
            if not h.is_thinking and random.random() > 0.6:
                order = self.coordinator.orders.get(h.tribe_id)
                target = None
                if order:
                    chiefs = [c for c in self.humans if c.tribe_id == h.tribe_id and c.is_chief]
                    target = (chiefs[0].x, chiefs[0].y) if chiefs else None
                dx = random.randint(-1, 1)
                dy = random.randint(-1, 1)
                if target:
                    dx = (target[0] - h.x)
                    dy = (target[1] - h.y)
                    dx = 1 if dx > 0 else -1 if dx < 0 else 0
                    dy = 1 if dy > 0 else -1 if dy < 0 else 0
                h.x += dx
                h.y += dy

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("Early Human AI Evolution")
    sim = Simulation()
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Verdana", 14)
    bold = pygame.font.SysFont("Verdana", 16, bold=True)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = pygame.mouse.get_pos()
                offset = (sim.selected.x - MAP_W//2, sim.selected.y - MAP_H//2)
                wx, wy = mx // TILE_SIZE + offset[0], my // TILE_SIZE + offset[1]
                for h in sim.humans:
                    if h.x == wx and h.y == wy:
                        sim.selected = h
            if event.type == pygame.KEYDOWN and event.key == pygame.K_t:
                sim.selected.trigger_thinking("A god speaks from the clouds.")

        sim.update()
        screen.fill(BLACK)

        # 1. Draw Map with viewport centered on selected human
        offset = (sim.selected.x - MAP_W//2, sim.selected.y - MAP_H//2)
        for y in range(MAP_H):
            for x in range(MAP_W):
                tile = sim.chunk_manager.get_tile(x + offset[0], y + offset[1])
                draw_world_tile(screen, x, y, tile)

        # 2. Draw Items
        for (x,y), item in sim.items.items():
            sx, sy = x - offset[0], y - offset[1]
            if 0 <= sx < MAP_W and 0 <= sy < MAP_H:
                ix, iy = sx*TILE_SIZE+TILE_SIZE//2, sy*TILE_SIZE+TILE_SIZE//2
                color = RED if item == "🍎" else WHITE if item == "🪨" else BROWN
                pygame.draw.circle(screen, color, (ix, iy), 6)

        # 3. Draw Buildings/Farms
        for b in self_sim_buildings := getattr(sim, "buildings", []):
            sx, sy = b["pos"][0] - offset[0], b["pos"][1] - offset[1]
            if 0 <= sx < MAP_W and 0 <= sy < MAP_H:
                pygame.draw.rect(screen, GOLD, (sx*TILE_SIZE+8, sy*TILE_SIZE+8, TILE_SIZE-16, TILE_SIZE-16), 2)
                screen.blit(font.render(b["type"], True, GOLD), (sx*TILE_SIZE+4, sy*TILE_SIZE+4))
        for (fx, fy), _ in sim.farms.items():
            sx, sy = fx - offset[0], fy - offset[1]
            if 0 <= sx < MAP_W and 0 <= sy < MAP_H:
                pygame.draw.rect(screen, (120, 80, 40), (sx*TILE_SIZE+10, sy*TILE_SIZE+10, TILE_SIZE-20, TILE_SIZE-20), 1)

        # 4. Draw Humans
        for h in sim.humans:
            if not h.alive: continue
            if h == sim.selected:
                pygame.draw.circle(screen, GOLD, ((h.x-offset[0])*TILE_SIZE+TILE_SIZE//2, (h.y-offset[1])*TILE_SIZE+TILE_SIZE//2), 22, 2)
            draw_agent(screen, h, offset)

        # 4. Draw Sidebar
        pygame.draw.rect(screen, (30, 25, 20), (MAP_W*TILE_SIZE, 0, SIDEBAR_W, SCREEN_H))
        sh = sim.selected
        
        # Text Header
        screen.blit(bold.render(f"AGENT: {sh.name}", True, GOLD), (MAP_W*TILE_SIZE+20, 20))
        # Visual Health Bar
        pygame.draw.rect(screen, (100, 0, 0), (MAP_W*TILE_SIZE+20, 50, 200, 10))
        pygame.draw.rect(screen, RED, (MAP_W*TILE_SIZE+20, 50, sh.hp * 2, 10))
        
        # Info
        info_list = [
            f"Inventory: {sh.inventory}",
            f"Tools: {sh.tools}",
            "---",
            "SYSTEM 2 THOUGHT:",
            f"{sh.thought}",
            "---",
            f"SPEECH: '{sh.speech}'",
            "---",
            f"Brain Activity: {'THINKING...' if sh.is_thinking else 'Automatic'}",
            "---",
            "Press 'T' to interact with selected human."
        ]
        
        y_pos = 100
        for line in info_list:
            if len(line) > 42: line = line[:40] + "..."
            color = GOLD if "THOUGHT" in line else WHITE
            screen.blit(font.render(line, True, color), (MAP_W*TILE_SIZE+20, y_pos))
            y_pos += 35

        pygame.display.flip()
        clock.tick(FPS)

if __name__ == "__main__":
    main()
