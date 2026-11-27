from pathlib import Path

import pytest
from support.audio_files import write_wavs

from phonlab_project.readers.read_tier_table import read_tier_table
from phonlab_project.readers.table_format import (
    WHITESPACE,
    ColumnRole,
    TableFormat,
    TimeUnit,
)

START, END, LABEL, UNKNOWN = (
    ColumnRole.START,
    ColumnRole.END,
    ColumnRole.LABEL,
    ColumnRole.UNKNOWN,
)


def audio(tmp_path: Path, seconds: float = 2.5) -> str:
    write_wavs(tmp_path, ["a.wav"], frames=int(seconds * 8000), fs=8000)
    return str(tmp_path / "a.wav")


def write(tmp_path: Path, name: str, text: str) -> str:
    path = tmp_path / name
    path.write_bytes(text.encode())
    return str(path)


def labels(
    path: str, audio_path: str | None = None, table: TableFormat | None = None
) -> list[tuple[float, float, str]]:
    return read_tier_table(path, "t", audio_path, table)["labels"]


# --------------------------- working out the table ---------------------------


def test_a_text_header_is_skipped_and_times_in_milliseconds_are_found_by_the_audio(
    tmp_path: Path,
):
    path = write(
        tmp_path,
        "a_phn.txt",
        "MillisecondsPerFrame: 1.0\r\nEND OF HEADER\r\n"
        "0.000000 59.491978 .sil\r\n59.491978 91.577538 p_c\r\n2400.0 2500.0 .sil\r\n",
    )

    result = labels(path, audio(tmp_path))

    assert result[0] == (0.0, pytest.approx(0.059491978), ".sil")
    assert result[2] == (pytest.approx(2.4), pytest.approx(2.5), ".sil")


def test_times_in_seconds_are_kept_when_they_fit_the_audio(tmp_path: Path):
    path = write(tmp_path, "a.txt", "0.5 2.0 x\n2.0 2.4 y\n")

    assert labels(path, audio(tmp_path)) == [(0.5, 2.0, "x"), (2.0, 2.4, "y")]


def test_without_audio_the_times_are_taken_to_be_seconds(tmp_path: Path):
    path = write(tmp_path, "a.txt", "0.5 2500 x\n")

    assert labels(path) == [(0.5, 2500.0, "x")]


def test_a_label_may_have_spaces_when_it_ends_the_line(tmp_path: Path):
    path = write(tmp_path, "a_snt.txt", "59.492 2477.7273 pero no so_7lo ame_7rica\n")

    assert labels(path, audio(tmp_path)) == [
        (pytest.approx(0.059492), pytest.approx(2.4777273), "pero no so_7lo ame_7rica")
    ]


def test_columns_may_come_in_any_order_and_have_names(tmp_path: Path):
    path = write(
        tmp_path,
        "a.tsv",
        "word\tfinish\tbegin\nhi\t1.0\t0.0\nthere\t2.0\t1.0\n",
    )

    assert labels(path) == [(0.0, 1.0, "hi"), (1.0, 2.0, "there")]


def test_a_comma_table_can_quote_its_labels(tmp_path: Path):
    path = write(tmp_path, "a.csv", 'start,end,label\n0,1,"hi, there"\n1,2,bye\n')

    assert labels(path) == [(0.0, 1.0, "hi, there"), (1.0, 2.0, "bye")]


def test_with_one_time_column_each_label_ends_where_the_next_begins(tmp_path: Path):
    path = write(tmp_path, "a.txt", "0.0 a\n0.5 b\n1.5 c\n")

    result = labels(path, audio(tmp_path, 2.0))

    assert result == [(0.0, 0.5, "a"), (0.5, 1.5, "b"), (1.5, 2.0, "c")]


def test_the_time_column_with_the_smallest_values_is_the_start_and_the_largest_the_end(
    tmp_path: Path,
):
    path = write(tmp_path, "a.txt", "0.2 0.5 0.9 a\n0.9 1.0 1.4 b\n")

    result = labels(path, audio(tmp_path))

    assert result == [(0.2, 0.9, "a"), (0.9, 1.4, "b")]


def test_two_time_columns_that_are_not_start_and_end_give_only_a_start(tmp_path: Path):
    path = write(tmp_path, "a.txt", "0.5 0.0 a\n1.0 0.2 b\n1.5 2.0 c\n")

    # (0.0, 0.2, 2.0) is not below (0.5, 1.0, 1.5) on every row
    assert [(b, e) for b, e, _ in labels(path)] == [(0.0, 0.2), (0.2, 2.0), (2.0, 2.0)]


# --------------------------- what the user says ---------------------------


def test_the_format_the_user_chose_is_used_as_it_is(tmp_path: Path):
    path = write(tmp_path, "a.txt", "x;0;5\ny;5;9\n")
    table = TableFormat(";", 0, (LABEL, START, END), TimeUnit.MILLISECONDS)

    result = labels(path, table=table)

    assert result[0] == (0.0, pytest.approx(0.005), "x")
    assert result[1] == (pytest.approx(0.005), pytest.approx(0.009), "y")


def test_a_column_given_the_role_unknown_is_ignored(tmp_path: Path):
    path = write(tmp_path, "a.txt", "0 1 9 x\n1 2 9 y\n")
    table = TableFormat(WHITESPACE, 0, (START, END, UNKNOWN, LABEL))

    assert [text for *_, text in labels(path, table=table)] == ["x", "y"]


# --------------------------- what cannot be read ---------------------------


def test_a_file_with_no_time_column_is_an_error(tmp_path: Path):
    path = write(tmp_path, "a.txt", "a b c\nd e f\n")

    with pytest.raises(ValueError):
        labels(path)


def test_an_empty_file_is_an_error(tmp_path: Path):
    path = write(tmp_path, "a.txt", "\n\n")

    with pytest.raises(ValueError):
        labels(path)


def test_a_row_with_a_time_that_is_not_a_number_is_an_error(tmp_path: Path):
    path = write(tmp_path, "a.txt", "0 1 x\n1 two y\n")
    table = TableFormat(WHITESPACE, 0, (START, END, LABEL))

    with pytest.raises(ValueError):
        labels(path, table=table)
