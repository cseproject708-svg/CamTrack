from fastapi import APIRouter
from datetime import datetime, date
from ..database import get_db
from ..models import StatusResponse

router = APIRouter(prefix="/api", tags=["status"])


@router.get("/status")
def get_status():
    conn = get_db()
    today = date.today().isoformat()

    inside = conn.execute(
        """SELECT COUNT(DISTINCT student_id) as cnt FROM (
            SELECT student_id, direction, timestamp,
                   ROW_NUMBER() OVER (PARTITION BY student_id ORDER BY timestamp DESC) as rn
            FROM gate_logs
            WHERE DATE(timestamp) = ?
        ) WHERE rn = 1 AND direction = 'entry'""",
        (today,),
    ).fetchone()["cnt"]

    today_logs = conn.execute(
        "SELECT COUNT(*) as cnt FROM gate_logs WHERE DATE(timestamp) = ?",
        (today,),
    ).fetchone()["cnt"]

    total_students = conn.execute("SELECT COUNT(*) as cnt FROM students").fetchone()["cnt"]
    total_cameras = conn.execute("SELECT COUNT(*) as cnt FROM cameras").fetchone()["cnt"]

    now = datetime.now().time()
    window_open = datetime.strptime("09:30", "%H:%M").time() <= now <= datetime.strptime("16:30", "%H:%M").time()

    conn.close()
    return StatusResponse(
        students_inside=inside,
        today_logs=today_logs,
        time_window_open=window_open,
        total_students=total_students,
        total_cameras=total_cameras,
    )
