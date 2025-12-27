"""Camera utilities for isometric transforms and zoom/pan controls."""

from dataclasses import dataclass


def clamp(value: float, min_value: float, max_value: float) -> float:
    """Clamp value between bounds."""
    return max(min_value, min(value, max_value))


@dataclass
class Camera:
    offset_x: float = 0.0
    offset_y: float = 0.0
    scale: float = 1.0
    tile_width: float = 36.0
    tile_height: float = 18.0
    min_scale: float = 0.6
    max_scale: float = 2.4

    def world_to_screen(self, tile_x: float, tile_y: float) -> tuple[float, float]:
        """Convert tile coordinates to isometric screen coordinates."""
        half_w = self.tile_width / 2
        half_h = self.tile_height / 2
        screen_x = (tile_x - tile_y) * half_w * self.scale + self.offset_x
        screen_y = (tile_x + tile_y) * half_h * self.scale + self.offset_y
        return screen_x, screen_y

    def screen_to_world(self, screen_x: float, screen_y: float) -> tuple[int, int]:
        """Convert screen coordinates back to tile grid positions (rounded)."""
        half_w = self.tile_width / 2
        half_h = self.tile_height / 2
        x_part = ((screen_x - self.offset_x) / self.scale) / half_w
        y_part = ((screen_y - self.offset_y) / self.scale) / half_h
        tile_x = (x_part + y_part) / 2
        tile_y = (y_part - x_part) / 2
        return round(tile_x), round(tile_y)

    def pan(self, dx: float, dy: float) -> None:
        """Pan camera by adjusting offsets."""
        self.offset_x += dx
        self.offset_y += dy

    def zoom_by(self, factor: float, pivot: tuple[float, float] | None = None) -> None:
        """Zoom while keeping an optional screen-space pivot fixed."""
        new_scale = clamp(self.scale * factor, self.min_scale, self.max_scale)
        if pivot is None:
            self.scale = new_scale
            return

        world_point = self.screen_to_world(*pivot)
        self.scale = new_scale
        anchor_x, anchor_y = self.world_to_screen(*world_point)
        self.offset_x += pivot[0] - anchor_x
        self.offset_y += pivot[1] - anchor_y
