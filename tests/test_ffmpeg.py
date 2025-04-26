from collections import Counter
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from parsed_ffmpeg import (
    AudioStream,
    FfmpegError,
    FfmpegStatus,
    FfprobeResult,
    StreamType,
    SubtitleStream,
    VideoStream,
    run_ffmpeg,
    run_ffprobe,
)


@pytest.fixture
def assets_dir() -> Path:
    return Path(__file__).resolve().parent / "assets"


@pytest.fixture
def test_file(assets_dir: Path) -> Path:
    return (assets_dir / "input.mp4").absolute()


@pytest.fixture
def test_file2(assets_dir: Path) -> Path:
    return (assets_dir / "multi-stream.mov").absolute()


@pytest.fixture
def subtitle_test_file(assets_dir: Path) -> Path:
    return (assets_dir / "subtitle-stream.mkv").absolute()


@pytest.fixture
def test_ffmpeg_command(test_file: Path) -> list[str | Path]:
    output_path = Path("./output.mp4").absolute()  # Ensure output path is valid
    return [
        "ffmpeg",
        "-i",
        test_file,
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        output_path,
    ]


@pytest.fixture
def test_ffprobe_command(test_file: Path) -> list[str | Path]:
    return [
        "ffprobe",
        test_file,
    ]


@pytest.mark.asyncio
async def test_ffprobe_basic(test_ffprobe_command: list[str]) -> None:
    """Tests basic ffprobe parsing on a simple file."""
    output = await run_ffprobe(test_ffprobe_command)
    assert isinstance(output, FfprobeResult)
    assert output.duration_ms == 6840
    assert len(output.streams) == 2


@pytest.mark.asyncio
async def test_ffprobe_multistream_summary(test_file2: Path) -> None:
    """Tests high-level parsing of ffprobe output for a multi-stream MOV file."""
    output: FfprobeResult = await run_ffprobe(["ffprobe", test_file2])

    # --- Basic Checks ---
    assert isinstance(output, FfprobeResult)
    # Check duration within a small tolerance
    if output.duration_ms is not None:
        assert 14100 < output.duration_ms < 14200, "Incorrect duration"
    else:
        pytest.fail("Duration should be parsed for multi-stream file")
    assert len(output.streams) == 6, "Incorrect number of streams"

    # --- Stream Type Counts ---
    stream_types = Counter(s.type for s in output.streams)
    assert stream_types[StreamType.VIDEO] == 1, "Should have 1 video stream"
    assert stream_types[StreamType.AUDIO] == 4, "Should have 4 audio streams"
    assert stream_types[StreamType.DATA] == 1, "Should have 1 data stream"

    # --- Data Verification ---
    video_stream = next((s for s in output.streams if isinstance(s, VideoStream)), None)
    audio_stream = next((s for s in output.streams if isinstance(s, AudioStream)), None)

    assert video_stream is not None, "Video stream not found"
    assert video_stream.resolution_w == 1920, "Video width mismatch"

    assert audio_stream is not None, "Audio stream not found"
    assert audio_stream.sample_rate == 48000, "Audio sample rate mismatch"


@pytest.mark.asyncio
async def test_ffprobe_subtitle_stream(subtitle_test_file: Path) -> None:
    """Tests ffprobe parsing on a file containing a subtitle stream."""
    command = ["ffprobe", str(subtitle_test_file)]
    output: FfprobeResult = await run_ffprobe(command)

    # --- Basic Checks ---
    assert isinstance(output, FfprobeResult)
    assert output.format_name == "matroska,webm", "Incorrect format name"
    # Duration: 00:59:54.49 -> 3594490 ms
    if output.duration_ms is not None:
        assert 3594400 < output.duration_ms < 3594500, "Incorrect duration"
    else:
        pytest.fail("Duration should be parsed for subtitle file")
    assert output.bitrate_kbs == 6, "Incorrect overall bitrate"
    assert len(output.streams) == 3, "Should have 3 streams"

    # --- Stream Type Counts ---
    stream_types = Counter(s.type for s in output.streams)
    assert stream_types[StreamType.VIDEO] == 1, "Should have 1 video stream"
    assert stream_types[StreamType.AUDIO] == 1, "Should have 1 audio stream"
    assert stream_types[StreamType.SUBTITLE] == 1, "Should have 1 subtitle stream"

    # --- Subtitle Stream Verification ---
    subtitle_stream = next((s for s in output.streams if s.type == StreamType.SUBTITLE), None)
    assert subtitle_stream is not None, "Subtitle stream not found"
    assert isinstance(subtitle_stream, SubtitleStream)
    assert subtitle_stream.stream_id == "0:2"
    assert subtitle_stream.codec == "subrip"
    # Bitrate for subtitles is often not reported or N/A, so it should parse as None
    assert subtitle_stream.bitrate_kbs is None, "Subtitle bitrate should be None"
    assert "DURATION" in subtitle_stream.metadata
    assert subtitle_stream.metadata["DURATION"] == "00:59:54.486000000"
    # Example didn't have language tag like (eng) in the stream line,
    # but if it did, check here:
    # assert 'language' not in subtitle_stream.metadata # Or check if it *is* present


@pytest.mark.asyncio
async def test_ffmpeg_success(test_ffmpeg_command: list[str]) -> None:
    """Tests successful ffmpeg execution and status callbacks."""
    on_status_mock = MagicMock()
    on_stdout_mock = MagicMock()
    on_stderr_mock = MagicMock()
    on_error_mock = MagicMock()
    on_warning_mock = MagicMock()

    input_file = test_ffmpeg_command[2]
    input_probe = await run_ffprobe(["ffprobe", input_file])

    # Define output path and clean up before/after
    output_file = Path(test_ffmpeg_command[-1])
    if output_file.exists():
        output_file.unlink()

    try:
        await run_ffmpeg(
            test_ffmpeg_command,
            on_status=on_status_mock,
            on_stdout=on_stdout_mock,
            on_stderr=on_stderr_mock,
            on_error=on_error_mock,
            on_warning=on_warning_mock,
            overwrite_output=True,  # Explicitly allow overwrite
        )

        on_status_mock.assert_called()
        on_stderr_mock.assert_called()
        on_error_mock.assert_not_called()  # Should not be called on success

        # Verify the last status update (closest to completion)
        final_status_call = on_status_mock.call_args_list[-1]
        status_update_arg = final_status_call[0][0]

        assert isinstance(status_update_arg, FfmpegStatus)
        # Check against the *input* duration from ffprobe test
        assert status_update_arg.duration_ms == input_probe.duration_ms
        # Check if progress indicates completion
        assert status_update_arg.progress == "end" or status_update_arg.completion == 1.0

        assert output_file.exists(), "Output file was not created"

    finally:
        # Clean up the output file
        if output_file.exists():
            output_file.unlink()


@pytest.mark.asyncio
async def test_ffmpeg_err() -> None:
    """Tests ffmpeg execution that results in an error."""
    on_error_mock = MagicMock()
    command = ["ffmpeg", "-i", "nonexistent_input.mp4", "output.mp4"]  # Invalid input

    with pytest.raises(FfmpegError) as exc_info:
        await run_ffmpeg(
            command,
            on_error=on_error_mock,
            overwrite_output=True,
        )

    # Check the exception details
    assert "Error opening input file nonexistent_input.mp4." in exc_info.value.err_lines
    assert len(exc_info.value.err_lines) > 0
    assert exc_info.value.user_command == command

    # Check if the callback was called
    on_error_mock.assert_called_once()
    error_lines_arg = on_error_mock.call_args[0][0]
    assert isinstance(error_lines_arg, list)
    assert "Error opening input file nonexistent_input.mp4." in "\n".join(error_lines_arg)
