"""
jobs_index.json + 각 job의 metadata.json을 읽어
콘텐츠 유형별/감정별/훅 패턴별 성과를 집계하고 StyleProfile을 생성한다.
"""
import json
from collections import defaultdict
from pathlib import Path
from typing import Optional

import config as cfg
from analytics.tracker import list_all_jobs, load_job
from models.data_models import StyleProfile


MIN_VIEWS_FOR_STATS = 10   # 이 이상 조회 수 있어야 통계에 포함


def _jobs_with_analytics() -> list[dict]:
    """analytics가 채워진 job들만 반환 (metadata.json 포함)"""
    result = []
    for job in list_all_jobs():
        if not job.get("view_count"):
            continue
        meta = load_job(job["job_id"])
        if meta and meta.get("analytics", {}).get("view_count", 0) >= MIN_VIEWS_FOR_STATS:
            result.append(meta)
    return result


def aggregate_by_content_type(jobs: list[dict]) -> dict:
    """콘텐츠 유형별 평균 조회수/참여율 집계"""
    buckets: dict[str, list] = defaultdict(list)
    for job in jobs:
        ct = job.get("content_type", "")
        a = job.get("analytics", {})
        if ct and a.get("view_count", 0) > 0:
            buckets[ct].append({
                "view_count": a["view_count"],
                "engagement_rate": a.get("engagement_rate", 0.0),
                "retention_rate": a.get("retention_rate", 0.0),
            })

    summary = {}
    for ct, records in buckets.items():
        n = len(records)
        summary[ct] = {
            "count": n,
            "avg_views": round(sum(r["view_count"] for r in records) / n),
            "avg_engagement": round(sum(r["engagement_rate"] for r in records) / n, 4),
            "avg_retention": round(sum(r["retention_rate"] for r in records) / n, 4),
        }
    return summary


def aggregate_by_emotional_tone(jobs: list[dict]) -> dict:
    """감정 톤별 평균 참여율 집계 (각 장면의 emotional_tone 활용)"""
    buckets: dict[str, list] = defaultdict(list)
    for job in jobs:
        a = job.get("analytics", {})
        if a.get("view_count", 0) == 0:
            continue
        scenes = job.get("visuals", {}).get("scenes", [])
        tones = {s.get("emotional_tone", "") for s in scenes if s.get("emotional_tone")}
        for tone in tones:
            buckets[tone].append(a.get("engagement_rate", 0.0))

    return {
        tone: {
            "count": len(rates),
            "avg_engagement": round(sum(rates) / len(rates), 4),
        }
        for tone, rates in buckets.items()
        if rates
    }


def get_top_performing_hooks(jobs: list[dict], top_n: int = 5) -> list[str]:
    """조회수 상위 N개 영상의 opening_hook 반환"""
    sorted_jobs = sorted(
        jobs,
        key=lambda j: j.get("analytics", {}).get("view_count", 0),
        reverse=True,
    )
    hooks = []
    for job in sorted_jobs[:top_n]:
        hook = job.get("script", {}).get("opening_hook", "")
        if hook:
            hooks.append(hook)
    return hooks


def get_top_performing_titles(jobs: list[dict], top_n: int = 5) -> list[str]:
    sorted_jobs = sorted(
        jobs,
        key=lambda j: j.get("analytics", {}).get("engagement_rate", 0),
        reverse=True,
    )
    return [j.get("script", {}).get("title", "") for j in sorted_jobs[:top_n] if j.get("script", {}).get("title")]


def get_low_performing_patterns(jobs: list[dict]) -> list[str]:
    """참여율 하위 20% 영상의 특징 반환"""
    if len(jobs) < 5:
        return []
    sorted_jobs = sorted(
        jobs,
        key=lambda j: j.get("analytics", {}).get("engagement_rate", 0),
    )
    bottom = sorted_jobs[:max(1, len(sorted_jobs) // 5)]
    patterns = []
    for job in bottom:
        title = job.get("script", {}).get("title", "")
        ct = job.get("content_type", "")
        if title:
            patterns.append(f"{ct}: {title}")
    return patterns


def build_performance_summary() -> dict:
    """전체 통계 요약 딕셔너리"""
    jobs = _jobs_with_analytics()
    if not jobs:
        return {"status": "데이터 없음", "job_count": 0}

    by_type = aggregate_by_content_type(jobs)
    by_tone = aggregate_by_emotional_tone(jobs)
    top_hooks = get_top_performing_hooks(jobs)
    top_titles = get_top_performing_titles(jobs)
    low_patterns = get_low_performing_patterns(jobs)

    return {
        "status": "정상",
        "job_count": len(jobs),
        "by_content_type": by_type,
        "by_emotional_tone": by_tone,
        "top_hooks": top_hooks,
        "top_titles": top_titles,
        "low_performing_patterns": low_patterns,
    }


def build_style_profile() -> Optional[StyleProfile]:
    """
    성과 데이터를 분석해 다음 생성에 사용할 StyleProfile 반환.
    데이터가 부족하면 None 반환.
    """
    from datetime import datetime

    jobs = _jobs_with_analytics()
    if not jobs:
        return None

    by_type = aggregate_by_content_type(jobs)
    by_tone = aggregate_by_emotional_tone(jobs)

    # 조회수 기준 상위 콘텐츠 유형
    best_types = sorted(by_type.items(), key=lambda x: x[1]["avg_views"], reverse=True)
    best_content_types = [ct for ct, _ in best_types[:2]]

    # 참여율 기준 상위 감정 톤
    best_tones_sorted = sorted(by_tone.items(), key=lambda x: x[1]["avg_engagement"], reverse=True)
    best_emotional_tones = [tone for tone, _ in best_tones_sorted[:3]]

    top_hooks = get_top_performing_hooks(jobs)
    low_patterns = get_low_performing_patterns(jobs)

    # 다음에 만들 주제 추천 (아직 만들지 않은 유형 우선)
    existing_topics = {j.get("topic", "") for j in jobs}
    recommended_topics = [f"{best_content_types[0]} 유형 추천 주제"] if best_content_types else []

    return StyleProfile(
        generated_at=datetime.utcnow().isoformat(),
        best_content_types=best_content_types,
        best_emotional_tones=best_emotional_tones,
        recommended_hooks=top_hooks,
        recommended_topics=recommended_topics,
        avoid_patterns=low_patterns,
        strategy_notes="",  # FeedbackAgent가 채움
    )


def print_dashboard():
    """터미널에 성과 대시보드 출력"""
    summary = build_performance_summary()

    print("\n" + "=" * 55)
    print("  📊 YouTube Shorts 성과 대시보드")
    print("=" * 55)

    if summary.get("status") == "데이터 없음":
        print("  아직 분석 데이터가 없습니다.")
        print("  python main.py --sync-analytics 를 먼저 실행하세요.")
        return

    print(f"  총 분석 영상: {summary['job_count']}개\n")

    print("  [콘텐츠 유형별 성과]")
    for ct, data in summary.get("by_content_type", {}).items():
        print(f"    {ct}: 평균 {data['avg_views']:,}회 | 참여율 {data['avg_engagement']:.1%} | {data['count']}개")

    print("\n  [감정 톤별 참여율]")
    for tone, data in summary.get("by_emotional_tone", {}).items():
        print(f"    {tone}: {data['avg_engagement']:.1%} ({data['count']}개)")

    print("\n  [성과 좋은 오프닝 훅 TOP5]")
    for i, hook in enumerate(summary.get("top_hooks", []), 1):
        print(f"    {i}. {hook}")

    print("\n  [개선 필요 패턴]")
    for pattern in summary.get("low_performing_patterns", []):
        print(f"    - {pattern}")

    print("=" * 55)
