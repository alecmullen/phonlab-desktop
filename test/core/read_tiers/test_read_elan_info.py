from pathlib import Path

from core.read_tiers.read_elan_info import ElanInfo, read_elan_info

EAF = """<?xml version="1.0" encoding="UTF-8"?>
<ANNOTATION_DOCUMENT FORMAT="3.0" VERSION="3.0">
<HEADER MEDIA_FILE="" TIME_UNITS="milliseconds">
{media}
</HEADER>
<TIME_ORDER/>
{tiers}
</ANNOTATION_DOCUMENT>
"""


def descriptor(url: str, mime: str, origin: int | None = None) -> str:
    name = url.rpartition("/")[2]
    time_origin = "" if origin is None else f' TIME_ORIGIN="{origin}"'
    return (
        f'<MEDIA_DESCRIPTOR MEDIA_URL="file:///Users/x/{url}" MIME_TYPE="{mime}" '
        f'RELATIVE_MEDIA_URL="./{name}"{time_origin}/>'
    )


def info_of(
    tmp_path: Path, *media: str, tiers: str = "", audio_stem: str = "a"
) -> ElanInfo:
    path = tmp_path / "a.eaf"
    path.write_text(EAF.format(media="\n".join(media), tiers=tiers))
    return read_elan_info(str(path), audio_stem)


def test_the_offset_of_the_sound_is_given_in_seconds(tmp_path: Path):
    media = info_of(tmp_path, descriptor("a.wav", "audio/x-wav", 1500))

    assert media == ElanInfo(offset=1.5, video=None)


def test_a_file_without_an_offset_has_none(tmp_path: Path):
    assert info_of(tmp_path, descriptor("a.wav", "audio/x-wav")).offset is None


def test_the_sound_named_like_the_recording_is_the_one_whose_offset_counts(
    tmp_path: Path,
):
    media = info_of(
        tmp_path,
        descriptor("other.wav", "audio/x-wav", 100),
        descriptor("a.wav", "audio/x-wav", 200),
    )

    assert media.offset == 0.2


def test_the_first_sound_counts_when_none_is_named_like_the_recording(tmp_path: Path):
    media = info_of(
        tmp_path,
        descriptor("x.wav", "audio/x-wav", 100),
        descriptor("y.wav", "audio/x-wav", 200),
    )

    assert media.offset == 0.1


def test_the_video_is_the_path_the_file_gives_from_itself(tmp_path: Path):
    media = info_of(
        tmp_path,
        descriptor("a.wav", "audio/x-wav"),
        '<MEDIA_DESCRIPTOR MEDIA_URL="file:///Users/x/Video%20files/a.mp4" '
        'MIME_TYPE="video/mp4" RELATIVE_MEDIA_URL="../Video%20files/a.mp4"/>',
    )

    assert media.video == "../Video files/a.mp4"


def test_a_video_without_a_relative_path_is_known_by_its_name(tmp_path: Path):
    media = info_of(
        tmp_path,
        '<MEDIA_DESCRIPTOR MEDIA_URL="file:///Users/x/clips/a.mp4" '
        'MIME_TYPE="video/mp4"/>',
    )

    assert media.video == "a.mp4"


def test_a_file_that_cannot_be_read_says_nothing(tmp_path: Path):
    path = tmp_path / "a.eaf"
    path.write_text("not xml")

    assert read_elan_info(str(path), "a") == ElanInfo()


def tier(name: str, participant: str | None) -> str:
    attribute = "" if participant is None else f' PARTICIPANT="{participant}"'
    return f'<TIER LINGUISTIC_TYPE_REF="t" TIER_ID="{name}"{attribute}></TIER>'


def test_the_participants_are_those_the_tiers_name_in_order_without_repeats(
    tmp_path: Path,
):
    tiers = (
        tier("a-words", "ann")
        + tier("a-phones", "ann")
        + tier("b-words", " bob ")
        + tier("notes", None)
        + tier("more", "")
    )

    assert info_of(tmp_path, tiers=tiers).participants == ("ann", "bob")
