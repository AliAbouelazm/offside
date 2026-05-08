"""
Pre-process all demo clips so they're instantly available in the UI.
Run once from offside/backend/:

    python scripts/precache.py

Clips already cached are skipped. Delete demo_results/<clip_id>.json to re-run one.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.vision.pipeline import list_demo_clips, process_clip_for_demo


def main():
    clips = list_demo_clips()
    if not clips:
        print("No clips found. Download them first with yt-dlp.")
        return

    print(f"Found {len(clips)} clip(s)\n")
    for clip in clips:
        cid = clip["id"]
        if clip.get("has_cache"):
            print(f"  {cid} — already cached, skipping")
            continue
        if not clip.get("has_video"):
            print(f"  {cid} — no video file, skipping")
            continue

        print(f"  {cid} — processing...")

        def on_progress(evt):
            if evt.get("type") == "progress":
                print(
                    f"    [{evt.get('phase', '')}] "
                    f"frame {evt.get('frame', '')} / {evt.get('total', '')} "
                    f"({evt.get('pct', '')}%)",
                    end="\r",
                    flush=True,
                )
            elif evt.get("type") == "status":
                print(f"    {evt.get('message', '')}")

        result = process_clip_for_demo(cid, frame_skip=2, on_progress=on_progress)
        print()
        if "error" in result:
            print(f"  ERROR: {result['error']}")
        else:
            frames = len(result.get("per_frame", []))
            print(f"  {cid} — done ({frames} frames)")

    print("\nAll done. Restart the backend and demo clips will load instantly.")


if __name__ == "__main__":
    main()
