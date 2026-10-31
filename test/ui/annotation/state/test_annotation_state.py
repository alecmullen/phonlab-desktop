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
    to_annotation,
    to_annotation_state,
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
