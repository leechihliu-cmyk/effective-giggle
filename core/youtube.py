import os
import time
from pathlib import Path


class UploadError(Exception):
    def __init__(self, message: str):
        super().__init__(f"[YouTube 업로드 오류] {message}")


def get_authenticated_service(client_secrets_file: str):
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    import googleapiclient.discovery

    SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
    token_path = str(Path(client_secrets_file).parent / "token.json")

    creds = None
    if Path(token_path).exists():
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, SCOPES)
            flow.redirect_uri = "http://localhost:8080/"
            auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline")
            print("\n" + "=" * 60)
            print("아래 URL을 브라우저에서 열고 Google 계정으로 허용하세요:")
            print(auth_url)
            print("=" * 60)
            print("\n허용 후 브라우저가 localhost:8080 으로 이동하면서")
            print("연결 실패 화면이 뜰 수 있습니다. 괜찮습니다.")
            print("그 화면의 주소창 URL 전체를 복사해서 아래에 붙여넣으세요.\n")
            redirect_response = input("리다이렉트 URL 붙여넣기: ").strip()
            flow.fetch_token(authorization_response=redirect_response)
            creds = flow.credentials
        Path(token_path).write_text(creds.to_json())

    return googleapiclient.discovery.build("youtube", "v3", credentials=creds)


def upload_short(
    youtube_service,
    video_path: str,
    title: str,
    description: str,
    hashtags: list[str],
    category_id: str = "22",
    privacy_status: str = "private",
) -> dict:
    import googleapiclient.http

    # ensure #Shorts is in description for Shorts classification
    shorts_desc = description
    if "#Shorts" not in shorts_desc and "#shorts" not in shorts_desc:
        shorts_desc = "#Shorts\n" + shorts_desc

    tags = [h.lstrip("#") for h in hashtags]
    tags.append("Shorts")

    body = {
        "snippet": {
            "title": title[:100],
            "description": shorts_desc[:5000],
            "tags": tags,
            "categoryId": category_id,
            "defaultLanguage": "ko",
            "defaultAudioLanguage": "ko",
        },
        "status": {
            "privacyStatus": privacy_status,
            "madeForKids": False,
            "selfDeclaredMadeForKids": False,
        },
    }

    media = googleapiclient.http.MediaFileUpload(
        video_path,
        mimetype="video/mp4",
        resumable=True,
        chunksize=256 * 1024,
    )

    request = youtube_service.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    print(f"  [YouTube] 업로드 시작: {title}")
    response = None
    retry_count = 0
    max_retries = 4

    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                pct = int(status.progress() * 100)
                print(f"  [YouTube] 업로드 진행: {pct}%")
        except Exception as e:
            retry_count += 1
            if retry_count > max_retries:
                raise UploadError(f"업로드 실패 (재시도 {max_retries}회 초과): {e}")
            wait = 2 ** retry_count
            print(f"  [YouTube] 오류 발생, {wait}초 후 재시도 ({retry_count}/{max_retries})...")
            time.sleep(wait)

    video_id = response.get("id", "")
    url = f"https://www.youtube.com/shorts/{video_id}"
    print(f"  [YouTube] 업로드 완료: {url}")
    return {"video_id": video_id, "url": url, "response": response}
