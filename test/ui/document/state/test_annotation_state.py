from core.parse_textgrid.annotation import Annotation, AnnotationLabel, AnnotationType
from ui.document.state.annotation_state import (
    AnnotationLabelState,
    AnnotationTypeState,
    to_annotation_state,
)


def test_to_annotation_state_converts_nodes_and_types():
    annotation = Annotation(
        nodes={0: 0.0, 1: 0.5, 2: 1.0},
        types=[
            AnnotationType(
                type="word",
                labels=[
                    AnnotationLabel(0, 1, "hello"),
                    AnnotationLabel(1, 2, "world"),
                ],
            )
        ],
    )

    state = to_annotation_state(annotation)

    assert state.nodes == {0: 0.0, 1: 0.5, 2: 1.0}
    assert state.types == [
        AnnotationTypeState(
            "word",
            [
                AnnotationLabelState(0, 1, "hello"),
                AnnotationLabelState(1, 2, "world"),
            ],
        )
    ]


def test_to_annotation_state_converts_multiple_types():
    annotation = Annotation(
        nodes={0: 0.0, 1: 1.0},
        types=[
            AnnotationType("word", [AnnotationLabel(0, 1, "hi")]),
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
