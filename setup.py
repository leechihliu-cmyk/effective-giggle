#!/usr/bin/env python3
"""One-time setup: download Korean font and verify API keys."""
import os
import sys
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

FONT_URL = "https://github.com/naver/nanumfont/raw/master/fonts/NanumGothicBold.ttf"
FONT_PATH = Path(__file__).parent / "assets" / "fonts" / "NanumGothicBold.ttf"

FALLBACK_FONT_URL = (
    "https://github.com/googlefonts/nanum/raw/main/fonts/ttf/NanumGothicBold.ttf"
)


def download_font():
    if FONT_PATH.exists():
        print(f"[OK] 폰트 이미 존재: {FONT_PATH}")
        return
    FONT_PATH.parent.mkdir(parents=True, exist_ok=True)
    print("한글 폰트 다운로드 중 (NanumGothicBold)...")
    for url in [FONT_URL, FALLBACK_FONT_URL]:
        try:
            resp = requests.get(url, timeout=30)
            if resp.status_code == 200 and len(resp.content) > 10000:
                FONT_PATH.write_bytes(resp.content)
                print(f"[OK] 폰트 저장됨: {FONT_PATH} ({len(resp.content):,} bytes)")
                return
        except Exception as e:
            print(f"  실패 ({url}): {e}")

    # apt fallback
    print("GitHub에서 다운로드 실패. apt로 설치 시도...")
    ret = os.system("apt-get install -y fonts-nanum 2>/dev/null")
    if ret == 0:
        system_font = Path("/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf")
        if system_font.exists():
            import shutil
            shutil.copy(system_font, FONT_PATH)
            print(f"[OK] 폰트 복사됨: {FONT_PATH}")
            return
    print("[FAIL] 폰트 설치 실패. 수동으로 NanumGothicBold.ttf를 assets/fonts/에 복사하세요.")
    sys.exit(1)


def check_env_var(name: str, test_fn=None) -> bool:
    val = os.getenv(name)
    if not val:
        print(f"[MISSING] {name}")
        return False
    if test_fn:
        try:
            test_fn(val)
            print(f"[OK] {name}")
        except Exception as e:
            print(f"[FAIL] {name}: {e}")
            return False
    else:
        print(f"[OK] {name} (값 존재)")
    return True


def test_anthropic(key: str):
    import anthropic
    client = anthropic.Anthropic(api_key=key)
    client.models.list()


def test_elevenlabs(key: str):
    resp = requests.get(
        "https://api.elevenlabs.io/v1/voices",
        headers={"xi-api-key": key},
        timeout=10,
    )
    if resp.status_code != 200:
        raise Exception(f"HTTP {resp.status_code}")


def test_pexels(key: str):
    resp = requests.get(
        "https://api.pexels.com/videos/search",
        params={"query": "nature", "per_page": 1},
        headers={"Authorization": key},
        timeout=10,
    )
    if resp.status_code != 200:
        raise Exception(f"HTTP {resp.status_code}")


def main():
    print("=" * 50)
    print("YouTube Shorts Generator - 초기 설정")
    print("=" * 50)

    download_font()

    print("\nAPI 키 검증:")
    results = [
        check_env_var("ANTHROPIC_API_KEY", test_anthropic),
        check_env_var("ELEVENLABS_API_KEY", test_elevenlabs),
        check_env_var("ELEVENLABS_VOICE_ID"),
        check_env_var("PEXELS_API_KEY", test_pexels),
    ]

    print("\nYouTube OAuth:")
    yt_file = os.getenv("YOUTUBE_CLIENT_SECRETS_FILE", "credentials/client_secret.json")
    if Path(yt_file).exists():
        print(f"[OK] {yt_file}")
    else:
        print(f"[INFO] {yt_file} 없음 — --skip-upload 모드로만 사용 가능")

    print("\n" + "=" * 50)
    if all(results):
        print("설정 완료! python main.py --help 로 사용법을 확인하세요.")
    else:
        print(".env 파일을 확인하고 누락된 키를 추가하세요.")
        print("(.env.example 참고)")


if __name__ == "__main__":
    main()
