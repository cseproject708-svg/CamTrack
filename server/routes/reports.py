from fastapi import APIRouter
from datetime import date, timedelta
from ..database import get_db

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/summary")
def get_report_summary():
    today = date.today().isoformat()
    week_ago = (date.today() - timedelta(days=7)).isoformat()
    conn = get_db()

    entries = conn.execute(
        "SELECT COUNT(*) as cnt FROM gate_logs WHERE direction = 'entry' AND DATE(timestamp) >= ?",
        (week_ago,),
    ).fetchone()["cnt"]

    exits = conn.execute(
        "SELECT COUNT(*) as cnt FROM gate_logs WHERE direction = 'exit' AND DATE(timestamp) >= ?",
        (week_ago,),
    ).fetchone()["cnt"]

    unique = conn.execute(
        "SELECT COUNT(DISTINCT student_id) as cnt FROM gate_logs WHERE DATE(timestamp) >= ?",
        (week_ago,),
    ).fetchone()["cnt"]

    peak = conn.execute(
        """SELECT CAST(strftime('%H', timestamp) AS INTEGER) as hour, COUNT(*) as cnt
           FROM gate_logs WHERE DATE(timestamp) >= ?
           GROUP BY hour ORDER BY cnt DESC LIMIT 1""",
        (week_ago,),
    ).fetchone()

    avg_conf = conn.execute(
        "SELECT AVG(confidence) as avg_conf FROM gate_logs WHERE DATE(timestamp) >= ?",
        (week_ago,),
    ).fetchone()["avg_conf"]

    spoofs = conn.execute(
        "SELECT COUNT(*) as cnt FROM gate_logs WHERE is_live = 0 AND DATE(timestamp) >= ?",
        (week_ago,),
    ).fetchone()["cnt"]

    unknowns = conn.execute(
        "SELECT COUNT(*) as cnt FROM unknown_logs WHERE DATE(timestamp) >= ?",
        (week_ago,),
    ).fetchone()["cnt"]

    conn.close()
    return {
        "total_entries": entries,
        "total_exits": exits,
        "unique_students": unique,
        "peak_hour": peak["hour"] if peak else 0,
        "avg_confidence": round(avg_conf or 0, 2),
        "spoof_attempts": spoofs + unknowns,
    }


@router.get("/daily")
def get_daily_report(days: int = 30):
    start = (date.today() - timedelta(days=days)).isoformat()
    conn = get_db()
    rows = conn.execute(
        """SELECT DATE(timestamp) as day, direction, COUNT(*) as count, AVG(confidence) as avg_conf
           FROM gate_logs
           WHERE DATE(timestamp) >= ?
           GROUP BY day, direction
           ORDER BY day""",
        (start,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.get("/student/{student_id}")
def get_student_report(student_id: int, days: int = 30):
    start = (date.today() - timedelta(days=days)).isoformat()
    conn = get_db()

    student = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    if not student:
        conn.close()
        return {"error": "Student not found"}

    logs = conn.execute(
        """SELECT gl.*, c.name as camera_name
           FROM gate_logs gl
           JOIN cameras c ON gl.camera_id = c.id
           WHERE gl.student_id = ? AND DATE(gl.timestamp) >= ?
           ORDER BY gl.timestamp""",
        (student_id, start),
    ).fetchall()

    summary = conn.execute(
        """SELECT direction, COUNT(*) as count
           FROM gate_logs
           WHERE student_id = ? AND DATE(timestamp) >= ?
           GROUP BY direction""",
        (student_id, start),
    ).fetchall()

    conn.close()
    return {
        "student": dict(student),
        "logs": [dict(r) for r in logs],
        "summary": [dict(r) for r in summary],
    }


@router.get("/camera")
def get_camera_report():
    conn = get_db()
    rows = conn.execute(
        """SELECT c.name, c.location, COUNT(gl.id) as total_events,
                  SUM(CASE WHEN gl.direction = 'entry' THEN 1 ELSE 0 END) as entries,
                  SUM(CASE WHEN gl.direction = 'exit' THEN 1 ELSE 0 END) as exits,
                  AVG(gl.confidence) as avg_confidence
           FROM cameras c
           LEFT JOIN gate_logs gl ON c.id = gl.camera_id
           GROUP BY c.id
           ORDER BY total_events DESC"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
