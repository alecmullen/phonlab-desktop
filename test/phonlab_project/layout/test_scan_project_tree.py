from pathlib import Path

from support.project_tree import make_tree

from phonlab_project.layout.scan_project_tree import scan_project_tree


def test_scan_lists_files_recursively_with_relative_paths(tmp_path: Path):
    make_tree(tmp_path, ["a.wav", "sub/deeper/b.WAV", "sub/c.TextGrid"])

    scan = scan_project_tree(str(tmp_path))

    assert [f.path for f in scan.files] == [
        "a.wav",
        "sub/c.TextGrid",
        "sub/deeper/b.WAV",
    ]


def test_scan_splits_dir_stem_and_casefolded_extension(tmp_path: Path):
    make_tree(tmp_path, ["sub/b.TextGrid"])

    [file] = scan_project_tree(str(tmp_path)).files

    assert (file.dir, file.stem, file.ext, file.name) == (
        "sub",
        "b",
        ".textgrid",
        "b.TextGrid",
    )
    assert file.path_without_ext == "sub/b"


def test_scan_ignores_hidden_files_and_phonlab_files(tmp_path: Path):
    make_tree(
        tmp_path,
        ["a.wav", ".DS_Store", ".hidden/x.wav", "phonlab.toml", "phonlab.db"],
    )

    scan = scan_project_tree(str(tmp_path))

    assert [f.path for f in scan.files] == ["a.wav"]


def test_scan_keeps_files_without_extension(tmp_path: Path):
    make_tree(tmp_path, ["README"])

    [file] = scan_project_tree(str(tmp_path)).files

    assert (file.stem, file.ext) == ("README", "")
