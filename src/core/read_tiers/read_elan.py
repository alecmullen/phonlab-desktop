import xml.etree.ElementTree as ET
from typing import Any

_SUBDIVISION = "Symbolic_Subdivision"
_SECONDS_PER_TIME_VALUE = 0.001  # ELAN times are milliseconds, whatever the header says


def read_elan_tiers(file_path: str) -> list[dict[str, Any]]:
    """Reads the tiers of an ELAN .eaf file, as the reader of Praat TextGrids does: a
    list of dicts with a `name` (the tier id) and `labels`, a list of
    (begin, end, text) tuples with the times in seconds.

    Annotations that sit on the time line (top-level, time subdivision and included-in
    tiers) are read as they are. Annotations that refer to another annotation have no
    times of their own: an association takes those of its parent, and the annotations
    that subdivide a parent share its interval equally, in the order ELAN chains them.
    Empty annotations are left out. A tier that names a participant has it as its
    `talker`."""
    try:
        root = ET.parse(file_path).getroot()
    except ET.ParseError as err:
        raise ValueError(f"Cannot read {file_path} as an ELAN file: {err}") from err

    slots = _slot_times(root.find("TIME_ORDER"))
    subdivided = {
        lt.get("LINGUISTIC_TYPE_ID"): lt.get("CONSTRAINTS") == _SUBDIVISION
        for lt in root.findall("LINGUISTIC_TYPE")
    }

    texts: dict[str, str] = {}
    spans: dict[str, tuple[float, float]] = {}
    refs: dict[str, _Ref] = {}  # reference annotation -> what it refers to
    tiers: list[tuple[str, list[str]]] = []
    talkers: dict[str, str] = {}  # tier -> the participant it names, if it does
    for tier in root.findall("TIER"):
        subdivides = subdivided.get(tier.get("LINGUISTIC_TYPE_REF", ""), False)
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
                    raise ValueError(
                        f"Annotation {ann_id} of {file_path} has no time: ELAN did "
                        "not give it times that can be worked out"
                    )
                spans[ann_id] = (begin, end)
            else:
                refs[ann_id] = _Ref(
                    annotation.get("ANNOTATION_REF", ""),
                    annotation.get("PREVIOUS_ANNOTATION"),
                    subdivides,
                )
        tiers.append((tier.get("TIER_ID", ""), ids))
        talkers[tier.get("TIER_ID", "")] = tier.get("PARTICIPANT", "").strip()

    _place_references(spans, refs)

    return [
        {
            "name": name,
            "labels": sorted(
                (*spans[ann_id], texts[ann_id])
                for ann_id in ids
                if texts[ann_id].strip() != ""
            ),
            **({"talker": talkers[name]} if talkers[name] else {}),
        }
        for name, ids in tiers
    ]


class _Ref:
    """An annotation that refers to a parent annotation instead of having times"""

    def __init__(self, parent: str, previous: str | None, subdivides: bool):
        self.parent = parent
        self.previous = previous
        self.subdivides = subdivides


def _slot_times(time_order: ET.Element | None) -> dict[str, float]:
    """The time of each time slot, in seconds. A slot that was never given a time (ELAN
    leaves these in the sequence of partly aligned annotations) is put between the
    slots around it, as the slots are listed in time order"""
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
            times[slot_id] = float(value) * _SECONDS_PER_TIME_VALUE
            continue
        before = [k for k in known if k[0] < i]
        after = [k for k in known if k[0] > i]
        if before and after:
            (i0, t0), (i1, t1) = before[-1], after[0]
            times[slot_id] = (
                t0 + (t1 - t0) * (i - i0) / (i1 - i0)
            ) * _SECONDS_PER_TIME_VALUE
    return times


def _place_references(
    spans: dict[str, tuple[float, float]], refs: dict[str, _Ref]
) -> None:
    """Give the times of its parent, or its share of them, to every annotation that
    refers to another. A parent may itself be a reference, so each is worked out
    after the one it refers to."""
    children: dict[str, list[str]] = {}
    for ann_id, ref in refs.items():
        if ref.subdivides:
            children.setdefault(ref.parent, []).append(ann_id)

    def place(ann_id: str, working: frozenset[str] = frozenset()) -> None:
        if ann_id in spans:
            return
        ref = refs.get(ann_id)
        if ref is None or ann_id in working:
            raise ValueError("An annotation refers to one that is not there")
        place(ref.parent, working | {ann_id})
        begin, end = spans[ref.parent]
        if not ref.subdivides:
            spans[ann_id] = (begin, end)
            return
        siblings = _in_chain_order(children[ref.parent], refs)
        share = (end - begin) / len(siblings)
        for i, sibling in enumerate(siblings):
            spans[sibling] = (begin + i * share, begin + (i + 1) * share)

    for ann_id in refs:
        place(ann_id)


def _in_chain_order(ids: list[str], refs: dict[str, _Ref]) -> list[str]:
    """Annotations that subdivide one parent in the order ELAN chains them, each
    naming the one before it; the order of the file if the chain is not complete"""
    following = {refs[i].previous: i for i in ids if refs[i].previous in ids}
    firsts = [i for i in ids if refs[i].previous not in ids]
    if len(firsts) != 1:
        return ids
    chain = [firsts[0]]
    while chain[-1] in following and len(chain) <= len(ids):
        chain.append(following[chain[-1]])
    return chain if len(chain) == len(ids) else ids
