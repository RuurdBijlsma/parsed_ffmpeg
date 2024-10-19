"""Example of ffmpeg with progress bar."""

import asyncio
from pathlib import Path

from parsed_ffmpeg import run_ffmpeg


async def process_video() -> None:
    input_video = Path(__file__).parent.parent / "tests/assets/input.mp4"
    await run_ffmpeg(
        f"ffmpeg -i {input_video} -vf scale=-1:1440 -c:v libx264 output.mp4",
        print_progress_bar=True,
        progress_bar_description=input_video.name,
        overwrite_output=True,
    )


if __name__ == "__main__":
    asyncio.run(process_video())
