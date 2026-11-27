from phonlab_project.layout.project_layout import FolderLevel, ProjectLayout
from phonlab_project.layout.template_variables import (
    layout_variables,
    talker_template_problem,
    template_names,
    without_unusable_templates,
)

LAYOUT = ProjectLayout(
    levels=(
        FolderLevel(3, "", "{session}-{agegroup}"),
        FolderLevel(2, "region"),
    ),
    filename_template="{talker}_{talker}_{n:d}",
)


def test_the_variables_of_a_layout_are_in_the_order_of_levels_then_file_names():
    assert layout_variables(LAYOUT) == ["region", "session", "agegroup", "talker", "n"]


def test_a_regular_expression_gives_its_named_groups():
    assert template_names(r"re:(?P<gender>[fm])_(?P<num>\d+)") == ["gender", "num"]


def test_a_template_that_cannot_be_used_names_nothing():
    assert template_names("{oops") == []
    assert template_names("") == []


def test_a_talker_template_naming_what_the_layout_gives_has_no_problem():
    layout = ProjectLayout(
        levels=LAYOUT.levels,
        filename_template=LAYOUT.filename_template,
        talker_template="{region}_{session}-{n}",
    )

    assert talker_template_problem(layout) == ""


def test_a_talker_template_names_the_variable_nothing_gives():
    problem = talker_template_problem(
        ProjectLayout(levels=LAYOUT.levels, talker_template="{region}_{nothing}")
    )

    assert "{nothing}" in problem
    assert "region" in problem


def test_unpaired_braces_in_a_talker_template_are_a_problem():
    assert talker_template_problem(ProjectLayout(talker_template="{region")) != ""


def test_unusable_templates_are_taken_out_and_the_first_is_reported():
    layout = ProjectLayout(
        levels=(FolderLevel(1, "a", "{oops"), FolderLevel(2, "b", "{x}-{y}")),
        filename_template="{bad",
    )

    cleaned, error = without_unusable_templates(layout)

    assert error != ""
    assert cleaned.filename_template == ""
    assert [level.template for level in cleaned.levels] == ["", "{x}-{y}"]
