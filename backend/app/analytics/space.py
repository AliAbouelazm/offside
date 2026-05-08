"""
Voronoi-based space control computation.

Each player controls the area of the pitch closer to them than to any
other player. Cells are clipped to the pitch boundary.
Space control is expressed as a percentage per team.

Dangerous space: a cell in the attacking final third with area above threshold.
"""
import numpy as np
from scipy.spatial import Voronoi
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union

PITCH_W = 105.0
PITCH_H = 68.0
FINAL_THIRD = 70.0       # pitch_x >= 70 for home team attacking final third
DANGER_AREA = 30.0       # sq meters threshold for "dangerous" cell

_PITCH_POLY = Polygon([(0, 0), (PITCH_W, 0), (PITCH_W, PITCH_H), (0, PITCH_H)])

# Far boundary points to close the Voronoi diagram
_BOUNDARY_PTS = np.array([
    [-500, -500], [500, -500], [-500, 500], [500, 500],
    [PITCH_W / 2, -500], [PITCH_W / 2, 500],
    [-500, PITCH_H / 2], [500, PITCH_H / 2],
], dtype=np.float64)


def _voronoi_cell(vor: Voronoi, idx: int) -> Polygon | None:
    region_idx = vor.point_region[idx]
    region = vor.regions[region_idx]
    if -1 in region or len(region) == 0:
        return None
    try:
        poly = Polygon([vor.vertices[i] for i in region])
        return poly.intersection(_PITCH_POLY)
    except Exception:
        return None


def compute_voronoi_control(
    players: list[dict],
) -> dict:
    """
    Compute Voronoi space control for all players.
    Returns dict with:
      home_pct, away_pct (0-100 floats)
      dangerous_space_home, dangerous_space_away (sq meters)
      cells: list of {track_id, team, area, polygon_coords}
    """
    if len(players) < 3:
        return {"home_pct": 50.0, "away_pct": 50.0,
                "dangerous_space_home": 0.0, "dangerous_space_away": 0.0, "cells": []}

    pts = np.array([[p["pitch_x"], p["pitch_y"]] for p in players], dtype=np.float64)
    all_pts = np.vstack([pts, _BOUNDARY_PTS])

    try:
        vor = Voronoi(all_pts)
    except Exception:
        return {"home_pct": 50.0, "away_pct": 50.0,
                "dangerous_space_home": 0.0, "dangerous_space_away": 0.0, "cells": []}

    home_area = 0.0
    away_area = 0.0
    dangerous_home = 0.0
    dangerous_away = 0.0
    cells = []

    for i, player in enumerate(players):
        cell = _voronoi_cell(vor, i)
        if cell is None or cell.is_empty:
            continue

        area = float(cell.area)
        team = player.get("team", "home")

        if team == "home":
            home_area += area
            # Final third for home = high pitch_x
            if player["pitch_x"] >= FINAL_THIRD and area >= DANGER_AREA:
                dangerous_home += area
        elif team == "away":
            away_area += area
            # Final third for away = low pitch_x
            if player["pitch_x"] <= PITCH_W - FINAL_THIRD and area >= DANGER_AREA:
                dangerous_away += area

        if hasattr(cell, "exterior"):
            coords = list(cell.exterior.coords)
        else:
            coords = []

        cells.append({
            "track_id": player.get("track_id"),
            "team": team,
            "area": round(area, 2),
            "polygon": [[round(x, 2), round(y, 2)] for x, y in coords],
        })

    total = home_area + away_area or 1.0
    return {
        "home_pct": round(100.0 * home_area / total, 1),
        "away_pct": round(100.0 * away_area / total, 1),
        "dangerous_space_home": round(dangerous_home, 2),
        "dangerous_space_away": round(dangerous_away, 2),
        "cells": cells,
    }
