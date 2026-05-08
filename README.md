# Offside

Computer vision and tactical analytics for broadcast soccer footage.

**Live demo:** _coming soon_

## What it does

Upload or select a broadcast clip. The pipeline:

1. Detects players, goalkeepers, referees, and the ball using YOLOv8m
2. Tracks each entity across frames with ByteTrack (persistent IDs)
3. Maps pixel positions to real pitch coordinates via homography estimation
4. Assigns teams via KMeans clustering on torso HSV colors
5. Computes per-frame **formation** (3- or 4-line KMeans on pitch depth)
6. Computes **pressing intensity** (0–100 score based on nearest opponents to ball carrier)
7. Computes **Voronoi space control** (% of pitch controlled per team)
8. Aggregates everything into a tactical dashboard

## Stack

| Layer | Tech |
|---|---|
| Detection | YOLOv8m (Ultralytics) |
| Tracking | ByteTrack via boxmot |
| Homography | OpenCV (HSV line detection + RANSAC) |
| Analytics | NumPy, SciPy, scikit-learn, Shapely |
| Backend | FastAPI + SSE streaming |
| Frontend | React 18 + Vite, plain CSS modules |
| Deployment | HuggingFace Spaces (backend) + Vercel (frontend) |

## Running locally

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev   # http://localhost:5173
```

### Fine-tune the detector (optional)

```bash
cd backend
python model/train.py --epochs 50 --batch 16
```

## Demo clips

Five broadcast clips are pre-loaded in `backend/demo_clips/`:

| ID | Match |
|---|---|
| `possession` | Possession sequence |
| `pressing` | High-press sequence |
| `open_play` | Chelsea vs Arsenal |
| `transition` | Tottenham vs Watford |
| `ucl` | Liverpool vs PSG (UCL) |

## Deployment

- Backend: HuggingFace Spaces (Docker) — see `backend/Dockerfile`
- Frontend: Vercel — set `VITE_API_URL` to your HF Space URL

> Work in progress
