import sys
import types
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def pygame_stub():
    """Provide a lightweight pygame stub so logic can be imported in headless tests."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    stub = types.SimpleNamespace()
    stub.init = lambda: None
    stub.quit = lambda: None
    stub.time = types.SimpleNamespace(get_ticks=lambda: 0)
    stub.draw = types.SimpleNamespace(
        ellipse=lambda *args, **kwargs: None,
        rect=lambda *args, **kwargs: None,
        circle=lambda *args, **kwargs: None,
        line=lambda *args, **kwargs: None,
    )
    stub.display = types.SimpleNamespace(
        set_mode=lambda *args, **kwargs: None,
        set_caption=lambda *args, **kwargs: None,
        flip=lambda: None,
    )
    stub.font = types.SimpleNamespace(
        SysFont=lambda *args, **kwargs: types.SimpleNamespace(render=lambda *a, **k: None)
    )
    stub.event = types.SimpleNamespace(get=lambda: [])
    stub.mouse = types.SimpleNamespace(get_pos=lambda: (0, 0))
    stub.key = types.SimpleNamespace(K_t="K_t")
    stub.QUIT = "QUIT"
    stub.MOUSEBUTTONDOWN = "MOUSEBUTTONDOWN"
    stub.KEYDOWN = "KEYDOWN"

    sys.modules["pygame"] = stub
    sys.modules["requests"] = types.SimpleNamespace(post=lambda *a, **k: types.SimpleNamespace(status_code=500, json=lambda: {}))
    yield
    sys.modules.pop("game", None)
    sys.modules.pop("pygame", None)
    sys.modules.pop("requests", None)


def test_dialogue_state_records_encounter():
    import game

    sim = game.Simulation()
    human_a, human_b = sim.humans[0], sim.humans[3]
    human_a.x = human_b.x = 5
    human_a.y, human_b.y = 5, 6

    sim.handle_dialogue(human_a, human_b)

    assert sim.dialogues, "Dialogue history should record encounters"
    last_dialogue = sim.dialogues[-1]
    assert last_dialogue["participants"] == (human_a.name, human_b.name)
    assert "state" in last_dialogue and "proposal" in last_dialogue
    assert human_a.thought != "I seek food and the light."


def test_fog_of_war_monotonic_exploration_property():
    import game

    sim = game.Simulation()
    scout = sim.humans[0]
    starting_tiles = len(sim.explored[scout.tribe_id])

    sim.reveal_area(scout)
    sim.reveal_area(scout)

    assert len(sim.explored[scout.tribe_id]) >= starting_tiles


def test_specialized_roles_adjust_capabilities():
    import game

    sim = game.Simulation()
    hunter = sim.humans[0]
    gatherer = sim.humans[1]
    gatherer.hunger = 10

    sim.apply_role_effects(hunter)
    sim.apply_role_effects(gatherer)

    assert hunter.attack_power > 10
    assert gatherer.hunger < 10


def test_natural_disaster_impacts_health_and_logs_event():
    import game

    sim = game.Simulation()
    sim.apply_disaster("lightning", severity=15)

    assert sim.disaster_log and sim.disaster_log[-1]["kind"] == "lightning"
    assert any(h.hp < 100 for h in sim.humans)
