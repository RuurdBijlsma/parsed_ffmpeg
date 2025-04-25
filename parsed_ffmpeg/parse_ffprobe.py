import re

from parsed_ffmpeg.types import (
    AudioStream,
    BaseStream,
    DataStream,
    FfprobeResult,
    StreamType,
    VideoStream,
)


def _parse_duration_to_ms(duration_str: str) -> int | None:
    """Parses HH:MM:SS.ms duration string to milliseconds."""
    match = re.match(r"(\d{2}):(\d{2}):(\d{2})\.(\d+)", duration_str)
    if match:
        h, m, s, ms_part = map(int, match.groups())
        # Handle varying ms precision (e.g., .18 vs .180)
        total_ms = (h * 3600 + m * 60 + s) * 1000
        total_ms += int(str(ms_part).ljust(3, "0")[:3])  # Ensure 3 digits for ms
        return total_ms
    return None


def _parse_bitrate(bitrate_str: str) -> int | None:
    """Parses 'N kb/s' or 'N b/s' string to integer kb/s."""
    if bitrate_str is None or bitrate_str.lower() == "n/a":
        return None
    match = re.match(r"(\d+)\s*(k?)b/s", bitrate_str.lower())
    if match:
        value, k = match.groups()
        value = int(value)
        if not k:  # If it was just b/s, convert to kb/s
            value = round(value / 1000)
        return value
    return None


def _try_float(value: str | None) -> float | None:
    """Safely convert string to float."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _try_int(value: str | None) -> int | None:
    """Safely convert string to int."""
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


# --- Main Parsing Function ---


def parse_ffprobe_output(output: str) -> FfprobeResult:
    """
    Parses the text output of ffprobe into an FfprobeResult object.
    """
    result = FfprobeResult()
    current_stream: Optional[BaseStream] = None  # Correct type hint
    in_input_metadata = False

    lines = output.splitlines()

    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue

        # --- Input Section ---
        input_match = re.match(r"Input #\d+,\s*([^,]+),\s*from", line)
        if input_match:
            result.format_name = input_match.group(1).strip()
            in_input_metadata = False
            continue

        # --- Duration/Start/Bitrate ---
        duration_match = re.search(
            r"Duration:\s*([\d:.]+),\s*start:\s*([\d.]+),\s*bitrate:\s*(\d+\s*k?b/s|N/A)",  # Allow kb/s or b/s
            line,
            re.IGNORECASE,
        )
        if duration_match:
            result.duration_ms = _parse_duration_to_ms(duration_match.group(1))
            result.start_time = _try_float(duration_match.group(2))
            # Handle N/A explicitly for overall bitrate
            bitrate_val = duration_match.group(3)
            if bitrate_val.upper() != "N/A":
                result.bitrate_kbs = _parse_bitrate(bitrate_val)
            else:
                result.bitrate_kbs = None  # Or 0, depending on desired behavior for N/A
            continue

        # --- Metadata Sections ---
        if line.lower() == "metadata:":
            if any(l.strip().startswith("Input #") for l in lines[max(0, i - 2) : i]):
                in_input_metadata = True
            elif current_stream:  # Check if we just processed a stream line
                # Heuristic: If the previous non-empty line was a Stream line, this is stream metadata
                prev_line_idx = i - 1
                while prev_line_idx >= 0 and not lines[prev_line_idx].strip():
                    prev_line_idx -= 1
                if prev_line_idx >= 0 and lines[prev_line_idx].strip().startswith("Stream #"):
                    in_input_metadata = False  # It's stream metadata
                else:
                    # Could still be input metadata if it appears after duration but before first stream
                    in_input_metadata = True

            else:  # Likely input metadata if before any streams
                in_input_metadata = True

            continue  # Skip the "Metadata:" line itself

        # --- Key-Value Metadata lines ---
        # Be more specific to avoid matching stream lines accidentally
        metadata_match = re.match(r"(\s*)(\w+)\s*:\s*(.*)", line)
        # Check indentation to distinguish from stream lines if necessary,
        # but relying on state (in_input_metadata) and stream regex matching first is better.
        # The main check is that it doesn't start with "Stream #"
        if metadata_match and not line.strip().startswith("Stream #"):
            _indent, key, value = metadata_match.groups()
            key = key.strip()
            value = value.strip()
            if in_input_metadata:
                result.metadata[key] = value
            elif current_stream:
                # Add to stream metadata if needed (requires adding a metadata dict to streams)
                # if not hasattr(current_stream, 'metadata'):
                #     current_stream.metadata = {}
                # current_stream.metadata[key] = value
                pass  # Currently ignoring stream metadata
            continue  # Processed this line

        # --- Stream Definition ---
        stream_match = re.match(
            r"Stream #(\d+:\d+)(?:\[(0x\w+)\])?\(?(\w+)?\)?: (Video|Audio|Data|Subtitle):\s*(.*)",
            line,
            re.IGNORECASE,
        )
        if stream_match:
            in_input_metadata = False  # Definitely not input metadata anymore
            stream_id, _hex_id, _lang, stream_type_str, stream_details_raw = stream_match.groups()
            stream_type_str = stream_type_str.upper()
            stream_details_raw = stream_details_raw.strip()

            try:
                stream_type = StreamType[stream_type_str]
            except KeyError:
                stream_type = StreamType.UNKNOWN

            codec = stream_details_raw.split(",")[0].split(" ")[0]  # Basic guess
            # Try to find bitrate within the stream details
            stream_bitrate_str = None
            bitrate_search = re.search(r"(\d+\s*k?b/s)", stream_details_raw, re.IGNORECASE)
            if bitrate_search:
                stream_bitrate_str = bitrate_search.group(1)

            # Base info common to all streams THAT ARE ACCEPTED BY BaseStream.__init__
            base_stream_init_args = {
                "stream_id": stream_id,
                "codec": codec,  # Will be refined below
                "details": stream_details_raw,
                "bitrate_kbs": _parse_bitrate(stream_bitrate_str),
            }
            # The 'type' field is handled differently depending on the final class

            # --- Video Stream Parsing ---
            if stream_type == StreamType.VIDEO:
                video_match = re.match(
                    # Make SAR/DAR group optional and non-capturing (?:...)
                    r"(\w+)(?:\s*\((.*?)\))?,\s*(.*?),\s*(\d+)x(\d+)(?:\[SAR.*?DAR.*?\])?(?:,\s*(\d+\s*k?b/s))?.*?,\s*(\d+\.?\d*)\s*fps",
                    stream_details_raw,
                    re.IGNORECASE,
                )
                if video_match:
                    codec, _profile, _pix_fmt, w, h, specific_bitrate_str, fps = (
                        video_match.groups()
                    )
                    current_stream = VideoStream(
                        **base_stream_init_args,  # Unpack args *without* 'type'
                        resolution_w=_try_int(w),
                        resolution_h=_try_int(h),
                        fps=_try_float(fps),
                    )
                    current_stream.codec = codec  # Refine codec
                    # Override bitrate if found specifically in video details
                    specific_bitrate = _parse_bitrate(specific_bitrate_str)
                    if specific_bitrate is not None:
                        current_stream.bitrate_kbs = specific_bitrate

                else:
                    # Fallback if regex fails
                    current_stream = VideoStream(**base_stream_init_args)

            # --- Audio Stream Parsing ---
            elif stream_type == StreamType.AUDIO:
                # Make bitrate group optional at the end
                audio_match = re.match(
                    r"(\w+)(?:\s*\(.*?\))?,\s*(\d+)\s*Hz,\s*([^,]+?),\s*([^,]+?)(?:,\s*(\d+\s*k?b/s))?",
                    stream_details_raw,
                    re.IGNORECASE,
                )
                if audio_match:
                    codec, sample_rate_str, channels_str, _format, specific_bitrate_str = (
                        audio_match.groups()
                    )
                    num_channels = None
                    chan_match = re.search(r"(\d+)\s*channel", channels_str, re.IGNORECASE)
                    if chan_match:
                        num_channels = _try_int(chan_match.group(1))
                    elif channels_str.lower() == "mono":
                        num_channels = 1
                    elif channels_str.lower() == "stereo":
                        num_channels = 2

                    current_stream = AudioStream(
                        **base_stream_init_args,  # Unpack args *without* 'type'
                        sample_rate=_try_int(sample_rate_str),
                        num_channels=num_channels,
                        channel_layout_str=channels_str.strip(),
                    )
                    current_stream.codec = codec  # Refine codec
                    # Override bitrate if found specifically in audio details
                    specific_bitrate = _parse_bitrate(specific_bitrate_str)
                    if specific_bitrate is not None:
                        current_stream.bitrate_kbs = specific_bitrate

                else:
                    # Fallback if regex fails
                    current_stream = AudioStream(**base_stream_init_args)

            # --- Data Stream Parsing ---
            elif stream_type == StreamType.DATA:
                data_match = re.match(
                    r"(\w+)(?:\s*\(.*?\))?(?:,\s*(\d+\s*k?b/s))?", stream_details_raw, re.IGNORECASE
                )
                if data_match:
                    codec, specific_bitrate_str = data_match.groups()
                    current_stream = DataStream(
                        **base_stream_init_args
                    )  # Unpack args *without* 'type'
                    current_stream.codec = codec
                    # Override bitrate if found specifically in data details
                    specific_bitrate = _parse_bitrate(specific_bitrate_str)
                    if specific_bitrate is not None:
                        current_stream.bitrate_kbs = specific_bitrate
                    # Often 0 or None, which base_stream_init_args might already have handled
                    elif current_stream.bitrate_kbs is None:
                        current_stream.bitrate_kbs = 0  # Default data bitrate to 0 if not found
                else:
                    current_stream = DataStream(**base_stream_init_args)
                    if current_stream.bitrate_kbs is None:
                        current_stream.bitrate_kbs = 0

            # --- Unknown Stream Type ---
            else:
                # For BaseStream, we *do* need to provide the type
                current_stream = BaseStream(**base_stream_init_args, type=stream_type)

            if current_stream:
                result.streams.append(current_stream)
            continue  # Processed stream line

        # --- Ignore other lines ---

    return result
