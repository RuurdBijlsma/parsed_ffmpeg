# FFmpeg output parser

## Overview

Do you already know the ffmpeg command line, and don't want to relearn some syntax of a pythonic ffmpeg wrapper? This is
the package for you. Just put in an ffmpeg or ffprobe command and this package structures the output while it's processing.

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

### Example output: custom status logging

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

### Example: Ffprobe

Ffprobe output is also supported, use it like this:

```python
input_video = "input.mp4"
result = await run_ffprobe(f"ffprobe {input_video}")
print(str(result))
```

The ffprobe result includes this info:

```json
{
  "bitrate_kbs": 3293,
  "duration_ms": 6840,
  "start_time": 0.0,
  "streams": [
    {
      "bitrate_kbs": 3152,
      "codec": "h264",
      "details": "yuv420p(tv, smpte170m, progressive), 1280x720 [SAR 1:1 DAR 16:9], 3152 kb/s, 60 fps, 60 tbr, 15360 tbn (default)",
      "type": "video",
      "resolution_w": 1280,
      "resolution_h": 720,
      "fps": 60
    },
    {
      "bitrate_kbs": 128,
      "codec": "aac",
      "details": "48000 Hz, stereo, fltp, 128 kb/s (default)",
      "type": "audio",
      "sample_rate": 48000,
      "channels": ["stereo", "fltp"]
    }
  ]
}
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
) -> str:
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

### `run_ffprobe`

```python
async def run_ffprobe(
    command: list[str | Path] | str,
    on_error: Callable[[list[str]], None] | None = None,
    on_warning: Callable[[str], None] | None = None,
    raise_on_error: bool = True,
) -> FfprobeResult:
    ...
```

### `ffprobe types`

```python
class AudioStream(BaseStream):
    bitrate_kbs: int
    codec: str
    details: str
    type: StreamType #(video or audio)
    sample_rate: int
    channels: list[str]

class VideoStream(BaseStream):
    bitrate_kbs: int
    codec: str
    details: str
    type: StreamType #(video or audio)
    resolution_w: int
    resolution_h: int
    fps: int

class FfprobeResult:
    bitrate_kbs: int
    duration_ms: int
    start_time: float
    streams: list[BaseStream]
```

## Changing ffmpeg install location

Just replace the first part of your command (ffmpeg) with the path to ffmpeg.
Example:

```python
await run_ffmpeg("C:/apps/ffmpeg.exe -i input.mp4 -c:v libx264 output.mp4 -y")
```

## License

MIT