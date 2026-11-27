import pytest

from phonlab_project.columns import column_name, convert, infer_sql_type
from phonlab_project.metadata import SqlType


def test_a_column_name_has_only_letters_digits_and_underscores():
    assert column_name("Age (years)", set()) == "Age_years"


def test_a_column_name_does_not_begin_with_a_digit():
    assert column_name("2nd", set()) == "c_2nd"


def test_a_column_name_differs_from_taken_ones_ignoring_case():
    assert column_name("Name", {"name"}) == "Name_2"


def test_a_name_with_nothing_usable_is_column():
    assert column_name("?!", set()) == "column"


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        (["1", "2", ""], SqlType.INTEGER),
        (["1", "2.5"], SqlType.REAL),
        (["1", "x"], SqlType.TEXT),
        ([""], SqlType.TEXT),
    ],
)
def test_a_column_is_typed_from_its_values(values: list[str], expected: SqlType):
    assert infer_sql_type(values) == expected


def test_values_are_converted_to_the_type_and_empty_ones_are_none():
    assert convert("3", SqlType.INTEGER) == 3
    assert convert("3.5", SqlType.REAL) == 3.5
    assert convert("x", SqlType.TEXT) == "x"
    assert convert("", SqlType.INTEGER) is None
