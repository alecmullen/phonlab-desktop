import re
from dataclasses import replace

from phonlab_project.layout.filename_template import (
    TemplateError,
    compile_template,
)
from phonlab_project.layout.project_layout import ProjectLayout

VARIABLE = re.compile(r"\{(\w+)\}")
_DUPLICATE_SUFFIX = re.compile(r"__\d+$")


def template_names(template: str) -> list[str]:
    """The variables a filename template reads, in order; none if it cannot be used"""
    if template.strip() == "":
        return []
    try:
        groups = compile_template(template).pattern.groupindex
    except TemplateError:
        return []
    ordered = sorted(groups, key=lambda name: groups[name])
    names = (_DUPLICATE_SUFFIX.sub("", name) for name in ordered)
    return list(dict.fromkeys(names))


def layout_variables(layout: ProjectLayout) -> list[str]:
    """The variables the folder and file names of a layout give, which a talker template
    can be built from: those that name a folder level, those the folder level and
    filename templates read"""
    names: list[str] = []
    for level in sorted(layout.levels, key=lambda level: level.depth):
        if level.field:
            names.append(level.field)
        names.extend(template_names(level.template))
    names.extend(template_names(layout.filename_template))
    return list(dict.fromkeys(names))


def talker_template_problem(layout: ProjectLayout) -> str:
    """What is wrong with the layout's talker template, or an empty string if nothing
    is: braces that do not pair, or a `{name}` that no folder level or file name gives"""
    template = layout.talker_template.strip()
    if template == "":
        return ""
    if re.search(r"[{}]", VARIABLE.sub("", template)):
        return "Unbalanced braces: write variables as {name}"
    available = layout_variables(layout)
    unknown = [name for name in VARIABLE.findall(template) if name not in available]
    if unknown:
        listed = ", ".join(f"{{{name}}}" for name in dict.fromkeys(unknown))
        have = ", ".join(available) or "none yet"
        return f"No folder or file name gives {listed}. Variables there are: {have}"
    return ""


def without_unusable_templates(layout: ProjectLayout) -> tuple[ProjectLayout, str]:
    """The layout with the filename and folder level templates that cannot be used taken
    out, and what is wrong with the first of them (an empty string if all can be used).
    A talker template that names variables the names do not give is taken out too, but
    that is not reported here (see `talker_template_problem`)."""
    error = ""
    filename_template = layout.filename_template
    if filename_template.strip() != "":
        try:
            compile_template(filename_template)
        except TemplateError as err:
            error, filename_template = str(err), ""

    levels = []
    for level in layout.levels:
        if level.template.strip() != "":
            try:
                compile_template(level.template)
            except TemplateError as err:
                error = error or f"Folder level {level.depth}: {err}"
                level = replace(level, template="")
        levels.append(level)

    layout = replace(layout, filename_template=filename_template, levels=tuple(levels))
    if talker_template_problem(layout):
        layout = replace(layout, talker_template="")
    return layout, error
