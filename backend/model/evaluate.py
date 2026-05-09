"""
Evaluate the fine-tuned (or fallback) YOLOv8 model on a held-out set.

Produces:
  model/eval_results/detection_metrics.json  , mAP, precision, recall per class
  model/eval_results/confusion_matrix.png
  model/eval_results/sample_{i}.jpg          , 10 annotated sample images

Usage:
    python model/evaluate.py [--weights model/best.pt] [--source path/to/images]
"""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np

MODEL_DIR = Path(__file__).parent
EVAL_DIR = MODEL_DIR / "eval_results"
BEST_PT = MODEL_DIR / "best.pt"
FALLBACK_PT = "yolov8m.pt"

CLASS_NAMES = ["player", "goalkeeper", "referee", "ball"]
CLASS_COLORS = {
    "player": (0, 180, 255),      # orange
    "goalkeeper": (0, 255, 120),  # green
    "referee": (200, 200, 0),     # cyan
    "ball": (255, 80, 80),        # blue
}


def _draw_detections(frame: np.ndarray, result) -> np.ndarray:
    """Draw YOLOv8 result boxes onto frame."""
    out = frame.copy()
    if result.boxes is None:
        return out
    for box in result.boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
        cls_idx = int(box.cls[0])
        conf = float(box.conf[0])
        cls_name = CLASS_NAMES[cls_idx] if cls_idx < len(CLASS_NAMES) else str(cls_idx)
        color = CLASS_COLORS.get(cls_name, (255, 255, 255))
        cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)
        label = f"{cls_name} {conf:.2f}"
        cv2.putText(out, label, (x1, y1 - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 1)
    return out


def evaluate(weights: str | None = None, source: str | None = None, sample_count: int = 10):
    from ultralytics import YOLO

    EVAL_DIR.mkdir(parents=True, exist_ok=True)

    weights_path = weights or (str(BEST_PT) if BEST_PT.exists() else FALLBACK_PT)
    model = YOLO(weights_path)

    print(f"Loaded weights: {weights_path}")

    # ------------------------------------------------------------------
    # Quantitative evaluation (requires a labeled dataset)
    # ------------------------------------------------------------------
    metrics_data = {
        "weights": str(weights_path),
        "classes": CLASS_NAMES,
    }

    if source:
        # Run YOLO val if we have a data.yaml or a folder
        if str(source).endswith(".yaml"):
            metrics = model.val(data=source, project=str(EVAL_DIR), name="val", exist_ok=True)
            box = metrics.box
            metrics_data.update({
                "mAP50": round(float(box.map50), 4),
                "mAP50_95": round(float(box.map), 4),
                "precision": round(float(box.mp), 4),
                "recall": round(float(box.mr), 4),
                "per_class": {
                    CLASS_NAMES[i]: {
                        "ap50": round(float(box.ap50[i]), 4) if i < len(box.ap50) else None,
                        "ap": round(float(box.ap[i]), 4) if i < len(box.ap) else None,
                    }
                    for i in range(len(CLASS_NAMES))
                },
            })
            print(f"mAP50: {metrics_data['mAP50']}  mAP50-95: {metrics_data['mAP50_95']}")
        else:
            print(f"Source {source} is not a .yaml; skipping quantitative eval.")

    with open(EVAL_DIR / "detection_metrics.json", "w") as f:
        json.dump(metrics_data, f, indent=2)
    print(f"Metrics saved to {EVAL_DIR / 'detection_metrics.json'}")

    # ------------------------------------------------------------------
    # Sample visualizations, run inference on whatever images are available
    # ------------------------------------------------------------------
    image_paths: list[Path] = []

    if source and not str(source).endswith(".yaml"):
        src_path = Path(source)
        if src_path.is_dir():
            for ext in ("*.jpg", "*.jpeg", "*.png"):
                image_paths.extend(src_path.glob(ext))
        elif src_path.is_file():
            image_paths = [src_path]

    if not image_paths:
        print("No sample images provided for visualization, skipping sample generation.")
        return metrics_data

    image_paths = image_paths[:sample_count]
    results = model(image_paths, verbose=False)

    for i, (img_path, result) in enumerate(zip(image_paths, results)):
        frame = cv2.imread(str(img_path))
        if frame is None:
            continue
        annotated = _draw_detections(frame, result)
        out_path = EVAL_DIR / f"sample_{i:02d}.jpg"
        cv2.imwrite(str(out_path), annotated)

    print(f"Saved {len(image_paths)} sample visualizations to {EVAL_DIR}/")

    # Confusion matrix is generated automatically by YOLO val; copy if present
    cm_src = EVAL_DIR / "val" / "confusion_matrix.png"
    if cm_src.exists():
        import shutil
        shutil.copy(cm_src, EVAL_DIR / "confusion_matrix.png")

    return metrics_data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate YOLOv8 model")
    parser.add_argument("--weights", type=str, default=None,
                        help="Path to .pt weights (default: model/best.pt or yolov8m.pt)")
    parser.add_argument("--source", type=str, default=None,
                        help="Path to data.yaml (for mAP) or image folder (for samples)")
    parser.add_argument("--samples", type=int, default=10)
    args = parser.parse_args()
    evaluate(weights=args.weights, source=args.source, sample_count=args.samples)
