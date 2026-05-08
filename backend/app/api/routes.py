import asyncio
import json
import tempfile
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

from app.vision.pipeline import list_demo_clips, process_clip_for_demo, process_video

router = APIRouter()


@router.get("/clips")
def get_clips():
    """List available demo clips."""
    return list_demo_clips()


@router.get("/clips/{clip_id}")
def get_clip_result(clip_id: str):
    """Return cached analysis for a demo clip (or trigger processing)."""
    result = process_clip_for_demo(clip_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/analyze/demo/{clip_id}")
async def analyze_demo_stream(
    clip_id: str,
    frame_skip: int = Query(default=2, ge=1, le=10),
):
    """
    SSE endpoint: streams progress events then sends the full result.
    The frontend connects to this and receives JSON-encoded events.
    """
    async def event_generator():
        loop = asyncio.get_event_loop()
        queue: asyncio.Queue = asyncio.Queue()

        def on_progress(event: dict):
            loop.call_soon_threadsafe(queue.put_nowait, event)

        async def run_pipeline():
            result = await loop.run_in_executor(
                None,
                lambda: process_clip_for_demo(clip_id, frame_skip=frame_skip),
            )
            await queue.put({"type": "done", "result": result})

        task = asyncio.create_task(run_pipeline())

        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=120.0)
            except asyncio.TimeoutError:
                yield {"data": json.dumps({"type": "error", "message": "timeout"})}
                break

            yield {"data": json.dumps(event)}

            if event.get("type") in ("done", "error"):
                break

        await task

    return EventSourceResponse(event_generator())


@router.post("/analyze/upload")
async def analyze_upload_stream(
    file: UploadFile = File(...),
    frame_skip: int = Query(default=2, ge=1, le=10),
):
    """
    SSE endpoint for user-uploaded video files.
    Saves to a temp file, runs the pipeline, streams progress.
    """
    suffix = Path(file.filename).suffix if file.filename else ".mp4"

    async def event_generator():
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp_path = tmp.name
            content = await file.read()
            tmp.write(content)

        loop = asyncio.get_event_loop()
        queue: asyncio.Queue = asyncio.Queue()

        def on_progress(event: dict):
            loop.call_soon_threadsafe(queue.put_nowait, event)

        async def run_pipeline():
            result = await loop.run_in_executor(
                None,
                lambda: process_video(tmp_path, frame_skip=frame_skip,
                                      on_progress=on_progress),
            )
            await queue.put({"type": "done", "result": result})

        task = asyncio.create_task(run_pipeline())

        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=300.0)
            except asyncio.TimeoutError:
                yield {"data": json.dumps({"type": "error", "message": "timeout"})}
                break

            yield {"data": json.dumps(event)}

            if event.get("type") in ("done", "error"):
                break

        await task
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    return EventSourceResponse(event_generator())
