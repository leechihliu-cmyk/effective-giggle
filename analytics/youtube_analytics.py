"""
YouTube Data API v3 + YouTube Analytics API를 통해 영상 성과 데이터 수집.

YouTube Data API v3 (기존 OAuth 토큰 재사용):
  - videos.list(part="statistics") → view/like/comment count
  - commentThreads.list() → 댓글 수집

YouTube Analytics API (추가 스코프 필요):
  - reports.query() → avg watch duration, retention

두 API 모두 하나의 OAuth 자격증명으로 처리.
"""
from datetime import datetime, timedelta
from models.data_models import VideoAnalytics
import config as cfg


YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]


def get_authenticated_services(client_secrets_file: str):
    """youtube(Data API) + youtubeAnalytics(Analytics API) 서비스 반환"""
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    import googleapiclient.discovery
    from pathlib import Path

    token_path = str(Path(client_secrets_file).parent / "token_analytics.json")
    creds = None
    if Path(token_path).exists():
        creds = Credentials.from_authorized_user_file(token_path, YOUTUBE_SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, YOUTUBE_SCOPES)
            creds = flow.run_local_server(port=0)
        Path(token_path).write_text(creds.to_json())

    youtube = googleapiclient.discovery.build("youtube", "v3", credentials=creds)
    yt_analytics = googleapiclient.discovery.build("youtubeAnalytics", "v2", credentials=creds)
    return youtube, yt_analytics


def fetch_video_stats(youtube, video_id: str) -> dict:
    """videos.list로 기본 통계 조회"""
    resp = youtube.videos().list(
        part="statistics,contentDetails",
        id=video_id,
    ).execute()

    items = resp.get("items", [])
    if not items:
        return {}

    stats = items[0].get("statistics", {})
    details = items[0].get("contentDetails", {})

    # ISO 8601 duration → seconds (e.g., "PT55S" → 55)
    duration_sec = _parse_duration(details.get("duration", "PT0S"))

    return {
        "view_count": int(stats.get("viewCount", 0)),
        "like_count": int(stats.get("likeCount", 0)),
        "comment_count": int(stats.get("commentCount", 0)),
        "duration_sec": duration_sec,
    }


def fetch_watch_time(yt_analytics, video_id: str, channel_id: str) -> dict:
    """YouTube Analytics API로 평균 시청 시간 조회"""
    end_date = datetime.today().strftime("%Y-%m-%d")
    start_date = (datetime.today() - timedelta(days=90)).strftime("%Y-%m-%d")

    try:
        resp = yt_analytics.reports().query(
            ids=f"channel=={channel_id}",
            startDate=start_date,
            endDate=end_date,
            metrics="averageViewDuration,averageViewPercentage",
            dimensions="video",
            filters=f"video=={video_id}",
        ).execute()

        rows = resp.get("rows", [])
        if rows:
            return {
                "avg_watch_duration_sec": float(rows[0][1]),
                "avg_watch_percentage": float(rows[0][2]),
            }
    except Exception:
        pass
    return {"avg_watch_duration_sec": 0.0, "avg_watch_percentage": 0.0}


def fetch_top_comments(youtube, video_id: str, max_results: int = 20) -> list[str]:
    """상위 댓글 텍스트 수집"""
    try:
        resp = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=max_results,
            order="relevance",
            textFormat="plainText",
        ).execute()
        return [
            item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
            for item in resp.get("items", [])
        ]
    except Exception:
        return []


def fetch_analytics_for_video(
    video_id: str,
    channel_id: str = "",
    client_secrets_file: str = "",
) -> VideoAnalytics:
    """단일 영상의 전체 Analytics 수집 → VideoAnalytics 반환"""
    secrets = client_secrets_file or cfg.YOUTUBE_CLIENT_SECRETS_FILE
    youtube, yt_analytics = get_authenticated_services(secrets)

    stats = fetch_video_stats(youtube, video_id)
    if not stats:
        return VideoAnalytics(fetched_at=datetime.utcnow().isoformat())

    watch_data = {}
    if channel_id:
        watch_data = fetch_watch_time(yt_analytics, video_id, channel_id)

    comments = fetch_top_comments(youtube, video_id)

    view_count = stats["view_count"]
    like_count = stats["like_count"]
    comment_count = stats["comment_count"]
    duration_sec = stats.get("duration_sec", 0)
    avg_watch_sec = watch_data.get("avg_watch_duration_sec", 0.0)
    avg_watch_pct = watch_data.get("avg_watch_percentage", 0.0)

    engagement_rate = round(
        (like_count + comment_count) / view_count if view_count > 0 else 0.0, 4
    )
    retention_rate = round(
        avg_watch_sec / duration_sec if duration_sec > 0 else 0.0, 4
    )

    return VideoAnalytics(
        fetched_at=datetime.utcnow().isoformat(),
        view_count=view_count,
        like_count=like_count,
        comment_count=comment_count,
        avg_watch_duration_sec=avg_watch_sec,
        avg_watch_percentage=avg_watch_pct,
        engagement_rate=engagement_rate,
        retention_rate=retention_rate,
        top_comments=comments,
    )


def sync_all_videos(channel_id: str = "") -> list[dict]:
    """
    jobs_index에서 video_id가 있는 모든 작업의 analytics를 동기화.
    Returns: list of {job_id, video_id, view_count, ...}
    """
    from analytics.tracker import list_jobs_with_video, update_analytics

    jobs = list_jobs_with_video()
    results = []
    for job in jobs:
        video_id = job["youtube_video_id"]
        print(f"  [{job['job_id']}] {job.get('title', '')} — 동기화 중...")
        try:
            analytics = fetch_analytics_for_video(video_id, channel_id=channel_id)
            update_analytics(job["job_id"], analytics)
            results.append({
                "job_id": job["job_id"],
                "video_id": video_id,
                "view_count": analytics.view_count,
                "like_count": analytics.like_count,
                "comment_count": analytics.comment_count,
                "engagement_rate": analytics.engagement_rate,
            })
            print(f"    → 조회수 {analytics.view_count:,} / 좋아요 {analytics.like_count} / 댓글 {analytics.comment_count}")
        except Exception as e:
            print(f"    → 오류: {e}")
    return results


def _parse_duration(iso_duration: str) -> int:
    """PT1H30M15S → 초 단위 정수"""
    import re
    pattern = r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?"
    m = re.match(pattern, iso_duration)
    if not m:
        return 0
    h = int(m.group(1) or 0)
    mins = int(m.group(2) or 0)
    s = int(m.group(3) or 0)
    return h * 3600 + mins * 60 + s
