import xml.etree.ElementTree as ET
from typing import Any

from res.constants import ELAN_TIME_UNITS

_SUBDIVISION = "Symbolic_Subdivision"


def read_elan_tiers(file_path: str) -> list[dict[str, Any]]:
    """Reads the tiers of an ELAN .eaf file, as the reader of Praat TextGrids does: a
    list of dicts with a `name` (the tier id) and `labels`, a list of
    (begin, end, text) tuples with the times in seconds.

    Annotations that sit on the time line are read as they are. Annotations that refer
    to another annotation (the tiers ELAN calls symbolic) have no times of their own:
    an association takes those of its parent, and the annotations that subdivide a
    parent share its interval equally. Empty annotations are left out."""
    try:
        root = ET.parse(file_path).getroot()
    except ET.ParseError as err:
        raise ValueError(f"Cannot read {file_path} as an ELAN file: {err}") from err

    header = root.find("HEADER")
    unit = header.get("TIME_UNITS", "milliseconds") if header is not None else ""
    if unit not in ELAN_TIME_UNITS:
        raise ValueError(f"Cannot read the time units {unit!r} of {file_path}")
    scale = ELAN_TIME_UNITS[unit]

    slots = _slot_times(root.find("TIME_ORDER"))
    subdivided = {
        lt.get("LINGUISTIC_TYPE_ID"): lt.get("CONSTRAINTS") == _SUBDIVISION
        for lt in root.findall("LINGUISTIC_TYPE")
    }

    texts: dict[str, str] = {}
    spans: dict[str, tuple[float, float]] = {}
    parents: dict[str, str] = {}  # reference annotation -> the annotation it refers to
    subdividing: set[str] = set()
    tier_ids: list[tuple[str, list[str]]] = []
    for tier in root.findall("TIER"):
        ids = []
        for annotation in tier.findall("ANNOTATION/*"):
            ann_id = annotation.get("ANNOTATION_ID", "")
            value = annotation.find("ANNOTATION_VALUE")
            texts[ann_id] = (value.text or "") if value is not None else ""
            ids.append(ann_id)
            if annotation.tag == "ALIGNABLE_ANNOTATION":
                begin = slots.get(annotation.get("TIME_SLOT_REF1", ""))
                end = slots.get(annotation.get("TIME_SLOT_REF2", ""))
                if begin is None or end is None:
                    raise ValueError(f"{file_path} has an annotation without a time")
                spans[ann_id] = (begin * scale, end * scale)
            else:
                parents[ann_id] = annotation.get("ANNOTATION_REF", "")
                if subdivided.get(tier.get("LINGUISTIC_TYPE_REF", ""), False):
                    subdividing.add(ann_id)
        tier_ids.append((tier.get("TIER_ID", ""), ids))

    _place_subdivisions(spans, parents, subdividing)
    for ann_id in parents:
        spans[ann_id] = _span(ann_id, spans, parents)

    return [
        {
            "name": name,
            "labels": sorted(
                (*spans[ann_id], texts[ann_id])
                for ann_id in ids
                if texts[ann_id].strip() != ""
            ),
        }
        for name, ids in tier_ids
    ]


def _slot_times(time_order: ET.Element | None) -> dict[str, float]:
    """The time of each time slot; a slot that was never given one (ELAN leaves these
    for annotations whose edges have not been aligned) is put between its neighbours"""
    if time_order is None:
        return {}
    slots = [
        (slot.get("TIME_SLOT_ID", ""), slot.get("TIME_VALUE"))
        for slot in time_order.findall("TIME_SLOT")
    ]
    known = [(i, float(value)) for i, (_, value) in enumerate(slots) if value]
    times: dict[str, float] = {}
    for i, (slot_id, value) in enumerate(slots):
        if value:
            times[slot_id] = float(value)
            continue
        before = [k for k in known if k[0] < i]
        after = [k for k in known if k[0] > i]
        if not before or not after:
            continue  # nothing to go by
        (i0, t0), (i1, t1) = before[-1], after[0]
        times[slot_id] = t0 + (t1 - t0) * (i - i0) / (i1 - i0)
    return times


def _span(
    ann_id: str,
    spans: dict[str, tuple[float, float]],
    parents: dict[str, str],
) -> tuple[float, float]:
    """The times of an annotation that has none of its own: those of its parent"""
    seen: set[str] = set()
    while ann_id not in spans:
        if ann_id in seen or ann_id not in parents:
            raise ValueError("An annotation refers to an annotation that is not there")
        seen.add(ann_id)
        ann_id = parents[ann_id]
    return spans[ann_id]


def _place_subdivisions(
    spans: dict[str, tuple[float, float]],
    parents: dict[str, str],
    subdividing: set[str],
) -> None:
    """Give the annotations that subdivide a parent equal shares of its interval, in
    the order they come in the file"""
    children: dict[str, list[str]] = {}
    for ann_id, parent in parents.items():
        if ann_id in subdividing:
            children.setdefault(parent, []).append(ann_id)
    for parent, ids in children.items():
        begin, end = _span(parent, spans, parents)
        share = (end - begin) / len(ids)
        for i, ann_id in enumerate(ids):
            spans[ann_id] = (begin + i * share, begin + (i + 1) * share)
