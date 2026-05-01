import os
import time
import requests
import numpy as np
from pathlib import Path
from tqdm import tqdm
from models.data_models import Scene

_PEXELS_AVAILABLE: bool | None = None  # cached after first check


def _check_pexels_available() -> bool:
    global _PEXELS_AVAILABLE
    if _PEXELS_AVAILABLE is not None:
        return _PEXELS_AVAILABLE
    api_key = os.getenv("PEXELS_API_KEY", "")
    try:
        r = requests.get(
            "https://api.pexels.com/videos/search",
            params={"query": "nature", "per_page": 1},
            headers={"Authorization": api_key},
            timeout=8,
            verify=False,
        )
        _PEXELS_AVAILABLE = r.status_code == 200
    except Exception:
        _PEXELS_AVAILABLE = False
    if not _PEXELS_AVAILABLE:
        print("  [Pexels] API 접근 불가 (호스트 차단 등) → 그라디언트 영상으로 대체")
    return _PEXELS_AVAILABLE


def _generate_placeholder_clip(output_path: str, duration: float, scene_number: int) -> str:
    """Generate a colored gradient video as a placeholder when Pexels is unavailable."""
    from moviepy import ImageClip
    import colorsys

    hue = (scene_number * 0.15) % 1.0
    r, g, b = colorsys.hsv_to_rgb(hue, 0.55, 0.40)
    color = (int(r * 255), int(g * 255), int(b * 255))

    h, w = 1280, 720
    frame = np.zeros((h, w, 3), dtype=np.uint8)
    for row in range(h):
        t = row / h
        r2, g2, b2 = colorsys.hsv_to_rgb(hue, 0.55, 0.25 + 0.30 * t)
        frame[row, :] = [int(r2 * 255), int(g2 * 255), int(b2 * 255)]

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    clip = ImageClip(frame, duration=duration)
    clip.write_videofile(output_path, fps=30, codec="libx264", logger=None)
    clip.close()
    print(f"  [Pexels] 장면 {scene_number} 그라디언트 플레이스홀더 생성: {output_path}")
    return output_path


class PexelsError(Exception):
    def __init__(self, keyword: str, scene_number: int, message: str = ""):
        self.keyword = keyword
        self.scene_number = scene_number
        super().__init__(f"[Pexels Scene {scene_number}] '{keyword}' 영상 없음. {message}")


def search_videos(
    keywords: list[str],
    orientation: str = "portrait",
    per_page: int = 10,
    min_duration: int = 3,
    max_duration: int = 30,
) -> list[dict]:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    api_key = os.getenv("PEXELS_API_KEY")
    if not api_key:
        raise PexelsError("", 0, "PEXELS_API_KEY가 설정되지 않았습니다.")

    for kw in keywords:
        params = {
            "query": kw,
            "orientation": orientation,
            "per_page": per_page,
            "size": "medium",
        }
        resp = requests.get(
            "https://api.pexels.com/videos/search",
            params=params,
            headers={"Authorization": api_key},
            timeout=15,
            verify=False,
        )
        if resp.status_code != 200:
            continue

        videos = resp.json().get("videos", [])
        filtered = [
            v for v in videos
            if min_duration <= v.get("duration", 0) <= max_duration
        ]
        if filtered:
            return filtered

        params.pop("orientation")
        resp2 = requests.get(
            "https://api.pexels.com/videos/search",
            params=params,
            headers={"Authorization": api_key},
            timeout=15,
            verify=False,
        )
        if resp2.status_code == 200:
            videos2 = resp2.json().get("videos", [])
            filtered2 = [
                v for v in videos2
                if min_duration <= v.get("duration", 0) <= max_duration
            ]
            if filtered2:
                return filtered2

    return []


def _pick_best_file(video_files: list[dict], preferred_quality: str = "hd") -> dict | None:
    quality_order = {"hd": 720, "sd": 480, "uhd": 1080}
    target_h = quality_order.get(preferred_quality, 720)

    portrait_files = [f for f in video_files if f.get("width", 0) < f.get("height", 1)]
    landscape_files = [f for f in video_files if f.get("width", 0) >= f.get("height", 1)]

    for pool in [portrait_files, landscape_files]:
        if not pool:
            continue
        # prefer height closest to target
        pool.sort(key=lambda f: abs(f.get("height", 0) - target_h))
        return pool[0]
    return None


def download_clip(video_metadata: dict, output_path: str) -> str:
    best = _pick_best_file(video_metadata.get("video_files", []))
    if not best:
        raise PexelsError("unknown", 0, "다운로드 가능한 파일 없음")

    url = best.get("link") or best.get("url")
    if not url:
        raise PexelsError("unknown", 0, "다운로드 URL 없음")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    resp = requests.get(url, stream=True, timeout=60)
    resp.raise_for_status()

    total = int(resp.headers.get("content-length", 0))
    with open(output_path, "wb") as f:
        with tqdm(total=total, unit="B", unit_scale=True, desc=Path(output_path).name, leave=False) as bar:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
                bar.update(len(chunk))
    return output_path


def fetch_scene_clips(
    scenes: list[Scene],
    output_dir: str,
    fallback_keywords: list[str],
) -> list[str]:
    pexels_ok = _check_pexels_available()
    clips = []

    for scene in scenes:
        output_path = str(Path(output_dir) / f"scene_{scene.scene_number:02d}.mp4")
        if Path(output_path).exists():
            print(f"  [Pexels] 장면 {scene.scene_number} 캐시 사용")
            clips.append(output_path)
            continue

        if not pexels_ok:
            _generate_placeholder_clip(output_path, scene.duration_sec, scene.scene_number)
            clips.append(output_path)
            continue

        print(f"  [Pexels] 장면 {scene.scene_number} 검색 중: {scene.pexels_keywords[:2]}")
        videos = search_videos(scene.pexels_keywords)

        if not videos:
            print(f"  [Pexels] 폴백 키워드로 재시도: {fallback_keywords[:2]}")
            videos = search_videos(fallback_keywords)

        if not videos:
            print(f"  [Pexels] 검색 실패 → 그라디언트 플레이스홀더 사용")
            _generate_placeholder_clip(output_path, scene.duration_sec, scene.scene_number)
            clips.append(output_path)
            continue

        download_clip(videos[0], output_path)
        print(f"  [Pexels] 장면 {scene.scene_number} 다운로드 완료: {output_path}")
        clips.append(output_path)
        time.sleep(0.3)

    return clips
