import os
import sys
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import Optional
from ..database import get_db
from ..models import StudentCreate
from config import DATASET_DIR

router = APIRouter(prefix="/api/data", tags=["data"])


@router.get("/hostels")
def list_hostels():
    conn = get_db()
    rows = conn.execute("SELECT * FROM hostels ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.get("/rooms")
def list_rooms(hostel_id: Optional[int] = None):
    conn = get_db()
    if hostel_id:
        rows = conn.execute(
            "SELECT * FROM rooms WHERE hostel_id = ? ORDER BY room_number",
            (hostel_id,),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM rooms ORDER BY room_number").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.get("/cameras")
def list_cameras():
    conn = get_db()
    rows = conn.execute(
        """SELECT c.*, h.name as hostel_name
           FROM cameras c
           LEFT JOIN hostels h ON c.hostel_id = h.id
           ORDER BY c.name"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.post("/import")
def import_students(students: list[StudentCreate]):
    conn = get_db()
    imported = 0
    for s in students:
        try:
            conn.execute(
                """INSERT INTO students (roll_number, name, email, phone, department, year_of_study, hostel_id, room_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (s.roll_number, s.name, s.email, s.phone, s.department, s.year_of_study, s.hostel_id, s.room_id),
            )
            imported += 1
        except Exception:
            continue
    conn.commit()
    conn.close()
    return {"imported": imported, "total": len(students)}


@router.get("/export")
def export_students():
    conn = get_db()
    rows = conn.execute(
        """SELECT s.*, h.name as hostel_name, r.room_number
           FROM students s
           LEFT JOIN hostels h ON s.hostel_id = h.id
           LEFT JOIN rooms r ON s.room_id = r.id
           ORDER BY s.name"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.delete("/clear-logs")
def clear_old_logs(days: int = 90):
    from datetime import date, timedelta
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    conn = get_db()
    result = conn.execute("DELETE FROM gate_logs WHERE DATE(timestamp) < ?", (cutoff,))
    conn.commit()
    deleted = result.rowcount
    conn.close()
    return {"deleted": deleted}


@router.post("/register-student")
async def register_student(
    roll_number: str = Form(...),
    name: str = Form(...),
    email: str = Form(default=None),
    phone: str = Form(default=None),
    department: str = Form(default=None),
    year_of_study: int = Form(default=None),
    hostel_id: int = Form(default=None),
    room_id: int = Form(default=None),
    photos: list[UploadFile] = File(..., description="Face photos (min 5)"),
):
    if len(photos) < 5:
        raise HTTPException(status_code=400, detail="At least 5 face photos required")

    conn = get_db()
    try:
        cur = conn.execute(
            """INSERT INTO students (roll_number, name, email, phone, department, year_of_study, hostel_id, room_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (roll_number, name, email, phone, department, year_of_study, hostel_id, room_id),
        )
        student_id = cur.lastrowid
        conn.commit()
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=400, detail=str(e))
    conn.close()

    person_dir = os.path.join(DATASET_DIR, name)
    os.makedirs(person_dir, exist_ok=True)

    saved = 0
    for photo in photos:
        contents = await photo.read()
        ext = os.path.splitext(photo.filename or "img.jpg")[1].lower()
        if ext not in (".jpg", ".jpeg", ".png"):
            continue
        filename = f"{uuid.uuid4().hex}{ext}"
        filepath = os.path.join(person_dir, filename)
        with open(filepath, "wb") as f:
            f.write(contents)
        saved += 1

    return {
        "student_id": student_id,
        "name": name,
        "roll_number": roll_number,
        "photos_saved": saved,
        "message": f"Student registered. {saved} photos saved. Run /api/data/retrain to update the model.",
    }


@router.post("/upload-photos")
async def upload_photos(
    name: str = Form(...),
    photos: list[UploadFile] = File(...),
):
    person_dir = os.path.join(DATASET_DIR, name)
    os.makedirs(person_dir, exist_ok=True)

    existing = len([f for f in os.listdir(person_dir) if f.lower().endswith((".jpg", ".jpeg", ".png"))])
    saved = 0
    for photo in photos:
        contents = await photo.read()
        ext = os.path.splitext(photo.filename or "img.jpg")[1].lower()
        if ext not in (".jpg", ".jpeg", ".png"):
            continue
        filename = f"{uuid.uuid4().hex}{ext}"
        filepath = os.path.join(person_dir, filename)
        with open(filepath, "wb") as f:
            f.write(contents)
        saved += 1

    return {
        "name": name,
        "photos_saved": saved,
        "total_photos": existing + saved,
        "message": f"{saved} photos added. Run /api/data/retrain to update the model.",
    }


@router.post("/retrain")
def retrain_model(full: bool = False):
    from model.face_recognition.trainer import train_all
    try:
        meta = train_all(det_size=640, force_cpu=False, incremental=not full)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "message": "Model retrained successfully",
        "mode": "full" if full else "incremental",
        "persons": meta["persons"],
        "n_samples": meta["n_samples_full"],
        "n_new_computed": meta["n_new_computed"],
        "n_cached": meta["n_cached"],
        "accuracy_full": meta["accuracy_full"],
        "accuracy_mask": meta["accuracy_mask"],
    }


@router.post("/reset-cache")
def reset_embedding_cache():
    from model.face_recognition.trainer import reset_cache
    reset_cache()
    return {"detail": "Embedding cache cleared. Next retrain will recompute all embeddings."}
