"""
Aggregate analytics across all processed frames into summary statistics.
"""
from collections import Counter

import numpy as np


def _avg_inter_player_distance(players: list[dict]) -> float:
    if len(players) < 2:
        return 0.0
    pts = np.array([[p["pitch_x"], p["pitch_y"]] for p in players])
    dists = []
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            dists.append(np.hypot(pts[i, 0] - pts[j, 0], pts[i, 1] - pts[j, 1]))
    return float(np.mean(dists)) if dists else 0.0


def aggregate_metrics(frame_results: list[dict]) -> dict:
    """
    frame_results: list of per-frame dicts with keys:
      pressing_score, pressing_team, space (control dict),
      formation_home, formation_away,
      home_players, away_players
    """
    if not frame_results:
        return {}

    pressing_scores = [f["pressing_score"] for f in frame_results]
    space_home = [f["space"]["home_pct"] for f in frame_results]
    space_away = [f["space"]["away_pct"] for f in frame_results]

    formations_home = [f["formation_home"] for f in frame_results
                       if f["formation_home"] != "unknown"]
    formations_away = [f["formation_away"] for f in frame_results
                       if f["formation_away"] != "unknown"]

    avg_dist_home_per_frame = [
        _avg_inter_player_distance(f["home_players"]) for f in frame_results
    ]
    avg_dist_away_per_frame = [
        _avg_inter_player_distance(f["away_players"]) for f in frame_results
    ]

    return {
        "avg_formation_home": Counter(formations_home).most_common(1)[0][0]
        if formations_home else "unknown",
        "avg_formation_away": Counter(formations_away).most_common(1)[0][0]
        if formations_away else "unknown",
        "peak_pressing_score": round(float(max(pressing_scores)), 1),
        "avg_pressing_score": round(float(np.mean(pressing_scores)), 1),
        "avg_space_control_home": round(float(np.mean(space_home)), 1),
        "avg_space_control_away": round(float(np.mean(space_away)), 1),
        "avg_inter_player_dist_home": round(
            float(np.mean([d for d in avg_dist_home_per_frame if d > 0])) if avg_dist_home_per_frame else 0.0, 2
        ),
        "avg_inter_player_dist_away": round(
            float(np.mean([d for d in avg_dist_away_per_frame if d > 0])) if avg_dist_away_per_frame else 0.0, 2
        ),
        "total_frames_analyzed": len(frame_results),
    }


def build_analytics_timeline(frame_results: list[dict]) -> dict:
    """Build time-series arrays for the frontend chart."""
    return {
        "frames": [f["frame_num"] for f in frame_results],
        "timestamps": [f["timestamp"] for f in frame_results],
        "pressing_scores": [f["pressing_score"] for f in frame_results],
        "space_control_home": [f["space"]["home_pct"] for f in frame_results],
        "space_control_away": [f["space"]["away_pct"] for f in frame_results],
        "formation_home": [f["formation_home"] for f in frame_results],
        "formation_away": [f["formation_away"] for f in frame_results],
        "pressing_team": [f.get("pressing_team", "none") for f in frame_results],
    }
