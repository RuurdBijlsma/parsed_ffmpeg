import os
from dataclasses import dataclass
from enum import StrEnum, auto
from pathlib import Path


class StreamType(StrEnum):
    VIDEO = auto()
    AUDIO = auto()


@dataclass
class BaseStream:
    bitrate_kbs: int
    codec: str
    details: str
    type: StreamType


@dataclass
class AudioStream(BaseStream):
    sample_rate: int
    channels: list[str]


@dataclass
class VideoStream(BaseStream):
    resolution_w: int
    resolution_h: int
    fps: int


@dataclass
class FfprobeResult:
    bitrate_kbs: int
    duration_ms: int
    start_time: float
    streams: list[BaseStream]


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
        err_lines: list[str],
        full_command: list[str],
        user_command: str | list[str | Path],
    ):
        super().__init__("\n".join(err_lines))
        self.err_lines = err_lines
        self.full_command = full_command
        self.user_command = user_command

    def format_error(self) -> str:
        if isinstance(self.user_command, list):
            user_command = (
                f"[{", ".join([f'"{str(part)}"' for part in self.user_command])}]"
            )
        else:
            user_command = self.user_command
        return (
            f"\n\n\tUser command:\n\t\t{user_command}\n"
            f"\tExecuted command:\n\t\t{" ".join([str(part) for part in self.full_command])}\n"
            f"\tWorking directory:\n\t\t{os.getcwd()}\n"
            f"\n{"\n".join(self.err_lines)}"
        )

    def __str__(self) -> str:
        return self.format_error()
