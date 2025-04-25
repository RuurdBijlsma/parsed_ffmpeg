"""Example of ffmpeg with error handling and getting the status as it comes in."""

import asyncio
from pathlib import Path

from parsed_ffmpeg import run_ffmpeg, FfmpegError


async def process_video() -> None:
    input_video = Path(__file__).parent.parent / "tests/assets/input.mp4"
    try:
        await run_ffmpeg(
            f"ffmpeg -i {input_video} -c:v libx264 output.mp4",
            on_status=lambda status: print(
                f"We're: {status.completion * 100:.1f}% there!"  # type: ignore[operator]
            ),
            overwrite_output=True,
        )
        print("Done!")
    except FfmpegError as e:
        print(f"ffmpeg failed with error: {e}")


if __name__ == "__main__":
    asyncio.run(process_video())
