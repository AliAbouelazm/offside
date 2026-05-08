"""
Broadcast-to-pitch homography estimation using OpenCV.

The pitch template uses meters with origin at top-left:
  x: 0 (left goal line) to 105 (right goal line)
  y: 0 (top touchline) to 68 (bottom touchline)

Estimation strategy:
  1. Detect green pitch area via HSV thresholding.
  2. Find white line segments within the green area.
  3. Classify lines as horizontal or vertical.
  4. Intersect extreme lines to get visible pitch corners.
  5. Match corners to pitch template using aspect-ratio heuristics.
  6. Compute homography with RANSAC.
  7. Fall back to cached or estimated transform if detection fails.
"""
import cv2
import numpy as np

PITCH_W = 105.0
PITCH_H = 68.0

# Key pitch points in meters (x, y) used as template correspondences
TEMPLATE_CORNERS = np.float32([
    [0, 0], [PITCH_W, 0], [0, PITCH_H], [PITCH_W, PITCH_H]
])

# HSV bounds for broadcast grass
_GREEN_LO = np.array([30, 30, 30])
_GREEN_HI = np.array([90, 255, 255])

# HSV bounds for pitch line markings
_WHITE_LO = np.array([0, 0, 180])
_WHITE_HI = np.array([180, 50, 255])


def _green_mask(frame: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, _GREEN_LO, _GREEN_HI)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    return cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)


def _white_mask(frame: np.ndarray, green: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, _WHITE_LO, _WHITE_HI)
    return cv2.bitwise_and(mask, green)


def _detect_segments(white: np.ndarray):
    edges = cv2.Canny(white, 50, 150)
    segs = cv2.HoughLinesP(edges, 1, np.pi / 180,
                           threshold=80, minLineLength=60, maxLineGap=15)
    return segs  # shape (N, 1, 4) or None


def _classify_lines(segs):
    h_lines, v_lines = [], []
    if segs is None:
        return h_lines, v_lines
    for seg in segs:
        x1, y1, x2, y2 = seg[0]
        angle = abs(np.degrees(np.arctan2(y2 - y1, x2 - x1)))
        if angle < 25 or angle > 155:
            h_lines.append((x1, y1, x2, y2))
        elif 65 < angle < 115:
            v_lines.append((x1, y1, x2, y2))
    return h_lines, v_lines


def _line_intersection(l1, l2):
    x1, y1, x2, y2 = l1
    x3, y3, x4, y4 = l2
    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(denom) < 1e-6:
        return None
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
    ix = x1 + t * (x2 - x1)
    iy = y1 + t * (y2 - y1)
    return (ix, iy)


def _representative_line(lines, axis):
    # axis=0: pick topmost/bottommost (y), axis=1: pick leftmost/rightmost (x)
    # returns line closest to min and max
    if not lines:
        return None, None
    vals = [min(l[axis], l[axis + 2]) for l in lines]
    lo = lines[int(np.argmin(vals))]
    hi = lines[int(np.argmax(vals))]
    return lo, hi


def _pitch_corners_from_lines(h_lines, v_lines, shape):
    h, w = shape[:2]

    # Fall back to full frame if not enough lines
    if len(h_lines) < 2 and len(v_lines) < 2:
        return None

    # Extend each line to a full-frame line for intersection purposes
    def extend(seg):
        x1, y1, x2, y2 = seg
        dx, dy = x2 - x1, y2 - y1
        if abs(dx) < 1 and abs(dy) < 1:
            return seg
        t_lo = -max(w, h)
        t_hi = max(w, h)
        return (x1 + t_lo * dx, y1 + t_lo * dy,
                x1 + t_hi * dx, y1 + t_hi * dy)

    h_top_raw, h_bot_raw = _representative_line(h_lines, 1)
    v_left_raw, v_right_raw = _representative_line(v_lines, 0)

    if h_top_raw is None or v_left_raw is None:
        return None

    h_top = extend(h_top_raw)
    h_bot = extend(h_bot_raw) if h_bot_raw else h_top
    v_left = extend(v_left_raw)
    v_right = extend(v_right_raw) if v_right_raw else v_left

    tl = _line_intersection(h_top, v_left)
    tr = _line_intersection(h_top, v_right)
    bl = _line_intersection(h_bot, v_left)
    br = _line_intersection(h_bot, v_right)

    if any(p is None for p in [tl, tr, bl, br]):
        return None

    corners = np.float32([tl, tr, bl, br])

    # Reject if corners are outside a reasonable region
    margin = max(w, h) * 0.3
    for c in corners:
        if c[0] < -margin or c[0] > w + margin or c[1] < -margin or c[1] > h + margin:
            return None

    return corners


def _fallback_from_green(green_mask: np.ndarray, shape) -> np.ndarray:
    h, w = shape[:2]
    cnts, _ = cv2.findContours(green_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        # Use full frame
        return np.float32([[0, 0], [w, 0], [0, h], [w, h]])

    largest = max(cnts, key=cv2.contourArea)
    rect = cv2.minAreaRect(largest)
    box = cv2.boxPoints(rect)
    box = box[np.argsort(box[:, 1])]  # sort by y
    top = box[:2][np.argsort(box[:2, 0])]
    bot = box[2:][np.argsort(box[2:, 0])]
    return np.float32([top[0], top[1], bot[0], bot[1]])


class HomographyEstimator:
    def __init__(self):
        self._cached_H: np.ndarray | None = None

    def estimate(self, frame: np.ndarray) -> tuple[np.ndarray | None, str]:
        H, quality = self._compute(frame)
        if H is not None:
            self._cached_H = H
            return H, quality
        if self._cached_H is not None:
            return self._cached_H, "cached"
        H = self._estimate_fallback(frame)
        return H, "estimated"

    def _compute(self, frame: np.ndarray):
        gm = _green_mask(frame)
        if gm.sum() < 1000:
            return None, "no_pitch"

        wm = _white_mask(frame, gm)
        segs = _detect_segments(wm)
        h_lines, v_lines = _classify_lines(segs)

        src = _pitch_corners_from_lines(h_lines, v_lines, frame.shape)

        if src is None:
            # Try fallback green boundary
            src = _fallback_from_green(gm, frame.shape)
            quality = "estimated"
        else:
            quality = "approximate"

        dst = TEMPLATE_CORNERS.copy()

        H, mask = cv2.findHomography(src, dst, cv2.RANSAC, 5.0)
        if H is None:
            return None, "failed"

        inliers = int(mask.sum()) if mask is not None else 0
        if inliers >= len(src) - 1:
            quality = "exact" if quality != "estimated" else "estimated"

        return H, quality

    def _estimate_fallback(self, frame: np.ndarray) -> np.ndarray:
        h, w = frame.shape[:2]
        src = np.float32([[0, 0], [w, 0], [0, h], [w, h]])
        H, _ = cv2.findHomography(src, TEMPLATE_CORNERS, 0)
        return H


def map_points(points_px: np.ndarray, H: np.ndarray) -> np.ndarray:
    """Transform (N, 2) pixel coordinates to pitch meters using homography H."""
    if len(points_px) == 0:
        return points_px
    pts = points_px.reshape(-1, 1, 2).astype(np.float32)
    mapped = cv2.perspectiveTransform(pts, H)
    return mapped.reshape(-1, 2)


def map_tracks_to_pitch(
    tracks: list[dict],
    H: np.ndarray,
) -> list[dict]:
    """Add pitch_x, pitch_y (meters) to each track dict."""
    if not tracks or H is None:
        return tracks

    feet = np.array([[t["foot_x"], t["foot_y"]] for t in tracks], dtype=np.float32)
    mapped = map_points(feet, H)

    result = []
    for track, (px, py) in zip(tracks, mapped):
        t = dict(track)
        # Clamp to pitch boundaries
        t["pitch_x"] = float(np.clip(px, 0.0, PITCH_W))
        t["pitch_y"] = float(np.clip(py, 0.0, PITCH_H))
        result.append(t)

    return result
