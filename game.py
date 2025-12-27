import pygame
import random
import sys
import requests
import threading
import math

# ==========================================
# CONFIGURATION
# ==========================================
MODEL_NAME = "qwen2.5:1.5b" 
TILE_SIZE = 36 
MAP_W, MAP_H = 18, 18
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
def draw_agent(surf, h):
    x, y = h.x * TILE_SIZE, h.y * TILE_SIZE
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
        self.world = [[random.choices([0,1,2,3], weights=[60,15,10,15])[0] for _ in range(MAP_W)] for _ in range(MAP_H)]
        self.items = {}
        for y in range(MAP_H):
            for x in range(MAP_W):
                if self.world[y][x] == 1: self.items[(x,y)] = "🍎"
                elif self.world[y][x] == 2: self.items[(x,y)] = "🦴" 
                elif self.world[y][x] == 3: self.items[(x,y)] = "🥢" 
        
        self.humans = [Human(i, random.randint(0,2), random.randint(0,2), 0) for i in range(3)] + \
                      [Human(i, random.randint(15,17), random.randint(15,17), 1) for i in range(3,6)]
        self.selected = self.humans[0]

    def update(self):
        for h in self.humans:
            if not h.alive: continue
            h.hunger += 0.05
            if h.hunger > 100: h.hp -= 0.5
            if h.hp <= 0: h.alive = False

            # System 1: Pickup
            item = self.items.get((h.x, h.y))
            if item:
                if item == "🍎": h.hunger = 0
                else: 
                    h.inventory.append(item)
                    h.trigger_thinking(f"I picked up a {item}.")
                self.items.pop((h.x, h.y))

            # Trigger Crafting Check
            if "🦴" in h.inventory and "🥢" in h.inventory and "SPEAR" not in h.tools:
                h.trigger_thinking("I have a stick and a stone. Can I make something?")

            # System 2: Combat
            for other in self.humans:
                if other.alive and other.tribe_id != h.tribe_id:
                    if abs(h.x-other.x) < 2 and abs(h.y-other.y) < 2:
                        other.hp -= (h.attack_power / 10)
                        h.trigger_thinking("Combat with a stranger!")

            # Movement Logic (Random but restricted when thinking)
            if not h.is_thinking and random.random() > 0.6:
                h.x = max(0, min(MAP_W-1, h.x + random.randint(-1, 1)))
                h.y = max(0, min(MAP_H-1, h.y + random.randint(-1, 1)))

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
                for h in sim.humans:
                    if abs(h.x*TILE_SIZE - mx) < TILE_SIZE and abs(h.y*TILE_SIZE - my) < TILE_SIZE:
                        sim.selected = h
            if event.type == pygame.KEYDOWN and event.key == pygame.K_t:
                sim.selected.trigger_thinking("A god speaks from the clouds.")

        sim.update()
        screen.fill(BLACK)

        # 1. Draw Map
        for y in range(MAP_H):
            for x in range(MAP_W): draw_world_tile(screen, x, y, sim.world[y][x])
        
        # 2. Draw Items
        for (x,y), item in sim.items.items():
            ix, iy = x*TILE_SIZE+TILE_SIZE//2, y*TILE_SIZE+TILE_SIZE//2
            color = RED if item == "🍎" else WHITE if item == "🦴" else BROWN
            pygame.draw.circle(screen, color, (ix, iy), 6)

        # 3. Draw Humans
        for h in sim.humans:
            if not h.alive: continue
            if h == sim.selected:
                pygame.draw.circle(screen, GOLD, (h.x*TILE_SIZE+TILE_SIZE//2, h.y*TILE_SIZE+TILE_SIZE//2), 22, 2)
            draw_agent(screen, h)

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
