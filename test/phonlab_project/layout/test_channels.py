from pathlib import Path

from support.audio_files import write_wavs
from support.project_tree import make_tree

from core.project_layout.infer_layout import InferLayout
from core.project_layout.resolve_recordings import ResolveRecordings
from core.project_layout.scan_project_tree import ScanProjectTree
from phonlab_project.layout.channels import detect_channels, group_audio
from phonlab_project.layout.project_layout import (
    ChannelRole,
    DataFileRole,
    ProjectLayout,
)
from phonlab_project.layout.project_scan import ScannedFile

LEFT_RIGHT = (ChannelRole("L", "_L"), ChannelRole("R", "_R"))


def files(*paths: str) -> list[ScannedFile]:
    return [ScannedFile.from_path(path) for path in paths]


def test_without_channels_every_audio_file_is_a_recording():
    units = group_audio(files("a_L.wav", "a_R.wav"), ())

    assert [u.base.path for u in units] == ["a_L.wav", "a_R.wav"]
    assert all(u.channels == {} for u in units)


def test_channel_files_become_one_unit_named_after_the_base():
    [unit] = group_audio(files("sub/a_L.wav", "sub/a_R.wav"), LEFT_RIGHT)

    assert unit.base.path == "sub/a.wav"
    assert unit.base.stem == "a"
    assert {label: f.path for label, f in unit.channels.items()} == {
        "L": "sub/a_L.wav",
        "R": "sub/a_R.wav",
    }
    assert unit.first_file.path == "sub/a_L.wav"


def test_channels_are_listed_in_the_order_of_the_roles():
    [unit] = group_audio(files("a_R.wav", "a_L.wav"), LEFT_RIGHT)

    assert list(unit.channels) == ["L", "R"]


def test_a_file_whose_other_channel_is_missing_stays_a_recording():
    units = group_audio(files("a_L.wav", "a_R.wav", "b_L.wav"), LEFT_RIGHT)

    assert [u.base.path for u in units] == ["a.wav", "b_L.wav"]


def test_channels_in_different_folders_are_not_combined():
    units = group_audio(files("x/a_L.wav", "y/a_R.wav"), LEFT_RIGHT)

    assert len(units) == 2


def test_suffix_matching_ignores_case():
    [unit] = group_audio(files("a_l.wav", "a_r.wav"), LEFT_RIGHT)

    assert unit.base.stem == "a"


def test_detects_files_differing_by_a_repeating_suffix(tmp_path: Path):
    write_wavs(tmp_path, ["a_L.wav", "a_R.wav", "b_L.wav", "b_R.wav"])
    scan = ScanProjectTree()(str(tmp_path))

    candidate = detect_channels(scan.files, str(tmp_path))

    assert candidate is not None
    assert [(r.label, r.suffix) for r in candidate.roles] == [("L", "_L"), ("R", "_R")]
    assert candidate.n_groups == 2
    assert candidate.looks_like_channels is True
    assert candidate.examples[0] == "a_L.wav + a_R.wav"


def test_files_that_differ_in_length_are_takes_not_channels(tmp_path: Path):
    write_wavs(tmp_path, ["a_L.wav"], frames=100)
    write_wavs(tmp_path, ["a_R.wav"], frames=300)
    scan = ScanProjectTree()(str(tmp_path))

    assert detect_channels(scan.files, str(tmp_path)) is None


def test_numbered_files_are_offered_only_if_the_headers_show_channels(tmp_path: Path):
    make_tree(tmp_path, ["a_1.wav", "a_2.wav"])  # unreadable
    scan = ScanProjectTree()(str(tmp_path))
    assert detect_channels(scan.files, str(tmp_path)) is None

    write_wavs(tmp_path, ["a_1.wav", "a_2.wav"])  # mono and equally long
    candidate = detect_channels(scan.files, str(tmp_path))

    assert candidate is not None and candidate.looks_like_channels is True


def test_many_suffixes_are_items_not_channels(tmp_path: Path):
    write_wavs(tmp_path, [f"a_{n}x.wav" for n in range(12)])
    scan = ScanProjectTree()(str(tmp_path))

    assert detect_channels(scan.files, str(tmp_path)) is None


def test_unreadable_audio_leaves_the_question_open(tmp_path: Path):
    make_tree(tmp_path, ["a_L.wav", "a_R.wav"])  # empty files
    scan = ScanProjectTree()(str(tmp_path))

    candidate = detect_channels(scan.files, str(tmp_path))

    assert candidate is not None and candidate.looks_like_channels is None


def test_a_single_pair_among_many_recordings_is_not_a_pattern(tmp_path: Path):
    write_wavs(tmp_path, ["a_L.wav", "a_R.wav", "c.wav", "d.wav", "e.wav", "f.wav"])
    scan = ScanProjectTree()(str(tmp_path))

    assert detect_channels(scan.files, str(tmp_path)) is None


def test_inference_takes_channels_when_the_headers_show_they_are(tmp_path: Path):
    write_wavs(tmp_path, ["a_L.wav", "a_R.wav", "b_L.wav", "b_R.wav"])
    make_tree(tmp_path, ["a.TextGrid", "b.TextGrid", "a.trk", "b.trk"])
    scan = ScanProjectTree()(str(tmp_path))

    suggestion = InferLayout()(scan)

    assert [r.label for r in suggestion.layout.channels] == ["L", "R"]
    assert suggestion.layout.annotation_ext == ".textgrid"
    assert [c.role.name for c in suggestion.data_file_candidates] == ["trk"]


def test_inference_leaves_unclear_channels_to_the_user(tmp_path: Path):
    make_tree(tmp_path, ["a_L.wav", "a_R.wav", "a.TextGrid"])
    scan = ScanProjectTree()(str(tmp_path))

    suggestion = InferLayout()(scan)

    assert suggestion.layout.channels == ()
    assert suggestion.channel_candidate is not None
    # the user's answer changes what is found
    answered = InferLayout()(scan, suggestion.channel_candidate.roles)
    assert answered.layout.annotation_ext == ".textgrid"


def test_inference_can_be_told_there_are_no_channels(tmp_path: Path):
    write_wavs(tmp_path, ["a_L.wav", "a_R.wav", "b_L.wav", "b_R.wav"])
    scan = ScanProjectTree()(str(tmp_path))

    suggestion = InferLayout()(scan, ())

    assert suggestion.layout.channels == ()


def test_channel_recording_gets_its_annotation_data_and_talkers(tmp_path: Path):
    make_tree(
        tmp_path,
        ["s/a_L.wav", "s/a_R.wav", "s/a.TextGrid", "s/a.trk", "s/b_L.wav", "s/b_R.wav"],
    )
    layout = ProjectLayout(
        channels=(ChannelRole("L", "_L", "Ann"), ChannelRole("R", "_R", "Bob")),
        data_files=(DataFileRole("trk", "", ".trk"),),
    )

    result = ResolveRecordings()(ScanProjectTree()(str(tmp_path)), layout)

    a, b = result.recordings
    assert a.file_stem == "s/a"
    assert a.audio_file == "s/a_L.wav"
    assert a.channel_files == {"L": "s/a_L.wav", "R": "s/a_R.wav"}
    assert a.channel_talkers == {"L": "Ann", "R": "Bob"}
    assert a.talkers == ["Ann", "Bob"]
    assert a.annotation_file == "s/a.TextGrid"
    assert a.data_files == {"trk": "s/a.trk"}
    assert b.annotation_file is None
    assert result.report.n_audio == 2
    assert result.report.n_audio_files == 4
    assert result.report.unpaired_audio == ["s/b_L.wav"]


def test_channels_without_talker_names_add_no_talkers(tmp_path: Path):
    make_tree(tmp_path, ["a_L.wav", "a_R.wav"])

    [recording] = ResolveRecordings()(
        ScanProjectTree()(str(tmp_path)), ProjectLayout(channels=LEFT_RIGHT)
    ).recordings

    assert recording.talkers == []
    assert recording.channel_talkers == {}


def test_filename_template_applies_to_the_name_without_the_channel_suffix(
    tmp_path: Path,
):
    make_tree(tmp_path, ["ab01_L.wav", "ab01_R.wav"])

    [recording] = ResolveRecordings()(
        ScanProjectTree()(str(tmp_path)),
        ProjectLayout(channels=LEFT_RIGHT, filename_template="{talker:2}{n:d}"),
    ).recordings

    assert (recording.talkers, recording.fields) == (["ab"], {"n": "01"})


# --------------------------- one channel has no ending: rl001.wav and rl001_lar.wav ---------------------------

PLAIN_AND_LAR = (ChannelRole("main", ""), ChannelRole("lar", "_lar"))


def test_the_file_named_like_the_recording_can_be_a_channel():
    [unit] = group_audio(files("rl001.wav", "rl001_lar.wav"), PLAIN_AND_LAR)

    assert unit.base.path == "rl001.wav"
    assert list(unit.channels) == ["main", "lar"]
    assert {label: f.path for label, f in unit.channels.items()} == {
        "main": "rl001.wav",
        "lar": "rl001_lar.wav",
    }


def test_a_plain_file_without_a_partner_stays_a_recording():
    units = group_audio(files("rl001.wav", "rl001_lar.wav", "other.wav"), PLAIN_AND_LAR)

    assert [u.base.path for u in units] == ["rl001.wav", "other.wav"]
    assert units[1].channels == {}


def test_the_ending_is_not_taken_for_part_of_another_recordings_name():
    units = group_audio(files("rl001.wav", "rl001_lar.wav", "rl002.wav"), PLAIN_AND_LAR)

    assert [u.base.stem for u in units] == ["rl001", "rl002"]


def test_detects_a_plain_name_next_to_a_name_with_an_ending(tmp_path: Path):
    write_wavs(tmp_path, ["rl001.wav", "rl001_lar.wav", "rl002.wav", "rl002_lar.wav"])
    scan = ScanProjectTree()(str(tmp_path))

    candidate = detect_channels(scan.files, str(tmp_path))

    assert candidate is not None
    assert [(r.label, r.suffix) for r in candidate.roles] == [
        ("main", ""),
        ("lar", "_lar"),
    ]
    assert candidate.n_groups == 2
    assert candidate.looks_like_channels is True
    assert candidate.examples[0] == "rl001.wav + rl001_lar.wav"


def test_inference_takes_them_as_channels_and_finds_the_rest(tmp_path: Path):
    write_wavs(tmp_path, ["rl001.wav", "rl001_lar.wav", "rl002.wav", "rl002_lar.wav"])
    make_tree(tmp_path, ["rl001.TextGrid", "rl002.TextGrid", "rl001.trk", "rl002.trk"])
    scan = ScanProjectTree()(str(tmp_path))

    suggestion = InferLayout()(scan)

    assert [r.label for r in suggestion.layout.channels] == ["main", "lar"]
    assert suggestion.layout.annotation_ext == ".textgrid"
    assert [c.role.name for c in suggestion.data_file_candidates] == ["trk"]


def test_resolving_pairs_the_annotation_with_the_plain_name(tmp_path: Path):
    make_tree(
        tmp_path,
        ["rl001.wav", "rl001_lar.wav", "rl001.TextGrid", "rl002.wav", "rl002_lar.wav"],
    )

    result = ResolveRecordings()(
        ScanProjectTree()(str(tmp_path)), ProjectLayout(channels=PLAIN_AND_LAR)
    )

    first, second = result.recordings
    assert first.file_stem == "rl001"
    assert first.audio_file == "rl001.wav"
    assert first.channel_files == {"main": "rl001.wav", "lar": "rl001_lar.wav"}
    assert first.annotation_file == "rl001.TextGrid"
    assert second.annotation_file is None
    assert result.report.n_audio == 2
    assert result.report.n_audio_files == 4
    assert result.report.unpaired_audio == ["rl002.wav"]
