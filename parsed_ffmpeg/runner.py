from collections.abc import Callable
from pathlib import Path

try:
    from tqdm import tqdm
except ImportError:
    _has_tqdm = False
else:
    _has_tqdm = True

from parsed_ffmpeg.ffmpeg import Ffmpeg
from parsed_ffmpeg.types import FfmpegError, FfmpegStatus


async def run_ffmpeg(
    command: list[str | Path] | str,
    on_status: Callable[[FfmpegStatus], None] | None = None,
    on_stdout: Callable[[str], None] | None = None,
    on_stderr: Callable[[str], None] | None = None,
    on_error: Callable[[list[str]], None] | None = None,
    on_warning: Callable[[str], None] | None = None,
    overwrite_output: bool = False,
    raise_on_error: bool = True,
    print_progress_bar: bool = False,
    progress_bar_description: str | None = None,
) -> None:
    command_list: list[str] = []
    if isinstance(command, list):
        command_list = [str(part) for part in command]
    elif isinstance(command, str):
        command_list = command.split(" ")
    if overwrite_output and "-y" not in command_list:
        command_list.append("-y")
    if "-progress" in command_list:
        raise ValueError("-progress parameter can't be in command.")
    command_list += ["-progress", "pipe:1"]
    error_lines: list[str] = []

    def on_error_listener(err: str) -> None:
        error_lines.append(err)

    pbar: tqdm | None = None
    if print_progress_bar and not _has_tqdm:
        raise ImportError(
            "tqdm is not included in your installation of parsed-ffmpeg, so the progress bar can't be used.\n"
            "Include it with `pip install parsed-ffmpeg[tqdm]`"
        )
    if print_progress_bar:
        pbar = tqdm(desc=progress_bar_description, unit="ms")
    try:

        def tqdm_update(status: FfmpegStatus) -> None:
            if on_status:
                on_status(status)
            if not status.out_time_ms or not status.duration_ms or pbar is None:
                return
            pbar.total = int(status.duration_ms)
            pbar.update(int(min(status.out_time_ms, status.duration_ms) - pbar.n))

        ffmpeg = Ffmpeg(
            command=command_list,
            on_status=tqdm_update,
            on_stdout=on_stdout,
            on_stderr=on_stderr,
            on_error=on_error_listener,
            on_warning=on_warning,
        )
        await ffmpeg.start()

        if on_error is not None and error_lines:
            on_error(error_lines)
        if raise_on_error and error_lines:
            raise FfmpegError(
                err_lines=error_lines, full_command=command_list, user_command=command
            )
    finally:
        if pbar is not None:
            pbar.close()