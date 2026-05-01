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
    """
    한국어 TTS 생성. ElevenLabs 키가 있으면 ElevenLabs 사용,
    없으면 gTTS(Google, 무료)로 자동 폴백.
    Returns (output_path, duration_seconds).
    """
    api_key = os.getenv("ELEVENLABS_API_KEY")
    vid = voice_id or os.getenv("ELEVENLABS_VOICE_ID")

    if api_key and vid:
        return _elevenlabs(text, output_path, vid, api_key, stability, similarity_boost, style, model_id)
    else:
        print("  [TTS] ElevenLabs 키 없음 → gTTS(Google, 무료)로 대체")
        return _gtts(text, output_path)


def _elevenlabs(
    text: str,
    output_path: str,
    vid: str,
    api_key: str,
    stability: float,
    similarity_boost: float,
    style: float,
    model_id: str,
) -> tuple[str, float]:
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
    print(f"  [TTS] ElevenLabs 음성 생성: {duration:.1f}초 → {output_path}")
    return output_path, duration


def _gtts(text: str, output_path: str) -> tuple[str, float]:
    # 1) edge-tts 시도
    try:
        return _edge_tts(text, output_path)
    except Exception:
        pass
    # 2) espeak-ng 오프라인 폴백 (SSL 불필요)
    try:
        return _espeak(text, output_path)
    except Exception as e:
        raise TTSError(f"모든 TTS 실패: {e}")


def _edge_tts(text: str, output_path: str) -> tuple[str, float]:
    import asyncio
    import ssl
    import aiohttp
    import edge_tts

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # 서버 환경의 자체 서명 인증서 우회
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    async def _run():
        connector = aiohttp.TCPConnector(ssl=ssl_ctx)
        async with aiohttp.ClientSession(connector=connector) as session:
            communicate = edge_tts.Communicate(text, voice="ko-KR-SunHiNeural")
            communicate._session = session
            await communicate.save(output_path)

    asyncio.run(_run())
    duration = get_audio_duration(output_path)
    print(f"  [TTS] edge-tts 음성 생성 (ko-KR-SunHiNeural): {duration:.1f}초 → {output_path}")
    return output_path, duration


def _espeak(text: str, output_path: str) -> tuple[str, float]:
    """espeak-ng 오프라인 한국어 TTS → WAV 생성 후 MP3로 변환"""
    import subprocess
    import imageio_ffmpeg

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    wav_path = output_path.replace(".mp3", ".wav")

    # espeak-ng로 WAV 생성 (-s 130: 속도, -p 50: 피치)
    result = subprocess.run(
        ["espeak-ng", "-v", "ko", "-s", "130", "-p", "50", "-w", wav_path, text],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise TTSError(f"espeak-ng 오류: {result.stderr}")

    # ffmpeg으로 WAV → MP3 변환
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run(
        [ffmpeg, "-y", "-i", wav_path, "-codec:a", "libmp3lame", "-q:a", "4", output_path],
        capture_output=True,
    )
    Path(wav_path).unlink(missing_ok=True)

    duration = get_audio_duration(output_path)
    print(f"  [TTS] espeak-ng 오프라인 음성 생성: {duration:.1f}초 → {output_path}")
    return output_path, duration


def get_audio_duration(audio_path: str) -> float:
    try:
        from mutagen.mp3 import MP3
        audio = MP3(audio_path)
        return audio.info.length
    except Exception:
        size = Path(audio_path).stat().st_size
        return size / 16000
