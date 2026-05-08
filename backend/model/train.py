"""
Fine-tune YOLOv8m on the Soccana player/ball detection dataset from HuggingFace.

Dataset: Adit-jain/Soccana_player_ball_detection_v1
Classes: player (0), goalkeeper (1), referee (2), ball (3)

Usage:
    python model/train.py [--epochs 50] [--batch 16] [--device cuda]

Outputs:
    model/best.pt        — best checkpoint (used by detector.py)
    model/train_results/ — training plots and metrics
"""
import argparse
import json
import os
import shutil
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
MODEL_DIR = Path(__file__).parent
BEST_PT = MODEL_DIR / "best.pt"
TRAIN_RESULTS_DIR = MODEL_DIR / "train_results"


def download_dataset(cache_dir: Path) -> Path:
    """
    Download Soccana dataset from HuggingFace Hub and convert to YOLO format.
    Returns path to the YOLO data.yaml file.
    """
    from datasets import load_dataset

    print("Downloading Soccana dataset from HuggingFace…")
    ds = load_dataset("Adit-jain/Soccana_player_ball_detection_v1", cache_dir=str(cache_dir))

    # Map split names: some HF datasets use 'validation' instead of 'val'
    split_map = {}
    for split in ds.keys():
        if split == "train":
            split_map["train"] = split
        elif split in ("val", "validation", "valid"):
            split_map["val"] = split
        elif split == "test":
            split_map["test"] = split

    if "val" not in split_map and "train" in split_map:
        # Create val split from last 10% of train
        train_ds = ds[split_map["train"]]
        n = len(train_ds)
        n_val = max(1, int(n * 0.1))
        split_map["train_ds"] = train_ds.select(range(n - n_val))
        split_map["val_ds"] = train_ds.select(range(n - n_val, n))
    else:
        split_map["train_ds"] = ds[split_map["train"]]
        split_map["val_ds"] = ds.get(split_map.get("val", ""), ds[split_map["train"]])

    class_names = ["player", "goalkeeper", "referee", "ball"]

    yolo_dir = cache_dir / "yolo_soccana"
    for split in ("train", "val"):
        (yolo_dir / split / "images").mkdir(parents=True, exist_ok=True)
        (yolo_dir / split / "labels").mkdir(parents=True, exist_ok=True)

    def _write_split(dataset, split_name: str):
        for i, sample in enumerate(dataset):
            img = sample["image"]
            w, h = img.size
            img.save(yolo_dir / split_name / "images" / f"{i:06d}.jpg")

            label_lines = []
            # HF dataset may store annotations in various keys
            objects = sample.get("objects") or sample.get("annotations") or []
            if isinstance(objects, dict):
                # COCO-style with 'bbox', 'category_id'
                bboxes = objects.get("bbox", [])
                cats = objects.get("category_id", [])
                for bbox, cat in zip(bboxes, cats):
                    # Convert cat id to our 0-3 scheme
                    cls = int(cat) % len(class_names)
                    # bbox in [x, y, w, h] pixels
                    xc = (bbox[0] + bbox[2] / 2) / w
                    yc = (bbox[1] + bbox[3] / 2) / h
                    bw = bbox[2] / w
                    bh = bbox[3] / h
                    label_lines.append(f"{cls} {xc:.6f} {yc:.6f} {bw:.6f} {bh:.6f}")
            elif isinstance(objects, list):
                for obj in objects:
                    cat = obj.get("category_id", obj.get("class_id", 0))
                    cls = int(cat) % len(class_names)
                    bbox = obj.get("bbox", obj.get("bounding_box", [0, 0, 1, 1]))
                    xc = (bbox[0] + bbox[2] / 2) / w
                    yc = (bbox[1] + bbox[3] / 2) / h
                    bw = bbox[2] / w
                    bh = bbox[3] / h
                    label_lines.append(f"{cls} {xc:.6f} {yc:.6f} {bw:.6f} {bh:.6f}")

            with open(yolo_dir / split_name / "labels" / f"{i:06d}.txt", "w") as f:
                f.write("\n".join(label_lines))

    print("Converting train split…")
    _write_split(split_map["train_ds"], "train")
    print("Converting val split…")
    _write_split(split_map["val_ds"], "val")

    # Write data.yaml
    yaml_content = f"""
path: {yolo_dir}
train: train/images
val: val/images

nc: {len(class_names)}
names: {class_names}
""".strip()

    yaml_path = yolo_dir / "data.yaml"
    yaml_path.write_text(yaml_content)
    print(f"Dataset ready at {yolo_dir}")
    return yaml_path


def train(epochs: int = 50, batch: int = 16, device: str = "auto", img_size: int = 640):
    from ultralytics import YOLO

    TRAIN_RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="soccana_") as tmp:
        cache_dir = Path(tmp)
        yaml_path = download_dataset(cache_dir)

        model = YOLO("yolov8m.pt")

        results = model.train(
            data=str(yaml_path),
            epochs=epochs,
            batch=batch,
            imgsz=img_size,
            device=device,
            project=str(TRAIN_RESULTS_DIR),
            name="run",
            exist_ok=True,
            patience=15,
            save=True,
            plots=True,
        )

        # Copy best checkpoint to model/best.pt
        run_dir = TRAIN_RESULTS_DIR / "run"
        best_src = run_dir / "weights" / "best.pt"
        if best_src.exists():
            shutil.copy(best_src, BEST_PT)
            print(f"Best checkpoint saved to {BEST_PT}")
        else:
            print(f"WARNING: best.pt not found at {best_src}")

        # Save metrics summary
        metrics_summary = {
            "epochs_trained": epochs,
            "batch_size": batch,
            "img_size": img_size,
            "device": str(device),
        }
        if hasattr(results, "results_dict"):
            metrics_summary.update(results.results_dict)

        with open(TRAIN_RESULTS_DIR / "metrics_summary.json", "w") as f:
            json.dump(metrics_summary, f, indent=2, default=str)

    print("Training complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fine-tune YOLOv8m on Soccana dataset")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--device", type=str, default="auto",
                        help="'cpu', 'cuda', '0', 'mps', or 'auto'")
    parser.add_argument("--imgsz", type=int, default=640)
    args = parser.parse_args()
    train(epochs=args.epochs, batch=args.batch, device=args.device, img_size=args.imgsz)
