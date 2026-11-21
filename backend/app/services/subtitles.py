from app.models.entities import Segment


def format_srt_time(seconds: float) -> str:
    milliseconds = max(0, round(seconds * 1000))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    whole_seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02}:{minutes:02}:{whole_seconds:02},{milliseconds:03}"


def format_vtt_time(seconds: float) -> str:
    return format_srt_time(seconds).replace(",", ".")


def build_srt(segments: list[Segment], translated: bool = True) -> str:
    blocks = []
    for number, segment in enumerate(sorted(segments, key=lambda item: item.start), start=1):
        text = (segment.translated_text if translated else segment.original_text) or ""
        blocks.append(f"{number}\n{format_srt_time(segment.start)} --> {format_srt_time(segment.end)}\n{text.strip()}")
    return "\n\n".join(blocks) + ("\n" if blocks else "")


def build_vtt(segments: list[Segment], translated: bool = True) -> str:
    body = build_srt(segments, translated).replace(",", ".")
    body = "\n".join(line for line in body.splitlines() if not line.strip().isdigit())
    return "WEBVTT\n\n" + body
