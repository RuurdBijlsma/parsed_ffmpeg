import asyncio
import re
from asyncio import subprocess, StreamReader
from collections.abc import Callable

from parsed_ffmpeg.types import FfmpegStatus


async def read_stream(stream: StreamReader, callback: Callable[[str], None]) -> None:
    """Read stream in chunks, split chunks on newline and call callback with each line.

    Not using readline here because it can cause an error if the \n isn't found with a given limit."""
    buffer = b''
    while True:
        chunk = await stream.read(1024)  # Read in chunks of 1024 bytes
        if not chunk:
            break
        buffer += chunk
        while b'\n' in buffer:
            line, buffer = buffer.split(b'\n', 1)
            callback(line.decode().strip())

    # Handle any remaining data in buffer
    if buffer:
        callback(buffer.decode().strip())


class Ffmpeg:
    status_update: FfmpegStatus = FfmpegStatus()
    process: subprocess.Process
    probe_mode: bool

    def __init__(
        self,
        command: list[str],
        on_status: Callable[[FfmpegStatus], None] | None = None,
        on_stdout: Callable[[str], None] | None = None,
        on_stderr: Callable[[str], None] | None = None,
        on_error: Callable[[str], None] | None = None,
        on_warning: Callable[[str], None] | None = None,
        group_output: bool = True,
    ):
        self.command = command
        self.group_output = group_output
        self.stderr_buffer = ""
        self.stdout_buffer = ""

        self.on_status = on_status
        self.on_error = on_error
        self.on_warning = on_warning

        self.on_stdout = on_stdout
        self.on_stderr = on_stderr

    def handle_stderr(self, line: str) -> None:
        self.stderr_buffer += line
        if self.on_stderr is not None:
            self.on_stderr(line)

        if line.startswith("Duration: "):
            reg_result = re.search(r"(\d{2}):(\d{2}):(\d{2})\.(\d{2})", line)
            if reg_result is not None:
                h, m, s, ms = map(int, reg_result.groups())
                self.status_update.duration_ms = (h * 3600 + m * 60 + s) * 1000 + ms

        if "error" in line.lower():
            if self.on_error:
                self.on_error(line)

        if "warning" in line.lower():
            if self.on_warning:
                self.on_warning(line)

    def handle_stdout(self, line: str) -> None:
        self.stdout_buffer += line
        if self.on_stdout is not None:
            self.on_stdout(line)

        key, val = line.split("=")
        if val == "N/A":
            return
        match key:
            case "frame":
                self.status_update.frame = int(val)
            case "fps":
                self.status_update.fps = float(val)
            case "bitrate":
                self.status_update.bitrate = val
            case "total_size":
                self.status_update.total_size = int(val)
            case "out_time_ms":
                self.status_update.out_time_ms = int(val) / 1000
            case "dup_frames":
                self.status_update.dup_frames = int(val)
            case "drop_frames":
                self.status_update.drop_frames = int(val)
            case "speed":
                self.status_update.speed = float(val[:-1])
            case "progress":
                self.status_update.progress = val
            case _:
                return

        if (
            self.on_status is not None
            and self.status_update.progress
            and (key == "progress" or not self.group_output)
        ):
            if self.status_update.duration_ms and self.status_update.out_time_ms:
                raw_progress = (
                    self.status_update.out_time_ms / self.status_update.duration_ms
                )
                self.status_update.completion = max(0.0, min(1.0, raw_progress))
            self.on_status(self.status_update)

    async def start(self) -> None:
        self.process = await asyncio.create_subprocess_exec(
            *self.command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            limit=1024 * 128
        )
        stdout_task: asyncio.Task[None] | None = None
        stderr_task: asyncio.Task[None] | None = None
        if self.process.stdout:
            stdout_task = asyncio.create_task(
                read_stream(self.process.stdout, self.handle_stdout)
            )
        if self.process.stderr:
            stderr_task = asyncio.create_task(
                read_stream(self.process.stderr, self.handle_stderr)
            )

        await self.process.wait()
        if stdout_task:
            await stdout_task
        if stderr_task:
            await stderr_task
