from fastapi import APIRouter, Query
from ..database import get_db

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("")
def search_students(q: str = Query(..., min_length=1)):
    conn = get_db()
    pattern = f"%{q}%"
    rows = conn.execute(
        """SELECT s.*, h.name as hostel_name, r.room_number
           FROM students s
           LEFT JOIN hostels h ON s.hostel_id = h.id
           LEFT JOIN rooms r ON s.room_id = r.id
           WHERE s.name LIKE ? OR s.roll_number LIKE ? OR s.email LIKE ? OR s.department LIKE ?
           ORDER BY s.name""",
        (pattern, pattern, pattern, pattern),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
