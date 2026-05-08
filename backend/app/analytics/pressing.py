"""
Pressing intensity and pressing trigger detection.

Pressing score: 0 (no pressure) to 100 (maximum pressure).
Computed as the average distance from the ball carrier to the
3 nearest opposition players, mapped to [0, 100].
"""
from collections import deque

import numpy as np

MAX_PRESS_DIST = 15.0  # meters at which pressing score = 0
TRIGGER_JUMP = 20.0    # score jump over 5 frames to flag a pressing trigger
TRIGGER_WINDOW = 5


def _euclidean(a: dict, b: dict) -> float:
    return float(np.hypot(a["pitch_x"] - b["pitch_x"], a["pitch_y"] - b["pitch_y"]))


def _nearest_n_distances(ball: dict, opponents: list[dict], n: int = 3) -> list[float]:
    dists = sorted(_euclidean(ball, p) for p in opponents)
    return dists[:n]


def compute_pressing_score(
    ball: dict | None,
    home_players: list[dict],
    away_players: list[dict],
    team_with_ball: str,
) -> tuple[float, str]:
    """
    Returns (pressing_score, pressing_team).
    pressing_team is the team applying pressure.
    """
    if ball is None or not home_players or not away_players:
        return 0.0, "none"

    pressing_team = "away" if team_with_ball == "home" else "home"
    pressing_players = away_players if team_with_ball == "home" else home_players

    dists = _nearest_n_distances(ball, pressing_players, 3)
    if not dists:
        return 0.0, pressing_team

    avg_dist = np.mean(dists[:min(3, len(dists))])
    score = float(np.clip(100.0 * (1.0 - avg_dist / MAX_PRESS_DIST), 0.0, 100.0))
    return round(score, 1), pressing_team


def who_has_ball(ball: dict | None, players: list[dict]) -> str:
    """Return 'home' or 'away' based on which player is nearest the ball."""
    if ball is None or not players:
        return "home"
    closest = min(players, key=lambda p: _euclidean(ball, p))
    return closest.get("team", "home")


class PressingTracker:
    """Detects pressing triggers: sudden jumps in pressing score."""

    def __init__(self):
        self._history: deque = deque(maxlen=TRIGGER_WINDOW)

    def update(self, score: float) -> bool:
        self._history.append(score)
        if len(self._history) == TRIGGER_WINDOW:
            jump = self._history[-1] - self._history[0]
            return jump >= TRIGGER_JUMP
        return False
