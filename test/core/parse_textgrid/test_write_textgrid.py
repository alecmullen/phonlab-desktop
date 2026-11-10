import logging
from pathlib import Path
from typing import Any

import phonlab as phon
import pytest

from core.annotation.entity.annotation import (
    Annotation,
    AnnotationLabel,
    AnnotationType,
)
from core.parse_textgrid.write_textgrid import TextgridType, WriteTextGrid


def make_annotation() -> Annotation:
    """A "word" interval tier and a "pt" point tier over nodes at 0, 0.5, 1 and 0.25"""
    return Annotation(
        nodes={0: 0.0, 1: 0.5, 2: 1.0, 3: 0.25},
        types=[
            AnnotationType(
                "word",
                [
                    AnnotationLabel(0, 1, 'say "hi"', 0),
                    AnnotationLabel(1, 2, "", 1),
                ],
                0,
            ),
            AnnotationType("pt", [AnnotationLabel(3, 3, "p", 2)], 1),
        ],
        id=0,
    )


def write(
    annotation: Annotation,
    path: Path,
    tg_type: TextgridType = TextgridType.SHORT,
    **kwargs: Any,  # noqa: ANN401
) -> str:
    list(WriteTextGrid()(annotation, str(path), tg_type, **kwargs))
    return path.read_text(encoding=kwargs.get("codec", "utf-8"))


# --------------------------- short format ---------------------------

EXPECTED_SHORT = '''File type = "ooTextFile"
Object class = "TextGrid"

0.0
1.0
<exists>
2
"IntervalTier"
"word"
0.0
1.0
2
0.0
0.5
"say ""hi"""
0.5
1.0
""
"TextTier"
"pt"
0.0
1.0
1
0.25
"p"'''


def test_writes_short_textgrid(tmp_path: Path):
    text = write(make_annotation(), tmp_path / "out.TextGrid")

    assert text == EXPECTED_SHORT


def test_short_is_the_default_type(tmp_path: Path):
    path = tmp_path / "out.TextGrid"
    list(WriteTextGrid()(make_annotation(), str(path)))

    assert "<exists>" in path.read_text()
    assert "xmin =" not in path.read_text()


# --------------------------- long format ---------------------------


def test_writes_long_textgrid_header_and_labels(tmp_path: Path):
    text = write(make_annotation(), tmp_path / "out.TextGrid", TextgridType.LONG)

    assert text.startswith(
        'File type = "ooTextFile"\nObject class = "TextGrid"\n\n'
        "xmin = 0.0\nxmax = 1.0\ntiers? <exists>\nsize = 2\nitem []:\n"
    )
    assert 'class = "IntervalTier"' in text
    assert 'class = "TextTier"' in text
    assert "intervals: size = 2" in text
    assert "points: size = 1" in text
    assert 'text = "say ""hi"""' in text
    assert "number = 0.25" in text
    assert 'mark = "p"' in text


def test_long_textgrid_numbers_tiers_from_one(tmp_path: Path):
    text = write(make_annotation(), tmp_path / "out.TextGrid", TextgridType.LONG)

    assert "item [1]:" in text
    assert "item [2]:" in text
    assert "item [0]:" not in text


# --------------------------- round trip ---------------------------


@pytest.mark.parametrize("tg_type", list(TextgridType))
def test_written_textgrid_can_be_read_back(tmp_path: Path, tg_type: TextgridType):
    path = tmp_path / "out.TextGrid"
    write(make_annotation(), path, tg_type)

    tiers = phon.read_textgrid_with(str(path))

    assert [(t["class"], t["name"]) for t in tiers] == [
        ("IntervalTier", "word"),
        ("TextTier", "pt"),
    ]
    assert tiers[0]["labels"] == [(0.0, 0.5, 'say "hi"'), (0.5, 1.0, "")]
    assert tiers[1]["labels"] == [(0.25, None, "p")]


def test_labels_are_written_in_time_order(tmp_path: Path):
    annotation = Annotation(
        nodes={0: 0.0, 1: 0.5, 2: 1.0},
        types=[
            AnnotationType(
                "word",
                [AnnotationLabel(1, 2, "second", 1), AnnotationLabel(0, 1, "first", 0)],
                0,
            )
        ],
    )

    path = tmp_path / "out.TextGrid"
    write(annotation, path)

    labels = phon.read_textgrid_with(str(path))[0]["labels"]
    assert [label[2] for label in labels] == ["first", "second"]


def test_writes_tier_without_labels(tmp_path: Path):
    annotation = Annotation(
        nodes={0: 0.0, 1: 1.0}, types=[AnnotationType("empty", [], 0)]
    )

    text = write(annotation, tmp_path / "out.TextGrid")

    assert text.endswith('"empty"\n0.0\n1.0\n0')


def test_writes_annotation_without_tiers(tmp_path: Path):
    text = write(
        Annotation(nodes={0: 0.0, 1: 2.0}, types=[]), tmp_path / "out.TextGrid"
    )

    assert text.endswith("<exists>\n0")


# --------------------------- encoding ---------------------------


def test_writes_with_requested_codec(tmp_path: Path):
    annotation = Annotation(
        nodes={0: 0.0, 1: 1.0},
        types=[AnnotationType("word", [AnnotationLabel(0, 1, "ʃɑ", 0)], 0)],
    )
    path = tmp_path / "out.TextGrid"

    write(annotation, path, codec="utf-16")

    assert path.read_bytes().startswith((b"\xff\xfe", b"\xfe\xff"))
    assert "ʃɑ" in path.read_text(encoding="utf-16")


# --------------------------- validation ---------------------------


def test_nothing_is_written_until_generator_is_consumed(tmp_path: Path):
    path = tmp_path / "out.TextGrid"

    task = WriteTextGrid()(make_annotation(), str(path))

    assert not path.exists()
    next(task)
    assert path.exists()


def test_raises_when_interval_ends_before_it_starts(tmp_path: Path):
    annotation = Annotation(
        nodes={0: 0.0, 1: 0.5},
        types=[AnnotationType("word", [AnnotationLabel(1, 0, "x", 0)], 0)],
    )

    with pytest.raises(RuntimeError, match="bad interval times"):
        write(annotation, tmp_path / "out.TextGrid")

    assert not (tmp_path / "out.TextGrid").exists()


def overlapping_annotation() -> Annotation:
    return Annotation(
        nodes={0: 0.0, 1: 0.6, 2: 0.4, 3: 1.0},
        types=[
            AnnotationType(
                "word",
                [AnnotationLabel(0, 1, "a", 0), AnnotationLabel(2, 3, "b", 1)],
                0,
            )
        ],
    )


def test_raises_when_intervals_overlap(tmp_path: Path):
    with pytest.raises(RuntimeError, match="cannot overlap"):
        write(overlapping_annotation(), tmp_path / "out.TextGrid")


def test_allow_overlaps_logs_error_and_still_writes(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
):
    with caplog.at_level(logging.ERROR):
        text = write(
            overlapping_annotation(), tmp_path / "out.TextGrid", allow_overlaps=True
        )

    assert '"a"' in text
    assert '"b"' in text
    assert any("overlap" in record.getMessage() for record in caplog.records)
