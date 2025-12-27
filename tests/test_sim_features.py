import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import math
import pygame
import game


def test_dreaming_creates_phobia_from_events():
    human = game.Human(0, 0, 0, tribe_id=0)
    human.day_log.extend([
        "Saw a friend get bitten by a long thing in the water",
        "Felt cold but survived"
    ])

    lesson = human.dream_and_learn()

    assert "water" in human.phobias
    assert "friend" in lesson.lower()
    assert human.last_lesson == lesson


def test_herbalism_cures_infection_and_records_knowledge():
    sim = game.Simulation()
    human = sim.humans[0]
    human.status_effects["infection"] = 3
    human.hp = 60
    human.inventory.append("🌿")

    sim.apply_status_effects(human)

    assert "infection" not in human.status_effects
    assert "medicine" in human.knowledge
    assert human.hp > 60


def test_cave_art_transfers_knowledge():
    sim = game.Simulation()
    human_artist = sim.humans[0]
    human_artist.knowledge.add("hunting")
    human_artist.inventory.append("🖌️")
    sim.world[human_artist.y][human_artist.x] = 4

    painting = sim.try_cave_art(human_artist)
    assert painting is not None

    learner = sim.humans[1]
    learner.x, learner.y = human_artist.x, human_artist.y
    sim.read_cave_art(learner)

    assert "hunting" in learner.knowledge


def test_dreaming_is_idempotent_without_new_events_property():
    human = game.Human(1, 0, 0, tribe_id=1)
    human.day_log.append("Attacked near water")

    first = human.dream_and_learn()
    phobia_count = len(human.phobias)
    second = human.dream_and_learn()

    assert len(human.phobias) == phobia_count
    assert second == human.last_lesson == first
