"""
ByteTrack multi-object tracker wrapping the boxmot library.
Produces persistent track IDs across frames for all detected objects.
"""
import numpy as np
import cv2

from app.vision.detector import Detector, CLASS_NAMES


def _make_byte_tracker():
    from boxmot.trackers.bytetrack.bytetrack import ByteTrack
    return ByteTrack(track_thresh=0.45, match_thresh=0.8, track_buffer=30)


class Tracker:
    def __init__(self, model_path=None):
        self.detector = Detector(model_path)
        self.byte_tracker = _make_byte_tracker()

    def track_frame(self, frame: np.ndarray, frame_num: int) -> list[dict]:
        detections = self.detector.detect(frame)

        if not detections:
            return []

        dets = np.array(
            [[d["bbox"][0], d["bbox"][1], d["bbox"][2], d["bbox"][3], d["conf"], d["cls"]]
             for d in detections],
            dtype=np.float32,
        )

        try:
            raw = self.byte_tracker.update(dets, frame)
        except Exception:
            return []

        if raw is None or len(raw) == 0:
            return []

        results = []
        for t in raw:
            x1, y1, x2, y2 = float(t[0]), float(t[1]), float(t[2]), float(t[3])
            track_id = int(t[4])
            conf = float(t[5]) if len(t) > 5 else 0.5
            cls = int(t[6]) if len(t) > 6 else 0
            results.append({
                "track_id": track_id,
                "bbox": [x1, y1, x2, y2],
                "conf": conf,
                "cls": cls,
                "class_name": CLASS_NAMES.get(cls, "player"),
                "frame_num": frame_num,
                # foot point used for pitch mapping
                "foot_x": (x1 + x2) / 2.0,
                "foot_y": y2,
            })

        return results

    def track_video(
        self,
        video_path: str,
        frame_skip: int = 2,
        on_progress=None,
    ) -> tuple[dict, dict]:
        cap = cv2.VideoCapture(str(video_path))
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        frame_tracks: dict[int, list[dict]] = {}
        frame_images: dict[int, np.ndarray] = {}
        frame_num = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_num % frame_skip == 0:
                tracks = self.track_frame(frame, frame_num)
                frame_tracks[frame_num] = tracks
                frame_images[frame_num] = frame.copy()

                if on_progress and frame_num % (frame_skip * 5) == 0:
                    pct = round(60.0 * frame_num / max(total_frames, 1), 1)
                    on_progress({"type": "progress", "phase": "tracking",
                                 "frame": frame_num, "total": total_frames, "pct": pct})

            frame_num += 1

        cap.release()

        metadata = {
            "fps": fps,
            "total_frames": total_frames,
            "processed_frames": sorted(frame_tracks.keys()),
            "width": width,
            "height": height,
            "duration": total_frames / fps,
            "frame_skip": frame_skip,
        }
        return frame_tracks, frame_images, metadata
