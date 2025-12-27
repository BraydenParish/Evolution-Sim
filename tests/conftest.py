"""Provide a lightweight pygame stub so logic can be unit tested headlessly."""
import sys
import types

class _DummyFont:
    def render(self, *args, **kwargs):
        return None

# Basic stub methods used by drawing functions.
def _noop(*args, **kwargs):
    return None

def _dummy_get_ticks():
    return 0

pygame_stub = types.SimpleNamespace(
    init=_noop,
    display=types.SimpleNamespace(set_mode=_noop, set_caption=_noop, flip=_noop),
    time=types.SimpleNamespace(get_ticks=_dummy_get_ticks),
    draw=types.SimpleNamespace(rect=_noop, circle=_noop, ellipse=_noop, line=_noop),
    font=types.SimpleNamespace(SysFont=lambda *args, **kwargs: _DummyFont()),
    event=types.SimpleNamespace(get=lambda: []),
    mouse=types.SimpleNamespace(get_pos=lambda: (0, 0)),
    key=types.SimpleNamespace(K_t=0),
    MOUSEBUTTONDOWN=1,
    KEYDOWN=2,
    QUIT=3,
)

sys.modules.setdefault("pygame", pygame_stub)

# Stub requests for environments without the dependency during headless tests.
requests_stub = types.SimpleNamespace(
    post=lambda *args, **kwargs: types.SimpleNamespace(status_code=400, json=lambda: {})
)

sys.modules.setdefault("requests", requests_stub)
