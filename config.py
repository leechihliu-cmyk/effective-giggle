import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

REQUIRED_ENV_VARS = [
    "ANTHROPIC_API_KEY",
    "PEXELS_API_KEY",
]
# ElevenLabs는 선택 — 없으면 gTTS(Google 무료)로 자동 대체

CLAUDE_MODEL = "claude-sonnet-4-6"

VIDEO_WIDTH = 720
VIDEO_HEIGHT = 1280
VIDEO_FPS = 30

TARGET_DURATION_MIN = 45
TARGET_DURATION_MAX = 60

KOREAN_FONT_PATH = str(Path(__file__).parent / "assets" / "fonts" / "NanumGothicBold.ttf")
SUBTITLE_FONT_SIZE = 52
SUBTITLE_COLOR = (255, 255, 255)
SUBTITLE_STROKE_COLOR = (0, 0, 0)
SUBTITLE_STROKE_WIDTH = 3
SUBTITLE_BOTTOM_MARGIN = 120

OUTPUT_DIR = str(Path(__file__).parent / "output")

MAX_REVISION_ROUNDS = int(os.getenv("MAX_REVISION_ROUNDS", "2"))
YOUTUBE_CLIENT_SECRETS_FILE = os.getenv(
    "YOUTUBE_CLIENT_SECRETS_FILE", "credentials/client_secret.json"
)


def validate_config(skip_youtube: bool = False) -> None:
    missing = [v for v in REQUIRED_ENV_VARS if not os.getenv(v)]
    if not skip_youtube:
        if not Path(YOUTUBE_CLIENT_SECRETS_FILE).exists():
            missing.append(f"YouTube client_secret.json at {YOUTUBE_CLIENT_SECRETS_FILE}")
    if missing:
        print("누락된 환경변수 / 파일:")
        for m in missing:
            print(f"  - {m}")
        print("\n.env.example을 참고하여 .env 파일을 설정하세요.")
        sys.exit(1)


def check_font() -> None:
    if not Path(KOREAN_FONT_PATH).exists():
        print(f"한글 폰트가 없습니다: {KOREAN_FONT_PATH}")
        print("python setup.py 를 먼저 실행하세요.")
        sys.exit(1)


def get_anthropic_client():
    import anthropic
    return anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
