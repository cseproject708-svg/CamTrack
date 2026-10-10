from fastapi import APIRouter, HTTPException
from typing import List
from ..database import get_db
from ..models import StudentCreate, StudentUpdate

router = APIRouter(prefix="/api/students", tags=["students"])


@router.get("")
def list_students():
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


@router.get("/{student_id}")
def get_student(student_id: int):
    conn = get_db()
    row = conn.execute(
        """SELECT s.*, h.name as hostel_name, r.room_number
           FROM students s
           LEFT JOIN hostels h ON s.hostel_id = h.id
           LEFT JOIN rooms r ON s.room_id = r.id
           WHERE s.id = ?""",
        (student_id,),
    ).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Student not found")
    return dict(row)


@router.post("")
def create_student(student: StudentCreate):
    conn = get_db()
    try:
        cur = conn.execute(
            """INSERT INTO students (roll_number, name, email, phone, department, year_of_study, hostel_id, room_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (student.roll_number, student.name, student.email, student.phone,
             student.department, student.year_of_study, student.hostel_id, student.room_id),
        )
        conn.commit()
        student_id = cur.lastrowid
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=400, detail=str(e))
    row = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    conn.close()
    return dict(row)


@router.put("/{student_id}")
def update_student(student_id: int, data: StudentUpdate):
    conn = get_db()
    fields = {k: v for k, v in data.model_dump().items() if v is not None}
    if not fields:
        conn.close()
        raise HTTPException(status_code=400, detail="No fields to update")
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [student_id]
    conn.execute(f"UPDATE students SET {set_clause} WHERE id = ?", values)
    conn.commit()
    row = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Student not found")
    return dict(row)


@router.delete("/{student_id}")
def delete_student(student_id: int):
    conn = get_db()
    conn.execute("DELETE FROM students WHERE id = ?", (student_id,))
    conn.commit()
    conn.close()
    return {"detail": "Student deleted"}


@router.get("/{student_id}/logs")
def get_student_logs(student_id: int):
    conn = get_db()
    rows = conn.execute(
        """SELECT gl.*, c.name as camera_name, s.name as student_name, s.roll_number
           FROM gate_logs gl
           JOIN students s ON gl.student_id = s.id
           LEFT JOIN cameras c ON gl.camera_id = c.id
           WHERE gl.student_id = ?
           ORDER BY gl.timestamp DESC
           LIMIT 100""",
        (student_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
