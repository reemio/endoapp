import sqlite3
from pathlib import Path


class Database:
    def __init__(self):
        self.db_path = Path("data/database/endoscopy.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_database()

    def init_database(self):
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()

            # Create patients table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS patients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_id TEXT UNIQUE,
                    name TEXT,
                    gender TEXT,
                    age INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Create reports table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_id TEXT,
                    report_date TIMESTAMP,
                    hospital_name TEXT,
                    referring_doctor TEXT,
                    findings TEXT,
                    conclusions TEXT,
                    recommendations TEXT,
                    FOREIGN KEY (patient_id) REFERENCES patients (patient_id)
                )
            """
            )

            conn.commit()
