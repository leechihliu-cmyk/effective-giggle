"""
작업 메타데이터를 JSON으로 저장/로드하는 영속성 레이어.

저장 구조:
  output/{job_id}/metadata.json  → 각 작업의 전체 기록
  output/jobs_index.json          → 전체 작업 목록 인덱스
"""
import json
import os
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from models.data_models import PipelineState, VideoAnalytics, StyleProfile
import config as cfg


_INDEX_PATH = Path(cfg.OUTPUT_DIR) / "jobs_index.json"


def _to_dict(obj) -> dict:
    """dataclass → dict, None 필드 포함"""
    if obj is None:
        return {}
    try:
        return asdict(obj)
    except TypeError:
        return {}


def save_job(state: PipelineState) -> str:
    """PipelineState를 JSON으로 저장. 저장 경로를 반환."""
    job_dir = Path(cfg.OUTPUT_DIR) / state.job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = job_dir / "metadata.json"

    data = {
        "job_id": state.job_id,
        "created_at": state.created_at,
        "topic": state.topic,
        "content_type": state.content_type,
        "youtube_video_id": state.youtube_video_id,
        "youtube_url": state.youtube_url,
        "final_video_path": state.final_video_path,
        "script": _to_dict(state.script),
        "research": _to_dict(state.research),
        "visuals": _to_dict(state.visuals),
        "approval": _to_dict(state.approval),
        "analytics": _to_dict(state.analytics),
        "style_profile_used": _to_dict(state.style_profile_used),
    }
    metadata_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    _update_index(state)
    return str(metadata_path)


def load_job(job_id: str) -> Optional[dict]:
    path = Path(cfg.OUTPUT_DIR) / job_id / "metadata.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


def update_analytics(job_id: str, analytics: VideoAnalytics) -> bool:
    """특정 job의 analytics 필드만 업데이트"""
    path = Path(cfg.OUTPUT_DIR) / job_id / "metadata.json"
    if not path.exists():
        return False
    data = json.loads(path.read_text())
    data["analytics"] = _to_dict(analytics)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    _update_index_analytics(job_id, analytics)
    return True


def list_all_jobs() -> list[dict]:
    """jobs_index.json에서 전체 작업 목록 반환"""
    if not _INDEX_PATH.exists():
        return []
    return json.loads(_INDEX_PATH.read_text())


def list_jobs_with_video() -> list[dict]:
    """YouTube video_id가 있는 작업만 반환"""
    return [j for j in list_all_jobs() if j.get("youtube_video_id")]


def _update_index(state: PipelineState):
    jobs = list_all_jobs()
    entry = {
        "job_id": state.job_id,
        "created_at": state.created_at,
        "topic": state.topic,
        "content_type": state.content_type,
        "title": state.script.title if state.script else "",
        "youtube_video_id": state.youtube_video_id,
        "youtube_url": state.youtube_url,
        "approval_score": state.approval.overall_score if state.approval else 0,
        "view_count": 0,
        "like_count": 0,
        "comment_count": 0,
        "engagement_rate": 0.0,
        "analytics_synced_at": None,
    }
    # 기존 항목 덮어쓰기
    jobs = [j for j in jobs if j["job_id"] != state.job_id]
    jobs.insert(0, entry)
    _INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    _INDEX_PATH.write_text(json.dumps(jobs, ensure_ascii=False, indent=2))


def _update_index_analytics(job_id: str, analytics: VideoAnalytics):
    jobs = list_all_jobs()
    for job in jobs:
        if job["job_id"] == job_id:
            job["view_count"] = analytics.view_count
            job["like_count"] = analytics.like_count
            job["comment_count"] = analytics.comment_count
            job["engagement_rate"] = analytics.engagement_rate
            job["analytics_synced_at"] = analytics.fetched_at
            break
    _INDEX_PATH.write_text(json.dumps(jobs, ensure_ascii=False, indent=2))
