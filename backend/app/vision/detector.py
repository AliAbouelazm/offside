"""
YOLOv8 detector wrapper. Loads fine-tuned model if available,
falls back to pretrained weights with COCO class remapping.
"""
from pathlib import Path

import numpy as np

MODEL_PATH = Path(__file__).parent.parent.parent / "model" / "best.pt"
PRETRAINED = "yolov8m.pt"

# Class indices expected from the fine-tuned model
CLASS_NAMES = {0: "player", 1: "goalkeeper", 2: "referee", 3: "ball"}

# COCO class indices used as fallback when running pretrained weights
COCO_REMAP = {0: "player", 32: "ball"}

CONF_THRESH = {"player": 0.30, "goalkeeper": 0.30, "referee": 0.30, "ball": 0.40}


class Detector:
    def __init__(self, model_path=None):
        from ultralytics import YOLO

        path = model_path or (MODEL_PATH if MODEL_PATH.exists() else PRETRAINED)
        self.model = YOLO(str(path))
        self._finetuned = MODEL_PATH.exists() if model_path is None else True
        print(f"Detector loaded: {path}  fine-tuned={self._finetuned}")

    def detect(self, frame: np.ndarray) -> list[dict]:
        results = self.model(frame, verbose=False)[0]
        detections = []

        for box in results.boxes:
            cls_id = int(box.cls.item())
            conf = float(box.conf.item())

            if self._finetuned:
                class_name = CLASS_NAMES.get(cls_id)
            else:
                class_name = COCO_REMAP.get(cls_id)

            if class_name is None:
                continue
            if conf < CONF_THRESH.get(class_name, 0.30):
                continue

            x1, y1, x2, y2 = box.xyxy[0].tolist()
            detections.append({
                "bbox": [float(x1), float(y1), float(x2), float(y2)],
                "conf": conf,
                "cls": cls_id,
                "class_name": class_name,
            })

        return detections
