import json
import math
import random
import sys
import threading
import math
from collections import deque

# ==========================================
# CONFIGURATION
# ==========================================
MODEL_NAME = "qwen2.5:1.5b" 
TILE_SIZE = 36
MAP_W, MAP_H = 18, 18
SIDEBAR_W = 360
LOG_HEIGHT = 140
SCREEN_W = (MAP_W * TILE_SIZE) + SIDEBAR_W
SCREEN_H = (MAP_H * TILE_SIZE) + LOG_HEIGHT
FPS = 15
DAY_LENGTH_TICKS = FPS * 20  # ~20 seconds per simulated day
SEASON_LENGTH_DAYS = 50

# Color Palette
C_GRASS  = (100, 180, 80)
C_TREE   = (34, 139, 34)
C_WATER  = (65, 105, 225)
C_STONE_G = (120, 120, 120)
C_HUT    = (160, 110, 60)
BROWN    = (100, 60, 30)
WHITE    = (255, 255, 255)
BLACK    = (20, 20, 20)
GOLD     = (255, 215, 0)
RED      = (220, 20, 60)
HUT_BROWN = (140, 100, 60)
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
        self.thirst = 0
        self.inventory, self.tools = [], []
        self.memories = []
        self.gender = random.choice(["M", "F"])
        self.alive = True
        self.thought = "I seek food and the light."
        self.speech = "..."
        self.is_thinking = False
        self.anim_timer = random.random() * 10
        self.attack_power = 10
        self.move_cooldown = 0.0

    def trigger_thinking(self, situation, async_call=True):
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
                    self.spear_uses = 5
            self.is_thinking = False

        if async_call:
            threading.Thread(target=run_ai, daemon=True).start()
        else:
            run_ai()

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
    base_lookup = [C_GRASS, C_TREE, C_STONE_G, C_WATER, HUT_BROWN]
    base = base_lookup[t_type]
    pygame.draw.rect(surf, base, rect)
    # Detail
    if t_type == 0: # Grass tuft
        pygame.draw.line(surf, (80, 150, 60), (x*TILE_SIZE+5, y*TILE_SIZE+10), (x*TILE_SIZE+7, y*TILE_SIZE+5), 1)
    elif t_type == 1: # Bush/Tree
        pygame.draw.circle(surf, (20, 80, 20), (x*TILE_SIZE+18, y*TILE_SIZE+18), 12)
        pygame.draw.circle(surf, (40, 100, 40), (x*TILE_SIZE+12, y*TILE_SIZE+12), 10)
    elif t_type == 4: # Hut outline
        pygame.draw.rect(surf, (120, 80, 40), (x*TILE_SIZE+6, y*TILE_SIZE+10, TILE_SIZE-12, TILE_SIZE-12), 2)
        pygame.draw.rect(surf, (200, 170, 120), (x*TILE_SIZE+10, y*TILE_SIZE+18, TILE_SIZE-20, TILE_SIZE-16))
    elif t_type == 3: # Shimmering water
        wave = int(math.sin(pygame.time.get_ticks()*0.005 + x)*3)
        pygame.draw.line(surf, WHITE, (x*TILE_SIZE+5, y*TILE_SIZE+15+wave), (x*TILE_SIZE+15, y*TILE_SIZE+15+wave), 1)
    elif t_type == 4: # Hut roof line
        pygame.draw.polygon(surf, (200, 180, 120), [
            (x*TILE_SIZE+6, y*TILE_SIZE+18),
            (x*TILE_SIZE+TILE_SIZE//2, y*TILE_SIZE+6),
            (x*TILE_SIZE+TILE_SIZE-6, y*TILE_SIZE+18)
        ])

# ==========================================
# MAIN SIMULATION CLASS
# ==========================================
class Simulation:
    def __init__(self, rng=None):
        self.rng = rng or random.Random()
        self.world = [[self.rng.choices([0,1,2,3], weights=[60,15,10,15])[0] for _ in range(MAP_W)] for _ in range(MAP_H)]
        self.items = {}
        self.apple_regrowth = {}
        for y in range(MAP_H):
            for x in range(MAP_W):
                if self.world[y][x] == 1:
                    self.items[(x,y)] = "🍎"
                elif self.world[y][x] == 2:
                    self.items[(x,y)] = "🦴"
                elif self.world[y][x] == 3:
                    self.items[(x,y)] = "🥢"

        self.humans = [Human(i, self.rng.randint(0,2), self.rng.randint(0,2), 0) for i in range(3)] + \
                      [Human(i, self.rng.randint(15,17), self.rng.randint(15,17), 1) for i in range(3,6)]
        self.selected = self.humans[0]
        self.migration_targets = {}
        self.next_human_id = len(self.humans)

        self.fires = {(2, 2), (15, 15)}
        self.log_events = deque(maxlen=8)
        self.first_spear_logged = False

        self.time_minutes = 8 * 60
        self.total_minutes = 0.0
        self.day_count = 0
        self.light_level = 1.0
        self.is_night = False
        self.is_raining = False
        self.temperature = 20
        self.log_event("The world begins at dawn.")

    def log_event(self, text):
        stamp_hour = int(self.time_minutes // 60) % 24
        stamp_min = int(self.time_minutes % 60)
        self.log_events.appendleft(f"D{self.day_count+1:02d} {stamp_hour:02d}:{stamp_min:02d} - {text}")

    def _compute_light_level(self):
        hour = (self.time_minutes / 60) % 24
        if 6 <= hour < 18:
            self.is_night = False
            if 6 <= hour < 8:
                return 0.3 + ((hour-6)/2)*0.7
            elif 16 <= hour < 18:
                return 1.0 - ((hour-16)/2)*0.7
            return 1.0
        self.is_night = True
        if 18 <= hour < 20:
            return 0.3 + ((20-hour)/2)*0.7
        elif 4 <= hour < 6:
            return 0.3 + ((hour-4)/2)*0.7
        return 0.3

    def _roll_weather(self):
        was_raining = self.is_raining
        self.is_raining = self.rng.random() < 0.1
        if self.is_raining:
            if self.fires:
                self.fires.clear()
                self.log_event("Rain douses every fire.")
            self.log_event("Rain clouds gather over the camp.")
        elif was_raining:
            self.log_event("The rain stops; embers fade.")

    def _update_apple_regrowth(self, dt_minutes):
        to_restore = []
        for pos in list(self.apple_regrowth.keys()):
            self.apple_regrowth[pos] += dt_minutes
            if self.apple_regrowth[pos] >= 3 * 24 * 60:
                to_restore.append(pos)

        for pos in to_restore:
            self.apple_regrowth.pop(pos, None)
            self.items[pos] = "🍎"
            self.log_event("An apple tree bears fruit again.")

    def _advance_time(self, dt_seconds):
        dt_minutes = dt_seconds * 1  # 1 real second = 1 in-game minute
        self.total_minutes += dt_minutes
        self.time_minutes += dt_minutes
        while self.time_minutes >= 24 * 60:
            self.time_minutes -= 24 * 60
            self.day_count += 1
            self._roll_weather()
        for y in range(MAP_H):
            for x in range(MAP_W):
                pos = (x, y)
                if self.world[y][x] == 1 and pos not in self.items and pos not in self.apple_regrowth:
                    self.apple_regrowth[pos] = 0
        self.light_level = self._compute_light_level()
        self.temperature = 26 if not self.is_night else 10
        if self.is_raining:
            self.temperature -= 3
        self._update_apple_regrowth(dt_minutes)

    def _is_sheltered(self, h):
        return self.world[h.y][h.x] == 1

    def _near_fire(self, h):
        for fx, fy in self.fires:
            if abs(fx - h.x) <= 2 and abs(fy - h.y) <= 2:
                return True
        return False

    def _vision_range(self, h):
        if self._near_fire(h):
            return 4
        return 4 if not self.is_night else 2

    def _find_nearest_tile(self, h, tile_type, max_dist):
        best = None
        for dy in range(-max_dist, max_dist+1):
            for dx in range(-max_dist, max_dist+1):
                tx, ty = h.x + dx, h.y + dy
                if 0 <= tx < MAP_W and 0 <= ty < MAP_H:
                    if abs(dx) + abs(dy) > max_dist:
                        continue
                    if self.world[ty][tx] == tile_type:
                        if best is None or abs(dx) + abs(dy) < abs(best[0]-h.x) + abs(best[1]-h.y):
                            best = (tx, ty)
        return best

    def _find_nearest_item(self, h, item, max_dist):
        best = None
        for (ix, iy), itm in self.items.items():
            if itm != item:
                continue
            dist = abs(ix - h.x) + abs(iy - h.y)
            if dist <= max_dist:
                if best is None or dist < abs(best[0]-h.x) + abs(best[1]-h.y):
                    best = (ix, iy)
        return best

    def _step_toward(self, h, target, purposeful=False):
        tx, ty = target
        dx = 0 if tx == h.x else (1 if tx > h.x else -1)
        dy = 0 if ty == h.y else (1 if ty > h.y else -1)
        nx, ny = h.x + dx, h.y + dy
        if 0 <= nx < MAP_W and 0 <= ny < MAP_H:
            if self.world[ny][nx] == 3 and not purposeful:
                return
            h.x, h.y = nx, ny
            if self.world[ny][nx] == 3:
                h.move_cooldown = max(h.move_cooldown, 0.75)

    def update(self, dt_seconds=1.0):
        self._advance_time(dt_seconds)
        for h in self.humans:
            if not h.alive: continue
            if h.move_cooldown > 0:
                h.move_cooldown = max(0.0, h.move_cooldown - dt_seconds)

            energy_factor = 1.3 if self.is_raining else 1.0
            h.hunger += 0.75 * dt_seconds * energy_factor
            h.thirst += 0.6 * dt_seconds * energy_factor
            if h.hunger > 100: h.hp -= 0.5 * dt_seconds
            if h.thirst > 100: h.hp -= 0.6 * dt_seconds
            if self.is_night and not (self._near_fire(h) or self._is_sheltered(h)):
                h.hp -= 0.25 * dt_seconds
            if h.hp <= 0: h.alive = False

            # Discovery of fire while contemplating.
            if h.is_thinking and h.inventory.count("🦴") >= 2 and random.random() < 0.05:
                self.items[(h.x, h.y)] = "🔥"

            # System 1: Cook meat if near fire.
            if "Corpse" in h.inventory and self._near_fire(h.x, h.y):
                h.inventory.remove("Corpse")
                h.inventory.append("Cooked Meat")
                h.hunger = 0

            # System 1: Pickup
            item = self.items.get((h.x, h.y))
            if item:
                if item == "🍎":
                    h.hunger = 0
                    self.apple_regrowth[(h.x, h.y)] = 0
                else:
                    h.inventory.append(item)
                    h.trigger_thinking(f"I picked up a {item}.")
                    self.items.pop((h.x, h.y))

            # Hut building using sticks
            if h.inventory.count("🥢") >= 3 and self.world[h.y][h.x] != 4:
                for _ in range(3):
                    h.inventory.remove("🥢")
                self.world[h.y][h.x] = 4

            # Ranged stone toss
            for other in self.humans:
                if other.alive and other.tribe_id != h.tribe_id:
                    dx, dy = abs(h.x-other.x), abs(h.y-other.y)
                    if max(dx, dy) == 2 and "🦴" in h.inventory:
                        h.inventory.remove("🦴")
                        other.hp -= 5
                        h.trigger_thinking("I hurled a stone at a foe!")

            if self.world[h.y][h.x] == 3 and h.thirst > 0:
                h.thirst = 0

            # Trigger Crafting Check
            if "🦴" in h.inventory and "🥢" in h.inventory and "SPEAR" not in h.tools:
                h.trigger_thinking("I have a stick and a stone. Can I make something?")

            # System 2: Combat
            for other in self.humans:
                if other.alive and other.tribe_id != h.tribe_id:
                    if abs(h.x-other.x) < 2 and abs(h.y-other.y) < 2:
                        other.hp -= (h.attack_power / 10)
                        h.use_spear()
                        h.trigger_thinking("Combat with a stranger!")

            vision = self._vision_range(h)
            moved = False
            if h.move_cooldown <= 0:
                if h.thirst >= 70:
                    target = self._find_nearest_tile(h, 3, vision)
                    if target:
                        self._step_toward(h, target, purposeful=True)
                        moved = True
                elif h.hunger >= 70:
                    target = self._find_nearest_item(h, "🍎", vision)
                    if target:
                        self._step_toward(h, target, purposeful=True)
                        moved = True

                if self.world[h.y][h.x] == 3 and h.thirst < 70:
                    moved = True

                # Movement Logic (Random but restricted when thinking)
                if not moved and not h.is_thinking and self.rng.random() > 0.6:
                    nx = max(0, min(MAP_W-1, h.x + self.rng.randint(-1, 1)))
                    ny = max(0, min(MAP_H-1, h.y + self.rng.randint(-1, 1)))
                    if self.world[ny][nx] != 3:
                        h.x, h.y = nx, ny
                    elif self.world[ny][nx] == 3 and self.rng.random() > 0.5:
                        h.x, h.y = nx, ny
                        h.move_cooldown = max(h.move_cooldown, 0.75)

            if self.world[h.y][h.x] == 3 and h.thirst > 0:
                h.thirst = 0

        if not self.first_spear_logged and any("SPEAR" in h.tools for h in self.humans):
            self.first_spear_logged = True
            self.log_event("The first spear was crafted.")

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
        dt_seconds = clock.tick(FPS) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = pygame.mouse.get_pos()
                if my < MAP_H * TILE_SIZE:
                    for h in sim.humans:
                        if abs(h.x*TILE_SIZE - mx) < TILE_SIZE and abs(h.y*TILE_SIZE - my) < TILE_SIZE:
                            sim.selected = h
            if event.type == pygame.KEYDOWN and event.key == pygame.K_t:
                sim.selected.trigger_thinking("A god speaks from the clouds.")

        sim.update(dt_seconds)
        screen.fill(BLACK)

        # 1. Draw Map
        for y in range(MAP_H):
            for x in range(MAP_W): draw_world_tile(screen, x, y, sim.world[y][x])

        # 2. Draw Items
        for (x,y), item in sim.items.items():
            ix, iy = x*TILE_SIZE+TILE_SIZE//2, y*TILE_SIZE+TILE_SIZE//2
            color = RED if item == "🍎" else WHITE if item == "🦴" else BROWN
            pygame.draw.circle(screen, color, (ix, iy), 6)

        # 3. Draw Fires
        for fx, fy in sim.fires:
            cx, cy = fx*TILE_SIZE+TILE_SIZE//2, fy*TILE_SIZE+TILE_SIZE//2
            pygame.draw.circle(screen, (255, 140, 0), (cx, cy-4), 6)
            pygame.draw.circle(screen, (255, 215, 0), (cx, cy+2), 4)

        # 4. Draw Humans
        for h in sim.humans:
            if not h.alive: continue
            if h == sim.selected:
                pygame.draw.circle(screen, GOLD, (h.x*TILE_SIZE+TILE_SIZE//2, h.y*TILE_SIZE+TILE_SIZE//2), 22, 2)
            draw_agent(screen, h)

        # Night shading
        dark_surface = pygame.Surface((MAP_W*TILE_SIZE, MAP_H*TILE_SIZE), pygame.SRCALPHA)
        alpha = int((1 - sim.light_level) * 180)
        dark_surface.fill((0, 0, 0, alpha))
        screen.blit(dark_surface, (0,0))

        if sim.is_raining:
            rain_surface = pygame.Surface((MAP_W*TILE_SIZE, MAP_H*TILE_SIZE), pygame.SRCALPHA)
            for rx in range(0, MAP_W*TILE_SIZE, 12):
                pygame.draw.line(rain_surface, (150, 180, 255, 120), (rx, 0), (rx-8, MAP_H*TILE_SIZE), 2)
            screen.blit(rain_surface, (0,0))

        # 5. Draw Sidebar
        pygame.draw.rect(screen, (30, 25, 20), (MAP_W*TILE_SIZE, 0, SIDEBAR_W, SCREEN_H))
        sh = sim.selected

        # Text Header
        screen.blit(bold.render(f"AGENT: {sh.name}", True, GOLD), (MAP_W*TILE_SIZE+20, 20))
        # Visual Health Bar
        pygame.draw.rect(screen, (100, 0, 0), (MAP_W*TILE_SIZE+20, 50, 200, 10))
        pygame.draw.rect(screen, RED, (MAP_W*TILE_SIZE+20, 50, max(0, sh.hp) * 2, 10))
        # Thirst Bar
        pygame.draw.rect(screen, (20, 20, 80), (MAP_W*TILE_SIZE+20, 70, 200, 10))
        pygame.draw.rect(screen, (70, 130, 180), (MAP_W*TILE_SIZE+20, 70, min(100, sh.thirst) * 2, 10))

        # Info
        info_list = [
            f"Temperature: {sim.temperature}C | {'Night' if sim.is_night else 'Day'}",
            f"Hunger: {int(sh.hunger)}  Thirst: {int(sh.thirst)}",
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

        # 6. World Logger
        log_rect = (0, MAP_H*TILE_SIZE, SCREEN_W, LOG_HEIGHT)
        pygame.draw.rect(screen, (15, 12, 10), log_rect)
        pygame.draw.rect(screen, GOLD, log_rect, 2)
        screen.blit(bold.render("HISTORICAL EVENTS", True, GOLD), (15, MAP_H*TILE_SIZE + 10))
        ly = MAP_H*TILE_SIZE + 40
        for evt in sim.log_events:
            screen.blit(font.render(evt, True, WHITE), (20, ly))
            ly += 18

        pygame.display.flip()

if __name__ == "__main__":
    main()
