from dataclasses import replace
from pathlib import Path
from types import MappingProxyType

import pytest
from pytestqt.qtbot import QtBot
from support.annotation_repository import SeedableAnnotationRepository
from support.job_manager import FakeJobManager
from support.view_models import make_annotation_view_model

from core.annotation.entity.annotation import (
    Annotation,
    AnnotationLabel,
    AnnotationType,
)
from res.constants import SAME_NODE_THRESHOLD
from ui.annotation.annotation_view_model import AnnotationViewModel
from ui.annotation.state.annotation_label_state import AnnotationLabelState
from ui.annotation.state.annotation_node_state import (
    AnnotationNodeExtentState,
    AnnotationNodeState,
)
from ui.annotation.state.annotation_selected_state import AnnotationSelectedState
from ui.annotation.state.annotation_state import AnnotationState
from ui.annotation.state.save_to_textgrid_state import SaveToTextGridAction
from ui.document.state.status_message_state import StatusMessageState

MOCK_ANNOTATION_NODES = MappingProxyType(
    {
        0: AnnotationNodeState(
            0, 0.0, extents=[AnnotationNodeExtentState(0)], is_visible=True
        ),
        1: AnnotationNodeState(
            1,
            1.0,
            extents=[AnnotationNodeExtentState(0, has_point_label=True)],
            is_visible=True,
        ),
        2: AnnotationNodeState(
            2, 2.0, extents=[AnnotationNodeExtentState(0)], is_visible=True
        ),
    }
)


def make_view_model(
    nodes: dict[int, AnnotationNodeState], start: float, end: float
) -> AnnotationViewModel:
    view_model = make_annotation_view_model()
    view_model.annotation_state = AnnotationState(nodes=nodes, types=[])
    view_model.window_state = (start, end)
    view_model.annotation_view_state = AnnotationState(nodes=nodes, types=[])
    return view_model


def test_change_node_state_moves_node_within_bounds(qtbot: QtBot):
    view_model = make_view_model(MOCK_ANNOTATION_NODES.copy(), start=0.0, end=2.0)

    with qtbot.waitSignal(view_model.state_changed, timeout=1000) as blocker:
        view_model.change_node_state(
            AnnotationNodeState(1, 1.0, [AnnotationNodeExtentState(0)]), 1.5
        )

    assert [node.x for node in view_model.annotation_state.nodes.values()] == [
        0.0,
        1.5,
        2.0,
    ]
    assert blocker.args[0] is view_model.annotation_view_state


def test_change_point_node_state_can_cross_other_nodes(qtbot: QtBot):
    view_model = make_view_model(MOCK_ANNOTATION_NODES.copy(), start=0.0, end=3.0)

    with qtbot.waitSignal(view_model.state_changed, timeout=1000) as blocker:
        view_model.change_node_state(
            AnnotationNodeState(
                1, 1.0, [AnnotationNodeExtentState(0, has_point_label=True)]
            ),
            2.5,
        )

    assert [node.x for node in view_model.annotation_state.nodes.values()] == [
        0.0,
        2.5,
        2.0,
    ]
    assert blocker.args[0] is view_model.annotation_view_state


def test_change_node_state_bounds_position_before_start(qtbot: QtBot):
    view_model = make_view_model(MOCK_ANNOTATION_NODES.copy(), start=-0.25, end=2.0)

    received = []
    view_model.subscribe(received.append)

    view_model.change_node_state(MOCK_ANNOTATION_NODES[0], -0.5)

    expected = MOCK_ANNOTATION_NODES.copy()
    expected[0] = replace(expected[0], x=-0.25)

    assert view_model.annotation_state.nodes == expected
    assert received == [view_model.annotation_view_state]


def test_change_node_state_bounds_position_after_end(qtbot: QtBot):
    view_model = make_view_model(MOCK_ANNOTATION_NODES.copy(), start=0.0, end=3.0)

    received = []
    view_model.subscribe(received.append)

    view_model.change_node_state(MOCK_ANNOTATION_NODES[2], 5.0)

    expected = MOCK_ANNOTATION_NODES.copy()
    expected[2] = replace(expected[2], x=3.0)

    assert view_model.annotation_state.nodes == expected
    assert received == [view_model.annotation_view_state]


def test_change_interval_node_state_does_not_cross_later_nodes(qtbot: QtBot):
    view_model = make_view_model(MOCK_ANNOTATION_NODES.copy(), start=0.0, end=3.0)

    view_model.change_node_state(
        AnnotationNodeState(0, 0.0, [AnnotationNodeExtentState(0)]), 1.5
    )

    assert [node.x for node in view_model.annotation_state.nodes.values()] == [
        1.0,
        1.0,
        2.0,
    ]


def test_change_interval_node_state_does_not_cross_earlier_nodes(qtbot: QtBot):
    view_model = make_view_model(MOCK_ANNOTATION_NODES.copy(), start=0.0, end=3.0)

    view_model.change_node_state(
        AnnotationNodeState(2, 2.0, [AnnotationNodeExtentState(0)]), 0.5
    )

    assert [node.x for node in view_model.annotation_state.nodes.values()] == [
        0.0,
        1.0,
        1.0,
    ]


def test_set_annotation_state_replaces_state_and_emits(qtbot: QtBot):
    view_model = make_view_model({0: 0.0}, start=0.0, end=1.0)
    nodes = {0: 0.0, 1: 1.0}
    annotation = Annotation(nodes=nodes, types=[])

    with qtbot.waitSignal(view_model.state_changed, timeout=1000) as blocker:
        view_model.set_annotation_state(annotation)

    new_state = AnnotationState(
        nodes={idx: AnnotationNodeState(idx, x) for idx, x in nodes.items()}
    )

    assert view_model.annotation_state == new_state
    assert blocker.args[0] == view_model.annotation_view_state


TEXTGRID_FIXTURE = """File type = "ooTextFile"
Object class = "TextGrid"
xmin = 0
xmax = 1.0
tiers? <exists>
size = 1
item []:
    item [1]:
        class = "IntervalTier"
        name = "word"
        xmin = 0
        xmax = 1.0
        intervals: size = 2
        intervals [1]:
            xmin = 0
            xmax = 0.5
            text = "hello"
        intervals [2]:
            xmin = 0.5
            xmax = 1.0
            text = "world"
"""


def run_parse_job(view_model: AnnotationViewModel):
    """Runs the recorded parse job synchronously, as the worker thread would"""
    job = view_model.job_managers["parse_textgrid"].jobs[0]
    try:
        result = next(job.task)
    except Exception as err:  # noqa: BLE001
        job.on_error(err)
    else:
        job.on_success(result)


def test_parse_textgrid_loads_annotation_state(
    tmp_path: Path, fake_job_manager: type[FakeJobManager]
):
    view_model = make_view_model({}, 0.0, 1.0)
    textgrid = tmp_path / "sample.TextGrid"
    textgrid.write_text(TEXTGRID_FIXTURE)

    view_model.parse_textgrid(str(textgrid), "sample")
    run_parse_job(view_model)

    assert {node.x for node in view_model.annotation_state.nodes.values()} == {
        0.0,
        0.5,
        1.0,
    }
    assert [t.type for t in view_model.annotation_state.types] == ["word"]
    assert [label.label for label in view_model.annotation_state.types[0].labels] == [
        "hello",
        "world",
    ]


POINT_TIER_TEXTGRID = """File type = "ooTextFile"
Object class = "TextGrid"
xmin = 0
xmax = 1.0
tiers? <exists>
size = 1
item []:
    item [1]:
        class = "TextTier"
        name = "mark"
        xmin = 0
        xmax = 1.0
        points: size = 1
        points [1]:
            number = 0.5
            mark = "click"
"""


BROKEN_TIER_TEXTGRID = """File type = "ooTextFile"
Object class = "TextGrid"
xmin = 0
xmax = 1.0
tiers? <exists>
size = 1
item []:
    item [1]:
        class = "UnknownTier"
        name = "word"
        xmin = 0
        xmax = 1.0
"""


def test_parse_textgrid_shows_status_message_on_invalid_tier_type(
    tmp_path: Path, fake_job_manager: type[FakeJobManager]
):
    view_model = make_view_model({}, 0.0, 1.0)
    textgrid = tmp_path / "broken.TextGrid"
    textgrid.write_text(BROKEN_TIER_TEXTGRID)
    received = []
    view_model.subscribe(received.append)

    view_model.parse_textgrid(str(textgrid), "sample")
    run_parse_job(view_model)

    status_messages = [s for s in received if isinstance(s, StatusMessageState)]
    assert len(status_messages) == 1
    assert "Error parsing TextGrid" in status_messages[0].message
    assert view_model.annotation_state.nodes == {}
    assert view_model.annotation_state.types == []


def test_select_label_emits_selected_state_from_node_positions(qtbot: QtBot):
    view_model = make_view_model(MOCK_ANNOTATION_NODES.copy(), start=0.0, end=2.0)

    with qtbot.waitSignal(view_model.state_changed, timeout=1000) as blocker:
        view_model.select_label(AnnotationLabelState(s_node=0, e_node=2, label="x"))

    assert blocker.args[0] == AnnotationSelectedState(0.0, 2.0)


def test_select_label_with_missing_node_raises(qtbot: QtBot):
    view_model = make_view_model(MOCK_ANNOTATION_NODES.copy(), start=0.0, end=2.0)

    with pytest.raises(ValueError):
        view_model.select_label(AnnotationLabelState(s_node=0, e_node=99, label="x"))


def make_annotated_view_model(
    nodes: dict[int, float],
    tiers: list[list[tuple[int, int, str]]],
    start: float = 0.0,
    end: float = 3.0,
) -> AnnotationViewModel:
    repository = SeedableAnnotationRepository()
    view_model = make_annotation_view_model(repository=repository)
    view_model.window_state = (start, end)
    view_model.set_annotation_state(
        repository.seed(
            Annotation(
                nodes=nodes,
                types=[
                    AnnotationType(
                        f"tier{idx}",
                        [
                            AnnotationLabel(*label, id=id)
                            for id, label in enumerate(labels)
                        ],
                    )
                    for idx, labels in enumerate(tiers)
                ],
            )
        )
    )
    return view_model


def label_spans(view_model: AnnotationViewModel, tier: int) -> list[tuple]:
    return sorted(
        (label.s_node, label.e_node, label.label)
        for label in view_model.annotation_state.types[tier].labels
    )


def test_delete_node_missing_node_raises(qtbot: QtBot):
    view_model = make_annotated_view_model({0: 0.0, 1: 1.0}, [[(0, 1, "a")]], end=1.0)

    with pytest.raises(ValueError):
        view_model.delete_node(99)


def test_delete_node_merges_adjacent_interval_labels(qtbot: QtBot):
    view_model = make_annotated_view_model(
        {0: 0.0, 1: 1.0, 2: 2.0}, [[(0, 1, "a"), (1, 2, "b")]]
    )
    first_label_id = view_model.annotation_state.types[0].labels[0].id

    with qtbot.waitSignal(view_model.state_changed, timeout=1000) as blocker:
        view_model.delete_node(1)

    labels = view_model.annotation_state.types[0].labels
    assert len(labels) == 1
    assert labels[0].id == first_label_id
    assert (labels[0].s_node, labels[0].e_node, labels[0].label) == (0, 2, "ab")
    assert 1 not in view_model.annotation_view_state.nodes
    assert blocker.args[0] is view_model.annotation_view_state


def test_delete_node_does_not_mutate_previous_state(qtbot: QtBot):
    view_model = make_annotated_view_model(
        {0: 0.0, 1: 1.0, 2: 2.0}, [[(0, 1, "a"), (1, 2, "b")]]
    )
    previous = view_model.annotation_state
    previous_labels = list(previous.types[0].labels)

    view_model.delete_node(1)

    assert previous.types[0].labels == previous_labels
    assert 1 in previous.nodes


@pytest.mark.parametrize("node", [0, 2])
def test_delete_end_node_with_attached_label_shows_status_message(
    qtbot: QtBot, node: int
):
    view_model = make_annotated_view_model(
        {0: 0.0, 1: 1.0, 2: 2.0}, [[(0, 1, "a"), (1, 2, "b")]]
    )
    received = []
    view_model.subscribe(received.append)

    view_model.delete_node(node)

    assert received == [StatusMessageState("Cannot delete node due to attached labels")]
    assert label_spans(view_model, 0) == [(0, 1, "a"), (1, 2, "b")]


def test_create_label_from_selection_adds_label_and_emits(qtbot: QtBot):
    view_model = make_annotated_view_model({0: 0.0, 1: 3.0}, [[], [(0, 1, "a")]])

    with qtbot.waitSignal(view_model.state_changed, timeout=1000) as blocker:
        view_model.create_label_from_selection(0, 1.0, 2.0, SAME_NODE_THRESHOLD)

    nodes = view_model.annotation_state.nodes
    labels = view_model.annotation_state.types[0].labels
    assert len(labels) == 1
    assert (nodes[labels[0].s_node].x, nodes[labels[0].e_node].x) == (1.0, 2.0)
    assert labels[0].label == ""
    assert label_spans(view_model, 1) == [(0, 1, "a")]
    assert blocker.args[0] is view_model.annotation_view_state


def test_create_label_from_selection_uses_same_node_threshold(qtbot: QtBot):
    view_model = make_annotated_view_model({0: 0.0, 1: 1.0, 2: 2.0, 3: 3.0}, [[]])

    view_model.create_label_from_selection(0, 1.1, 1.9, 0.2)

    assert list(view_model.annotation_state.nodes) == [0, 1, 2, 3]
    assert label_spans(view_model, 0) == [(1, 2, "")]


def test_create_label_from_too_short_selection_shows_status_message(qtbot: QtBot):
    view_model = make_annotated_view_model({0: 0.0, 1: 1.0, 2: 3.0}, [[(0, 1, "a")]])
    previous = view_model.annotation_state
    received = []
    view_model.subscribe(received.append)

    view_model.create_label_from_selection(0, 1.05, 1.2, 0.35)

    assert len(received) == 1
    assert isinstance(received[0], StatusMessageState)
    assert view_model.annotation_state is previous


def make_persisting_view_model() -> tuple[
    AnnotationViewModel, SeedableAnnotationRepository
]:
    repository = SeedableAnnotationRepository()
    view_model = make_annotation_view_model(repository=repository)
    view_model.window_state = (0.0, 2.0)
    view_model.set_annotation_state(
        repository.seed(
            Annotation(
                nodes={0: 0.0, 1: 1.0, 2: 2.0},
                types=[
                    AnnotationType(
                        "tier0",
                        [
                            AnnotationLabel(0, 1, "a", id=0),
                            AnnotationLabel(1, 2, "b", id=1),
                        ],
                    )
                ],
            )
        )
    )
    return view_model, repository


def test_change_label_text_updates_state_and_repository():
    view_model, repository = make_persisting_view_model()
    label = view_model.annotation_state.types[0].labels[1]

    view_model.change_label_text(label, "changed")

    assert label_spans(view_model, 0) == [(0, 1, "a"), (1, 2, "changed")]
    stored = repository.get_annotation_by_id(0)
    assert [l.label for l in stored.types[0].labels] == ["a", "changed"]


def test_change_node_state_persists_node_position(qtbot: QtBot):
    view_model, repository = make_persisting_view_model()
    node = view_model.annotation_state.nodes[1]

    view_model.change_node_state(node, 1.5)

    assert repository.get_annotation_by_id(0).nodes[1] == 1.5


def test_parse_textgrid_sets_loading_state_until_job_finishes(
    tmp_path: Path, fake_job_manager: type[FakeJobManager]
):
    view_model = make_view_model({}, 0.0, 1.0)
    textgrid = tmp_path / "sample.TextGrid"
    textgrid.write_text(TEXTGRID_FIXTURE)

    view_model.parse_textgrid(str(textgrid), "sample")
    assert view_model.loading_state.is_loading is True

    run_parse_job(view_model)
    assert view_model.loading_state.is_loading is False


def test_trigger_write_textgrid_dialog_emits_save_action(qtbot: QtBot):
    view_model = make_view_model({}, 0.0, 1.0)

    with qtbot.waitSignal(view_model.state_changed, timeout=1000) as blocker:
        view_model.trigger_write_textgrid_dialog()

    assert isinstance(blocker.args[0], SaveToTextGridAction)


def test_opens_empty_for_a_stem_without_annotation():
    repository = SeedableAnnotationRepository()
    repository.create_annotation("sample")

    view_model = make_annotation_view_model(filestem="sample", repository=repository)

    state = view_model.annotation_state
    assert state.id is not None  # bound to the registered database row
    assert state.nodes == {}
    assert state.types == []


def test_has_annotation_is_false_for_empty_annotation():
    assert make_annotation_view_model().has_annotation() is False


def test_has_annotation_is_true_for_annotation_loaded_from_repository():
    repository = SeedableAnnotationRepository()
    id = repository.create_annotation("sample")
    repository.create_types(id, [AnnotationType("word", [])])

    view_model = make_annotation_view_model(filestem="sample", repository=repository)

    assert view_model.has_annotation() is True


def test_parse_textgrid_overwrites_loaded_annotation_when_requested(
    tmp_path: Path, fake_job_manager: type[FakeJobManager]
):
    repository = SeedableAnnotationRepository()
    id = repository.create_annotation("sample")
    repository.create_types(id, [AnnotationType("old", [])])
    view_model = make_annotation_view_model(filestem="sample", repository=repository)
    textgrid = tmp_path / "sample.TextGrid"
    textgrid.write_text(TEXTGRID_FIXTURE)

    view_model.parse_textgrid(str(textgrid), "sample", overwrite=True)
    run_parse_job(view_model)

    assert [t.type for t in view_model.annotation_state.types] == ["word"]
