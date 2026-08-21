from ui.annotation.annotation_state import (
    AnnotationLabelState,
    AnnotationState,
    AnnotationTypeState,
)

FAKE_ANNOTATION_STATE = AnnotationState(
    {
        0: 0.0,
        1: 0.24,
        2: 1.3,
        3: 1.8,
        4: 4.1,
        5: 5.2,
        6: 5.9,
        7: 6.3,
        8: 10.0,
    },
    [
        AnnotationTypeState(
            "utter",
            [
                AnnotationLabelState(0, 8, "fake note")
            ],
        ),
        AnnotationTypeState(
            "word",
            [
                AnnotationLabelState(0, 3, "fake"),
                AnnotationLabelState(4, 7, "note"),
            ],
        ),
        AnnotationTypeState(
            "phon",
            [
                AnnotationLabelState(0, 1, "f"),
                AnnotationLabelState(1, 2, "æ"),
                AnnotationLabelState(2, 3, "k"),
                AnnotationLabelState(3, 4, ""),
                AnnotationLabelState(4, 5, "n"),
                AnnotationLabelState(5, 6, "ow"),
                AnnotationLabelState(6, 7, "t"),
                AnnotationLabelState(7, 8, ""),
            ]
        ),
    ]
)