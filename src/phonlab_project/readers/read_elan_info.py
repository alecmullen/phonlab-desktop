import posixpath
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from urllib.parse import unquote, urlparse


@dataclass(frozen=True)
class ElanInfo:
    """What an ELAN file says besides its annotations: about the media its times are
    for, and who is speaking"""

    # TIME_ORIGIN of the sound, in seconds, as ELAN wrote it (None if it did not)
    offset: float | None = None
    # the video file as ELAN names it: a path relative to the .eaf file if it gave
    # one, else the file name
    video: str | None = None
    # the participants its tiers name, in the order they first appear
    participants: tuple[str, ...] = ()


def read_elan_info(file_path: str, audio_stem: str) -> ElanInfo:
    """The offset of the sound, the video and the participants of an ELAN file. The sound is
    the media file named like `audio_stem` or, if none is, the first sound the file
    lists. A file that cannot be read says nothing."""
    try:
        descriptors, participants = _read_header_and_tiers(file_path)
    except (ET.ParseError, OSError):
        return ElanInfo()

    sounds = [d for d in descriptors if d.get("MIME_TYPE", "").startswith("audio/")]
    named = [d for d in sounds if posixpath.splitext(_name(d))[0] == audio_stem]
    sound = (named or sounds or [None])[0]
    video = next(
        (d for d in descriptors if d.get("MIME_TYPE", "").startswith("video/")), None
    )
    origin = sound.get("TIME_ORIGIN") if sound is not None else None
    return ElanInfo(
        offset=int(origin) / 1000 if origin else None,
        video=_path(video) if video is not None else None,
        participants=participants,
    )


def _read_header_and_tiers(
    file_path: str,
) -> tuple[list[dict[str, str]], tuple[str, ...]]:
    """The MEDIA_DESCRIPTORs of the header and the participants of the tiers"""
    descriptors: list[dict[str, str]] = []
    participants: dict[str, None] = {}
    for event, element in ET.iterparse(file_path, events=("start", "end")):
        if event == "end" and element.tag == "MEDIA_DESCRIPTOR":
            descriptors.append(dict(element.attrib))
        elif event == "start" and element.tag == "TIER":
            name = element.get("PARTICIPANT", "").strip()
            if name:
                participants[name] = None
        elif event == "end" and element.tag == "ANNOTATION":
            element.clear()  # the annotations themselves are not wanted here
    return descriptors, tuple(participants)


def _path(descriptor: dict[str, str]) -> str:
    url = descriptor.get("RELATIVE_MEDIA_URL") or descriptor.get("MEDIA_URL", "")
    path = unquote(urlparse(url).path)
    # a relative URL is a path from the .eaf file; a full one is only useful for its name
    if descriptor.get("RELATIVE_MEDIA_URL"):
        return posixpath.normpath(path)
    return posixpath.basename(path)


def _name(descriptor: dict[str, str]) -> str:
    return posixpath.basename(_path(descriptor))
