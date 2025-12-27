import game

def setup_grass_world():
    sim = game.Simulation()
    # Ensure deterministic, build-friendly terrain for tests.
    sim.world = [[0 for _ in range(game.MAP_W)] for _ in range(game.MAP_H)]
    sim.items.clear()
    return sim

def test_builds_hut_when_requirements_met():
    sim = setup_grass_world()
    human = sim.humans[0]
    human.x = human.y = 5
    # Provide required resources for building.
    human.inventory = ["🦴", "🥢"]

    built = sim.attempt_build_hut(human)

    assert built is True
    assert (5, 5) in sim.huts
    assert "🦴" not in human.inventory
    assert "🥢" not in human.inventory


def test_building_is_idempotent_on_existing_hut():
    """Property: attempting to build twice on the same tile does not duplicate huts."""
    sim = setup_grass_world()
    human = sim.humans[0]
    human.x = human.y = 3
    human.inventory = ["🦴", "🥢", "🦴", "🥢"]

    first = sim.attempt_build_hut(human)
    second = sim.attempt_build_hut(human)

    assert first is True
    assert second is False
    assert list(sim.huts.keys()).count((3, 3)) == 1
    # Ensure extra materials remain if build is rejected after hut exists.
    assert human.inventory.count("🦴") == 1
    assert human.inventory.count("🥢") == 1
