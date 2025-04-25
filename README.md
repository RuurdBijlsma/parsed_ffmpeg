# FFmpeg/FFprobe output parser

## Overview

Do you already know the ffmpeg command line, and don't want to relearn some syntax of a pythonic wrapper? This is
the package for you. Just put in an ffmpeg or ffprobe command and this package structures the output while it's processing or after completion.

## Usage

### Example: FFmpeg with Progress

The code below converts a video, and prints the percentage completion while it's working.
This example includes optional error handling, output shown below.

```python
async def process_video(input_video: Path, output_video: Path):
    def handle_status(status: FfmpegStatus):
        if status.completion is not None:
            print(f"We're: {status.completion * 100:.1f}% there!")

    try:
        await run_ffmpeg(
            ["ffmpeg", "-i", input_video, "-c:v", "libx264", output_video],
            on_status=handle_status,
            overwrite_output=True
        )
        print("Done!")
    except FfmpegError as e:
        print(f"ffmpeg failed with error: {e.format_error()}") # Use format_error() for detailed info
```

#### Example output: custom status logging

```text
We're: 8.2% there!
We're: 45.5% there!
We're: 100.0% there!
Done!
```

#### Error example

```text
ffmpeg failed with error: 

	User command:
		['ffmpeg', '-i', 'nonexistent_input.mp4', '-c:v', 'libx264', 'output.mp4']
	Executed command:
		ffmpeg -i nonexistent_input.mp4 -c:v libx264 output.mp4 -y -progress pipe:1
	Working directory:
		C:\Users\your_user\path\to\project

[in#0 @ 0x...] Error opening input: No such file or directory
Error opening input file nonexistent_input.mp4.
Error opening input files: No such file or directory

```

### Example: Ffprobe

Ffprobe output is also supported, use it like this:

```python
async def probe_video(input_video: Path):
    try:
        result = await run_ffprobe(["ffprobe", input_video])
        # You can now access structured data
        print(f"Duration: {result.duration_ms} ms")
        print(f"Format: {result.format_name}")
        print(f"Overall Bitrate: {result.bitrate_kbs} kb/s")
        print(f"Found {len(result.streams)} streams:")
        for stream in result.streams:
            print(f"  - Stream {stream.stream_id} ({stream.type}): Codec={stream.codec}")
            if isinstance(stream, VideoStream):
                print(f"    Res: {stream.resolution_w}x{stream.resolution_h}, FPS: {stream.fps}")
            elif isinstance(stream, AudioStream):
                 print(f"    Sample Rate: {stream.sample_rate} Hz, Channels: {stream.num_channels}")

    except FfmpegError as e:
        print(f"ffprobe failed with error: {e.format_error()}")
```

The ffprobe result object (`FfprobeResult`) contains structured information. Here's an example representing the parsed data for a multi-stream file:

```json
{
  "duration_ms": 14180,
  "start_time": 0.0,
  "bitrate_kbs": 37744,
  "streams": [
    {
      "stream_id": "0:0",
      "codec": "prores",
      "type": "video",
      "details": "prores (LT) (apcs / 0x73637061), yuv422p10le(bt709, top coded first (swapped)), 1920x1080, 31008 kb/s, SAR 1:1 DAR 16:9, 59.94 fps, 59.94 tbr, 60k tbn (default)",
      "bitrate_kbs": 31008,
      "resolution_w": 1920,
      "resolution_h": 1080,
      "fps": 59.94
    },
    {
      "stream_id": "0:1",
      "codec": "pcm_s16le",
      "type": "audio",
      "details": "pcm_s16le (sowt / 0x74776F73), 48000 Hz, 2 channels, s16, 1536 kb/s (default)",
      "bitrate_kbs": 1536,
      "sample_rate": 48000,
      "num_channels": 2,
      "channel_layout_str": "2 channels"
    },
    {
      "stream_id": "0:2",
      "codec": "pcm_s16le",
      "type": "audio",
      "details": "pcm_s16le (sowt / 0x74776F73), 48000 Hz, 2 channels, s16, 1536 kb/s (default)",
      "bitrate_kbs": 1536,
      "sample_rate": 48000,
      "num_channels": 2,
      "channel_layout_str": "2 channels"
    },
    {
      "stream_id": "0:3",
      "codec": "pcm_s16le",
      "type": "audio",
      "details": "pcm_s16le (sowt / 0x74776F73), 48000 Hz, 2 channels, s16, 1536 kb/s (default)",
      "bitrate_kbs": 1536,
      "sample_rate": 48000,
      "num_channels": 2,
      "channel_layout_str": "2 channels"
    },
    {
      "stream_id": "0:4",
      "codec": "pcm_s16le",
      "type": "audio",
      "details": "pcm_s16le (sowt / 0x74776F73), 48000 Hz, 2 channels, s16, 1536 kb/s (default)",
      "bitrate_kbs": 1536,
      "sample_rate": 48000,
      "num_channels": 2,
      "channel_layout_str": "2 channels"
    },
    {
      "stream_id": "0:5",
      "codec": "none",
      "type": "data",
      "details": "none (tmcd / 0x64636D74), 0 kb/s (default)",
      "bitrate_kbs": 0
    }
  ],
  "format_name": "mov,mp4,m4a,3gp,3g2,mj2",
  "metadata": {
    "major_brand": "qt",
    "minor_version": "537199360",
    "compatible_brands": "qt",
    "creation_time": "2021-03-04T16:00:20.000000Z"
  }
}
```

### Example: run with tqdm to get a progressbar

If you install the tqdm extra dependency (`pip install parsed-ffmpeg[tqdm]`), you can do the following:

```python
from pathlib import Path
from parsed_ffmpeg import run_ffmpeg

input_video = Path(__file__).parent.parent / "tests/assets/input.mp4" # Adjust path
output_video = Path("output_scaled.mp4")

await run_ffmpeg(
    ["ffmpeg", "-i", input_video, "-vf", "scale=-1:1440", "-c:v", "libx264", output_video],
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

Remember that this package does not come with an ffmpeg/ffprobe binary, you have to have it in your system's PATH or point to it explicitly in your command.

```shell
pip install parsed-ffmpeg
```
or with tqdm support:
```shell
pip install parsed-ffmpeg[tqdm]
```

## API

### `run_ffmpeg`

```python
async def run_ffmpeg(
    command: list[str | Path] | str, # Command as list or single string
    on_status: Callable[[FfmpegStatus], None] | None = None,
    on_stdout: Callable[[str], None] | None = None, # stdout lines
    on_stderr: Callable[[str], None] | None = None, # stderr lines
    on_error: Callable[[list[str]], None] | None = None, # Called with error lines
    on_warning: Callable[[str], None] | None = None, # Called with warning lines
    overwrite_output: bool = False, # Add -y flag if True
    raise_on_error: bool = True, # Raise FfmpegError on failure
    print_progress_bar: bool = False, # Use tqdm for progress (requires [tqdm] extra)
    progress_bar_description: str | None = None, # Description for tqdm bar
) -> str: # Returns the full stderr output as a single string on success
    ...
```

### `FfmpegStatus`

This dataclass holds the parsed status/progress information provided via the `on_status` callback during `run_ffmpeg`. Fields are `None` if not available in a specific progress update.

```python
@dataclass
class FfmpegStatus:
    frame: int | None = None
    fps: float | None = None
    bitrate: str | None = None # e.g., "1536kbits/s"
    total_size: int | None = None # In bytes
    out_time_ms: float | None = None # Microseconds processed
    dup_frames: int | None = None
    drop_frames: int | None = None
    speed: float | None = None # e.g., 1.5x
    progress: str | None = None
    # Calculated fields:
    duration_ms: int | None = None # Estimated total duration in ms (if known)
    completion: float | None = None # Estimated completion ratio (0.0 to 1.0) (if duration known)

```

### `run_ffprobe`

```python
async def run_ffprobe(
    command: list[str | Path] | str, # Command as list or single string
    on_error: Callable[[list[str]], None] | None = None, # Called with error lines if raise_on_error=False
    on_warning: Callable[[str], None] | None = None, # Called with warning lines
    raise_on_error: bool = True, # Raise FfmpegError on failure
) -> FfprobeResult: # Returns the parsed FfprobeResult object
    ...
```

### `ffprobe types`

These are the dataclasses used within the `FfprobeResult`. Fields marked `...|None` may be `None` if the information is not present in the `ffprobe` output for that specific stream.

```python
class StreamType(StrEnum):
    VIDEO = auto()
    AUDIO = auto()
    DATA = auto()
    UNKNOWN = auto()  # For unrecognized types


@dataclass
class BaseStream:
    stream_id: str  # e.g., "0:0"
    codec: str  # e.g., "h264", "aac", "prores", "pcm_s16le"
    type: StreamType  # The type of stream
    details: str  # Raw details string from ffprobe for this stream
    bitrate_kbs: int | None = None  # Stream bitrate in kb/s


@dataclass
class VideoStream(BaseStream):
    type: StreamType = field(default=StreamType.VIDEO, init=False)
    resolution_w: int | None = None
    resolution_h: int | None = None
    fps: float | None = None


@dataclass
class AudioStream(BaseStream):
    type: StreamType = field(default=StreamType.AUDIO, init=False)
    sample_rate: int | None = None  # e.g., 44100, 48000
    num_channels: int | None = None  # e.g., 1, 2, 6
    channel_layout_str: str | None = None  # e.g., "mono", "stereo", "5.1(side)"


@dataclass
class DataStream(BaseStream):
    type: StreamType = field(default=StreamType.DATA, init=False)


@dataclass
class FfprobeResult:
    duration_ms: int | None = None  # Total duration in milliseconds
    start_time: float | None = None  # Start time in seconds
    bitrate_kbs: int | None = None  # Overall file bitrate in kb/s
    streams: list[BaseStream] = field(default_factory=list)  # List of detected streams (Video, Audio, Data, etc.)
    format_name: str | None = None  # e.g., "mov,mp4,m4a,3gp,3g2,mj2", "matroska,webm"
    metadata: dict[str, str] = field(default_factory=dict)  # Top-level metadata tags

```

### `FfmpegError`

This exception is raised by default when `ffmpeg` or `ffprobe` returns a non-zero exit code.

```python
class FfmpegError(Exception):
    def __init__(
        self,
        err_lines: Sequence[str],
        full_command: Sequence[str | Path], # The exact command executed
        user_command: str | Sequence[str | Path], # The command user provided
    ) -> None: ...

    def format_error(self) -> str: # Get the formatted error string shown above
        ...

    # Attributes:
    # err_lines: Sequence[str] - List of lines from stderr considered errors
    # full_command: Sequence[str | Path] - The exact command executed, including added flags like -y, -progress
    # user_command: str | Sequence[str | Path] - The command originally passed to run_ffmpeg/run_ffprobe

```

## Changing ffmpeg install location

Just replace the first part of your command (`ffmpeg` or `ffprobe`) with the full path to the executable.

Example:

```python
await run_ffmpeg(["C:/apps/ffmpeg/bin/ffmpeg.exe", "-i", "input.mp4", "-c:v", "libx264", "output.mp4"])
# or
result = await run_ffprobe(["/usr/local/bin/ffprobe", "input.mp4"])
```

## License

MIT