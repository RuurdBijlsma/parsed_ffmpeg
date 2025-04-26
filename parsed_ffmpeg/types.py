from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum, auto
from pathlib import Path


class StreamType(StrEnum):
    VIDEO = auto()
    AUDIO = auto()
    DATA = auto()
    SUBTITLE = auto()
    UNKNOWN = auto()


@dataclass
class BaseStream:
    stream_id: str
    codec: str
    type: StreamType
    details: str
    bitrate_kbs: int | None = None
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass
class AudioStream(BaseStream):
    type: StreamType = field(default=StreamType.AUDIO, init=False)
    sample_rate: int | None = None
    num_channels: int | None = None
    channel_layout_str: str | None = None


@dataclass
class VideoStream(BaseStream):
    type: StreamType = field(default=StreamType.VIDEO, init=False)
    resolution_w: int | None = None
    resolution_h: int | None = None
    fps: float | None = None


@dataclass
class DataStream(BaseStream):
    type: StreamType = field(default=StreamType.DATA, init=False)


@dataclass
class SubtitleStream(BaseStream):
    type: StreamType = field(default=StreamType.SUBTITLE, init=False)


@dataclass
class FfprobeResult:
    duration_ms: int | None = None
    start_time: float | None = None
    bitrate_kbs: int | None = None
    streams: list[BaseStream] = field(default_factory=list)
    format_name: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass
class FfmpegStatus:
    frame: int | None = None
    fps: float | None = None
    bitrate: str | None = None
    total_size: int | None = None
    out_time_ms: float | None = None
    dup_frames: int | None = None
    drop_frames: int | None = None
    speed: float | None = None
    progress: str | None = None
    duration_ms: int | None = None
    completion: float | None = None


class FfmpegError(Exception):
    def __init__(
        self,
        err_lines: Sequence[str],
        full_command: Sequence[str],
        user_command: str | Sequence[str | Path],
    ) -> None:
        super().__init__("\n".join(err_lines))
        self.err_lines = err_lines
        self.full_command = full_command
        self.user_command = user_command

    def format_error(self) -> str:
        user_command: str | Sequence[str | Path]
        if isinstance(self.user_command, list):
            user_command = f"[{', '.join([f'"{part!s}"' for part in self.user_command])}]"
        else:
            user_command = self.user_command
        return (
            f"\n\n\tUser command:\n\t\t{user_command}\n"
            f"\tExecuted command:\n\t\t{' '.join([str(part) for part in self.full_command])}\n"
            f"\tWorking directory:\n\t\t{Path.cwd()}\n"
            f"\n{'\n'.join(self.err_lines)}"
        )

    def __str__(self) -> str:
        return self.format_error()
