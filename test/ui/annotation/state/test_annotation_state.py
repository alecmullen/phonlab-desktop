from core.annotation.entity.annotation import (
    Annotation,
    AnnotationLabel,
    AnnotationType,
)
from ui.annotation.state.annotation_node_state import AnnotationNodeState
from ui.annotation.state.annotation_state import (
    AnnotationLabelState,
    AnnotationState,
    AnnotationTypeState,
    displayed_types,
    to_annotation,
    to_annotation_state,
    update_annotation_state_from_window,
)


def test_to_annotation_state_converts_nodes_and_types():
    annotation = Annotation(
        nodes={0: 0.0, 1: 0.5, 2: 1.0},
        types=[
            AnnotationType(
                type="word",
                labels=[
                    AnnotationLabel(0, 1, "hello", id=1),
                    AnnotationLabel(1, 2, "world", id=2),
                ],
            )
        ],
    )

    state = to_annotation_state(annotation)

    assert state.nodes == {
        0: AnnotationNodeState(0, 0.0),
        1: AnnotationNodeState(1, 0.5),
        2: AnnotationNodeState(2, 1.0),
    }
    assert state.types == [
        AnnotationTypeState(
            "word",
            [
                AnnotationLabelState(1, 0, 1, "hello"),
                AnnotationLabelState(2, 1, 2, "world"),
            ],
        )
    ]


def test_to_annotation_state_converts_multiple_types():
    annotation = Annotation(
        nodes={0: 0.0, 1: 1.0},
        types=[
            AnnotationType("word", [AnnotationLabel(0, 1, "hi", id=1)]),
            AnnotationType("phone", []),
        ],
    )

    state = to_annotation_state(annotation)

    assert [t.type for t in state.types] == ["word", "phone"]
    assert state.types[1].labels == []


def test_to_annotation_state_handles_empty_annotation():
    state = to_annotation_state(Annotation())

    assert state.nodes == {}
    assert state.types == []


def test_to_annotation_converts_nodes_and_types():
    state = AnnotationState(
        nodes={
            0: AnnotationNodeState(0, 0.0, is_visible=True),
            2: AnnotationNodeState(2, 1.0),
        },
        types=[
            AnnotationTypeState(
                "word",
                [AnnotationLabelState(4, 0, 2, "hi", is_visible=True, pos=(0.5, 0.5))],
            ),
            AnnotationTypeState("phone", []),
        ],
    )

    annotation = to_annotation(state)

    assert annotation == Annotation(
        nodes={0: 0.0, 2: 1.0},
        types=[
            AnnotationType("word", [AnnotationLabel(0, 2, "hi", id=4)]),
            AnnotationType("phone", []),
        ],
    )


def test_to_annotation_round_trips_through_annotation_state():
    annotation = Annotation(
        nodes={3: 0.0, 1: 0.5, 2: 1.0},
        types=[
            AnnotationType(
                "word",
                [AnnotationLabel(3, 1, "a", id=2), AnnotationLabel(1, 2, "b", id=5)],
            ),
            AnnotationType("mark", [AnnotationLabel(1, 1, "x", id=0)]),
        ],
    )

    assert to_annotation(to_annotation_state(annotation)) == annotation


def _two_tier_state() -> AnnotationState:
    return AnnotationState(
        nodes={0: AnnotationNodeState(0, 0.0), 1: AnnotationNodeState(1, 1.0)},
        types=[
            AnnotationTypeState("word", [AnnotationLabelState(1, 0, 1, "hi")], id=10),
            AnnotationTypeState("phone", [AnnotationLabelState(2, 0, 1, "h")], id=11),
        ],
    )


def test_update_from_window_shows_every_type_by_default():
    state = update_annotation_state_from_window(_two_tier_state(), 0.0, 1.0)

    assert [t.type for t in state.types] == ["word", "phone"]


def test_update_from_window_leaves_out_hidden_types():
    state = update_annotation_state_from_window(
        _two_tier_state(), 0.0, 1.0, hidden_tiers={"word"}
    )

    assert [t.type for t in state.types] == ["phone"]
    assert state.types[0].id == 11


def test_update_from_window_renumbers_tiers_of_shown_types():
    state = update_annotation_state_from_window(
        _two_tier_state(), 0.0, 1.0, hidden_tiers={"word"}
    )

    assert state.types[0].labels[0].pos[1] == 0.5
    assert all(
        extent.tier == 0 for node in state.nodes.values() for extent in node.extents
    )


def test_update_from_window_orders_types_by_tier_order():
    state = update_annotation_state_from_window(
        _two_tier_state(), 0.0, 1.0, tier_order=["phone", "word"]
    )

    assert [t.type for t in state.types] == ["phone", "word"]


def test_update_from_window_puts_unlisted_types_after_ordered_ones_in_own_order():
    types = [
        AnnotationTypeState(name, [], id=idx)
        for idx, name in enumerate(["a", "b", "c", "d"])
    ]

    shown = displayed_types(types, tier_order=["c", "a"])

    assert [t.type for t in shown] == ["c", "a", "b", "d"]


def test_displayed_types_ignores_names_in_the_order_that_are_not_types():
    shown = displayed_types(_two_tier_state().types, tier_order=["tone", "phone"])

    assert [t.type for t in shown] == ["phone", "word"]


def test_displayed_types_leaves_out_hidden_types_before_ordering():
    shown = displayed_types(
        _two_tier_state().types, hidden_tiers=["phone"], tier_order=["phone", "word"]
    )

    assert [t.type for t in shown] == ["word"]


def test_update_from_window_numbers_tiers_by_display_row():
    state = update_annotation_state_from_window(
        _two_tier_state(), 0.0, 1.0, tier_order=["phone", "word"]
    )

    assert [t.labels[0].pos[1] for t in state.types] == [0.5, 1.5]


def test_update_from_window_with_every_tier_hidden_is_empty():
    state = update_annotation_state_from_window(
        _two_tier_state(), 0.0, 1.0, hidden_tiers={"word", "phone"}
    )

    assert state.types == []
    assert state.nodes == {}
