import pytest

from core.project_layout.filename_template import TemplateError, compile_template


def fields(template: str, stem: str) -> list[tuple[str, str]] | None:
    return compile_template(template).match(stem)


def test_fixed_width_fields_split_a_name():
    assert fields("{talker:3}{session:2}{part}", "s0101a") == [
        ("talker", "s01"),
        ("session", "01"),
        ("part", "a"),
    ]


def test_delimited_fields_use_literal_text_between_them():
    assert fields("{talker}_{item}", "ab_cd_07") == [
        ("talker", "ab"),
        ("item", "cd_07"),
    ]


def test_digit_and_letter_formats():
    assert fields("{lang:a}{num:d}", "fr123") == [("lang", "fr"), ("num", "123")]


def test_wildcard_is_not_kept():
    assert fields("{*}_{talker}", "x_y_z") == [("talker", "y_z")]


def test_repeated_name_gives_each_value():
    assert fields("{talker}_{talker}", "ab_cd") == [("talker", "ab"), ("talker", "cd")]


def test_whole_name_must_match():
    assert fields("{a:2}", "abc") is None
    assert fields("x{a}", "yab") is None


def test_regex_with_named_groups():
    assert fields(r"re:(?P<talker>[a-z]+)(?P<n>\d+)", "ab12") == [
        ("talker", "ab"),
        ("n", "12"),
    ]


@pytest.mark.parametrize(
    "template",
    ["{bad name}", "{a:zz}", "{a:0}", "a{", "}", "re:(unclosed"],
)
def test_invalid_templates_raise(template: str):
    with pytest.raises(TemplateError):
        compile_template(template)


def test_ignored_rest_may_be_there_or_not():
    assert fields("{talker:7}(ignore)", "S24-002") == [("talker", "S24-002")]
    assert fields("{talker:7}(ignore)", "S24-002-1") == [("talker", "S24-002")]


def test_ignored_rest_is_not_kept_as_a_field():
    assert fields("{talker:3}(ignore)_{n:d}", "abc-x_12") == [
        ("talker", "abc"),
        ("n", "12"),
    ]


def test_a_name_that_is_too_short_does_not_fit_even_with_an_ignored_rest():
    assert fields("{talker:7}(ignore)", "S24-02") is None


def test_ignored_part_can_come_first_or_in_the_middle():
    assert fields("(ignore){talker:3}", "xx_abc") == [("talker", "abc")]
    assert fields("(ignore){talker:3}", "abc") == [("talker", "abc")]
    assert fields("{talker:3}(ignore)_{n:d}", "abc_07") == [
        ("talker", "abc"),
        ("n", "07"),
    ]
    assert fields("{a}(ignore)_{n:d}", "x-y_7") == [("a", "x"), ("n", "7")]
