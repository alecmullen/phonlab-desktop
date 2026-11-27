from pathlib import Path

import pytest

from phonlab_project.readers.metadata_table import MetadataTable
from phonlab_project.readers.read_metadata_csv import read_metadata_csv


def read(tmp_path: Path, text: str, encoding: str = "utf-8") -> MetadataTable:
    path = tmp_path / "info.csv"
    path.write_text(text, encoding=encoding)
    return read_metadata_csv(str(path))


def test_reads_headers_and_rows(tmp_path: Path):
    table = read(tmp_path, "talker,age,sex\nab,31,F\ncd,45,M\n")

    assert table.headers == ["talker", "age", "sex"]
    assert table.rows == [["ab", "31", "F"], ["cd", "45", "M"]]
    assert table.column("age") == ["31", "45"]


@pytest.mark.parametrize("delimiter", [";", "\t", "|"])
def test_other_delimiters_are_detected(tmp_path: Path, delimiter: str):
    table = read(tmp_path, f"talker{delimiter}age\nab{delimiter}31\ncd{delimiter}45\n")

    assert table.headers == ["talker", "age"]


def test_byte_order_mark_is_not_part_of_the_first_header(tmp_path: Path):
    table = read(tmp_path, "talker,age\nab,31\n", encoding="utf-8-sig")

    assert table.headers[0] == "talker"


def test_cells_are_trimmed_and_short_rows_padded(tmp_path: Path):
    table = read(tmp_path, "talker, age ,sex\n ab , 31\n")

    assert table.rows == [["ab", "31", ""]]


def test_blank_and_repeated_headers_are_made_distinct(tmp_path: Path):
    table = read(tmp_path, "a,,a\n1,2,3\n")

    assert table.headers == ["a", "column 2", "a (2)"]


def test_blank_lines_are_skipped(tmp_path: Path):
    table = read(tmp_path, "talker,age\n\nab,31\n\n")

    assert table.rows == [["ab", "31"]]


def test_file_without_rows_is_rejected(tmp_path: Path):
    with pytest.raises(ValueError):
        read(tmp_path, "talker,age\n")
