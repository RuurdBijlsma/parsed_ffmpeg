import re

from parsed_ffmpeg.types import BaseStream, VideoStream, StreamType, AudioStream, \
    FfprobeResult


def parse_ffprobe_output(output) -> FfprobeResult:
    # Dictionary to store extracted information
    duration_ms: int = -1
    start_time: float = -1
    bitrate_kbs: int = -1
    streams: list[BaseStream] = []

    # Extract video duration and bitrate
    duration_match = re.search(r"Duration: (\S+), start: (\S+), bitrate: (\S+) kb/s",
                               output)
    if duration_match:
        duration_str = duration_match.group(1)
        # Parse the duration (HH:MM:SS.xx)
        hours, minutes, seconds = map(
            float,
            re.split(':', duration_str)
        )
        duration_ms = int(
            hours * 3600000 + minutes * 60000 + seconds * 1000
        )

        start_time = float(duration_match.group(2))
        bitrate_kbs = int(duration_match.group(3))

    # Parse streams
    stream_pattern = re.compile(
        r"Stream #\d+:\d+\[.*?\]\(.*?\): (Video|Audio): (.+?)\s+\((.*?)\), (.+)"
    )
    for stream_match in stream_pattern.finditer(output):
        stream_type = stream_match.group(1)
        stream_codec = stream_match.group(2)
        stream_details = stream_match.group(4)
        if stream_type == 'Video':
            # Extract additional video information
            video_details_match = re.search(
                r"(\d+x\d+).*?, (\d+) kb/s, (\d+) fps", stream_details
            )
            if video_details_match:
                stream_resolution = video_details_match.group(1).split("x")
                stream_bitrate = int(video_details_match.group(2))
                stream_fps = int(video_details_match.group(3))
                streams.append(VideoStream(
                    type=StreamType.VIDEO,
                    details=stream_details,
                    bitrate_kbs=stream_bitrate,
                    codec=stream_codec,
                    resolution_w=int(stream_resolution[0]),
                    resolution_h=int(stream_resolution[1]),
                    fps=stream_fps,
                ))
        elif stream_type == 'Audio':
            # Extract additional audio information
            audio_details_match = re.search(
                r"(\d+) Hz, (.+?), (\d+) kb/s", stream_details
            )
            if audio_details_match:
                stream_sample_rate = int(audio_details_match.group(1))
                stream_channels = audio_details_match.group(2).split(", ")
                stream_bitrate = int(audio_details_match.group(3))
                streams.append(AudioStream(
                    type=StreamType.AUDIO,
                    details=stream_details,
                    channels=stream_channels,
                    bitrate_kbs=stream_bitrate,
                    codec=stream_codec,
                    sample_rate=stream_sample_rate,
                ))

    return FfprobeResult(
        bitrate_kbs=bitrate_kbs,
        duration_ms=duration_ms,
        start_time=start_time,
        streams=streams,
    )
