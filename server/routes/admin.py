import hashlib
import secrets

from fastapi import APIRouter
from ..database import get_db
from ..models import AdminLogin

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _hash_password(password: str, salt: str = None) -> str:
    if salt is None:
        salt = secrets.token_hex(16)
    hashed = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
    return f"{salt}${hashed}"


def _verify_password(password: str, password_hash: str) -> bool:
    salt, hashed = password_hash.split("$", 1)
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest() == hashed


@router.post("/login")
def admin_login(creds: AdminLogin):
    conn = get_db()
    user = conn.execute(
        "SELECT id, username, full_name, password_hash FROM admin_users WHERE username = ?",
        (creds.username,),
    ).fetchone()
    conn.close()
    if not user or not _verify_password(creds.password, user["password_hash"]):
        return {"success": False, "message": "Invalid credentials"}
    return {
        "success": True,
        "user": {"id": user["id"], "username": user["username"], "full_name": user["full_name"]},
    }


@router.post("/setup")
def setup_admin():
    conn = get_db()
    password_hash = _hash_password("admin123")
    try:
        conn.execute(
            "INSERT INTO admin_users (username, password_hash, full_name) VALUES (?, ?, ?)",
            ("admin", password_hash, "System Administrator"),
        )
        conn.commit()
    except Exception:
        pass
    conn.close()
    return {"detail": "Admin user ready (username: admin, password: admin123)"}
