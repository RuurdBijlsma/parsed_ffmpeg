# FFmpeg output parser

## Overview

Do you already know the ffmpeg command line, and don't want to relearn some syntax of a pythonic ffmpeg wrapper? This is
the package for you. Just put in an ffmpeg command and this package structures the output while it's processing.

## Usage

The code below converts a video, and prints the percentage completion while it's working.
This example includes optional error handling, output shown below.

```python
from parsed_ffmpeg import run_ffmpeg, FfmpegError


async def process_video():
    try:
        await run_ffmpeg(
            f"ffmpeg -i input.mp4 -c:v libx264 output.mp4",
            on_status=lambda status: print(f"We're: {status.completion * 100:.1f}% there!"),
            overwrite_output=True
        )
        print("Done!")
    except FfmpegError as e:
        print(f"ffmpeg failed with error: {e}")
```

### Example script output

```text
We're: 8.2% there!
We're: 45.5% there!
We're: 100.0% there!
Done!
```

### Error example

```text
ffmpeg failed with error: 

	User command:
		ffmpeg -i input.mp4 -c:v libx264 output.mp4
	Full command:
		ffmpeg -i input.mp4 -c:v libx264 output.mp4 -y -progress pipe:1
	Working directory:
		C:\Users\rutenl\PycharmProjects\parsed_ffmpeg

[in#0 @ 00000208d2d4e1c0] Error opening input: No such file or directory
Error opening input file input.mp4.
Error opening input files: No such file or directory
```

### Example: run with tqdm to get a progressbar

If you install the tqdm extra dependency (`pip install parsed-ffmpeg[tqdm]`), you can do the following:

```python
input_video = Path(__file__).parent.parent / "tests/assets/input.mp4"
await run_ffmpeg(
    f"ffmpeg -i {input_video} -vf scale=-1:1440 -c:v libx264 output.mp4",
    print_progress_bar=True,
    progress_bar_description=input_video.name,
    overwrite_output=True,
)
```

It'll give output like this:

```text
input.mp4:  73%|███████▎  | 4466/6084 [00:04<00:00, 1620.10ms/s]
```

## Installation

Remember that this package does not come with an ffmpeg binary, you have to have it in path or point to it in your
command.

```shell
pip install parsed-ffmpeg
```

## API

### `run_ffmpeg`

```python
async def run_ffmpeg(
    command: list[str] | str,
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
    ...
```

### `StatusUpdate`

```python
class StatusUpdate:
    frame: int | None
    fps: float | None
    bitrate: str | None
    total_size: int | None
    out_time_ms: float | None
    dup_frames: int | None
    drop_frames: int | None
    speed: float | None
    progress: str | None
    duration_ms: int | None
    completion: float | None
```

## Changing ffmpeg install location

Just replace the first part of your command (ffmpeg) with the path to ffmpeg.
Example:

```python
await run_ffmpeg("C:/apps/ffmpeg.exe -i input.mp4 -c:v libx264 output.mp4 -y")
```

## License

MIT