# Campus Gate Access Control System

A face recognition-based campus management system that automates student entry/exit tracking at hostel gates using deep learning.

## Functional Requirements

1. **Student Register** — Register students with face capture via webcam
2. **Face Liveness** — Anti-spoof detection (printed photos, replay attacks)
3. **Face Recognition** — Dual-classifier SVM approach for masked/unmasked faces
4. **Multiple Face** — Detect and recognize multiple faces simultaneously
5. **Entry Log** — Timestamp, student name, direction (entry)
6. **Exit Log** — Timestamp, student name, direction (exit)
7. **Student Search** — Search by name, roll number, email, department
8. **Reports & Analytics** — Daily/hourly charts, peak hours, top students
9. **Admin Login** — Admin panel access (no security implementation)
10. **Detect Unknown** — Flag unrecognized faces as unknown
11. **Data Management** — Import/export students, clear old logs

## Non-Functional Requirements

1. **Real-time Processing** — Live webcam feed with background inference
2. **Secure Data & Auth** — Database-backed storage with admin login
3. **Fast Response** — Optimized ONNX inference with GPU/CPU fallback
4. **Easy to Use** — Clean Next.js dashboard with intuitive navigation
5. **Scalable DB** — SQLite with WAL mode, extensible schema
6. **Accuracy 90%+** — Dual-SVM classifiers achieved 100% on test set
7. **Reliability** — Background worker threads, error recovery
8. **Compatibility** — Windows/Linux, CPU/DirectML/CUDA support
9. **Privacy** — Local processing, no cloud dependencies

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.11 |
| Face Recognition | InsightFace (`buffalo_l`) + scikit-learn SVM |
| Anti-Spoof | MiniFASNetV2 (ONNX) |
| Mask Inpainting | LaMa (ONNX) |
| Runtime | ONNX Runtime (CPU / DirectML / CUDA) |
| Computer Vision | OpenCV |
| Backend | FastAPI + Uvicorn |
| Database | SQLite (WAL mode) |
| Frontend | Next.js 14 + Tailwind CSS |

## Project Structure

```
BE_Project/
├── config.py                  # Central configuration (paths, thresholds)
├── capture.py                 # Webcam dataset capture tool
├── recognize2.py              # CLI real-time recognition
├── reconstruct_demo.py        # Offline mask reconstruction demo
├── train2.ipynb               # Jupyter notebook to train SVM classifiers
│
├── model/                     # Core ML/inference modules
│   ├── onnx_providers.py      # ONNX provider selection (CPU/DML/CUDA)
│   ├── face_recognition/
│   │   ├── classifier.py      # Dual-SVM face classification
│   │   └── worker.py          # Background recognition thread
│   ├── liveness/
│   │   └── detector.py        # MiniFASNetV2 anti-spoof detection
│   └── mask/
│       ├── locator.py         # Mask polygon detection
│       ├── reconstructor.py   # LaMa inpainting wrapper
│       └── worker.py          # Background reconstruction thread
│
├── server/                    # FastAPI backend
│   ├── main.py                # FastAPI app entry point
│   ├── database.py            # SQLite connection + init + seed
│   ├── models.py              # Pydantic request/response models
│   ├── schema.sql             # Database schema
│   ├── campus.db              # SQLite database (auto-created)
│   └── routes/
│       ├── students.py        # Student CRUD endpoints
│       ├── status.py          # System status endpoint
│       ├── logs.py            # Gate log endpoints
│       ├── search.py          # Student search endpoint
│       ├── reports.py         # Reports & analytics endpoints
│       ├── recognition.py     # Face recognition API
│       ├── admin.py           # Admin login endpoint
│       └── data.py            # Data management endpoints
│
├── frontend/                  # Next.js 14 frontend
│   ├── package.json
│   ├── next.config.js         # API proxy to backend
│   ├── tailwind.config.js
│   └── src/app/
│       ├── layout.tsx         # Root layout with sidebar
│       ├── page.tsx           # Dashboard
│       ├── register/          # Student registration + face capture
│       ├── recognition/       # Real-time face recognition
│       ├── logs/              # Gate entry/exit logs
│       ├── search/            # Student search
│       ├── reports/           # Reports & analytics
│       ├── admin/             # Admin login panel
│       └── data/              # Data management
│
├── Other Models/              # Pre-trained model weights
│   ├── face_recognition/
│   │   ├── buffalo_l/         # InsightFace models
│   │   ├── svm.pkl            # Full-face SVM classifier
│   │   ├── svm_mask.pkl       # Mask-robust SVM classifier
│   │   ├── labels.json        # Person labels
│   │   └── embed_meta.json    # Training metadata
│   ├── liveness/
│   │   └── MiniFASNetV2.onnx  # Anti-spoof model
│   └── mask/
│       └── lama_fp32.onnx     # LaMa inpainting model
│
├── dataset/                   # Training face images (100 per person)
│   ├── Calvin/
│   ├── Mohan/
│   ├── Ronit/
│   └── Vedang/
│
└── Test_Samples/              # Test images for offline demo
```

## Prerequisites

- Python 3.11
- Node.js 18+
- Webcam (for real-time recognition)
- Optional: GPU with DirectML or CUDA support

### Required Python Packages

```
fastapi
uvicorn
opencv-python
numpy
insightface
onnxruntime
scikit-learn
```

### Required Node Packages

```bash
cd frontend && npm install
```

## Usage

### 1. Install Dependencies

```bash
# Python
pip install fastapi uvicorn opencv-python numpy insightface onnxruntime scikit-learn

# Frontend
cd frontend && npm install
```

### 2. Initialize the Database

```bash
python -m server.database
```

### 3. Capture Training Dataset (optional — already populated)

```bash
python capture.py
```

### 4. Train SVM Classifiers (optional — models already saved)

```bash
jupyter notebook train2.ipynb
```

### 5. Start the Backend (port 8000)

```bash
python -m server.main
```

### 6. Start the Frontend (port 3000)

```bash
cd frontend && npm run dev
```

Open `http://localhost:3000` in a browser.

### 7. Run CLI Recognition (optional)

```bash
python recognize2.py --camera 0 --cpu --det-size 320
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/status` | System status (inside count, logs, window) |
| `GET` | `/api/students` | List all students |
| `POST` | `/api/students` | Register a student |
| `PUT` | `/api/students/:id` | Update a student |
| `DELETE` | `/api/students/:id` | Delete a student |
| `GET` | `/api/students/:id/logs` | Get student's gate logs |
| `GET` | `/api/logs` | Get gate logs (paginated) |
| `GET` | `/api/logs/today` | Today's gate logs |
| `GET` | `/api/logs/stats` | Daily/hourly stats |
| `GET` | `/api/logs/unknown` | Unknown face logs |
| `GET` | `/api/search?q=` | Search students |
| `GET` | `/api/reports/summary` | Weekly report summary |
| `GET` | `/api/reports/daily` | Daily report data |
| `GET` | `/api/reports/camera` | Camera performance |
| `POST` | `/api/recognition/recognize` | Recognize faces in image |
| `POST` | `/api/admin/login` | Admin login |
| `GET` | `/api/data/hostels` | List hostels |
| `GET` | `/api/data/rooms` | List rooms |
| `GET` | `/api/data/cameras` | List cameras |
| `POST` | `/api/data/import` | Bulk import students |
| `GET` | `/api/data/export` | Export all students |
| `DELETE` | `/api/data/clear-logs` | Clear old logs |

## How It Works

### Recognition Pipeline

1. **Capture** — Webcam frame captured (browser or CLI)
2. **Detection** — InsightFace `buffalo_l` detects faces, extracts 512-d embeddings
3. **Liveness Check** — MiniFASNetV2 classifies: `live`, `print`, or `replay`
4. **Dual Classification** — Both SVMs run in parallel:
   - `svm.pkl` — trained on full (unmasked) faces
   - `svm_mask.pkl` — trained on synthetically masked faces
5. **Selection** — Higher confidence prediction wins
6. **Logging** — Entry/exit event saved to database

### Mask Reconstruction

Optional LaMa inpainting pipeline:
1. Locate mask region via 106-point facial landmarks
2. Generate binary mask polygon
3. Run LaMa inpainting to reconstruct hidden lower face
4. Re-classify reconstructed face

## Database Schema

- `hostels` — Hostel buildings (A-block, B-block)
- `rooms` — Room assignments per hostel
- `students` — Student records with roll numbers, contact info
- `cameras` — Gate camera positions
- `gate_logs` — Entry/exit events with timestamps and confidence
- `unknown_logs` — Unrecognized face events
- `admin_users` — Admin credentials

## Configuration

All paths and thresholds in `config.py`:

```python
CONFIDENCE_THRESHOLD = 0.45  # Minimum confidence for recognition
```

ONNX provider selection (`model/onnx_providers.py`):
1. DirectML (GPU) — preferred
2. CUDA (GPU) — fallback
3. CPU — default

> **Note:** InsightFace is forced to CPU due to SCRFD detector compatibility issues with DirectML.
