"""What phonlab_project offers is what `__all__` lists, and all of it is documented
(phonlab's documentation is made from the docstrings)."""

import inspect

import phonlab_project

PUBLIC_METHODS_OF_PROJECT = [
    name
    for name, _ in inspect.getmembers(phonlab_project.Project, inspect.isfunction)
    if not name.startswith("_")
]


def test_every_name_in_all_exists_and_is_documented():
    undocumented = [
        name
        for name in phonlab_project.__all__
        if not (inspect.getdoc(getattr(phonlab_project, name)) or "").strip()
    ]

    assert undocumented == []


def test_every_public_function_documents_its_parameters_and_what_it_returns():
    lacking = []
    for name in phonlab_project.__all__:
        item = getattr(phonlab_project, name)
        if not inspect.isfunction(item):
            continue
        doc = inspect.getdoc(item) or ""
        parameters = [p for p in inspect.signature(item).parameters if p != "self"]
        if parameters and "Parameters\n----------" not in doc:
            lacking.append(f"{name}: Parameters")
        if (
            inspect.signature(item).return_annotation not in (None, "None")
            and "Returns\n-------" not in doc
        ):
            lacking.append(f"{name}: Returns")

    assert lacking == []


def test_every_public_method_of_a_project_is_documented():
    undocumented = [
        name
        for name in PUBLIC_METHODS_OF_PROJECT
        if not (inspect.getdoc(getattr(phonlab_project.Project, name)) or "").strip()
    ]

    assert undocumented == []


def test_the_public_names_are_sorted_and_not_repeated():
    names = phonlab_project.__all__

    assert names == sorted(names)
    assert len(names) == len(set(names))
