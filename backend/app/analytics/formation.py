"""
Formation detection from pitch coordinates.
Clusters outfield players by depth (pitch_x) into defensive,
midfield, and attacking lines, then counts per line.
"""
from collections import deque, Counter

import numpy as np
from sklearn.cluster import KMeans

MIN_PLAYERS = 7
SMOOTH_WINDOW = 15


def _cluster_into_lines(depths: np.ndarray, n_lines: int) -> list[int]:
    if len(depths) < n_lines:
        return []
    X = depths.reshape(-1, 1)
    km = KMeans(n_clusters=n_lines, n_init=5, random_state=42)
    labels = km.fit_predict(X)
    # Sort cluster indices by their centroid (left to right = back to front for home)
    order = np.argsort(km.cluster_centers_.flatten())
    rank = np.empty_like(order)
    rank[order] = np.arange(n_lines)
    return rank[labels].tolist()


def _line_counts_to_string(sorted_counts: list[int]) -> str:
    return "-".join(str(c) for c in sorted_counts)


def detect_formation(players: list[dict], attacking_right: bool = True) -> tuple[str, float]:
    """
    Detect formation from a list of pitch-mapped player dicts.
    Each dict must have pitch_x and optionally class_name.
    Returns (formation_string, confidence).
    """
    outfield = [p for p in players if p.get("class_name") != "goalkeeper"
                and p.get("team") not in ("referee", None)]

    if len(outfield) < MIN_PLAYERS:
        return "unknown", 0.0

    depths = np.array([p["pitch_x"] for p in outfield])
    if not attacking_right:
        depths = PITCH_W - depths

    # Try k=3 (most formations) and k=4 (e.g. 4-2-3-1)
    best_formation = "unknown"
    best_conf = 0.0

    for k in [3, 4]:
        if len(depths) < k:
            continue
        labels = _cluster_into_lines(depths, k)
        if not labels:
            continue
        counts = sorted(Counter(labels[i] for i in range(len(labels))).items())
        line_counts = [c for _, c in sorted(counts)]
        formation = _line_counts_to_string(line_counts)
        # Confidence based on inertia ratio (lower inertia = more distinct lines)
        X = depths.reshape(-1, 1)
        km = KMeans(n_clusters=k, n_init=5, random_state=42).fit(X)
        spread = depths.std()
        inertia_norm = km.inertia_ / (spread ** 2 * len(depths) + 1e-6)
        conf = float(np.clip(1.0 - inertia_norm, 0.1, 0.95))
        if conf > best_conf:
            best_conf = conf
            best_formation = formation

    return best_formation, best_conf


PITCH_W = 105.0


class FormationTracker:
    """Smooth formation strings over a sliding window to avoid flickering."""

    def __init__(self, window: int = SMOOTH_WINDOW):
        self._home: deque = deque(maxlen=window)
        self._away: deque = deque(maxlen=window)

    def update(self, home_formation: str, away_formation: str):
        if home_formation != "unknown":
            self._home.append(home_formation)
        if away_formation != "unknown":
            self._away.append(away_formation)

    def current(self) -> tuple[str, str]:
        home = Counter(self._home).most_common(1)[0][0] if self._home else "unknown"
        away = Counter(self._away).most_common(1)[0][0] if self._away else "unknown"
        return home, away
