import re
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from models.data_models import SubtitleChunk
from config import (
    KOREAN_FONT_PATH,
    SUBTITLE_FONT_SIZE,
    SUBTITLE_COLOR,
    SUBTITLE_STROKE_COLOR,
    SUBTITLE_STROKE_WIDTH,
    SUBTITLE_BOTTOM_MARGIN,
    VIDEO_WIDTH,
    VIDEO_HEIGHT,
)

_SENTENCE_ENDINGS = re.compile(r"(?<=[.!?。])\s*|(?<=[,，])\s+")
_NATURAL_BREAKS = re.compile(r"(?<=그리고|하지만|그런데|그래서|그러나|그러면|그렇지만)\s*")
MAX_CHARS_PER_LINE = 15


def chunk_narration(narration: str, audio_duration: float) -> list[SubtitleChunk]:
    # split into sentences first
    raw_sentences = re.split(r"(?<=[.!?。,，])\s*", narration.strip())
    sentences = [s.strip() for s in raw_sentences if s.strip()]

    # further split long sentences at natural breaks
    chunks_text = []
    for sent in sentences:
        if len(sent) <= MAX_CHARS_PER_LINE:
            chunks_text.append(sent)
        else:
            # split at natural connectors
            parts = re.split(r"(그리고|하지만|그런데|그래서|그러나|그러면)", sent)
            current = ""
            for part in parts:
                if len(current) + len(part) <= MAX_CHARS_PER_LINE * 2:
                    current += part
                else:
                    if current:
                        chunks_text.append(current.strip())
                    current = part
            if current:
                chunks_text.append(current.strip())

    # remove empty
    chunks_text = [c for c in chunks_text if c]
    if not chunks_text:
        return []

    # assign timestamps proportional to char count
    total_chars = sum(len(c) for c in chunks_text)
    chunks = []
    elapsed = 0.0
    for text in chunks_text:
        duration = (len(text) / total_chars) * audio_duration
        chunks.append(SubtitleChunk(
            text=text,
            start_sec=elapsed,
            end_sec=elapsed + duration,
        ))
        elapsed += duration

    return chunks


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(KOREAN_FONT_PATH, size)
    except OSError:
        return ImageFont.load_default()


def render_subtitle_frame(
    frame: np.ndarray,
    text: str,
    font_size: int = SUBTITLE_FONT_SIZE,
) -> np.ndarray:
    img = Image.fromarray(frame, "RGB")
    draw = ImageDraw.Draw(img)
    font = _load_font(font_size)

    # wrap text if too long
    lines = _wrap_text(text, font, draw, VIDEO_WIDTH - 40)

    line_height = font_size + 8
    total_height = len(lines) * line_height
    y = VIDEO_HEIGHT - SUBTITLE_BOTTOM_MARGIN - total_height

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        text_w = bbox[2] - bbox[0]
        x = (VIDEO_WIDTH - text_w) // 2

        # draw stroke (8 directions)
        sw = SUBTITLE_STROKE_WIDTH
        for dx in range(-sw, sw + 1):
            for dy in range(-sw, sw + 1):
                if dx == 0 and dy == 0:
                    continue
                draw.text((x + dx, y + dy), line, font=font, fill=SUBTITLE_STROKE_COLOR)

        # draw main white text
        draw.text((x, y), line, font=font, fill=SUBTITLE_COLOR)
        y += line_height

    return np.array(img)


def _wrap_text(text: str, font, draw, max_width: int) -> list[str]:
    if len(text) <= MAX_CHARS_PER_LINE:
        return [text]
    mid = len(text) // 2
    return [text[:mid], text[mid:]]


def burn_subtitles(
    input_video_path: str,
    subtitle_chunks: list[SubtitleChunk],
    output_path: str,
) -> str:
    from moviepy.editor import VideoFileClip

    video = VideoFileClip(input_video_path)

    chunk_list = subtitle_chunks

    def process_frame(get_frame, t):
        frame = get_frame(t)
        active = next(
            (c for c in chunk_list if c.start_sec <= t < c.end_sec), None
        )
        if active:
            frame = render_subtitle_frame(frame, active.text)
        return frame

    processed = video.fl(process_frame)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    processed.write_videofile(
        output_path,
        codec="libx264",
        audio_codec="aac",
        logger=None,
        verbose=False,
    )
    video.close()
    processed.close()
    print(f"  [자막] 자막 삽입 완료: {output_path}")
    return output_path
