import math

from camera import Camera


def test_world_to_screen_round_trip_property():
    """Screen/world transforms should be roughly invertible for tile centers."""
    camera = Camera(offset_x=200, offset_y=120, scale=1.2, tile_width=36, tile_height=18)
    samples = [(0, 0), (1, 1), (5, 7), (10, 3), (17, 17)]
    for tx, ty in samples:
        sx, sy = camera.world_to_screen(tx, ty)
        round_trip = camera.screen_to_world(sx, sy)
        assert (tx, ty) == round_trip


def test_zoom_keeps_pivot_screen_position():
    """Zooming around a pivot keeps that world point anchored on screen within a tolerance."""
    camera = Camera(
        offset_x=100,
        offset_y=80,
        scale=1.0,
        tile_width=36,
        tile_height=18,
        max_scale=1.5,
    )
    pivot = (4, 6)
    before = camera.world_to_screen(*pivot)

    camera.zoom_by(1.6, pivot=before)

    after = camera.world_to_screen(*pivot)
    distance = math.hypot(after[0] - before[0], after[1] - before[1])
    assert distance < 1e-6
    assert camera.scale == camera.max_scale
