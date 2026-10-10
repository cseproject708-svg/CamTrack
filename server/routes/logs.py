from fastapi import APIRouter
from ..database import get_db

router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.get("")
def get_gate_logs(limit: int = 100, offset: int = 0):
    conn = get_db()
    rows = conn.execute(
        """SELECT gl.id, s.name as student_name, s.roll_number,
                  c.name as camera_name, gl.direction, gl.confidence,
                  gl.is_live, gl.timestamp
           FROM gate_logs gl
           LEFT JOIN students s ON gl.student_id = s.id
           LEFT JOIN cameras c ON gl.camera_id = c.id
           ORDER BY gl.timestamp DESC
           LIMIT ? OFFSET ?""",
        (limit, offset),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.get("/today")
def get_today_logs():
    from datetime import date
    today = date.today().isoformat()
    conn = get_db()
    rows = conn.execute(
        """SELECT gl.id, s.name as student_name, s.roll_number,
                  c.name as camera_name, gl.direction, gl.confidence,
                  gl.is_live, gl.timestamp
           FROM gate_logs gl
           LEFT JOIN students s ON gl.student_id = s.id
           LEFT JOIN cameras c ON gl.camera_id = c.id
           WHERE DATE(gl.timestamp) = ?
           ORDER BY gl.timestamp DESC""",
        (today,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.get("/unknown")
def get_unknown_logs(limit: int = 50):
    conn = get_db()
    rows = conn.execute(
        """SELECT id, camera_id, confidence, snapshot_path, timestamp
           FROM unknown_logs
           ORDER BY timestamp DESC
           LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.get("/stats")
def get_log_stats():
    from datetime import date, timedelta
    today = date.today().isoformat()
    week_ago = (date.today() - timedelta(days=7)).isoformat()

    conn = get_db()

    daily = conn.execute(
        """SELECT DATE(timestamp) as day, direction, COUNT(*) as count
           FROM gate_logs
           WHERE DATE(timestamp) >= ?
           GROUP BY day, direction
           ORDER BY day""",
        (week_ago,),
    ).fetchall()

    hourly = conn.execute(
        """SELECT CAST(strftime('%H', timestamp) AS INTEGER) as hour, direction, COUNT(*) as count
           FROM gate_logs
           WHERE DATE(timestamp) = ?
           GROUP BY hour, direction
           ORDER BY hour""",
        (today,),
    ).fetchall()

    top_students = conn.execute(
        """SELECT s.name, s.roll_number, COUNT(*) as visits
           FROM gate_logs gl
           JOIN students s ON gl.student_id = s.id
           WHERE DATE(timestamp) >= ?
           GROUP BY gl.student_id
           ORDER BY visits DESC
           LIMIT 10""",
        (week_ago,),
    ).fetchall()

    conn.close()
    return {
        "daily": [dict(r) for r in daily],
        "hourly": [dict(r) for r in hourly],
        "top_students": [dict(r) for r in top_students],
    }
