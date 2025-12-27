"""Core logic primitives for the evolution simulation.

This module keeps the heavyweight, simulation-only logic isolated from the
pygame front-end so it can be unit tested without a display.
"""

from __future__ import annotations

import json
import math
import os
import random
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

# Tile identifiers
TILE_GRASS = 0
TILE_TREE = 1
TILE_STONE = 2
TILE_WATER = 3


@dataclass
class ChunkManager:
    """Lazily generates tiles in chunk-sized grids to support an infinite map."""

    chunk_size: int = 32
    tile_weights: Tuple[int, int, int, int] = (60, 15, 10, 15)
    rng: random.Random = field(default_factory=random.Random)
    chunks: Dict[Tuple[int, int], List[List[int]]] = field(default_factory=dict)

    def _chunk_coords(self, x: int, y: int) -> Tuple[int, int]:
        return (math.floor(x / self.chunk_size), math.floor(y / self.chunk_size))

    def _ensure_chunk(self, cx: int, cy: int) -> List[List[int]]:
        key = (cx, cy)
        if key not in self.chunks:
            tiles = [
                [self.rng.choices([TILE_GRASS, TILE_TREE, TILE_STONE, TILE_WATER], weights=self.tile_weights)[0]
                 for _ in range(self.chunk_size)]
                for _ in range(self.chunk_size)
            ]
            self.chunks[key] = tiles
        return self.chunks[key]

    def get_tile(self, x: int, y: int) -> int:
        cx, cy = self._chunk_coords(x, y)
        chunk = self._ensure_chunk(cx, cy)
        lx = x - cx * self.chunk_size
        ly = y - cy * self.chunk_size
        return chunk[ly][lx]


@dataclass
class KnowledgeBase:
    """Tracks knowledge tiers for a tribe."""

    tier: int = 1  # Tier 1: Stone Tools

    def evaluate_progress(self, resource_events: Dict[str, bool]):
        # Tier 2: Fire & Clothing
        if self.tier < 2 and resource_events.get("stone_tools"):
            self.tier = 2
        # Tier 3: Pottery & Agriculture
        if self.tier < 3 and resource_events.get("fire") and resource_events.get("clothing"):
            self.tier = 3
        # Tier 4: Bronze & Permanent Settlements
        if self.tier < 4 and resource_events.get("pottery") and resource_events.get("agriculture"):
            self.tier = 4


@dataclass
class MemoryChronicle:
    """JSON-backed event history shared across sessions."""

    path: str | os.PathLike[str]

    def __post_init__(self):
        if not os.path.exists(self.path):
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump([], f)

    def log_event(self, year: int, description: str):
        with open(self.path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data.append({"year": year, "event": description})
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)


@dataclass
class BuildOrder:
    type: str
    wood_cost: int
    stone_cost: int


class BuildingPlanner:
    """Decides what to construct when resources allow."""

    def choose_build(self, resources: Dict[str, int], known_tier: int) -> BuildOrder:
        if resources.get("wood", 0) < 10 or resources.get("stone", 0) < 5:
            raise ValueError("Insufficient resources for construction")

        choice_pool = ["Hut"]
        if known_tier >= 2:
            choice_pool.append("Watchtower")
        if known_tier >= 3:
            choice_pool.append("Granary")
        selection = random.choice(choice_pool)
        resources["wood"] -= 10
        resources["stone"] -= 5
        return BuildOrder(type=selection, wood_cost=10, stone_cost=5)


@dataclass
class TribeOrder:
    tribe_id: int
    chief_id: int
    directive: str


class TribeCoordinator:
    """Maintains chiefs and propagates their directives to tribe members."""

    def __init__(self):
        self.chiefs: Dict[int, int] = {}
        self.orders: Dict[int, TribeOrder] = {}

    def designate_chiefs(self, humans: List[Dict]) -> Dict[int, int]:
        tribe_members: Dict[int, List[int]] = {}
        for h in humans:
            tribe_members.setdefault(h["tribe_id"], []).append(h["id"])
        for tribe, ids in tribe_members.items():
            self.chiefs[tribe] = min(ids)
        return self.chiefs

    def set_order(self, tribe_id: int, chief_id: int, directive: str) -> TribeOrder:
        order = TribeOrder(tribe_id=tribe_id, chief_id=chief_id, directive=directive)
        self.orders[tribe_id] = order
        return order

    def propagate_order(self, tribe_id: int, humans: List[Dict]) -> Dict[int, TribeOrder]:
        if tribe_id not in self.orders:
            return {}
        order = self.orders[tribe_id]
        result: Dict[int, Dict[str, object]] = {}
        for h in humans:
            if h["tribe_id"] == tribe_id:
                result[h["id"]] = {"directive": order.directive, "chief_id": order.chief_id}
        return result
