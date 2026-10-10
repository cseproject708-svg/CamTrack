from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class StudentCreate(BaseModel):
    roll_number: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    department: Optional[str] = None
    year_of_study: Optional[int] = None
    hostel_id: Optional[int] = None
    room_id: Optional[int] = None


class StudentUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    department: Optional[str] = None
    year_of_study: Optional[int] = None
    hostel_id: Optional[int] = None
    room_id: Optional[int] = None


class GateLogResponse(BaseModel):
    id: int
    student_name: str
    roll_number: str
    camera_name: str
    direction: str
    confidence: float
    is_live: bool
    timestamp: str


class RecognitionResult(BaseModel):
    name: str
    confidence: float
    is_live: bool
    direction: str
    camera_id: int
    timestamp: str


class AdminLogin(BaseModel):
    username: str
    password: str


class StatusResponse(BaseModel):
    students_inside: int
    today_logs: int
    time_window_open: bool
    total_students: int
    total_cameras: int


class ReportSummary(BaseModel):
    total_entries: int
    total_exits: int
    unique_students: int
    peak_hour: int
    avg_confidence: float
    spoof_attempts: int
