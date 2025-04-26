import re

from parsed_ffmpeg.types import (
    AudioStream,
    BaseStream,
    DataStream,
    FfprobeResult,
    StreamType,
    SubtitleStream,
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


def _parse_bitrate(bitrate_str: str | None) -> int | None:
    """Parses 'N kb/s' or 'N b/s' string to integer kb/s."""
    if bitrate_str is None or bitrate_str.lower() == "n/a":
        return None
    match = re.match(r"(\d+)\s*(k?)b/s", bitrate_str.lower().strip())
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
        # Handle potential float strings like "10.0" before int conversion
        return int(float(value))
    except (ValueError, TypeError):
        return None


# --- Main Parsing Function ---


def parse_ffprobe_output(output: str) -> FfprobeResult:
    """
    Parses the text output of ffprobe into an FfprobeResult object.
    """
    result = FfprobeResult()
    current_stream: BaseStream | None = None
    in_input_metadata = False

    lines = output.splitlines()

    for i, raw_line in enumerate(lines):
        line = raw_line.strip()
        if not line:
            continue

        # --- Input Section ---
        input_match = re.match(r"Input #\d+,\s*(.*?),\s*from", line, re.IGNORECASE)
        if input_match:
            result.format_name = input_match.group(1).strip()
            in_input_metadata = False
            current_stream = None  # Reset current stream when new input found
            continue

        # --- Duration/Start/Bitrate ---
        # Allow N/A for bitrate
        duration_match = re.search(
            r"Duration:\s*([\d:.]+),\s*start:\s*([\d.]+),\s*bitrate:\s*(\d+\s*k?b/s|N/A)",
            line,
            re.IGNORECASE,
        )
        if duration_match:
            result.duration_ms = _parse_duration_to_ms(duration_match.group(1))
            result.start_time = _try_float(duration_match.group(2))
            bitrate_val = duration_match.group(3)
            if bitrate_val.upper() != "N/A":
                result.bitrate_kbs = _parse_bitrate(bitrate_val)
            else:
                result.bitrate_kbs = None
            continue

        # --- Metadata Sections ---
        if line.lower() == "metadata:":
            # Determine if it's input metadata or stream metadata
            is_likely_stream_metadata = False
            if current_stream:
                prev_line_idx = i - 1
                while prev_line_idx >= 0 and not lines[prev_line_idx].strip():
                    prev_line_idx -= 1
                if prev_line_idx >= 0 and lines[prev_line_idx].strip().startswith("Stream #"):
                    is_likely_stream_metadata = True

            if is_likely_stream_metadata:
                in_input_metadata = False
            else:
                # Could be input metadata if it's after Input # or before first Stream #
                # Check previous lines for "Input #"
                is_after_input = any(
                    line.strip().startswith("Input #") for line in lines[max(0, i - 3) : i]
                )
                # Check if any stream has been defined yet
                is_before_any_stream = not any(s for s in result.streams)

                in_input_metadata = is_after_input or is_before_any_stream

            continue  # Skip the "Metadata:" line itself

        # --- Key-Value Metadata lines ---
        # Ensure it doesn't start with "Stream #" or other known section headers
        if (
            not line.startswith("Stream #")
            and not line.startswith("Duration:")
            and not line.startswith("Input #")
        ):
            metadata_match = re.match(r"(\w+)\s*:\s*(.*)", line)
            if metadata_match:
                key, value = metadata_match.groups()
                key = key.strip()
                value = value.strip()
                if (
                    in_input_metadata and result.format_name
                ):  # Only add input metadata if format_name is set
                    result.metadata[key] = value
                elif current_stream:
                    # Ensure metadata dict exists (though default_factory should handle this)
                    if not hasattr(current_stream, "metadata") or current_stream.metadata is None:
                        current_stream.metadata = {}
                    current_stream.metadata[key] = value
                # else: metadata line appeared unexpectedly, ignore or log
                continue  # Processed metadata line

        # --- Stream Definition ---
        # Updated regex to include Subtitle
        stream_match = re.match(
            r"Stream #(\d+:\d+)(?:\[(0x\w+)\])?\(?(\w+)?\)?: (Video|Audio|Data|Subtitle):\s*(.*)",
            line,
            re.IGNORECASE,
        )
        if stream_match:
            in_input_metadata = False  # Definitely not input metadata anymore
            current_stream = None  # Reset current stream for the new line
            stream_id, _hex_id, lang_code, stream_type_str, stream_details_raw = (
                stream_match.groups()
            )
            stream_type_str = stream_type_str.upper()
            stream_details_raw = stream_details_raw.strip()

            try:
                stream_type = StreamType[stream_type_str]
            except KeyError:
                stream_type = StreamType.UNKNOWN

            # Basic codec guess (first word)
            codec_parts = stream_details_raw.split(",")[0].split("(")
            codec = codec_parts[0].strip()

            # Try to find bitrate within the stream details (less common for subs)
            stream_bitrate_str = None
            bitrate_search = re.search(r"(\d+\s*k?b/s)", stream_details_raw, re.IGNORECASE)
            if bitrate_search:
                stream_bitrate_str = bitrate_search.group(1)

            parsed_bitrate = _parse_bitrate(stream_bitrate_str)  # _parse_bitrate handles None

            # Base info common to all streams
            base_stream_init_args = {
                "stream_id": stream_id,
                "codec": codec,
                "details": stream_details_raw,
                "bitrate_kbs": parsed_bitrate,
                # 'type' is handled by the specific class or BaseStream fallback
                # 'metadata' is added later
            }

            # --- Video Stream Parsing ---
            if stream_type == StreamType.VIDEO:
                video_match = re.match(
                    # Make profile/pix_fmt optional non-capturing,
                    # make SAR/DAR optional non-capturing
                    r"(\w+)(?:\s*\((.*?)\))?,\s*(.*?),\s*(\d+)x(\d+)"
                    r"(?:\[SAR.*?DAR.*?])?(?:,\s*(\d+\s*k?b/s))?.*?,\s*([\d.]+)\s*fps",
                    stream_details_raw,
                    re.IGNORECASE,
                )
                if video_match:
                    v_codec, _profile, _pix_fmt, w, h, specific_bitrate_str, fps = (
                        video_match.groups()
                    )
                    current_stream = VideoStream(
                        **base_stream_init_args,  # type: ignore[arg-type]
                        resolution_w=_try_int(w),
                        resolution_h=_try_int(h),
                        fps=_try_float(fps),
                    )
                    current_stream.codec = v_codec.strip()  # Refine codec
                    specific_bitrate = _parse_bitrate(specific_bitrate_str)
                    if specific_bitrate is not None:
                        current_stream.bitrate_kbs = specific_bitrate
                else:
                    # Fallback if detailed regex fails
                    current_stream = VideoStream(**base_stream_init_args)  # type: ignore[arg-type]

            # --- Audio Stream Parsing ---
            elif stream_type == StreamType.AUDIO:
                # Make profile/bitrate optional
                audio_match = re.match(
                    r"(\w+)(?:\s*\(.*?\))?,\s*([\d.]+)\s*Hz,\s*([^,]+?),\s*([^,]+?)(?:,\s*(\d+\s*k?b/s))?",
                    stream_details_raw,
                    re.IGNORECASE,
                )
                if audio_match:
                    a_codec, sample_rate_str, channels_str, _format, specific_bitrate_str = (
                        audio_match.groups()
                    )
                    num_channels = None
                    chan_match = re.search(
                        r"(\d+)\s*channel|mono|stereo", channels_str, re.IGNORECASE
                    )
                    if chan_match:
                        if chan_match.group(1):
                            num_channels = _try_int(chan_match.group(1))
                        elif "mono" in chan_match.group(0).lower():
                            num_channels = 1
                        elif "stereo" in chan_match.group(0).lower():
                            num_channels = 2

                    current_stream = AudioStream(
                        **base_stream_init_args,  # type: ignore[arg-type]
                        sample_rate=_try_int(sample_rate_str),
                        num_channels=num_channels,
                        channel_layout_str=channels_str.strip(),
                    )
                    current_stream.codec = a_codec.strip()  # Refine codec
                    specific_bitrate = _parse_bitrate(specific_bitrate_str)
                    if specific_bitrate is not None:
                        current_stream.bitrate_kbs = specific_bitrate
                else:
                    # Fallback if detailed regex fails
                    current_stream = AudioStream(**base_stream_init_args)  # type: ignore[arg-type]

            # --- Data Stream Parsing ---
            elif stream_type == StreamType.DATA:
                # Simple regex for codec and optional bitrate
                data_match = re.match(
                    r"(\w+)(?:\s*\(.*?\))?(?:,\s*(\d+\s*k?b/s))?", stream_details_raw, re.IGNORECASE
                )
                if data_match:
                    d_codec, specific_bitrate_str = data_match.groups()
                    current_stream = DataStream(**base_stream_init_args)  # type: ignore[arg-type]
                    current_stream.codec = d_codec.strip()  # Refine codec
                    specific_bitrate = _parse_bitrate(specific_bitrate_str)
                    if specific_bitrate is not None:
                        current_stream.bitrate_kbs = specific_bitrate
                    elif current_stream.bitrate_kbs is None:
                        current_stream.bitrate_kbs = 0  # Default data bitrate
                else:
                    # Fallback
                    current_stream = DataStream(**base_stream_init_args)  # type: ignore[arg-type]
                    if current_stream.bitrate_kbs is None:
                        current_stream.bitrate_kbs = 0

            # --- Subtitle Stream Parsing (Added) ---
            elif stream_type == StreamType.SUBTITLE:
                # Subtitles rarely have structured details like video/audio on this line
                # Codec is the main info, already extracted in base_stream_init_args
                # Bitrate is usually N/A or 0, handled by base parsing
                subtitle_match = re.match(
                    r"(\w+)(?:\s*\((.*?)\))?", stream_details_raw, re.IGNORECASE
                )
                current_stream = SubtitleStream(**base_stream_init_args)  # type: ignore[arg-type]
                if subtitle_match:
                    s_codec, _s_format_hint = subtitle_match.groups()
                    current_stream.codec = s_codec.strip()  # Refine codec

            # --- Unknown Stream Type ---
            else:  # Includes StreamType.UNKNOWN
                # For BaseStream, we need to provide the type explicitly
                current_stream = BaseStream(**base_stream_init_args, type=stream_type)  # type: ignore[arg-type]

            # --- Finalize Stream ---
            if current_stream:
                # Add language code if detected in the stream definition line `(lang)`
                if lang_code and hasattr(current_stream, "metadata"):
                    if not current_stream.metadata:
                        current_stream.metadata = {}
                    current_stream.metadata["language"] = lang_code  # Add as metadata

                result.streams.append(current_stream)
            continue  # Processed stream line

    return result
