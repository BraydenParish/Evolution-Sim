import json
import os
import random

import pytest

from simulation_core import (
    BuildingPlanner,
    ChunkManager,
    KnowledgeBase,
    MemoryChronicle,
    TribeCoordinator,
)


def test_chunk_manager_idempotent_property():
    rng = random.Random(42)
    manager = ChunkManager(rng=rng)
    coords = [(x, y) for x in range(-2, 3) for y in range(-2, 3)]
    first_pass = {c: manager.get_tile(*c) for c in coords}
    # Property: repeated fetches yield the same tile type
    for coord, initial in first_pass.items():
        for _ in range(3):
            assert manager.get_tile(*coord) == initial


def test_knowledge_progression_triggers_tiers():
    kb = KnowledgeBase()
    kb.evaluate_progress(resource_events={"stone_tools": True})
    assert kb.tier == 2
    kb.evaluate_progress(resource_events={"fire": True, "clothing": True})
    assert kb.tier == 3
    kb.evaluate_progress(resource_events={"pottery": True, "agriculture": True})
    assert kb.tier == 4


def test_building_planner_requires_resources():
    planner = BuildingPlanner()
    resources = {"wood": 12, "stone": 6}
    build = planner.choose_build(resources, known_tier=2)
    assert build.type in {"Hut", "Granary", "Watchtower"}
    assert resources["wood"] <= 2  # resources consumed
    assert resources["stone"] <= 1


def test_memory_chronicle_appends(tmp_path):
    chron_path = tmp_path / "chronicle.json"
    chronicle = MemoryChronicle(path=chron_path)
    chronicle.log_event(year=10, description="Moon Tribe attacked")
    chronicle.log_event(year=11, description="Fire rediscovered")
    with open(chron_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data[-1]["year"] == 11
    assert "Fire rediscovered" in data[-1]["event"]


def test_chief_orders_propagate_to_tribe():
    coordinator = TribeCoordinator()
    humans = [
        {"id": 0, "tribe_id": 1},
        {"id": 1, "tribe_id": 1},
        {"id": 2, "tribe_id": 2},
    ]
    coordinator.designate_chiefs(humans)
    order = coordinator.set_order(tribe_id=1, chief_id=0, directive="Gather wood north of camp")
    assert coordinator.orders[1] == order
    propagated = coordinator.propagate_order(tribe_id=1, humans=humans)
    assert propagated[1]["directive"] == order.directive
    assert propagated[0]["directive"] == order.directive
    assert 2 not in propagated
