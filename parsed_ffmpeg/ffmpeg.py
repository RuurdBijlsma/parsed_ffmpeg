import os
from collections.abc import Callable

from parsed_ffmpeg.ffmpeg_class import StatusUpdate, Ffmpeg


class FfmpegError(Exception):
    def __init__(
        self,
        err_lines: list[str],
        full_command: list[str],
        user_command: str | list[str],
    ):
        super().__init__("\n".join(err_lines))
        self.err_lines = err_lines
        self.full_command = full_command
        self.user_command = user_command

    def format_error(self) -> str:
        if isinstance(self.user_command, list):
            user_command = f"[{", ".join(self.user_command)}]"
        else:
            user_command = self.user_command
        return (
            f"\n\n\tUser command:\n\t\t{user_command}\n"
            f"\tFull command:\n\t\t{" ".join(self.full_command)}\n"
            f"\tWorking directory:\n\t\t{os.getcwd()}\n"
            f"\n{"\n".join(self.err_lines)}"
        )

    def __str__(self) -> str:
        return self.format_error()


async def run_ffmpeg(
    command: list[str] | str,
    on_status: Callable[[StatusUpdate], None] | None = None,
    on_stdout: Callable[[str], None] | None = None,
    on_stderr: Callable[[str], None] | None = None,
    on_error: Callable[[list[str]], None] | None = None,
    on_warning: Callable[[str], None] | None = None,
    overwrite_output: bool = False,
    raise_on_error: bool = True,
) -> None:
    user_command = command
    if isinstance(command, str):
        command = command.split(" ")
    if overwrite_output and "-y" not in command:
        command.append("-y")
    if "-progress" in command:
        raise ValueError("-progress parameter can't be in command.")
    command += ["-progress", "pipe:1"]
    error_lines: list[str] = []

    def on_error_listener(err: str) -> None:
        error_lines.append(err)

    ffmpeg = Ffmpeg(
        command=command,
        on_status=on_status,
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
            err_lines=error_lines, full_command=command, user_command=user_command
        )
