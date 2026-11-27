from core.annotation.entity.annotation import AnnotationLabel


def test_annotation_label_defaults_to_empty_text():
    assert AnnotationLabel(0, 1).label == ""
