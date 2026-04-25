import os
import requests
from pathlib import Path


class TTSError(Exception):
    pass


def generate_audio(
    text: str,
    output_path: str,
    voice_id: str | None = None,
    stability: float = 0.75,
    similarity_boost: float = 0.85,
    style: float = 0.40,
    model_id: str = "eleven_multilingual_v2",
) -> tuple[str, float]:
    """Returns (output_path, duration_seconds)."""
    api_key = os.getenv("ELEVENLABS_API_KEY")
    vid = voice_id or os.getenv("ELEVENLABS_VOICE_ID")
    if not api_key or not vid:
        raise TTSError("ELEVENLABS_API_KEY 또는 ELEVENLABS_VOICE_ID가 설정되지 않았습니다.")

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{vid}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {
        "text": text,
        "model_id": model_id,
        "voice_settings": {
            "stability": stability,
            "similarity_boost": similarity_boost,
            "style": style,
            "use_speaker_boost": True,
        },
    }

    resp = requests.post(url, json=payload, headers=headers, timeout=60, stream=True)
    if resp.status_code != 200:
        raise TTSError(f"ElevenLabs API 오류 {resp.status_code}: {resp.text[:200]}")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=4096):
            f.write(chunk)

    duration = get_audio_duration(output_path)
    print(f"  [TTS] 음성 생성 완료: {duration:.1f}초 → {output_path}")
    return output_path, duration


def get_audio_duration(audio_path: str) -> float:
    try:
        from mutagen.mp3 import MP3
        audio = MP3(audio_path)
        return audio.info.length
    except Exception:
        # fallback: estimate from file size (128kbps ≈ 16KB/s)
        size = Path(audio_path).stat().st_size
        return size / 16000
