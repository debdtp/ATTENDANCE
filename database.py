import sqlite3
import os
import logging
from datetime import datetime
import pandas as pd
from typing import List, Dict, Any, Optional

from config import DATABASE_PATH

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_connection():
    """Returns a connection to the SQLite database."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # Returns rows that can be accessed like dicts
    return conn

def initialize_db() -> None:
    """Initializes the database schema if it doesn't exist."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # Create students table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS students (
                    student_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    roll_number TEXT NOT NULL UNIQUE,
                    class_name TEXT NOT NULL,
                    section TEXT NOT NULL,
                    gender TEXT NOT NULL,
                    phone TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create attendance table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS attendance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    class_name TEXT NOT NULL,
                    section TEXT NOT NULL,
                    date TEXT NOT NULL,
                    time TEXT NOT NULL,
                    status TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
                    UNIQUE(student_id, date)
                )
            """)
            
            # Create unknown_log table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS unknown_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    time TEXT NOT NULL,
                    confidence REAL NOT NULL
                )
            """)
            conn.commit()
            logger.info("Database tables initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise e

def log_unknown_detection(confidence: float) -> bool:
    """Logs an unknown face detection to the database."""
    now = datetime.now()
    today_date = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M:%S")
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO unknown_log (date, time, confidence)
                VALUES (?, ?, ?)
            """, (today_date, current_time, confidence))
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Error logging unknown face: {e}")
        return False

def get_unknown_detections_today() -> int:
    """Returns the count of unknown face detections logged today."""
    today_date = datetime.now().strftime("%Y-%m-%d")
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM unknown_log WHERE date = ?", (today_date,))
            row = cursor.fetchone()
            return row["count"] if row else 0
    except Exception as e:
        logger.error(f"Error counting unknown detections: {e}")
        return 0

def add_student(student_id: str, name: str, roll_number: str, class_name: str, section: str, gender: str, phone: Optional[str] = None) -> bool:
    """Adds a new student to the database."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO students (student_id, name, roll_number, class_name, section, gender, phone)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (student_id, name, roll_number, class_name, section, gender, phone))
            conn.commit()
            logger.info(f"Student {name} (ID: {student_id}) registered successfully.")
            return True
    except sqlite3.IntegrityError as e:
        logger.warning(f"Integrity error registering student: {e}")
        return False
    except Exception as e:
        logger.error(f"Error adding student: {e}")
        return False

def update_student(student_id: str, name: str, roll_number: str, class_name: str, section: str, gender: str, phone: Optional[str] = None) -> bool:
    """Updates an existing student's details."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE students
                SET name = ?, roll_number = ?, class_name = ?, section = ?, gender = ?, phone = ?
                WHERE student_id = ?
            """, (name, roll_number, class_name, section, gender, phone, student_id))
            conn.commit()
            logger.info(f"Student ID: {student_id} updated successfully.")
            return True
    except sqlite3.IntegrityError as e:
        logger.warning(f"Integrity error updating student: {e}")
        return False
    except Exception as e:
        logger.error(f"Error updating student: {e}")
        return False

def delete_student(student_id: str) -> bool:
    """Deletes a student and their attendance history from the database."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            # SQLite does not support ON DELETE CASCADE by default unless foreign keys are enabled, 
            # so we explicitly delete attendance records first or enable PRAGMA foreign_keys = ON
            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.execute("DELETE FROM students WHERE student_id = ?", (student_id,))
            conn.commit()
            logger.info(f"Student ID: {student_id} deleted successfully.")
            return True
    except Exception as e:
        logger.error(f"Error deleting student: {e}")
        return False

def get_student(student_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a student's profile."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM students WHERE student_id = ?", (student_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    except Exception as e:
        logger.error(f"Error fetching student: {e}")
        return None

def get_all_students() -> List[Dict[str, Any]]:
    """Retrieves all registered students."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM students ORDER BY name ASC")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Error fetching all students: {e}")
        return []

def mark_attendance(student_id: str, name: str, class_name: str, section: str, confidence: float, status: str = "Present") -> bool:
    """Logs a student's attendance for today if not already logged."""
    now = datetime.now()
    today_date = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M:%S")
    
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO attendance (student_id, name, class_name, section, date, time, status, confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (student_id, name, class_name, section, today_date, current_time, status, confidence))
            conn.commit()
            logger.info(f"Attendance marked for student {name} (ID: {student_id}) on {today_date} at {current_time}.")
            return True
    except sqlite3.IntegrityError:
        # Duplicate entry for this student today
        return False
    except Exception as e:
        logger.error(f"Error logging attendance: {e}")
        return False

def get_attendance_today() -> List[Dict[str, Any]]:
    """Gets today's attendance logs."""
    today_date = datetime.now().strftime("%Y-%m-%d")
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM attendance 
                WHERE date = ? 
                ORDER BY time DESC
            """, (today_date,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Error fetching today's attendance: {e}")
        return []

def delete_attendance_record(record_id: int) -> bool:
    """Deletes an attendance log by its record ID."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM attendance WHERE id = ?", (record_id,))
            conn.commit()
            logger.info(f"Attendance record ID: {record_id} deleted successfully.")
            return True
    except Exception as e:
        logger.error(f"Error deleting attendance record: {e}")
        return False

def query_attendance_history(
    student_query: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    class_name: Optional[str] = None,
    section: Optional[str] = None
) -> pd.DataFrame:
    """Queries the attendance records and returns a Pandas DataFrame."""
    query = """
        SELECT a.id, a.student_id, a.name, a.class_name, a.section, a.date, a.time, a.status, a.confidence
        FROM attendance a
        LEFT JOIN students s ON a.student_id = s.student_id
        WHERE 1=1
    """
    params = []
    
    if student_query:
        query += " AND (a.student_id LIKE ? OR a.name LIKE ?)"
        params.append(f"%{student_query}%")
        params.append(f"%{student_query}%")
        
    if start_date:
        query += " AND a.date >= ?"
        params.append(start_date)
        
    if end_date:
        query += " AND a.date <= ?"
        params.append(end_date)
        
    if class_name and class_name != "All":
        query += " AND a.class_name = ?"
        params.append(class_name)
        
    if section and section != "All":
        query += " AND a.section = ?"
        params.append(section)
        
    query += " ORDER BY a.date DESC, a.time DESC"
    
    try:
        conn = get_connection()
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return df
    except Exception as e:
        logger.error(f"Error querying attendance history: {e}")
        return pd.DataFrame()

def clear_all_attendance_logs() -> bool:
    """Deletes all attendance records from the database."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM attendance")
            conn.commit()
            logger.info("All attendance records deleted successfully.")
            return True
    except Exception as e:
        logger.error(f"Error clearing attendance records: {e}")
        return False
