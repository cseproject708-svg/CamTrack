import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi import APIRouter, UploadFile, File, Query
import cv2
import numpy as np

from config import (
    CONFIDENCE_THRESHOLD, ENTRY_CONFIDENCE_THRESHOLD, LIVENESS_MODEL_PATH,
    DETECTION_RETRY_ENHANCED, LIVENESS_SOFT_FALLBACK, LIVENESS_MIN_CONF_FOR_SOFT,
    ensure_dirs,
)
from model.face_recognition import load_models
from model.liveness import LivenessDetector
from model.preprocessing import assess_frame, normalize_illumination
from server.database import get_db

router = APIRouter(prefix="/api/recognition", tags=["recognition"])

_models_loaded = False
_app = None
_svm_full = None
_svm_mask = None
_persons = None
_liveness = None


def _load_models():
    global _models_loaded, _app, _svm_full, _svm_mask, _persons, _liveness
    if _models_loaded:
        return
    ensure_dirs()
    _app, _svm_full, _svm_mask, _persons = load_models(det_size=320, force_cpu=False)
    try:
        _liveness = LivenessDetector(LIVENESS_MODEL_PATH, force_cpu=False)
    except Exception:
        _liveness = None
    _models_loaded = True
    print("Recognition models loaded.")


def _determine_direction(conn, student_id, camera_id):
    last_log = conn.execute(
        """SELECT direction FROM gate_logs
           WHERE student_id = ? AND camera_id = ?
           ORDER BY timestamp DESC LIMIT 1""",
        (student_id, camera_id),
    ).fetchone()
    if last_log is None:
        return "entry"
    return "exit" if last_log["direction"] == "entry" else "entry"


def _is_duplicate(conn, student_id, camera_id, cooldown_seconds=15):
    last_log = conn.execute(
        """SELECT timestamp FROM gate_logs
           WHERE student_id = ? AND camera_id = ?
           ORDER BY timestamp DESC LIMIT 1""",
        (student_id, camera_id),
    ).fetchone()
    if last_log is None:
        return False
    try:
        ts_raw = last_log["timestamp"]
        # DB stores either "YYYY-MM-DD HH:MM:SS" or ISO "YYYY-MM-DDTHH:MM:SS"
        last_ts = datetime.fromisoformat(ts_raw.replace("Z", ""))
    except Exception:
        return False
    return (datetime.now() - last_ts).total_seconds() < cooldown_seconds


def _log_unknown(conn, camera_id, confidence):
    """Persist spoof/unknown attempts so reports can count them."""
    try:
        conn.execute(
            "INSERT INTO unknown_logs (camera_id, confidence, timestamp) VALUES (?, ?, ?)",
            (camera_id, float(confidence or 0), datetime.now().isoformat()),
        )
        conn.commit()
    except Exception as e:
        print(f"[recognition] unknown-log error: {e}")


@router.post("/recognize")
async def recognize_face(
    file: UploadFile = File(...),
    camera_id: int = Query(default=1, ge=1),
):
    _load_models()

    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if frame is None:
        return {"faces": [], "logs": []}

    quality = assess_frame(frame)

    faces = _app.get(frame)
    from_enhanced = False
    if not faces and DETECTION_RETRY_ENHANCED and quality["warnings"]:
        # Dynamic lighting retry: white-balance + gamma + CLAHE, then
        # detect again on the normalized frame (same size, bboxes align).
        try:
            enhanced = normalize_illumination(frame)
            faces = _app.get(enhanced)
            from_enhanced = len(faces) > 0
        except Exception as e:
            print(f"[recognition] enhanced detection error: {e}")
            enhanced = None
    else:
        enhanced = None
    # If faces came from the enhanced frame, run liveness on it too so
    # bboxes stay aligned; otherwise use the raw frame (MiniFASNet was
    # trained on raw pixels).
    infer_frame = enhanced if from_enhanced else frame
    results = []
    logs = []

    for face in faces:
        bbox = [int(v) for v in face.bbox]

        is_live = True
        live_conf = 1.0
        if _liveness is not None:
            try:
                # Stateless: each REST request may be a different person,
                # so don't use cross-request temporal smoothing here.
                is_live, probs = _liveness.predict(infer_frame, bbox, smooth=False)
                live_conf = float(np.asarray(probs, dtype=np.float32)[_liveness.live_index])
            except Exception as e:
                print(f"[liveness] error: {e}")
                is_live = True  # fail-open: don't block recognition on liveness crash

        from model.face_recognition.classifier import classify_detailed
        emb = np.asarray(face.normed_embedding, dtype=np.float32)
        name, conf, via = classify_detailed(_svm_full, _svm_mask, _persons, emb, CONFIDENCE_THRESHOLD)

        if not is_live and LIVENESS_SOFT_FALLBACK and name != "Unknown" and conf >= LIVENESS_MIN_CONF_FOR_SOFT:
            # Dynamic-environment soft pass: lighting/blur makes MiniFASNet
            # under-confident on genuine faces. Keep the recognition result,
            # flag it, and log with is_live=0 instead of dropping the entry.
            face_is_live = False
            results.append({"bbox": bbox, "name": name, "confidence": round(conf, 4),
                            "is_live": False, "spoof": False, "liveness_warning": True,
                            "live_confidence": round(live_conf, 4)})
        elif not is_live:
            results.append({"bbox": bbox, "name": "Spoof", "confidence": 0, "is_live": False, "spoof": True})
            try:
                conn = get_db()
                _log_unknown(conn, camera_id, 0)
                conn.close()
            except Exception:
                pass
            continue
        else:
            face_is_live = True
            results.append({"bbox": bbox, "name": name, "confidence": round(conf, 4), "is_live": True, "spoof": False})

        if name != "Unknown" and conf >= ENTRY_CONFIDENCE_THRESHOLD:
            try:
                conn = get_db()
                student = conn.execute("SELECT id FROM students WHERE name = ?", (name,)).fetchone()
                if not student:
                    conn.execute(
                        "INSERT INTO students (roll_number, name) VALUES (?, ?)",
                        (name.lower(), name),
                    )
                    conn.commit()
                    student = conn.execute("SELECT id FROM students WHERE name = ?", (name,)).fetchone()
                    print(f"[recognition] auto-created student: {name}")

                camera = conn.execute("SELECT id, name FROM cameras WHERE id = ?", (camera_id,)).fetchone()
                if not camera:
                    conn.execute(
                        "INSERT OR IGNORE INTO cameras (id, name, location) VALUES (?, ?, ?)",
                        (camera_id, f"Camera {camera_id}", "Main Gate"),
                    )
                    conn.commit()

                if _is_duplicate(conn, student["id"], camera_id):
                    print(f"[recognition] duplicate skipped: {name} (cooldown)")
                else:
                    direction = _determine_direction(conn, student["id"], camera_id)
                    conn.execute(
                        "INSERT INTO gate_logs (student_id, camera_id, direction, confidence, is_live, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                        (student["id"], camera_id, direction, round(conf, 4), 1 if face_is_live else 0, datetime.now().isoformat()),
                    )
                    conn.commit()
                    logs.append({
                        "student_name": name,
                        "direction": direction,
                        "camera_id": camera_id,
                        "camera_name": f"Camera {camera_id}",
                        "timestamp": datetime.now().isoformat(),
                        "liveness_warning": not face_is_live,
                    })
                    print(f"[recognition] LOGGED: {name} -> {direction} (conf={conf:.2%})")
                conn.close()
            except Exception as e:
                print(f"[recognition] log error: {e}")

    return {"faces": results, "logs": logs, "quality": quality}
