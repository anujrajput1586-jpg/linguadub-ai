from app.models.entities import Segment
from app.services.audio_timing import atempo_chain
from app.services.subtitles import build_srt, build_vtt, format_srt_time


def test_subtitle_timestamps_and_language_text():
    segments = [Segment(start=1.2346, end=3.0, original_text="主轴 rotates", translated_text="स्पिंडल घूमता है")]
    srt = build_srt(segments)
    vtt = build_vtt(segments)
    assert "00:00:01,235 --> 00:00:03,000" in srt
    assert "स्पिंडल घूमता है" in srt
    assert "WEBVTT" in vtt
    assert "00:00:01.235 --> 00:00:03.000" in vtt
    assert format_srt_time(-1) == "00:00:00,000"


def test_atempo_chain_stays_within_ffmpeg_filter_limits():
    assert atempo_chain(2.5) == "atempo=2.0,atempo=1.25000"
    assert atempo_chain(0.25) == "atempo=0.5,atempo=0.50000"
