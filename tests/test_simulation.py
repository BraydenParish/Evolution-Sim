import random
import math
import game


def build_flat_world(sim, tile_type):
    for y in range(game.MAP_H):
        for x in range(game.MAP_W):
            sim.world[y][x] = tile_type
    sim.items.clear()


def test_day_night_cycle_light_and_state():
    sim = game.Simulation(rng=random.Random(0))
    build_flat_world(sim, 0)
    sim.time_minutes = (17 * 60) + 50  # 5:50 PM, just before dusk

    sim.update(600)  # advance 10 real seconds => 10 in-game minutes

    assert getattr(sim, "is_night", False), "Simulation should mark night after sunset"
    assert sim.light_level < 0.6, "Light level should darken at night"


def test_thirst_drives_agent_to_water():
    sim = game.Simulation(rng=random.Random(1))
    build_flat_world(sim, 0)
    # Place a water source to the east
    sim.world[0][2] = 3
    sim.items.clear()
    agent = sim.humans[0]
    agent.x, agent.y = 0, 0
    agent.thirst = 90

    for _ in range(20):
        sim.update(1)

    assert (agent.x, agent.y) == (2, 0), "Agent should move to water when thirsty"
    assert agent.thirst == 0, "Agent should drink and reset thirst near water"


def test_apple_regrowth_every_three_days():
    sim = game.Simulation(rng=random.Random(2))
    build_flat_world(sim, 1)
    harvest_spot = (0, 0)
    sim.items[harvest_spot] = "🍎"
    sim.items.pop(harvest_spot)

    sim.update(2.5 * 24 * 60)  # 2.5 in-game days
    assert harvest_spot not in sim.items, "Apple should not regrow before 3 days"

    sim.update(1 * 24 * 60)  # push past the 3-day mark
    assert sim.items.get(harvest_spot) == "🍎", "Apple should regrow after 3 in-game days"
