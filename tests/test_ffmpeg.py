from pathlib import Path
from unittest.mock import MagicMock

import pytest

from parsed_ffmpeg import run_ffmpeg, FfmpegStatus, FfmpegError
from parsed_ffmpeg.runner import run_ffprobe


@pytest.fixture  # type: ignore
def test_file() -> Path:
    return (Path(__file__).resolve().parent / "assets/input.mp4").absolute()


@pytest.fixture  # type: ignore[misc]
def test_ffmpeg_command(test_file: Path) -> list[str]:
    return [
        "ffmpeg",
        "-i",
        str(test_file),
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "output.mp4",
    ]


@pytest.fixture  # type: ignore[misc]
def test_ffprobe_command(test_file: Path) -> list[str]:
    return [
        "ffprobe",
        str(test_file),
    ]


@pytest.mark.asyncio  # type: ignore
async def test_ffprobe(test_ffprobe_command: list[str]) -> None:
    output = await run_ffprobe(test_ffprobe_command)
    assert output.duration_ms == 6840
    assert len(output.streams) == 2


@pytest.mark.asyncio  # type: ignore
async def test_ffmpeg_success(test_ffmpeg_command: list[str]) -> None:
    on_status_mock = MagicMock()
    on_stdout_mock = MagicMock()
    on_stderr_mock = MagicMock()
    on_error_mock = MagicMock()
    on_warning_mock = MagicMock()

    await run_ffmpeg(
        test_ffmpeg_command,
        on_status=on_status_mock,
        on_stdout=on_stdout_mock,
        on_stderr=on_stderr_mock,
        on_error=on_error_mock,
        on_warning=on_warning_mock,
        overwrite_output=True,
    )

    on_status_mock.assert_called()
    on_stdout_mock.assert_called()
    on_stderr_mock.assert_called()

    status_update_arg = on_status_mock.call_args[0][0]
    assert isinstance(status_update_arg, FfmpegStatus)
    assert status_update_arg.duration_ms == 6084


@pytest.mark.asyncio  # type: ignore
async def test_ffmpeg_err() -> None:
    on_error_mock = MagicMock()

    with pytest.raises(FfmpegError) as e:
        await run_ffmpeg(
            "ffmpeg -i input.mp4 output.mp4",
            on_error=on_error_mock,
            overwrite_output=True,
        )
    assert len(e.value.err_lines) == 3
    on_error_mock.assert_called()
