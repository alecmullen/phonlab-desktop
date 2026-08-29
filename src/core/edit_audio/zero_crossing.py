import numpy as np


def nearest_zero_crossing(x: np.ndarray, index: int, search_radius: int) -> int:
    """Return the sample index within `search_radius` of `index` where the
    signal crosses (or touches) zero, closest to `index`. `index` is an
    INCLUSIVE sample position (use `nearest_zero_crossing_boundary` below
    for an exclusive/between-samples position, e.g. a slice end or an
    insertion point). Returns `index` unchanged if no crossing is found in
    range (e.g. DC-offset audio, a silent/constant-sign stretch, or
    `index` itself out of bounds) — never silently clamped."""
    if len(x) == 0:
        return index

    clamped = min(max(index, 0), len(x) - 1)
    lo = max(0, clamped - search_radius)
    hi = min(len(x) - 1, clamped + search_radius)
    if hi <= lo:
        return index

    window = x[lo : hi + 1].astype(np.float64)
    signs = np.sign(window)
    signs[signs == 0] = 1  # an exact-zero sample still forms a crossing with a real sign change next to it
    crossing_offsets = np.where(np.diff(signs) != 0)[0]
    if len(crossing_offsets) == 0:
        return index  # no crossing nearby; leave the original position untouched

    target_offset = clamped - lo
    best_offset = crossing_offsets[np.argmin(np.abs(crossing_offsets - target_offset))]
    i0, i1 = lo + best_offset, lo + best_offset + 1
    return i0 if abs(x[i0]) <= abs(x[i1]) else i1


def nearest_zero_crossing_boundary(x: np.ndarray, boundary: int, search_radius: int) -> int:
    """Like `nearest_zero_crossing`, but for an EXCLUSIVE/between-samples
    position — a slice end (`x[start:boundary]`) or an insertion point
    (`np.concatenate([x[:boundary], ...])`) — which may legitimately equal
    `len(x)` (the true end of the buffer). Snapping that naively via
    `nearest_zero_crossing` would clamp it to `len(x) - 1` first and could
    never return `len(x)` again, silently shrinking a full-length range by
    one sample even when no real crossing is nearby. Snapping the last
    INCLUDED sample instead and converting back to exclusive avoids that."""
    return nearest_zero_crossing(x, boundary - 1, search_radius) + 1
