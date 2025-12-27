import pygame
import random
import sys
import requests
import threading
import math
import datetime

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
DAY_LENGTH_TICKS = FPS * 20  # ~20 seconds per simulated day
SEASON_LENGTH_DAYS = 50

# Color Palette
C_GRASS  = (100, 180, 80)
C_TREE   = (34, 139, 34)
C_WATER  = (65, 105, 225)
C_STONE_G = (120, 120, 120)
BONE_GRAY = (150, 150, 150)
ICE_BLUE = (180, 220, 255)
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
        self.day_log = []
        self.phobias = set()
        self.knowledge = set()
        self.status_effects = {}
        self.last_lesson = ""

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
    # MEMORY & DREAMING
    # ==========================================
    def log_event(self, event: str):
        self.day_log.append(event)

    def dream_and_learn(self):
        if not self.day_log and self.last_lesson:
            return self.last_lesson

        hazards = {"water": ["water", "river", "lake"], "fire": ["fire", "burn"], "beast": ["wolf", "beast", "bite"]}
        lesson_bits = []
        for entry in self.day_log:
            lower = entry.lower()
            for phobia, keywords in hazards.items():
                if any(k in lower for k in keywords):
                    self.phobias.add(phobia)
            if "friend" in lower or "tribe" in lower:
                lesson_bits.append("Protect kin; remember friend")
            if "bitten" in lower or "wound" in lower:
                lesson_bits.append("Avoid danger")

        if self.phobias:
            lesson_bits.append("Fear " + ", ".join(sorted(self.phobias)))

        self.last_lesson = "; ".join(lesson_bits) if lesson_bits else "Rested with no dreams"
        self.day_log.clear()
        return self.last_lesson

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
    base_palette = [C_GRASS, C_TREE, C_STONE_G, C_WATER, BONE_GRAY, ICE_BLUE]
    base = base_palette[t_type]
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
    elif t_type == 4: # Cave entrance
        pygame.draw.rect(surf, BROWN, (x*TILE_SIZE+8, y*TILE_SIZE+8, TILE_SIZE-16, TILE_SIZE-16))
        pygame.draw.circle(surf, BLACK, (x*TILE_SIZE+TILE_SIZE//2, y*TILE_SIZE+TILE_SIZE//2), 6)
    elif t_type == 5: # Snow/ice
        pygame.draw.rect(surf, ICE_BLUE, rect)

# ==========================================
# MAIN SIMULATION CLASS
# ==========================================
class Simulation:
    def __init__(self):
        self.world = [[random.choices([0,1,2,3,4], weights=[50,14,8,14,4])[0] for _ in range(MAP_W)] for _ in range(MAP_H)]
        self.items = {}
        for y in range(MAP_H):
            for x in range(MAP_W):
                if self.world[y][x] == 1: self.items[(x,y)] = "🍎"
                elif self.world[y][x] == 2: self.items[(x,y)] = "🦴"
                elif self.world[y][x] == 3: self.items[(x,y)] = "🥢"
                elif self.world[y][x] == 0 and random.random() < 0.05: self.items[(x,y)] = "🌿"  # Bitter herb
                elif self.world[y][x] == 4 and random.random() < 0.3: self.items[(x,y)] = "🖌️"  # Pigment near caves

        self.humans = [Human(i, random.randint(0,2), random.randint(0,2), 0) for i in range(3)] + \
                      [Human(i, random.randint(15,17), random.randint(15,17), 1) for i in range(3,6)]
        self.selected = self.humans[0]
        self.cave_paintings = {}
        self.tick_count = 0
        self.day_count = 0
        self.wolves = [(random.randint(5,12), random.randint(5,12), False)]  # (x,y,is_tame)
        self.tribal_taboos = {0: set(), 1: set()}

    def update(self):
        self.tick_count += 1
        if self.tick_count % DAY_LENGTH_TICKS == 0:
            self.day_count += 1
            self.process_end_of_day()
            self.apply_seasonal_changes()

        for h in self.humans:
            if not h.alive: continue
            h.hunger += 0.05
            if h.hunger > 100: h.hp -= 0.5
            if h.hp <= 0: h.alive = False

            # System 1: Pickup
            item = self.items.get((h.x, h.y))
            if item and (h.x, h.y) not in self.tribal_taboos[h.tribe_id]:
                if item == "🍎": h.hunger = 0
                elif item == "🌿":
                    h.inventory.append(item)
                    h.log_event("Found bitter herb")
                elif item == "🖌️":
                    h.inventory.append(item)
                    h.log_event("Found pigment")
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
                        if random.random() < 0.2:
                            other.status_effects["infection"] = other.status_effects.get("infection", 2) + 1
                            other.log_event("Wounded in combat")
                        h.trigger_thinking("Combat with a stranger!")

            # Movement Logic (Random but restricted when thinking)
            if not h.is_thinking and random.random() > 0.6:
                h.x = max(0, min(MAP_W-1, h.x + random.randint(-1, 1)))
                h.y = max(0, min(MAP_H-1, h.y + random.randint(-1, 1)))

            self.apply_status_effects(h)
            self.try_cave_art(h)
            self.try_domestication(h)

        for idx, (wx, wy, tame) in enumerate(self.wolves):
            self.wolves[idx] = self.update_wolf(wx, wy, tame)

    # ==========================================
    # STATUS EFFECTS & MEDICINE
    # ==========================================
    def apply_status_effects(self, human: Human):
        if "infection" in human.status_effects:
            human.hp -= 0.3
            human.status_effects["infection"] -= 1
            if human.status_effects["infection"] <= 0:
                human.status_effects.pop("infection", None)
            if "🌿" in human.inventory and human.hp < 80:
                human.inventory.remove("🌿")
                human.status_effects.pop("infection", None)
                human.knowledge.add("medicine")
                human.hp = min(100, human.hp + 10)
                human.log_event("Bitter herb eased the wound")

    # ==========================================
    # CAVE ART & CULTURAL MEMORY
    # ==========================================
    def try_cave_art(self, human: Human):
        if self.world[human.y][human.x] != 4:
            return None
        if "🖌️" not in human.inventory or not human.knowledge:
            return None
        knowledge = sorted(list(human.knowledge))[0]
        desc = f"Painting of {human.name} teaching {knowledge}"
        painting = {"artist": human.name, "knowledge": knowledge, "description": desc, "day": self.day_count}
        self.cave_paintings[(human.x, human.y)] = painting
        human.inventory.remove("🖌️")
        human.log_event(f"Left cave art about {knowledge}")
        return painting

    def read_cave_art(self, human: Human):
        painting = self.cave_paintings.get((human.x, human.y))
        if painting:
            human.knowledge.add(painting["knowledge"])
            human.log_event(f"Learned {painting['knowledge']} from cave art")

    # ==========================================
    # SEASONS & MIGRATION PRESSURE
    # ==========================================
    def apply_seasonal_changes(self):
        season_phase = (self.day_count // SEASON_LENGTH_DAYS) % 2
        if season_phase == 1:  # Winter
            for y in range(MAP_H):
                for x in range(MAP_W):
                    if self.world[y][x] == 0:
                        self.world[y][x] = 5  # snow
                    elif self.world[y][x] == 3:
                        self.world[y][x] = 5
        else:
            for y in range(MAP_H):
                for x in range(MAP_W):
                    if self.world[y][x] == 5:
                        self.world[y][x] = 0

    # ==========================================
    # DREAMING CYCLE
    # ==========================================
    def process_end_of_day(self):
        for h in self.humans:
            if not h.alive:
                continue
            lesson = h.dream_and_learn()
            if "lightning" in lesson.lower():
                taboo = (h.x, h.y)
                self.tribal_taboos[h.tribe_id].add(taboo)

    # ==========================================
    # DOMESTICATION
    # ==========================================
    def try_domestication(self, human: Human):
        for idx, (wx, wy, tame) in enumerate(self.wolves):
            if abs(wx - human.x) <= 1 and abs(wy - human.y) <= 1 and not tame:
                if "🍎" in human.inventory or "🍖" in human.inventory:
                    offer = "🍖" if "🍖" in human.inventory else "🍎"
                    human.inventory.remove(offer)
                    self.wolves[idx] = (wx, wy, True)
                    human.knowledge.add("domestication")
                    human.log_event("Shared food with wolf; it followed")

    def update_wolf(self, x, y, tame):
        if tame and self.humans:
            leader = min((h for h in self.humans if h.alive), key=lambda h: abs(h.x - x) + abs(h.y - y), default=None)
            if leader:
                dx = 1 if leader.x > x else -1 if leader.x < x else 0
                dy = 1 if leader.y > y else -1 if leader.y < y else 0
                return (x + dx, y + dy, True)
        else:
            x = max(0, min(MAP_W-1, x + random.randint(-1,1)))
            y = max(0, min(MAP_H-1, y + random.randint(-1,1)))
        return (x, y, tame)

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
