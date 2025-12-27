import random
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Lightweight pygame stub so logic can be imported without the real dependency.
pygame_stub = types.SimpleNamespace(
    init=lambda: None,
    QUIT=0,
    MOUSEBUTTONDOWN=1,
    KEYDOWN=2,
    K_t=116,
)
pygame_stub.time = types.SimpleNamespace(get_ticks=lambda: 0, Clock=lambda: types.SimpleNamespace(tick=lambda *_: None))
pygame_stub.draw = types.SimpleNamespace(
    ellipse=lambda *_, **__: None,
    circle=lambda *_, **__: None,
    rect=lambda *_, **__: None,
    line=lambda *_, **__: None,
    polygon=lambda *_, **__: None,
)
pygame_stub.display = types.SimpleNamespace(set_mode=lambda *_, **__: None, set_caption=lambda *_, **__: None, flip=lambda: None)
pygame_stub.font = types.SimpleNamespace(SysFont=lambda *_, **__: types.SimpleNamespace(render=lambda *_, **__: None))
pygame_stub.event = types.SimpleNamespace(get=lambda: [])
pygame_stub.mouse = types.SimpleNamespace(get_pos=lambda: (0, 0))
sys.modules.setdefault("pygame", pygame_stub)

requests_stub = types.SimpleNamespace(post=lambda *_, **__: types.SimpleNamespace(status_code=500, json=lambda: {}))
sys.modules.setdefault("requests", requests_stub)

from game import Human, Simulation


def _freeze_random(monkeypatch, value=0.0):
    """Force random.random to return a constant for deterministic logic."""
    monkeypatch.setattr(random, "random", lambda: value)


def _basic_sim():
    sim = Simulation()
    # Normalize world/items for deterministic tests
    sim.world = [[0 for _ in range(sim.world[0].__len__())] for _ in range(len(sim.world))]
    sim.items.clear()
    return sim


def test_spear_durability_depletes(monkeypatch):
    sim = _basic_sim()
    _freeze_random(monkeypatch)
    attacker, defender = sim.humans[0], sim.humans[1]
    attacker.x = attacker.y = 0
    defender.x = defender.y = 1
    defender.tribe_id = 1
    attacker.tools = ["SPEAR"]
    attacker.attack_power = 40
    attacker.spear_uses = 5

    for _ in range(5):
        sim.update()

    assert "SPEAR" not in attacker.tools
    assert attacker.inventory.count("🥢") >= 1


def test_fire_discovery_when_thinking(monkeypatch):
    sim = _basic_sim()
    _freeze_random(monkeypatch, 0.01)
    thinker = sim.humans[0]
    thinker.is_thinking = True
    thinker.inventory = ["🦴", "🦴"]
    thinker.x = thinker.y = 3

    sim.update()

    assert sim.items.get((3, 3)) == "🔥"


def test_cooks_corpse_near_fire(monkeypatch):
    sim = _basic_sim()
    _freeze_random(monkeypatch)
    cook = sim.humans[0]
    cook.inventory = ["Corpse"]
    cook.hunger = 50
    cook.x = cook.y = 4
    sim.items[(4, 4)] = "🔥"

    sim.update()

    assert "Corpse" not in cook.inventory
    assert "Cooked Meat" in cook.inventory
    assert cook.hunger == 0


def test_ranged_stone_throw_hits_enemy(monkeypatch):
    sim = _basic_sim()
    _freeze_random(monkeypatch)
    thrower, target = sim.humans[0], sim.humans[1]
    thrower.inventory = ["🦴"]
    thrower.x = thrower.y = 0
    target.x, target.y = 2, 0
    target.tribe_id = 1

    initial_hp = target.hp
    sim.update()

    assert target.hp < initial_hp
    assert "🦴" not in thrower.inventory


def test_basket_increases_apple_capacity(monkeypatch):
    sim = _basic_sim()
    _freeze_random(monkeypatch)
    carrier = sim.humans[0]
    carrier.inventory = ["Vine Basket"]

    apple_positions = [(0, 0), (1, 0), (2, 0)]
    for pos in apple_positions:
        sim.items[pos] = "🍎"
        carrier.x, carrier.y = pos
        sim.update()

    assert carrier.inventory.count("🍎") == len(apple_positions)

    # Without a basket, only one apple should be retained.
    sim2 = _basic_sim()
    _freeze_random(monkeypatch)
    for pos in [(0, 0), (1, 0)]:
        sim2.items[pos] = "🍎"
    gatherer = sim2.humans[0]
    gatherer.x = gatherer.y = 0
    sim2.update()
    gatherer.x, gatherer.y = 1, 0
    sim2.update()

    assert gatherer.inventory.count("🍎") <= 1


def test_builds_hut_with_three_sticks(monkeypatch):
    sim = _basic_sim()
    _freeze_random(monkeypatch)
    builder = sim.humans[0]
    builder.inventory = ["🥢", "🥢", "🥢"]
    builder.x = builder.y = 5

    sim.update()

    assert sim.world[5][5] == 4
    assert builder.inventory.count("🥢") == 0


def test_spear_durability_never_negative_property(monkeypatch):
    """Property: spear uses decrease to zero and never go negative."""
    sim = _basic_sim()
    _freeze_random(monkeypatch)
    user, foe = sim.humans[0], sim.humans[1]
    user.x = user.y = 0
    foe.x = foe.y = 1
    user.tools = ["SPEAR"]
    user.attack_power = 40
    user.spear_uses = 5

    for _ in range(10):
        sim.update()
        assert getattr(user, "spear_uses", 0) >= 0
        if "SPEAR" not in user.tools:
            break

    assert getattr(user, "spear_uses", 0) >= 0
