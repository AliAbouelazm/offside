"""
Main video processing pipeline for Offside.

Orchestrates: tracking → homography → team assignment → analytics
"""
import json
import os
import time
from pathlib import Path
from typing import Callable

import cv2
import numpy as np
from sklearn.cluster import KMeans

from app.analytics.formation import FormationTracker, detect_formation
from app.analytics.metrics import aggregate_metrics, build_analytics_timeline
from app.analytics.pressing import PressingTracker, compute_pressing_score, who_has_ball
from app.analytics.space import compute_voronoi_control
from app.vision.homography import HomographyEstimator, map_tracks_to_pitch
from app.vision.tracker import Tracker

DEMO_CLIPS_DIR = Path(__file__).parent.parent.parent / "demo_clips"
RESULTS_DIR = Path(__file__).parent.parent.parent / "demo_results"

# Fraction of frame height used for torso crop (0.2–0.5 of bbox height)
TORSO_TOP_FRAC = 0.2
TORSO_BOT_FRAC = 0.5

# Number of frames from which to sample torso colors for team assignment
COLOR_SAMPLE_FRAMES = 10


def _torso_hsv(frame: np.ndarray, track: dict) -> np.ndarray | None:
    """Return mean HSV of the torso region of a detected player bounding box."""
    h_frame, w_frame = frame.shape[:2]
    x1 = int(np.clip(track.get("x1", 0), 0, w_frame - 1))
    y1 = int(np.clip(track.get("y1", 0), 0, h_frame - 1))
    x2 = int(np.clip(track.get("x2", w_frame), 0, w_frame))
    y2 = int(np.clip(track.get("y2", h_frame), 0, h_frame))
    bh = y2 - y1
    if bh < 10 or (x2 - x1) < 5:
        return None
    ty1 = y1 + int(bh * TORSO_TOP_FRAC)
    ty2 = y1 + int(bh * TORSO_BOT_FRAC)
    crop = frame[ty1:ty2, x1:x2]
    if crop.size == 0:
        return None
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    return hsv.reshape(-1, 3).mean(axis=0)


def _assign_teams(
    sample_frames: list[tuple[np.ndarray, list[dict]]],
) -> dict[int, str]:
    """
    Cluster torso HSV colors into 3 groups (home, away, referee) using KMeans.
    Returns {track_id: team_label}.
    """
    track_colors: dict[int, list[np.ndarray]] = {}
    for frame, tracks in sample_frames:
        for t in tracks:
            if t.get("class_name") not in ("player", "goalkeeper"):
                continue
            tid = t.get("track_id")
            if tid is None:
                continue
            color = _torso_hsv(frame, t)
            if color is not None:
                track_colors.setdefault(tid, []).append(color)

    if not track_colors:
        return {}

    track_ids = list(track_colors.keys())
    features = np.array([np.mean(track_colors[tid], axis=0) for tid in track_ids])

    n_clusters = min(3, len(track_ids))
    km = KMeans(n_clusters=n_clusters, n_init=10, random_state=42)
    labels = km.fit_predict(features)

    # Identify referee cluster: highest V (brightness) and lowest S (saturation)
    centers = km.cluster_centers_  # shape (n_clusters, 3) — H, S, V
    # Referees typically wear black (low V) or bright yellow (high S, high V) —
    # simplest heuristic: fewest players in a cluster is likely referee cluster
    cluster_counts = np.bincount(labels, minlength=n_clusters)
    ref_cluster = int(np.argmin(cluster_counts))

    # Remaining two clusters: higher S*V product → home (typically more colorful kit)
    remaining = [i for i in range(n_clusters) if i != ref_cluster]
    if len(remaining) == 2:
        sv0 = centers[remaining[0], 1] * centers[remaining[0], 2]
        sv1 = centers[remaining[1], 1] * centers[remaining[1], 2]
        home_cluster = remaining[0] if sv0 >= sv1 else remaining[1]
        away_cluster = remaining[1] if sv0 >= sv1 else remaining[0]
    elif len(remaining) == 1:
        home_cluster = remaining[0]
        away_cluster = remaining[0]
    else:
        home_cluster = away_cluster = 0

    label_map = {ref_cluster: "referee", home_cluster: "home", away_cluster: "away"}

    return {track_ids[i]: label_map.get(int(labels[i]), "home") for i in range(len(track_ids))}


def process_video(
    video_path: str,
    frame_skip: int = 2,
    on_progress: Callable[[dict], None] | None = None,
) -> dict:
    """
    Full pipeline: track → homography → team assign → analytics → aggregate.

    on_progress(event_dict) is called after each processed frame with:
      {"type": "progress", "frame": int, "total": int, "pct": float}
    """
    tracker = Tracker()
    homography_est = HomographyEstimator()
    formation_tracker = FormationTracker()
    pressing_tracker = PressingTracker()

    # Phase 1 — Tracking
    if on_progress:
        on_progress({"type": "status", "message": "Tracking players and ball…"})

    frame_tracks, frame_images, metadata = tracker.track_video(
        video_path,
        frame_skip=frame_skip,
        on_progress=lambda f, t: on_progress(
            {"type": "progress", "phase": "tracking", "frame": f, "total": t,
             "pct": round(50.0 * f / max(t, 1), 1)}
        ) if on_progress else None,
    )

    total_frames = len(frame_tracks)
    if total_frames == 0:
        return {"error": "No frames tracked", "metadata": metadata}

    # Phase 2 — Team color assignment from first COLOR_SAMPLE_FRAMES processed frames
    if on_progress:
        on_progress({"type": "status", "message": "Assigning team colors…"})

    sample_count = min(COLOR_SAMPLE_FRAMES, total_frames)
    sample_data = [
        (frame_images[i], frame_tracks[i])
        for i in range(sample_count)
        if frame_images[i] is not None
    ]
    team_map = _assign_teams(sample_data)

    # Phase 3 — Per-frame analytics
    if on_progress:
        on_progress({"type": "status", "message": "Computing analytics…"})

    frame_results = []

    for idx, (tracks, frame_img) in enumerate(zip(frame_tracks, frame_images)):
        frame_num = tracks[0]["frame_num"] if tracks else idx * frame_skip
        timestamp = frame_num / max(metadata.get("fps", 25.0), 1.0)

        # Homography
        H, h_quality = (None, "no_frame")
        if frame_img is not None:
            H, h_quality = homography_est.estimate(frame_img)

        # Map to pitch
        if H is not None:
            mapped = map_tracks_to_pitch(tracks, H)
        else:
            mapped = tracks

        # Apply team labels
        for t in mapped:
            tid = t.get("track_id")
            if t.get("class_name") in ("player", "goalkeeper"):
                t["team"] = team_map.get(tid, "home")
            elif t.get("class_name") == "referee":
                t["team"] = "referee"

        # Split by role
        home_players = [t for t in mapped if t.get("team") == "home"]
        away_players = [t for t in mapped if t.get("team") == "away"]
        balls = [t for t in mapped if t.get("class_name") == "ball"]
        ball = balls[0] if balls else None

        # Formation
        home_formation, _ = detect_formation(home_players, attacking_right=True)
        away_formation, _ = detect_formation(away_players, attacking_right=False)
        formation_tracker.update(home_formation, away_formation)
        smooth_home, smooth_away = formation_tracker.current()

        # Pressing
        team_with_ball = who_has_ball(ball, home_players + away_players)
        pressing_score, pressing_team = compute_pressing_score(
            ball, home_players, away_players, team_with_ball
        )
        pressing_trigger = pressing_tracker.update(pressing_score)

        # Space control
        all_field_players = home_players + away_players
        space = compute_voronoi_control(all_field_players)

        frame_results.append({
            "frame_num": frame_num,
            "timestamp": round(timestamp, 3),
            "homography_quality": h_quality,
            "home_players": home_players,
            "away_players": away_players,
            "ball": ball,
            "team_with_ball": team_with_ball,
            "formation_home": smooth_home,
            "formation_away": smooth_away,
            "pressing_score": pressing_score,
            "pressing_team": pressing_team,
            "pressing_trigger": pressing_trigger,
            "space": space,
        })

        if on_progress:
            pct = 50.0 + round(50.0 * (idx + 1) / total_frames, 1)
            on_progress({"type": "progress", "phase": "analytics",
                         "frame": idx + 1, "total": total_frames, "pct": pct})

    # Phase 4 — Aggregate
    summary = aggregate_metrics(frame_results)
    timeline = build_analytics_timeline(frame_results)

    # Strip heavy polygon data from the top-level result to keep payload lean;
    # full Voronoi cells are only included in per_frame if caller needs them.
    per_frame_slim = []
    for f in frame_results:
        slim = {k: v for k, v in f.items()
                if k not in ("home_players", "away_players", "space")}
        slim["space"] = {
            "home_pct": f["space"]["home_pct"],
            "away_pct": f["space"]["away_pct"],
            "dangerous_space_home": f["space"]["dangerous_space_home"],
            "dangerous_space_away": f["space"]["dangerous_space_away"],
        }
        per_frame_slim.append(slim)

    return {
        "metadata": metadata,
        "summary": summary,
        "timeline": timeline,
        "per_frame": per_frame_slim,
    }


def process_clip_for_demo(clip_id: str, frame_skip: int = 2) -> dict:
    """
    Load a pre-processed demo clip result from demo_results/ or compute it
    from the raw clip in demo_clips/.

    Returns the same structure as process_video().
    """
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    result_path = RESULTS_DIR / f"{clip_id}.json"

    # Return cached result if it exists
    if result_path.exists():
        with open(result_path) as f:
            return json.load(f)

    # Find the raw video clip
    video_path = None
    for ext in (".mp4", ".mov", ".avi", ".mkv"):
        candidate = DEMO_CLIPS_DIR / f"{clip_id}{ext}"
        if candidate.exists():
            video_path = str(candidate)
            break

    if video_path is None:
        return {"error": f"Demo clip '{clip_id}' not found in {DEMO_CLIPS_DIR}"}

    result = process_video(video_path, frame_skip=frame_skip)

    # Cache the result so subsequent calls are instant
    with open(result_path, "w") as f:
        json.dump(result, f)

    return result


def list_demo_clips() -> list[dict]:
    """List available demo clips (raw or pre-processed)."""
    clips = {}

    if DEMO_CLIPS_DIR.exists():
        for p in DEMO_CLIPS_DIR.iterdir():
            if p.suffix.lower() in (".mp4", ".mov", ".avi", ".mkv"):
                clips[p.stem] = {"id": p.stem, "has_video": True, "has_cache": False}

    if RESULTS_DIR.exists():
        for p in RESULTS_DIR.iterdir():
            if p.suffix == ".json":
                cid = p.stem
                if cid in clips:
                    clips[cid]["has_cache"] = True
                else:
                    clips[cid] = {"id": cid, "has_video": False, "has_cache": True}

    return list(clips.values())
