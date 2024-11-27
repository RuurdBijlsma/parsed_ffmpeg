"""Example of ffprobe."""

import asyncio
from pathlib import Path

from parsed_ffmpeg import FfmpegError
from parsed_ffmpeg.runner import run_ffprobe


async def probe_video() -> None:
    input_video = Path(__file__).parent.parent / "tests/assets/input.mp4"
    try:
        result = await run_ffprobe(f"ffprobe {input_video}")
        print("Done!" + str(result))
    except FfmpegError as e:
        print(f"ffprobe failed with error: {e}")


if __name__ == "__main__":
    asyncio.run(probe_video())
