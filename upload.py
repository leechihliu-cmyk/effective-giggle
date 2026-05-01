#!/usr/bin/env python3
"""YouTube 업로드 스크립트 — 터미널에서 직접 실행하세요: python upload.py"""
import sys
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

VIDEO_PATH = "output/test-run-01/final.mp4"
TITLE = "며느리 손편지 한 장에 이십 년 서운함이 녹았습니다"
DESCRIPTION = "#Shorts #시니어 #감동사연 #공감 #노후 #5060 #고부관계 #손편지"
HASHTAGS = ["시니어", "감동사연", "공감", "노후", "5060", "Shorts", "고부관계", "손편지"]
PRIVACY = "private"
CLIENT_SECRETS = "credentials/client_secret.json"


def get_creds(client_secrets_file):
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
    token_path = str(Path(client_secrets_file).parent / "token.json")

    creds = None
    if Path(token_path).exists():
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if creds and creds.valid:
        print("기존 토큰 사용")
        return creds

    if creds and creds.expired and creds.refresh_token:
        print("토큰 갱신 중...")
        creds.refresh(Request())
        Path(token_path).write_text(creds.to_json())
        return creds

    # 새로 인증
    flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, SCOPES)
    flow.redirect_uri = "http://localhost:8080/"
    auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline")

    print("\n" + "=" * 60)
    print("1) 아래 URL을 브라우저에서 여세요:")
    print()
    print(auth_url)
    print()
    print("=" * 60)
    print("2) Google 계정으로 로그인 후 '허용' 클릭")
    print("3) 브라우저가 localhost:8080 으로 이동하면서 오류 화면이 뜹니다")
    print("4) 주소창의 URL 전체를 복사해서 아래에 붙여넣으세요")
    print("   (예: http://localhost:8080/?state=...&code=...&scope=...)")
    print()

    redirect_url = input("리다이렉트 URL 붙여넣기: ").strip()
    flow.fetch_token(authorization_response=redirect_url)
    creds = flow.credentials
    Path(token_path).write_text(creds.to_json())
    print("인증 완료! 토큰 저장됨.")
    return creds


def main():
    if not Path(VIDEO_PATH).exists():
        print(f"오류: 영상 파일 없음 → {VIDEO_PATH}")
        sys.exit(1)

    print(f"업로드할 영상: {VIDEO_PATH}")
    print(f"제목: {TITLE}")
    print(f"공개 설정: {PRIVACY}")
    print()

    creds = get_creds(CLIENT_SECRETS)

    import googleapiclient.discovery
    import googleapiclient.http

    youtube = googleapiclient.discovery.build("youtube", "v3", credentials=creds)

    description = DESCRIPTION
    if "#Shorts" not in description:
        description = "#Shorts\n" + description

    body = {
        "snippet": {
            "title": TITLE[:100],
            "description": description[:5000],
            "tags": HASHTAGS,
            "categoryId": "22",
            "defaultLanguage": "ko",
            "defaultAudioLanguage": "ko",
        },
        "status": {
            "privacyStatus": PRIVACY,
            "madeForKids": False,
            "selfDeclaredMadeForKids": False,
        },
    }

    media = googleapiclient.http.MediaFileUpload(
        VIDEO_PATH,
        mimetype="video/mp4",
        resumable=True,
        chunksize=256 * 1024,
    )

    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    print(f"\n업로드 시작...")
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"  진행: {int(status.progress() * 100)}%")

    video_id = response.get("id", "")
    url = f"https://www.youtube.com/shorts/{video_id}"
    print(f"\n업로드 완료!")
    print(f"YouTube URL: {url}")
    print(f"(비공개로 업로드됨 — YouTube Studio에서 공개로 변경 가능)")


if __name__ == "__main__":
    main()
