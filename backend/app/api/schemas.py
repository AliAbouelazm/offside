from pydantic import BaseModel
from typing import Any


class ClipInfo(BaseModel):
    id: str
    has_video: bool
    has_cache: bool


class AnalysisSummary(BaseModel):
    avg_formation_home: str
    avg_formation_away: str
    peak_pressing_score: float
    avg_pressing_score: float
    avg_space_control_home: float
    avg_space_control_away: float
    avg_inter_player_dist_home: float
    avg_inter_player_dist_away: float
    total_frames_analyzed: int


class TimelineData(BaseModel):
    frames: list[int]
    timestamps: list[float]
    pressing_scores: list[float]
    space_control_home: list[float]
    space_control_away: list[float]
    formation_home: list[str]
    formation_away: list[str]
    pressing_team: list[str]


class FrameData(BaseModel):
    frame_num: int
    timestamp: float
    homography_quality: str
    team_with_ball: str
    formation_home: str
    formation_away: str
    pressing_score: float
    pressing_team: str
    pressing_trigger: bool
    space: dict[str, Any]


class AnalysisResult(BaseModel):
    metadata: dict[str, Any]
    summary: AnalysisSummary
    timeline: TimelineData
    per_frame: list[FrameData]
