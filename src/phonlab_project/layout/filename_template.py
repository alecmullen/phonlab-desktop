import re
from dataclasses import dataclass

from phonlab_project.constants import TEMPLATE_IGNORE_REST

REGEX_PREFIX = "re:"

_FIELD = re.compile(r"\{([^{}]*)\}")
_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_DUPLICATE_SUFFIX = re.compile(r"__\d+$")


class TemplateError(ValueError):
    pass


@dataclass(frozen=True)
class FilenameTemplate:
    """Splits a file name (without extension) into named fields.

    Template syntax: text matches itself and `{name}` is a field. A field is any
    run of characters (as short as possible) unless it has a format:
      {name:3}  exactly 3 characters      {name:d}  one or more digits
      {name:a}  one or more letters       {*}       any characters, not kept
    `(ignore)` can go anywhere in the template. It allows anything, or nothing, at
    that point and keeps none of it:
    `{talker:7}(ignore)` reads S24-002 and S24-002-1 as talker S24-002.
    A name used twice (`{talker}_{talker}`) gives two values for that field.
    A template that starts with `re:` is a regular expression with named groups.
    The whole name has to match."""

    pattern: re.Pattern[str]

    def match(self, stem: str) -> list[tuple[str, str]] | None:
        found = self.pattern.fullmatch(stem)
        if found is None:
            return None
        groups = sorted(self.pattern.groupindex.items(), key=lambda item: item[1])
        return [
            (_DUPLICATE_SUFFIX.sub("", name), found.group(name))
            for name, _ in groups
            if found.group(name) is not None
        ]


def compile_template(template: str) -> FilenameTemplate:
    if template.startswith(REGEX_PREFIX):
        try:
            return FilenameTemplate(re.compile(template[len(REGEX_PREFIX) :]))
        except re.error as err:
            raise TemplateError(f"Invalid regular expression: {err}") from err

    seen: dict[str, int] = {}
    parts: list[str] = []
    position = 0
    for found in _FIELD.finditer(template):
        parts.append(_literal(template[position : found.start()]))
        name, _, spec = found.group(1).partition(":")
        body = _field_body(spec)
        if name == "*":
            parts.append(f"(?:{body})")
        else:
            if not _NAME.fullmatch(name):
                raise TemplateError(
                    f"'{name}' is not a valid field name (use letters, digits, _)"
                )
            seen[name] = seen.get(name, 0) + 1
            group = name if seen[name] == 1 else f"{name}__{seen[name]}"
            parts.append(f"(?P<{group}>{body})")
        position = found.end()
    parts.append(_literal(template[position:]))

    return FilenameTemplate(re.compile("".join(parts)))


def _literal(text: str) -> str:
    if "{" in text or "}" in text:
        raise TemplateError("Unbalanced braces: write fields as {name}")
    return "(?:.*?)".join(re.escape(part) for part in text.split(TEMPLATE_IGNORE_REST))


def _field_body(spec: str) -> str:
    if spec == "":
        return ".+?"
    if spec.isdigit():
        width = int(spec)
        if width < 1:
            raise TemplateError("A field width has to be at least 1")
        return f".{{{width}}}"
    if spec == "d":
        return r"\d+"
    if spec == "a":
        return r"[^\W\d_]+"
    raise TemplateError(f"Unknown field format '{spec}': use a width, d, or a")
