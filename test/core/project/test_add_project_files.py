from pathlib import Path

from support.audio_files import write_wavs
from support.textgrid import write_simple_textgrid

from core.annotation.entity.annotation import AnnotationType
from core.annotation.entity.recording import Recording
from core.annotation.repository.in_mem_annotation_repository import (
    InMemAnnotationRepository,
)
from core.parse_textgrid.parse_textgrid import ParseTextGrid
from core.project.add_project_files import AddProjectFiles
from core.project.entity.project_file import ProjectFile
from core.project.entity.project_import_result import (
    ImportStage,
    ProjectImportResult,
)
from core.read_tiers.entity.table_format import TierFile


def make_use_case(
    repository: InMemAnnotationRepository | None = None,
) -> tuple[AddProjectFiles, InMemAnnotationRepository]:
    repository = repository or InMemAnnotationRepository()
    return AddProjectFiles(repository, ParseTextGrid(repository)), repository


def run(use_case: AddProjectFiles, files: list[ProjectFile]) -> list:
    return list(use_case(files))


def textgrid_file(tmp_path: Path, stem: str) -> ProjectFile:
    return ProjectFile(
        stem,
        str(tmp_path / f"{stem}.wav"),
        write_simple_textgrid(tmp_path / f"{stem}.TextGrid"),
    )


def test_registers_stem_of_audio_file_without_textgrid(tmp_path: Path):
    use_case, repository = make_use_case()

    results = run(use_case, [ProjectFile("a", str(tmp_path / "a.wav"))])

    annotation = repository.find_annotation_by_file_stem("a")
    assert annotation is not None and annotation.types == []
    assert results[-1].registered == 1


def test_reads_textgrid_of_new_stem(tmp_path: Path):
    use_case, repository = make_use_case()

    results = run(use_case, [textgrid_file(tmp_path, "a")])

    annotation = repository.find_annotation_by_file_stem("a")
    assert annotation is not None
    assert [type.type for type in annotation.types] == ["word"]
    assert results[-1].imported == ["a"]


def test_reads_textgrid_of_registered_stem_with_empty_annotation(tmp_path: Path):
    use_case, repository = make_use_case()
    repository.create_annotations_if_missing(["a"])

    results = run(use_case, [textgrid_file(tmp_path, "a")])

    assert results[-1].registered == 0
    assert results[-1].imported == ["a"]
    assert len(repository.filenames) == 1


def test_does_not_read_textgrid_of_stem_that_already_has_annotation(tmp_path: Path):
    use_case, repository = make_use_case()
    id = repository.create_annotation("a")
    repository.create_types(id, [AnnotationType("mine", [])])

    results = run(use_case, [textgrid_file(tmp_path, "a")])

    annotation = repository.find_annotation_by_file_stem("a")
    assert annotation is not None
    assert [type.type for type in annotation.types] == ["mine"]
    assert results[-1].imported == []
    assert results[-1].total == 0


def test_reports_progress_while_registering_and_around_each_textgrid(tmp_path: Path):
    use_case, _ = make_use_case()
    files = [textgrid_file(tmp_path, "a"), textgrid_file(tmp_path, "b")]

    results = run(use_case, files)

    assert [(r.stage, r.done, r.total, r.current) for r in results] == [
        (ImportStage.REGISTERING, 0, 0, ""),
        (ImportStage.READING, 0, 2, ""),
        (ImportStage.READING, 0, 2, "a.TextGrid"),
        (ImportStage.READING, 1, 2, ""),
        (ImportStage.READING, 1, 2, "b.TextGrid"),
        (ImportStage.READING, 2, 2, ""),
    ]
    assert [r.finished for r in results] == [False] * 5 + [True]


def test_yields_a_finished_result_when_there_is_nothing_to_read(tmp_path: Path):
    use_case, _ = make_use_case()

    results = run(use_case, [ProjectFile("a", str(tmp_path / "a.wav"))])

    assert results[-1] == ProjectImportResult(0, 0, registered=1)
    assert results[-1].finished
    assert not any(result.finished for result in results[:-1])


def test_unreadable_textgrid_is_reported_and_does_not_stop_the_others(tmp_path: Path):
    use_case, repository = make_use_case()
    bad = tmp_path / "bad.TextGrid"
    bad.write_text("not a textgrid")
    files = [
        ProjectFile("bad", str(tmp_path / "bad.wav"), str(bad)),
        textgrid_file(tmp_path, "good"),
    ]

    results = run(use_case, files)

    assert results[-1].failed == ["bad"]
    assert results[-1].imported == ["good"]
    assert results[-1].finished
    assert repository.find_annotation_by_file_stem("bad") is not None


def test_running_again_changes_nothing(tmp_path: Path):
    use_case, repository = make_use_case()
    files = [textgrid_file(tmp_path, "a")]
    run(use_case, files)
    before = repository.find_annotation_by_file_stem("a")

    results = run(use_case, files)

    assert repository.find_annotation_by_file_stem("a") == before
    assert results[-1].registered == 0
    assert results[-1].imported == []


# --------------------------- what the project's layout says about each recording ---------------------------


def test_recordings_of_the_layout_are_kept_next_to_the_annotations():
    use_case, repository = make_use_case()
    recording = Recording(
        "t1/a", audio_file="t1/a.wav", talkers=["Ann"], fields={"dialect": "north"}
    )
    files = [ProjectFile("t1/a", "/p/t1/a.wav", None, recording)]

    run(use_case, files)

    assert repository.list_recordings() == [recording]
    assert repository.list_talkers() == ["Ann"]


def test_recordings_that_left_the_project_are_dropped_unless_they_hold_annotations():
    use_case, repository = make_use_case()
    repository.create_annotations_if_missing(["gone", "kept"])
    repository.create_nodes(
        repository.find_annotation_by_file_stem("kept").get_id(), [0.0], 0.0
    )
    keep = Recording("a", audio_file="a.wav")
    files = [ProjectFile("a", "/p/a.wav", None, keep)]

    run(use_case, files)

    assert sorted(repository.filenames.values()) == ["a", "kept"]


def test_files_without_layout_information_only_register_their_stems():
    use_case, repository = make_use_case()
    repository.create_annotations_if_missing(["old"])
    files = [ProjectFile("a", "/p/a.wav", None)]

    run(use_case, files)

    assert sorted(repository.filenames.values()) == ["a", "old"]
    assert repository.list_recordings() == []


# --------------------------- tiers kept in files of their own ---------------------------


def tier_file_project(tmp_path: Path) -> ProjectFile:
    write_wavs(tmp_path, ["s1.wav"], frames=22050, fs=8000)
    (tmp_path / "s1_phn.txt").write_text(HEADER + "0.0 400.0 h\n400.0 1000.0 ay\n")
    (tmp_path / "s1_wrd.txt").write_text(HEADER + "0.0 1000.0 hi\n")
    return ProjectFile(
        "s1",
        str(tmp_path / "s1.wav"),
        None,
        tier_files={
            "Phone": TierFile(str(tmp_path / "s1_phn.txt")),
            "Word": TierFile(str(tmp_path / "s1_wrd.txt")),
        },
    )


HEADER = "MillisecondsPerFrame: 1.0\nEND OF HEADER\n"


def test_a_recording_with_tier_files_and_no_textgrid_is_read(tmp_path: Path):
    use_case, repository = make_use_case()

    results = run(use_case, [tier_file_project(tmp_path)])

    annotation = repository.find_annotation_by_file_stem("s1")
    assert annotation is not None
    assert [type.type for type in annotation.types] == ["Phone", "Word"]
    assert results[-1].imported == ["s1"] and results[-1].finished


def test_the_progress_names_the_first_tier_file_being_read(tmp_path: Path):
    use_case, _ = make_use_case()

    results = run(use_case, [tier_file_project(tmp_path)])

    assert [r.current for r in results if r.current] == ["s1_phn.txt"]


def test_the_times_of_tier_files_in_milliseconds_are_in_seconds_in_the_database(
    tmp_path: Path,
):
    use_case, repository = make_use_case()

    run(use_case, [tier_file_project(tmp_path)])

    annotation = repository.find_annotation_by_file_stem("s1")
    assert annotation is not None
    assert sorted(annotation.nodes.values()) == [0.0, 0.4, 1.0]


# --------------------------- reading annotations again ---------------------------


def test_replace_reads_the_textgrids_again_over_what_the_database_has(tmp_path: Path):
    use_case, repository = make_use_case()
    id = repository.create_annotation("a")
    repository.create_types(id, [AnnotationType("mine", [])])

    results = list(use_case([textgrid_file(tmp_path, "a")], replace=True))

    annotation = repository.find_annotation_by_file_stem("a")
    assert annotation is not None
    assert [type.type for type in annotation.types] == ["word"]
    assert results[-1].imported == ["a"] and results[-1].finished


def test_replace_leaves_the_rest_of_the_database_alone(tmp_path: Path):
    use_case, repository = make_use_case()
    other = repository.create_annotation("other")
    repository.create_types(other, [AnnotationType("mine", [])])
    repository.upsert_recordings([Recording("other"), Recording("gone")])

    list(use_case([textgrid_file(tmp_path, "a")], replace=True))

    assert repository.find_annotation_by_file_stem("gone") is not None
    kept = repository.find_annotation_by_file_stem("other")
    assert kept is not None and [t.type for t in kept.types] == ["mine"]
